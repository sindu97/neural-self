"""Centralized application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "NeuralShelf"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: SecretStr = SecretStr(
        "postgresql://neuralshelf:neuralshelf_local_dev@localhost:5433/neuralshelf"
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3.5:2b-q4_K_M"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)
    # nomic-embed-text expects task prefixes; set both to "" for other models.
    embedding_document_prefix: str = "search_document: "
    embedding_query_prefix: str = "search_query: "

    log_level: str = Field(default="INFO")
    log_format: Literal["text", "json"] = "text"

    # Browser origins allowed to call the API, e.g. the web app's dev server.
    # Comma-separated in .env: CORS_ORIGINS=http://localhost:3000,http://localhost:5173
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    # Rate limits: max requests per window, per client IP (and per email for login).
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_login_per_ip: int = Field(default=20, ge=1)
    rate_limit_login_per_email: int = Field(default=5, ge=1)
    rate_limit_signup_per_ip: int = Field(default=5, ge=1)
    rate_limit_refresh_per_ip: int = Field(default=30, ge=1)

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Web clients get the refresh token as an httpOnly cookie that JavaScript
    # cannot read. Secure (HTTPS-only) defaults to on in production.
    auth_cookie_name: str = "ns_refresh"
    auth_cookie_secure: bool | None = None
    auth_cookie_samesite: Literal["strict", "lax", "none"] = "strict"
    auth_cookie_domain: str | None = None

    upload_dir: Path = _BACKEND_ROOT / "storage" / "uploads"
    max_upload_size_mb: int = Field(default=20, ge=1)
    chunk_size_chars: int = Field(default=1000, ge=100)
    chunk_overlap_chars: int = Field(default=150, ge=0)

    chat_history_max_messages: int = Field(default=10, ge=0)

    # Ingestion worker / job queue
    worker_poll_interval_seconds: float = Field(default=5.0, gt=0)
    job_lease_seconds: int = Field(default=120, ge=10)
    job_max_attempts: int = Field(default=5, ge=1)
    job_retry_base_seconds: float = Field(default=10.0, gt=0)
    job_retry_max_seconds: float = Field(default=600.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Accept CORS_ORIGINS as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        """Reject a chunk overlap that is not smaller than the chunk size."""
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")
        return self

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        """Require a JWT secret of at least 32 characters in production."""
        # HS256 keys shorter than 32 bytes are brute-forceable (RFC 7518 3.2).
        if self.app_env == "production" and len(self.jwt_secret_key.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        return self

    @property
    def job_heartbeat_seconds(self) -> float:
        """Renew the lease well before it expires, tolerating a missed beat or two."""
        return self.job_lease_seconds / 4

    @property
    def refresh_cookie_secure(self) -> bool:
        """Whether the refresh cookie is HTTPS-only: AUTH_COOKIE_SECURE, else on in production."""
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.app_env == "production"

    @property
    def refresh_cookie_path(self) -> str:
        """Only the auth endpoints ever receive the cookie."""
        return f"{self.api_v1_prefix}/auth"

    @property
    def max_upload_size_bytes(self) -> int:
        """MAX_UPLOAD_SIZE_MB in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance."""
    return Settings()
