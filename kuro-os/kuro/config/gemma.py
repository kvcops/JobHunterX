"""
Kuro OS — Gemma direct calling + budget tracker (Google AI Studio)

Gemma models return 503s through LiteLLM on the free tier, so we call
`google.genai` directly (verified in test_gemma.py). This module also owns
the free-tier budget: 15k RPD / 30 RPM, persisted to disk so a restart of
the server never resets the daily counter and burns the quota faster.

Model: gemma-4-26b-a4b-it (thinkingLevel=minimal).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from kuro.config.logging import get_logger
from kuro.config.settings import get_settings

log = get_logger("gemma")

MODEL = "gemma-4-26b-a4b-it"

# Free-tier hard limits (override via env GEMMA_DAILY_TOKENS / GEMMA_RPM)
DEFAULT_DAILY_TOKENS = 15000
DEFAULT_RPM = 15

# Inter-request minimum gap for Google AI Studio Free Tier (3.5s ensures no 429/500 rate limit spikes)
_MIN_INTERVAL_S = 3.5

# Budget state file lives under the data dir, next to the run.
_budget_path: Path | None = None
_tokens_used = 0
_requests_today = 0
_loaded_date: str | None = None
_last_request_mono = 0.0
_rate_lock: asyncio.Lock | None = None
_genai_client: Any | None = None


def _state_file() -> Path:
    global _budget_path
    if _budget_path is None:
        _budget_path = Path(get_settings().db_full_path.parent) / "gemma_budget.json"
    return _budget_path


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> None:
    """Load (or reset) the daily budget counters."""
    global _tokens_used, _requests_today, _loaded_date
    today = _today_str()
    if _loaded_date == today:
        return
    state = {}
    try:
        f = _state_file()
        if f.exists():
            state = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    if state.get("date") == today:
        _tokens_used = int(state.get("tokens", 0))
        _requests_today = int(state.get("requests", 0))
    else:
        _tokens_used = 0
        _requests_today = 0
    _loaded_date = today


def _save_state() -> None:
    try:
        f = _state_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({
            "date": _today_str(),
            "tokens": _tokens_used,
            "requests": _requests_today,
        }), encoding="utf-8")
    except Exception as exc:
        log.warning("gemma_budget_save_failed", error=str(exc))


def _daily_cap() -> int:
    settings = get_settings()
    return int(getattr(settings, "gemma_daily_tokens", None) or DEFAULT_DAILY_TOKENS)


def _rpm_cap() -> int:
    settings = get_settings()
    return int(getattr(settings, "gemma_rpm", None) or DEFAULT_RPM)


def budget_status() -> dict:
    """Return current budget usage. Safe to call from any thread/process."""
    _load_state()
    cap = _daily_cap()
    rpm = _rpm_cap()
    return {
        "model": MODEL,
        "date": _today_str(),
        "tokens_used": _tokens_used,
        "tokens_cap": cap,
        "tokens_remaining": max(0, cap - _tokens_used),
        "requests_today": _requests_today,
        "rpm_cap": rpm,
        "exhausted": _tokens_used >= cap,
    }


def is_exhausted() -> bool:
    _load_state()
    return _tokens_used >= _daily_cap()


def _rate_lock_() -> asyncio.Lock:
    global _rate_lock
    if _rate_lock is None:
        _rate_lock = asyncio.Lock()
    return _rate_lock


async def gemma_available() -> bool:
    """True if the API key exists AND the daily budget is not exhausted."""
    settings = get_settings()
    if not (settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        return False
    return not is_exhausted()


async def call_gemma(
    system: str,
    user: str,
    *,
    max_tokens: int = 1024,
    temperature: float | None = None,
    thinking_level: str = "minimal",
) -> str:
    """Direct Gemma call (thread executor), budget-tracked.

    Enforces per-provider spacing (30 RPM) and the daily token cap (15k)
    persisted to disk. Raises RuntimeError('gemma_budget_exhausted') when
    the cap is hit so callers can fall back gracefully (skip scoring).
    """
    global _last_request_mono, _tokens_used, _requests_today, _genai_client
    settings = get_settings()
    api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No Google API key configured")

    _load_state()
    if _tokens_used >= _daily_cap():
        log.warning("gemma_budget_exhausted", used=_tokens_used)
        raise RuntimeError("gemma_budget_exhausted")

    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)

    cfg = {"thinkingConfig": {"thinkingLevel": thinking_level}}
    if temperature is not None:
        cfg["temperature"] = temperature
    if max_tokens:
        cfg["max_output_tokens"] = max_tokens

    async def _run_with_ratelimit() -> str:
        global _last_request_mono
        max_retries = 3
        backoff = 3.0

        for attempt in range(max_retries):
            async with _rate_lock_():
                now = time.monotonic()
                wait = (_last_request_mono + _MIN_INTERVAL_S) - now
                if wait > 0:
                    await asyncio.sleep(wait)
                _last_request_mono = time.monotonic()

                def _sync_call() -> str:
                    response = _genai_client.models.generate_content(
                        model=MODEL,
                        contents=f"SYSTEM INSTRUCTIONS:\n{system}\n\nUSER:\n{user}",
                        config=cfg,
                    )
                    return getattr(response, "text", "") or ""

                try:
                    return await asyncio.to_thread(_sync_call)
                except Exception as exc:
                    err_str = str(exc)
                    is_transient = any(code in err_str for code in ["500", "503", "429", "RESOURCE_EXHAUSTED", "INTERNAL"])
                    if is_transient and attempt < max_retries - 1:
                        log.warning("gemma_transient_error_retry", attempt=attempt+1, error=err_str[:120], backoff_s=backoff)
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    raise

        return ""

    content = await _run_with_ratelimit()

    # Estimate tokens (prompt + response). ~4 chars/token is typical.
    est_tokens = max(1, (len(system) + len(user) + len(content)) // 4)
    _load_state()
    _tokens_used += est_tokens
    _requests_today += 1
    _save_state()
    log.info("gemma_call", estimated_tokens=est_tokens, tokens_used=_tokens_used,
             requests_today=_requests_today)
    return content