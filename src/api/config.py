import os
from pathlib import Path

from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """
    Central configuration for VERITY FastAPI application.
    Supports environment variable overrides.
    """

    app_name: str = Field(default="VERITY Enterprise Intelligence & Compliance API")
    version: str = Field(default="1.0.0")
    environment: str = Field(default="production")
    debug: bool = Field(default=False)

    # Server settings
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    # Storage paths
    db_path: Path = Field(default=Path("data/sqlite/verity.db"))
    faiss_dir: Path = Field(default=Path("data/faiss"))
    upload_dir: Path = Field(default=Path("data/uploads"))
    quarantine_dir: Path = Field(default=Path("data/quarantine"))

    # Security & Upload constraints
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024)  # 25 MB
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".txt"])
    allowed_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ]
    )

    # Auth & RBAC
    auth_disabled: bool = Field(default=False)
    api_key_header_name: str = Field(default="X-API-Key")
    admin_api_key: str = Field(default="verity-admin-secret-key")
    auditor_api_key: str = Field(default="verity-auditor-secret-key")
    user_api_key: str = Field(default="verity-user-secret-key")

    # Concurrency and Performance bounds
    max_concurrent_agent_requests: int = Field(default=2)
    agent_timeout_seconds: float = Field(default=35.0)
    ollama_base_url: str = Field(default="http://localhost:11434")

    # CORS settings
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    )

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Construct config from environment variables with sensible defaults."""
        return cls(
            app_name=os.getenv("VERITY_APP_NAME", "VERITY Enterprise Intelligence & Compliance API"),
            version=os.getenv("VERITY_APP_VERSION", "1.0.0"),
            environment=os.getenv("VERITY_ENV", "production"),
            debug=os.getenv("VERITY_DEBUG", "false").lower() in ("true", "1", "yes"),
            host=os.getenv("VERITY_HOST", "127.0.0.1"),
            port=int(os.getenv("VERITY_PORT", "8000")),
            db_path=Path(os.getenv("VERITY_DB_PATH", "data/sqlite/verity.db")),
            faiss_dir=Path(os.getenv("VERITY_FAISS_DIR", "data/faiss")),
            upload_dir=Path(os.getenv("VERITY_UPLOAD_DIR", "data/uploads")),
            quarantine_dir=Path(os.getenv("VERITY_QUARANTINE_DIR", "data/quarantine")),
            max_upload_size_bytes=int(os.getenv("VERITY_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))),
            auth_disabled=os.getenv("VERITY_AUTH_DISABLED", "false").lower() in ("true", "1", "yes"),
            admin_api_key=os.getenv("VERITY_ADMIN_API_KEY", "verity-admin-secret-key"),
            auditor_api_key=os.getenv("VERITY_AUDITOR_API_KEY", "verity-auditor-secret-key"),
            user_api_key=os.getenv("VERITY_USER_API_KEY", "verity-user-secret-key"),
            max_concurrent_agent_requests=int(os.getenv("VERITY_MAX_CONCURRENT_AGENT", "2")),
            agent_timeout_seconds=float(os.getenv("VERITY_AGENT_TIMEOUT", "35.0")),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )


_config: APIConfig | None = None


def get_api_config() -> APIConfig:
    global _config
    if _config is None:
        _config = APIConfig.from_env()
    return _config


def set_api_config(config: APIConfig | None) -> None:
    global _config
    _config = config
