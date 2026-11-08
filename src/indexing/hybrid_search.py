import logging

from src.indexing.embedding_service import EmbeddingService
from src.schemas.document import SearchResult
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)

RRF_K_CONSTANT = 60


class HybridSearchEngine:
    """
    Combines dense semantic vector search (FAISS) and lexical BM25 search (SQLite FTS5)
    using Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
    ):
        self.db = db_manager
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        candidate_multiplier: int = 4,
    ) -> list[SearchResult]:
        """
        Execute hybrid search:
        1. Dense semantic search via FAISS.
        2. Lexical keyword search via SQLite FTS5 (BM25).
        3. Reciprocal Rank Fusion (RRF) to merge candidate rankings.
        """
        query_text = query.strip()
        if not query_text:
            return []

        # Request larger candidate pools for robust RRF ranking
        pool_size = max(top_k * candidate_multiplier, 20)

        # ---------------------------------------------------------------------
        # 1. Dense Semantic Retrieval (FAISS)
        # ---------------------------------------------------------------------
        dense_ranks: dict[str, int] = {}
        query_vector = self.embedding_service.embed_query(query_text)
        raw_dense_results = self.vector_store.search(query_vector, top_k=pool_size)

        rank_counter = 1
        for chunk_id, _score in raw_dense_results:
            # If document filter applied, check chunk ownership
            if document_id:
                chunk_meta = self.db.get_chunk_by_id(chunk_id)
                if not chunk_meta or chunk_meta["document_id"] != document_id:
                    continue
            dense_ranks[chunk_id] = rank_counter
            rank_counter += 1

        # ---------------------------------------------------------------------
        # 2. Lexical Retrieval (SQLite FTS5 BM25)
        # ---------------------------------------------------------------------
        lexical_ranks: dict[str, int] = {}
        raw_lexical_results = self.db.lexical_search(
            query_text=query_text,
            limit=pool_size,
            document_id=document_id,
        )

        for idx, row in enumerate(raw_lexical_results):
            # One-based rank
            lexical_ranks[row["chunk_id"]] = idx + 1

        # ---------------------------------------------------------------------
        # 3. Reciprocal Rank Fusion (RRF)
        # Formula: RRF(d) = sum( 1 / (60 + rank_m(d)) )
        # ---------------------------------------------------------------------
        all_chunk_ids = set(dense_ranks.keys()).union(set(lexical_ranks.keys()))
        if not all_chunk_ids:
            return []

        rrf_scores: dict[str, float] = {}
        for cid in all_chunk_ids:
            score = 0.0
            if cid in dense_ranks:
                score += 1.0 / (RRF_K_CONSTANT + dense_ranks[cid])
            if cid in lexical_ranks:
                score += 1.0 / (RRF_K_CONSTANT + lexical_ranks[cid])
            rrf_scores[cid] = score

        # Sort candidate chunk IDs by descending RRF score
        sorted_chunk_ids = sorted(
            all_chunk_ids,
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )[:top_k]

        # ---------------------------------------------------------------------
        # 4. Hydrate Metadata & Return SearchResults
        # ---------------------------------------------------------------------
        results: list[SearchResult] = []
        for cid in sorted_chunk_ids:
            chunk_data = self.db.get_chunk_by_id(cid)
            if not chunk_data:
                continue

            results.append(
                SearchResult(
                    chunk_id=cid,
                    document_id=chunk_data["document_id"],
                    document_name=chunk_data.get("document_name", "Unknown"),
                    page_number=chunk_data.get("page_number"),
                    section_heading=chunk_data.get("section_heading", "General"),
                    locator=chunk_data.get("locator", ""),
                    content=chunk_data["content"],
                    rrf_score=round(rrf_scores[cid], 5),
                    dense_rank=dense_ranks.get(cid),
                    lexical_rank=lexical_ranks.get(cid),
                )
            )

        return results
