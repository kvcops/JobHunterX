"""
JobHunterX — Application Settings

Loads configuration from .env file using pydantic-settings BaseSettings.
All API keys are optional for graceful degradation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_PREFIXES = ("your_", "your-", "<", "xxx", "changeme", "change_me", "replace", "paste", "todo", "none", "null")


def is_real_key(value: Optional[str]) -> bool:
    """False for empty values and template placeholders like `your_gemini_api_key` copied from .env.example."""
    v = (value or "").strip().strip('"').strip("'")
    return len(v) >= 12 and not v.lower().startswith(_PLACEHOLDER_PREFIXES)


# Project root (jobhunterx/): settings.py lives at jobhunterx/jobhunterx/config/settings.py
_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider Keys (all optional — system degrades gracefully) ---
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None          # NVIDIA NIM (build.nvidia.com), free key, 40 requests/minute
    kilo_api_key: Optional[str] = None            # optional: Kilo's free pool works without any key

    @field_validator("google_api_key", "groq_api_key", "mistral_api_key", "nvidia_api_key", "kilo_api_key", "tinyfish_api_key", "tavily_api_key",
                     "exa_api_key", "brave_api_key", mode="before")
    @classmethod
    def _drop_placeholder_keys(cls, v):
        # A placeholder must count as "no key": otherwise every AI call fails and retries, and the UI waits forever.
        return v.strip().strip('"').strip("'") if isinstance(v, str) and is_real_key(v) else None

    # --- Free-tier limits (defaults live in config/models.py; JSON overrides per model) ---
    gemma_daily_requests: int = 1500
    gemma_daily_tokens: int = 1500
    gemma_rpm: int = 15
    model_limits_json: str = ""

    # --- Application ---
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    browser_use_headless: bool = True   # legacy; the live view always runs headless unless BROWSER_SHOW_WINDOW=true
    browser_use_headless_original: bool = False # fallback reference
    # --- Auto-apply ---
    browser_show_window: bool = False   # also open a real Chrome window (debugging); default: live view in the app only
    browser_max_steps: int = 40         # agent steps per run before it hands back to you
    browser_step_delay_s: float = 1.0   # pause between agent steps (429s are retried with backoff anyway)
    apply_with_cover_letter: bool = True  # prepare a cover letter before applying
    apply_with_cv: bool = True            # prepare a full CV too (uploaded only where a form asks for a separate CV)
    browser_use_cloud: bool = False     # set True + BROWSER_USE_API_KEY in .env to use stealth cloud browsers
    # auto: real Chrome window parked off-screen on a desktop (looks human to bot checks), headless on a server
    browser_window_mode: str = "auto"   # auto | offscreen | headless | window
    # drive a Chrome you started yourself (chrome --remote-debugging-port=9222 --user-data-dir=…) or a hosted
    # stealth browser (Browserbase, Steel, Browser Use cloud…): its IP, cookies and logins are used
    browser_cdp_url: str = ""

    # --- Web Search API Provider Keys & Router Settings ---
    enable_web_search_apis: bool = True
    primary_search_provider: str = "tinyfish"
    strict_zero_spend_protection: bool = True

    tinyfish_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    exa_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    brave_enabled: bool = False
    tavily_search_depth: str = "basic"
    exa_search_num_results: int = 10


    # --- Matching / discovery tuning (JSON overrides, see intelligence/policy.py) ---
    match_policy_json: str = ""
    max_jobs_per_search: int = 60
    enable_linkedin_source: bool = True     # LinkedIn's public (logged-out) job feed: newest posts, resolved to employer boards
    linkedin_max_applicants: int = 150      # skip LinkedIn posts that already show this many applicants
    max_llm_jd_extractions_per_search: int = 40
    watch_interval_hours: float = 4.0            # how often watchlist boards are checked while the app runs; 0 = off
    fetch_timeout_s: float = 12.0
    allow_private_network_fetch: bool = False   # SSRF guard; keep False

    # --- Storage Paths ---
    db_path: str = str(_BASE_DIR / "data" / "jobhunterx.db")
    cache_dir: str = str(_BASE_DIR / "data" / "cache")
    screenshots_dir: str = str(_BASE_DIR / "data" / "screenshots")

    # --- Concurrency Limits (RPM-aware) ---
    gemini_concurrency: int = 3   # Gemini free: ~15 RPM, conservative
    groq_concurrency: int = 1     # Groq free: 30 RPM, serial with 2s delay
    mistral_concurrency: int = 1  # Mistral free: ~60 RPM, serial with 1s delay
    max_job_pipelines: int = 1    # Max concurrent per-job pipelines (serial to respect rate limits)

    @property
    def available_providers(self) -> list[str]:
        """Return list of providers with configured API keys."""
        providers = []
        if self.google_api_key:
            providers.append("google")
        providers.append("kilo")               # Kilo's free pool needs no key
        if self.nvidia_api_key:
            providers.append("nvidia")
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
