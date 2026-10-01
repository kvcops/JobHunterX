"""
JobHunterX — Gemma direct calling + budget tracker (Google AI Studio)

Gemma runs on the Gemini API (see Google's "Gemma on Gemini API" guide). It has
no system role, so instructions are sent inline. Calls go through `google.genai`
directly; the router spaces requests to the model's RPM (config/models.py) and
this module tracks the daily request budget.

Google's free Gemma endpoint sometimes answers "500 INTERNAL" for a while. We
retry once (without the thinking setting, which is a common trigger), then give
up fast so the router can move to the next model; the router also rests Gemma
for a few minutes after repeated errors (config/models.py → model health), so
one bad spell never slows a whole search down.

Default model: gemma-4-31b-it (override with GEMMA_MODEL in .env).
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from datetime import datetime, timezone

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings

log = get_logger("gemma")

MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")

# Free-tier limits for Gemma 4 31B on Google AI Studio (see config/models.py; editable via MODEL_LIMITS_JSON)
DEFAULT_DAILY_REQUESTS = 1500
DEFAULT_RPM = 15

# Spacing is enforced by the router's per-model budget; this is only a floor between retries.
_MIN_INTERVAL_S = 0.5
_SERVER_ERRORS = ("500", "502", "503", "504", "INTERNAL", "UNAVAILABLE", "DEADLINE", "overloaded", "timed out", "Timeout")
_TIMEOUT_S = float(os.getenv("GEMMA_TIMEOUT_S", "150"))     # a slow answer is better than none, but not forever

_tokens_used = 0
_requests_today = 0
_loaded_date: str | None = None
_last_request_mono = 0.0
_rate_lock: asyncio.Lock | None = None
_genai_client: Any | None = None


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> None:
    """Load (or reset) the daily budget counters in-memory."""
    global _tokens_used, _requests_today, _loaded_date
    today = _today_str()
    if _loaded_date != today:
        _tokens_used = 0
        _requests_today = 0
        _loaded_date = today


def _daily_rpd_cap() -> int:
    from jobhunterx.config.models import limits
    return int(limits(f"gemini/{MODEL}").get("rpd") or getattr(get_settings(), "gemma_daily_requests", None) or DEFAULT_DAILY_REQUESTS)


def _daily_cap() -> int:
    return _daily_rpd_cap()


def _rpm_cap() -> int:
    from jobhunterx.config.models import limits
    return int(limits(f"gemini/{MODEL}").get("rpm") or getattr(get_settings(), "gemma_rpm", None) or DEFAULT_RPM)


def budget_status() -> dict:
    """Return current budget usage. Safe to call from any thread/process."""
    _load_state()
    rpd_cap = _daily_rpd_cap()
    rpm = _rpm_cap()
    return {
        "model": MODEL,
        "date": _today_str(),
        "tokens_used": _tokens_used,
        "requests_today": _requests_today,
        "requests_cap": rpd_cap,
        "tokens_cap": rpd_cap,  # backward compatibility alias
        "requests_remaining": max(0, rpd_cap - _requests_today),
        "rpm_cap": rpm,
        "tpm_cap": None,
        "exhausted": _requests_today >= rpd_cap,
    }


def is_exhausted() -> bool:
    _load_state()
    return _requests_today >= _daily_rpd_cap()


def _rate_lock_() -> asyncio.Lock:
    global _rate_lock
    if _rate_lock is None:
        _rate_lock = asyncio.Lock()
    return _rate_lock


async def gemma_available() -> bool:
    """True if the API key exists AND the daily RPD budget is not exhausted."""
    settings = get_settings()
    if not (settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        return False
    return not is_exhausted()


async def call_gemma(
    system: str,
    user: str,
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float | None = None,
    thinking_level: str = "minimal",
) -> str:
    """Direct Gemma call (thread executor), RPD & RPM budget-tracked.

    Enforces per-provider spacing (30 RPM) and daily request cap (14,400 RPD) in-memory.
    Raises RuntimeError('gemma_budget_exhausted') when the RPD cap is hit.
    """
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_prefix = (
        f"Today's date is {today_str}. Judge dates, freshness and deadlines relative to it.\n\n"
    )
    if "Today's date is" not in system:
        system = date_prefix + system

    global _last_request_mono, _tokens_used, _requests_today, _genai_client
    settings = get_settings()
    api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No Google API key configured")

    _load_state()
    if _requests_today >= _daily_rpd_cap():
        log.warning("gemma_budget_exhausted", requests_today=_requests_today)
        raise RuntimeError("gemma_budget_exhausted")

    if _genai_client is None:
        from google import genai
        from google.genai import types
        _genai_client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(_TIMEOUT_S * 1000)))

    model = model or MODEL
    # automatic_function_calling off: we never pass tools (also silences "AFC is enabled…" on every call)
    cfg: dict[str, Any] = {"thinkingConfig": {"thinkingLevel": thinking_level}, "automatic_function_calling": {"disable": True}}
    if temperature is not None:
        cfg["temperature"] = temperature
    if max_tokens:
        cfg["max_output_tokens"] = max_tokens

    def _sync_call() -> tuple[str, int, int]:
        response = _genai_client.models.generate_content(
            model=model,
            contents=f"SYSTEM INSTRUCTIONS:\n{system}\n\nUSER:\n{user}",
            config=cfg,
        )
        text = getattr(response, "text", "") or ""
        usage_meta = getattr(response, "usage_metadata", None)
        t_in = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
        t_out = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
        if not t_in and not t_out:
            t_in = max(1, (len(system) + len(user)) // 4)
            t_out = max(1, len(text) // 4)
        return text, int(t_in or 0), int(t_out or 0)

    async def _run_with_ratelimit() -> tuple[str, int, int]:
        global _last_request_mono
        import random
        retried = False
        for _ in range(3):                            # one quick retry on a server error, then let the router fall back
            async with _rate_lock_():                 # the lock only spaces requests; it is never held while waiting on Google
                wait = (_last_request_mono + _MIN_INTERVAL_S) - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                _last_request_mono = time.monotonic()
            try:
                return await asyncio.to_thread(_sync_call)
            except Exception as exc:
                err = str(exc)
                if "thinking" in err.lower() and "thinkingConfig" in cfg:
                    cfg.pop("thinkingConfig", None)    # this model doesn't take a thinking level
                    continue
                if not retried and any(code in err for code in _SERVER_ERRORS):
                    retried = True
                    cfg.pop("thinkingConfig", None)    # Google's 500s on Gemma often go away without thinking
                    delay = 1.5 + random.uniform(0, 1.5)
                    log.warning("gemma_server_error_retry", error=err[:100], retry_in_s=round(delay, 1))
                    await asyncio.sleep(delay)
                    continue
                raise RuntimeError(f"Gemma is having trouble on Google's side ({err[:140]})") from exc
        raise RuntimeError("Gemma did not answer")

    t0 = time.monotonic()
    content, tokens_in, tokens_out = await _run_with_ratelimit()
    latency_ms = (time.monotonic() - t0) * 1000

    _load_state()
    total_tokens = tokens_in + tokens_out
    _tokens_used += total_tokens
    _requests_today += 1

    # Record token usage in database
    try:
        from jobhunterx.config import database as _db
        if _db._db_path:
            await _db.log_agent_event(
                run_id="gemma",
                agent_name="gemma_direct",
                event_type="llm_call",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=f"gemini/{model}",
                latency_ms=round(latency_ms, 1),
            )
    except Exception as exc:
        log.warning("gemma_db_log_failed", error=str(exc))

    log.info("gemma_call", tokens_in=tokens_in, tokens_out=tokens_out, tokens_used=_tokens_used,
             requests_today=_requests_today)
    return content
