"""Application configuration. Every secret comes from the environment — nothing is hardcoded."""
from __future__ import annotations

import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("novatech.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NovaTech Solutions — Enterprise Intelligence Platform"
    environment: str = "development"

    # Database. PostgreSQL (+pgvector) is the target; SQLite is a zero-setup fallback for laptops.
    database_url: str = "sqlite:///./novatech_demo.db"
    reset_db_on_start: bool = False

    # OpenAI. When the key is absent the app runs the deterministic offline engine so the demo never breaks.
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: float = 30.0
    openai_base_url: str | None = None  # optional OpenAI-compatible endpoint
    embedding_dim: int = 384
    use_openai_embeddings: bool = True

    # Sessions / auth
    session_secret: str = ""
    session_ttl_minutes: int = 480
    demo_mode: bool = True  # enables the judge-facing identity switcher. MUST be false in production.
    guest_mode_enabled: bool = True  # public "Continue as Guest" — PUBLIC data only, enforced server-side
    guest_session_ttl_minutes: int = 120
    guest_rate_limit_per_minute: int = 6

    # Rate limiting (real, enforced in-app)
    rate_limit_per_minute: int = 120
    chat_rate_limit_per_minute: int = 20
    login_rate_limit_per_minute: int = 10

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    company_timezone: str = "Asia/Kolkata"
    max_upload_bytes: int = 2_000_000

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.session_secret:
        s.session_secret = secrets.token_urlsafe(48)
        log.warning("SESSION_SECRET not set — generated an ephemeral secret (sessions reset on restart).")
    return s
