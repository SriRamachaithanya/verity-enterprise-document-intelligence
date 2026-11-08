import json
import logging
import os
from pathlib import Path
from threading import RLock

import faiss
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_FAISS_DIR = Path(os.getenv("VERITY_FAISS_DIR", "data/faiss"))
INDEX_FILENAME = "index.faiss"
MAPPING_FILENAME = "id_mapping.json"
EMBEDDING_DIM = 384


class FAISSVectorStore:
    """
    Manages persistent CPU-only FAISS IndexFlatIP (cosine similarity on normalized vectors).
    Maintains an explicit, stable bidirectional mapping between FAISS vector integer positions
    and application chunk string IDs.
    """

    def __init__(self, index_dir: Path | str = DEFAULT_FAISS_DIR):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / INDEX_FILENAME
        self.mapping_path = self.index_dir / MAPPING_FILENAME

        self._lock = RLock()
        self.index: faiss.IndexFlatIP | None = None
        # Bi-directional mappings:
        # vector_id (int) -> chunk_id (str)
        self.id_to_chunk: dict[int, str] = {}
        # chunk_id (str) -> vector_id (int)
        self.chunk_to_id: dict[str, int] = {}

        self.load_or_create()

    def load_or_create(self) -> None:
        """Load existing index from disk or create a fresh IndexFlatIP."""
        with self._lock:
            if self.index_path.is_file() and self.mapping_path.is_file():
                try:
                    logger.info("Loading existing FAISS index from %s", self.index_path)
                    self.index = faiss.read_index(str(self.index_path))
                    with open(self.mapping_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # JSON keys are strings, convert back to int
                        self.id_to_chunk = {int(k): v for k, v in data.items()}
                        self.chunk_to_id = {v: int(k) for k, v in data.items()}

                    if self.index.ntotal != len(self.id_to_chunk):
                        logger.warning(
                            "FAISS count (%d) mismatch with mapping count (%d).",
                            self.index.ntotal,
                            len(self.id_to_chunk),
                        )
                    logger.info("FAISS index loaded with %d vectors.", self.index.ntotal)
                    return
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to load FAISS index: %s. Creating fresh index.", e)

            # Create fresh Flat Inner Product index (equivalent to cosine similarity for normalized vectors)
            self._create_empty_index()

    def _create_empty_index(self) -> None:
        """Initialize a new empty IndexFlatIP."""
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.id_to_chunk = {}
        self.chunk_to_id = {}
        logger.info("Created new empty FAISS IndexFlatIP (dim=%d).", EMBEDDING_DIM)

    def save(self) -> None:
        """Safely persist FAISS index and mapping to disk using atomic rename."""
        with self._lock:
            if self.index is None:
                return

            temp_index = self.index_path.with_suffix(".tmp")
            temp_mapping = self.mapping_path.with_suffix(".tmp")

            faiss.write_index(self.index, str(temp_index))
            with open(temp_mapping, "w", encoding="utf-8") as f:
                json.dump(self.id_to_chunk, f, indent=2)

            # Atomic replace
            if temp_index.exists():
                temp_index.replace(self.index_path)
            if temp_mapping.exists():
                temp_mapping.replace(self.mapping_path)

            logger.info("Persisted FAISS index (%d vectors) to disk.", self.index.ntotal)

    def add_vectors(
        self,
        chunk_ids: list[str],
        vectors: np.ndarray,
    ) -> list[int]:
        """
        Add normalized vectors to the FAISS index.
        Returns list of newly assigned FAISS integer vector IDs.
        """
        if len(chunk_ids) == 0:
            return []

        if len(chunk_ids) != len(vectors):
            raise ValueError(
                f"Mismatch between chunk_ids count ({len(chunk_ids)}) and vectors count ({len(vectors)})"
            )

        vectors = vectors.astype(np.float32)

        with self._lock:
            start_id = self.index.ntotal
            assigned_ids: list[int] = []

            for offset, chunk_id in enumerate(chunk_ids):
                vid = start_id + offset
                assigned_ids.append(vid)
                self.id_to_chunk[vid] = chunk_id
                self.chunk_to_id[chunk_id] = vid

            self.index.add(vectors)
            self.save()
            return assigned_ids

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """
        Search top_k nearest neighbors by cosine similarity.
        Returns list of (chunk_id, similarity_score).
        """
        with self._lock:
            if self.index is None or self.index.ntotal == 0:
                return []

            query_2d = query_vector.reshape(1, -1).astype(np.float32)
            actual_k = min(top_k, self.index.ntotal)

            scores, indices = self.index.search(query_2d, actual_k)
            results: list[tuple[str, float]] = []

            for score, vid in zip(scores[0], indices[0]):
                if vid == -1:
                    continue
                chunk_id = self.id_to_chunk.get(int(vid))
                if chunk_id:
                    results.append((chunk_id, float(score)))

            return results

    def get_total_vectors(self) -> int:
        """Return total vectors in the index."""
        with self._lock:
            return self.index.ntotal if self.index else 0

    def rebuild_index(
        self,
        chunk_ids: list[str],
        vectors: np.ndarray,
    ) -> None:
        """
        Completely reset and rebuild the FAISS index from clean data.
        Essential for index recovery and after document deletions.
        """
        with self._lock:
            logger.info("Rebuilding FAISS index from scratch with %d vectors...", len(chunk_ids))
            self._create_empty_index()
            if len(chunk_ids) > 0:
                vectors = vectors.astype(np.float32)
                for vid, cid in enumerate(chunk_ids):
                    self.id_to_chunk[vid] = cid
                    self.chunk_to_id[cid] = vid
                self.index.add(vectors)
            self.save()
            logger.info("FAISS index rebuild complete (%d vectors).", self.index.ntotal)
