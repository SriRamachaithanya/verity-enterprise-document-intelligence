from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Liveness status")
    service: str = Field(default="verity-api", description="Service identifier")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ComponentHealth(BaseModel):
    status: str = Field(description="'healthy', 'degraded', or 'unhealthy'")
    latency_ms: float = Field(default=0.0, description="Diagnostic check latency in ms")
    details: dict[str, Any] = Field(default_factory=dict, description="Component-specific telemetry")


class ReadinessResponse(BaseModel):
    status: str = Field(description="'ready' or 'degraded'")
    components: dict[str, ComponentHealth] = Field(description="Subsystem health statuses")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable safe error message")
    field: str | None = Field(default=None, description="Request field that caused validation error")


class ErrorResponse(BaseModel):
    error: ErrorDetail = Field(description="Error details payload")
    request_id: str = Field(description="Unique correlation ID for tracing")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
