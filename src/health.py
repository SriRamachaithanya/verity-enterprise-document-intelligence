from datetime import UTC, datetime

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


def create_health_app() -> FastAPI:
    app = FastAPI(title="Verity Healthcheck")

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health_check():
        return {
            "status": "healthy",
            "service": "verity-backend",
            "version": "0.1.0",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return app
