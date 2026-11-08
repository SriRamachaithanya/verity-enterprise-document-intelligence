import logging
from threading import RLock
from typing import Any

from src.compliance.engine import ComplianceIntelligenceEngine
from src.indexing.embedding_service import EmbeddingService
from src.indexing.hybrid_search import HybridSearchEngine
from src.knowledge.graph_service import KnowledgeGraphService
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)

_lock = RLock()
_db: DatabaseManager | None = None
_vector_store: FAISSVectorStore | None = None
_embedding_service: EmbeddingService | None = None
_hybrid_search: HybridSearchEngine | None = None
_compliance_engine: ComplianceIntelligenceEngine | None = None
_knowledge_service: KnowledgeGraphService | None = None


def get_db() -> DatabaseManager:
    """Retrieve or initialize singleton DatabaseManager."""
    global _db
    with _lock:
        if _db is None:
            _db = DatabaseManager()
        return _db


def get_vector_store() -> FAISSVectorStore:
    """Retrieve or initialize singleton FAISSVectorStore."""
    global _vector_store
    with _lock:
        if _vector_store is None:
            _vector_store = FAISSVectorStore()
        return _vector_store


def get_embedding_service() -> EmbeddingService:
    """Retrieve or initialize singleton EmbeddingService."""
    global _embedding_service
    with _lock:
        if _embedding_service is None:
            _embedding_service = EmbeddingService()
        return _embedding_service


def get_hybrid_search() -> HybridSearchEngine:
    """Retrieve or initialize singleton HybridSearchEngine."""
    global _hybrid_search
    with _lock:
        if _hybrid_search is None:
            _hybrid_search = HybridSearchEngine(
                db_manager=get_db(),
                vector_store=get_vector_store(),
                embedding_service=get_embedding_service(),
            )
        return _hybrid_search


def get_compliance_engine() -> ComplianceIntelligenceEngine:
    """Retrieve or initialize singleton ComplianceIntelligenceEngine."""
    global _compliance_engine
    with _lock:
        if _compliance_engine is None:
            _compliance_engine = ComplianceIntelligenceEngine(
                db=get_db(),
                hybrid_engine=get_hybrid_search(),
            )
        return _compliance_engine


def get_knowledge_service() -> KnowledgeGraphService:
    """Retrieve or initialize singleton KnowledgeGraphService."""
    global _knowledge_service
    with _lock:
        if _knowledge_service is None:
            _knowledge_service = KnowledgeGraphService(db=get_db())
        return _knowledge_service


def set_dependencies(
    db: DatabaseManager | None = None,
    vector_store: FAISSVectorStore | None = None,
    embedding_service: EmbeddingService | None = None,
    hybrid_search: HybridSearchEngine | None = None,
    compliance_engine: ComplianceIntelligenceEngine | None = None,
    knowledge_service: KnowledgeGraphService | None = None,
) -> None:
    """Explicitly inject dependencies (useful for isolated tests)."""
    global _db, _vector_store, _embedding_service, _hybrid_search, _compliance_engine, _knowledge_service
    with _lock:
        if db is not None:
            _db = db
        if vector_store is not None:
            _vector_store = vector_store
        if embedding_service is not None:
            _embedding_service = embedding_service
        if hybrid_search is not None:
            _hybrid_search = hybrid_search
        elif db is not None or vector_store is not None or embedding_service is not None:
            _hybrid_search = HybridSearchEngine(
                db_manager=get_db(),
                vector_store=get_vector_store(),
                embedding_service=get_embedding_service(),
            )
        _compliance_engine = compliance_engine
        _knowledge_service = knowledge_service


def cleanup_dependencies() -> dict[str, Any]:
    """Clean up and reset dependencies on server shutdown."""
    global _db, _vector_store, _embedding_service, _hybrid_search, _compliance_engine, _knowledge_service
    with _lock:
        status: dict[str, Any] = {"reset": True}
        if _vector_store is not None:
            try:
                _vector_store.save()
                status["vector_store_saved"] = True
            except Exception as e:  # noqa: BLE001
                status["vector_store_save_error"] = str(e)
        _db = None
        _vector_store = None
        _embedding_service = None
        _hybrid_search = None
        _compliance_engine = None
        _knowledge_service = None
        return status

