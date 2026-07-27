"""
Vellum OS — Application Settings

Loads configuration from .env file using pydantic-settings BaseSettings.
All API keys are optional for graceful degradation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider Keys (all optional — system degrades gracefully) ---
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # --- Application ---
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    browser_use_headless: bool = False

    # --- Storage Paths ---
    db_path: str = "./data/vellum.db"
    cache_dir: str = "./data/cache"
    screenshots_dir: str = "./data/screenshots"

    # --- Concurrency Limits (RPM-aware) ---
    gemini_concurrency: int = 5   # Conservative: stay well under 30 RPM
    groq_concurrency: int = 1
    mistral_concurrency: int = 1
    max_job_pipelines: int = 2    # Max concurrent per-job pipelines

    @property
    def available_providers(self) -> list[str]:
        """Return list of providers with configured API keys."""
        providers = []
        if self.google_api_key:
            providers.append("google")
        if self.groq_api_key:
            providers.append("groq")
        if self.mistral_api_key:
            providers.append("mistral")
        return providers

    @property
    def db_full_path(self) -> Path:
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cache_full_path(self) -> Path:
        p = Path(self.cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def screenshots_full_path(self) -> Path:
        p = Path(self.screenshots_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
