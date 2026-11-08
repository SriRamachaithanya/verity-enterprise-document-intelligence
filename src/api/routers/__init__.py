from src.api.routers.chat import router as chat_router
from src.api.routers.compliance import router as compliance_router
from src.api.routers.documents import router as documents_router
from src.api.routers.health import router as health_router
from src.api.routers.knowledge import router as knowledge_router
from src.api.routers.search import router as search_router

__all__ = [
    "chat_router",
    "compliance_router",
    "documents_router",
    "health_router",
    "knowledge_router",
    "search_router",
]

