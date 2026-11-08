import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from src.indexing.chunker import DocumentChunker
from src.indexing.embedding_service import EmbeddingService
from src.parsers import get_parser_for_file
from src.parsers.base import BaseDocumentParser
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_DIR = Path("data/uploads")


class IngestionPipeline:
    """
    Orchestrates secure document ingestion:
    1. Pre-ingestion SHA-256 deduplication check.
    2. Parsing and extraction with validation.
    3. Sentence-boundary chunking.
    4. Dense vector embedding generation.
    5. Atomic storage in SQLite, FTS5, and FAISS with staging and rollback.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
        upload_dir: Path | str = DEFAULT_UPLOAD_DIR,
    ):
        self.db = db_manager
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = DocumentChunker()

    def ingest_document(
        self,
        source_path: Path | str,
        custom_metadata: dict[str, Any] | None = None,
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Ingest a single document.
        Returns document information and ingestion status.
        """
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source file not found: {src}")

        # 1. SHA-256 Deduplication check BEFORE heavy processing
        file_hash = BaseDocumentParser.calculate_sha256(src)
        existing_doc = self.db.get_document_by_hash(file_hash)

        if existing_doc:
            logger.info(
                "Document '%s' already ingested (hash: %s). Returning existing record.",
                src.name,
                file_hash,
            )
            chunks = self.db.get_chunks_for_document(existing_doc["id"])
            return {
                "status": "already_exists",
                "document": existing_doc,
                "chunks_count": len(chunks),
                "message": "Duplicate document detected by SHA-256 digest. Existing record returned.",
            }

        # 2. Parse document with appropriate format extractor
        parser = get_parser_for_file(src)
        extracted = parser.parse(src)
        if original_filename:
            extracted.metadata.filename = original_filename

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        staged_filepath = self.upload_dir / f"{file_hash}{src.suffix.lower()}"

        # 3. Chunk document into semantic sections
        chunks = self.chunker.chunk_document(extracted, doc_id)
        if not chunks:
            raise ValueError(f"No textual content could be extracted from {src.name}")

        # 4. Generate dense embeddings for all chunks in bounded batches
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts, batch_size=16)

        # 5. Atomic persistence with staging and rollback
        staged_copy_done = False
        try:
            # Stage file to permanent content-addressed storage
            if not staged_filepath.exists():
                shutil.copy2(src, staged_filepath)
                staged_copy_done = True

            # Insert document into SQLite
            doc_record = self.db.insert_document(
                doc_id=doc_id,
                meta=extracted.metadata,
                filepath=str(staged_filepath),
                extra_metadata=custom_metadata,
            )

            # Insert chunks into SQLite (triggers FTS5 automatically)
            self.db.insert_chunks(chunks)

            # Add vectors to FAISS and record assigned vector IDs
            chunk_ids = [c.id for c in chunks]
            assigned_faiss_ids = self.vector_store.add_vectors(chunk_ids, embeddings)

            # Update faiss_index_id on chunks in SQLite
            for cid, fid in zip(chunk_ids, assigned_faiss_ids):
                self.db.update_chunk_faiss_id(cid, fid)

            logger.info(
                "Successfully ingested '%s' (%s): %d chunks indexed in SQLite & FAISS.",
                src.name,
                doc_id,
                len(chunks),
            )

            return {
                "status": "ingested",
                "document": doc_record,
                "chunks_count": len(chunks),
                "message": f"Successfully indexed {len(chunks)} chunks.",
            }

        except Exception as e:
            logger.error("Ingestion failed for '%s'. Rolling back: %s", src.name, e)
            # Rollback: Clean up SQLite records
            try:
                self.db.delete_document(doc_id)
            except Exception as rollback_err:  # noqa: BLE001
                logger.error("Error during DB rollback: %s", rollback_err)

            # Clean up staged file if newly created
            if staged_copy_done and staged_filepath.exists():
                try:
                    staged_filepath.unlink()
                except Exception as file_err:  # noqa: BLE001
                    logger.error("Error removing staged file: %s", file_err)

            raise RuntimeError(f"Ingestion transaction failed: {e}") from e

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document, cascade chunks/FTS, and rebuild FAISS index cleanly.
        """
        doc = self.db.get_document_by_id(document_id)
        if not doc:
            return False

        # Delete from SQLite (cascades to chunks and FTS5)
        success = self.db.delete_document(document_id)
        if not success:
            return False

        # Clean up storage file
        filepath = Path(doc["filepath"])
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not delete file %s: %s", filepath, e)

        # Rebuild FAISS index from remaining chunks in DB
        self.rebuild_vector_index()
        return True

    def rebuild_vector_index(self) -> int:
        """
        Rebuild the FAISS vector index from all active chunks in the SQLite database.
        Guarantees 100% consistency if index is corrupted or after deletions.
        """
        all_chunks = self.db.get_all_chunks_with_documents()
        if not all_chunks:
            self.vector_store.rebuild_index([], np.empty((0, 384), dtype=np.float32))
            return 0

        chunk_ids = [c["chunk_id"] for c in all_chunks]
        contents = [c["content"] for c in all_chunks]

        embeddings = self.embedding_service.embed_texts(contents, batch_size=16)
        self.vector_store.rebuild_index(chunk_ids, embeddings)

        # Synchronize updated FAISS IDs back to SQLite
        for vid, cid in enumerate(chunk_ids):
            self.db.update_chunk_faiss_id(cid, vid)

        logger.info("Rebuilt FAISS index for %d active chunks.", len(chunk_ids))
        return len(chunk_ids)
