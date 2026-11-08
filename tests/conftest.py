import pytest

from src.indexing.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture(scope="session")
def session_embedding_service() -> EmbeddingService:
    """
    Session-scoped embedding service fixture.
    Ensures all-MiniLM-L6-v2 is loaded exactly once for the entire test session.
    """
    return get_embedding_service()
