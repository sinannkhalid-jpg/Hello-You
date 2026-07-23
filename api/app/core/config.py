"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "OSINT Nexus"
    app_env: str = "development"
    app_debug: bool = True
    app_url: str = "http://localhost:8000"
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Security
    secret_key: str = "change-me-to-a-long-random-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    # Database
    database_url: str = "sqlite+aiosqlite:///./osint_nexus.db"
    direct_url: str | None = None

    # Supabase
    use_supabase: bool = False
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    # OSINT
    hibp_api_key: str | None = None
    ipapi_base_url: str = "https://ipapi.co"
    abuseipdb_api_key: str | None = None
    virustotal_api_key: str | None = None

    # Rate limit
    rate_limit_per_minute: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
