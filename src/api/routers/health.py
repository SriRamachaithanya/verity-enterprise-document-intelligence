import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from src.api.config import get_api_config
from src.api.dependencies import get_db, get_vector_store
from src.api.schemas.common import ComponentHealth, HealthResponse, ReadinessResponse
from src.storage.db import DatabaseManager
from src.storage.faiss_store import FAISSVectorStore

router = APIRouter(tags=["Health & Diagnostics"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Probe",
    description="Fast non-blocking healthcheck verifying the HTTP application is alive.",
)
@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    include_in_schema=False,
)
def liveness_check() -> HealthResponse:
    config = get_api_config()
    return HealthResponse(
        status="healthy",
        service=config.app_name,
        version=config.version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Comprehensive readiness check querying SQLite database, FAISS vector index, and Ollama reachability.",
)
async def readiness_check(
    db: Annotated[DatabaseManager, Depends(get_db)],
    vector_store: Annotated[FAISSVectorStore, Depends(get_vector_store)],
) -> ReadinessResponse:
    config = get_api_config()
    components: dict[str, ComponentHealth] = {}
    is_ready = True

    # 1. SQLite Database check
    t0 = time.perf_counter()
    try:
        conn = db.get_connection()
        with conn:
            row = conn.execute("SELECT 1").fetchone()
            db_ok = row is not None and row[0] == 1
        lat_db = (time.perf_counter() - t0) * 1000.0
        components["sqlite"] = ComponentHealth(
            status="healthy" if db_ok else "unhealthy",
            latency_ms=round(lat_db, 2),
            details={"path": str(config.db_path.name)},
        )
        if not db_ok:
            is_ready = False
    except Exception as e:  # noqa: BLE001
        lat_db = (time.perf_counter() - t0) * 1000.0
        components["sqlite"] = ComponentHealth(
            status="unhealthy",
            latency_ms=round(lat_db, 2),
            details={"error": str(e)},
        )
        is_ready = False

    # 2. FAISS Vector Store check
    t0 = time.perf_counter()
    try:
        total_vectors = vector_store.get_total_vectors()
        lat_faiss = (time.perf_counter() - t0) * 1000.0
        components["faiss"] = ComponentHealth(
            status="healthy",
            latency_ms=round(lat_faiss, 2),
            details={"indexed_vectors": total_vectors},
        )
    except Exception as e:  # noqa: BLE001
        lat_faiss = (time.perf_counter() - t0) * 1000.0
        components["faiss"] = ComponentHealth(
            status="unhealthy",
            latency_ms=round(lat_faiss, 2),
            details={"error": str(e)},
        )
        is_ready = False

    # 3. Ollama LLM reachability check (non-blocking degraded fallback)
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{config.ollama_base_url}/api/tags")
            lat_ollama = (time.perf_counter() - t0) * 1000.0
            if resp.status_code == 200:
                components["ollama"] = ComponentHealth(
                    status="healthy",
                    latency_ms=round(lat_ollama, 2),
                    details={"reachability": "connected"},
                )
            else:
                components["ollama"] = ComponentHealth(
                    status="degraded",
                    latency_ms=round(lat_ollama, 2),
                    details={"status_code": resp.status_code, "fallback": "active"},
                )
    except Exception:  # noqa: BLE001
        lat_ollama = (time.perf_counter() - t0) * 1000.0
        components["ollama"] = ComponentHealth(
            status="degraded",
            latency_ms=round(lat_ollama, 2),
            details={"reachability": "offline", "deterministic_fallback": "operational"},
        )

    return ReadinessResponse(
        status="ready" if is_ready else "degraded",
        components=components,
    )
