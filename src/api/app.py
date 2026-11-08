import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import APIConfig, get_api_config
from src.api.dependencies import get_db, get_vector_store, reset_api_dependencies
from src.api.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_exception_handlers,
)
from src.api.routers import (
    chat_router,
    compliance_router,
    documents_router,
    health_router,
    knowledge_router,
    search_router,
)

logger = logging.getLogger("verity.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager executing safe startup diagnostics
    and graceful shutdown state preservation.
    """
    config = get_api_config()
    logger.info("Initializing %s v%s...", config.app_name, config.version)

    # 1. Ensure storage directories exist
    config.upload_dir.mkdir(parents=True, exist_ok=True)
    config.quarantine_dir.mkdir(parents=True, exist_ok=True)
    config.faiss_dir.mkdir(parents=True, exist_ok=True)

    # 2. Initialize database schema & baseline frameworks
    try:
        from src.storage.seed_data import seed_baseline_data_if_empty

        db = get_db()
        db.initialize_schema()
        seed_baseline_data_if_empty(db)
        logger.info("Database schema initialized and verified with baseline frameworks.")
    except Exception as e:  # noqa: BLE001
        logger.error("Database initialization warning: %s", e)

    # 3. Verify FAISS index
    try:
        store = get_vector_store()
        logger.info("FAISS vector store ready with %d vectors.", store.get_total_vectors())
    except Exception as e:  # noqa: BLE001
        logger.warning("FAISS vector store warning: %s", e)

    yield

    # Shutdown sequence
    logger.info("Initiating graceful shutdown...")
    try:
        store = get_vector_store()
        store.save()
        logger.info("FAISS vector index saved to disk.")
    except Exception as err:  # noqa: BLE001
        logger.warning("Error saving FAISS store during shutdown: %s", err)

    reset_api_dependencies()
    logger.info("VERITY API shutdown complete.")


def create_app(config: APIConfig | None = None) -> FastAPI:
    """
    Application factory constructing a fully configured FastAPI application.
    """
    cfg = config or get_api_config()

    docs_enabled = cfg.debug or cfg.environment != "production"
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.version,
        description=(
            "Enterprise Document Intelligence & Compliance Agent API. "
            "Delivers verifiable evidence grounding, zero-trust compliance evaluation, "
            "Obsidian-style knowledge graph discovery, and hybrid semantic retrieval."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        lifespan=lifespan,
    )

    # 1. Centralized exception handlers (prevents stack trace leakage)
    setup_exception_handlers(app)

    # 2. Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. Request Logging & Tracing Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 4. Enterprise CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-MS"],
    )

    # 5. Include API Routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(compliance_router)
    app.include_router(knowledge_router)

    return app
