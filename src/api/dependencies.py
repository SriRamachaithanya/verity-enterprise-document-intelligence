import asyncio
import logging
from threading import RLock

from src.agent.orchestrator import AgentOrchestrator
from src.api.config import get_api_config
from src.compliance.engine import ComplianceIntelligenceEngine
from src.indexing.embedding_service import EmbeddingService, get_embedding_service
from src.indexing.hybrid_search import HybridSearchEngine
from src.indexing.ingestion_pipeline import IngestionPipeline
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
_ingestion_pipeline: IngestionPipeline | None = None
_agent_orchestrator: AgentOrchestrator | None = None
_agent_semaphore: asyncio.Semaphore | None = None


def get_db() -> DatabaseManager:
    """Retrieve singleton DatabaseManager."""
    global _db
    with _lock:
        if _db is None:
            config = get_api_config()
            _db = DatabaseManager(db_path=config.db_path)
        return _db


def get_vector_store() -> FAISSVectorStore:
    """Retrieve singleton FAISSVectorStore."""
    global _vector_store
    with _lock:
        if _vector_store is None:
            config = get_api_config()
            _vector_store = FAISSVectorStore(index_dir=config.faiss_dir)
        return _vector_store


def get_embed_service() -> EmbeddingService:
    """Retrieve singleton EmbeddingService."""
    global _embedding_service
    with _lock:
        if _embedding_service is None:
            _embedding_service = get_embedding_service()
        return _embedding_service


def get_hybrid_search() -> HybridSearchEngine:
    """Retrieve singleton HybridSearchEngine."""
    global _hybrid_search
    with _lock:
        if _hybrid_search is None:
            _hybrid_search = HybridSearchEngine(
                db_manager=get_db(),
                vector_store=get_vector_store(),
                embedding_service=get_embed_service(),
            )
        return _hybrid_search


def get_compliance_engine() -> ComplianceIntelligenceEngine:
    """Retrieve singleton ComplianceIntelligenceEngine."""
    global _compliance_engine
    with _lock:
        if _compliance_engine is None:
            _compliance_engine = ComplianceIntelligenceEngine(
                db=get_db(),
                hybrid_engine=get_hybrid_search(),
            )
        return _compliance_engine


def get_knowledge_service() -> KnowledgeGraphService:
    """Retrieve singleton KnowledgeGraphService."""
    global _knowledge_service
    with _lock:
        if _knowledge_service is None:
            _knowledge_service = KnowledgeGraphService(db=get_db())
        return _knowledge_service


def get_ingestion_pipeline() -> IngestionPipeline:
    """Retrieve singleton IngestionPipeline."""
    global _ingestion_pipeline
    with _lock:
        if _ingestion_pipeline is None:
            config = get_api_config()
            _ingestion_pipeline = IngestionPipeline(
                db_manager=get_db(),
                vector_store=get_vector_store(),
                embedding_service=get_embed_service(),
                upload_dir=config.upload_dir,
            )
        return _ingestion_pipeline


def get_agent_orchestrator() -> AgentOrchestrator:
    """Retrieve singleton AgentOrchestrator."""
    global _agent_orchestrator
    with _lock:
        if _agent_orchestrator is None:
            config = get_api_config()
            env = {
                "SQLITE_DB_PATH": str(config.db_path),
                "VERITY_DB_PATH": str(config.db_path),
                "FAISS_DIR": str(config.faiss_dir),
                "VERITY_FAISS_DIR": str(config.faiss_dir),
            }
            _agent_orchestrator = AgentOrchestrator(
                db_manager=get_db(),
                env=env,
            )
        return _agent_orchestrator


def get_agent_semaphore() -> asyncio.Semaphore:
    """Bounded concurrency semaphore for CPU-friendly inference."""
    global _agent_semaphore
    if _agent_semaphore is None:
        config = get_api_config()
        _agent_semaphore = asyncio.Semaphore(config.max_concurrent_agent_requests)
    return _agent_semaphore


def set_api_dependencies(
    db: DatabaseManager | None = None,
    vector_store: FAISSVectorStore | None = None,
    embedding_service: EmbeddingService | None = None,
    hybrid_search: HybridSearchEngine | None = None,
    compliance_engine: ComplianceIntelligenceEngine | None = None,
    knowledge_service: KnowledgeGraphService | None = None,
    ingestion_pipeline: IngestionPipeline | None = None,
    agent_orchestrator: AgentOrchestrator | None = None,
) -> None:
    """Explicitly inject dependencies (for isolated unit/integration tests)."""
    global _db, _vector_store, _embedding_service, _hybrid_search
    global _compliance_engine, _knowledge_service, _ingestion_pipeline, _agent_orchestrator
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
                embedding_service=get_embed_service(),
            )
        _compliance_engine = compliance_engine
        _knowledge_service = knowledge_service
        _ingestion_pipeline = ingestion_pipeline
        _agent_orchestrator = agent_orchestrator


def reset_api_dependencies() -> None:
    """Reset singletons for fresh state."""
    global _db, _vector_store, _embedding_service, _hybrid_search
    global _compliance_engine, _knowledge_service, _ingestion_pipeline, _agent_orchestrator, _agent_semaphore
    with _lock:
        _db = None
        _vector_store = None
        _embedding_service = None
        _hybrid_search = None
        _compliance_engine = None
        _knowledge_service = None
        _ingestion_pipeline = None
        _agent_orchestrator = None
        _agent_semaphore = None

