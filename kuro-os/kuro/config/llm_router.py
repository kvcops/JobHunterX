"""
Kuro OS — Unified LLM Router (LiteLLM 1.93.x)

Wraps litellm.acompletion with:
  • Auto-detection and parameter injection for thinking models
  • Per-provider concurrency semaphores (respects RPM limits)
  • Exponential-backoff retry via tenacity
  • Disk-cache for identical prompt+model combos
  • Token usage tracking via structlog
  • Graceful fallback across providers
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kuro.config.logging import get_logger
from kuro.config.settings import get_settings

log = get_logger("llm_router")

# ---------------------------------------------------------------------------
# Provider-specific reasoning configuration.
# ---------------------------------------------------------------------------

THINKING_MODELS = {
    "groq/openai/gpt-oss-120b",
    "groq/openai/gpt-oss-20b",
}

# Models that use reasoning_effort parameter (Groq GPT-OSS)
REASONING_EFFORT_MODELS = {"groq/openai/gpt-oss-120b", "groq/openai/gpt-oss-20b"}

# Do not inject LiteLLM thinking into Mistral: the provider rejects it for these IDs.
THINKING_PARAM_MODELS: set[str] = set()

# Provider → model fallback chains. Gemma (google.genai-backed) is preferred;
# gemini-3.1-flash-lite is an in-family fallback using the same Google key.
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "fast": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
    ],
    "reasoning": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
    ],
    "tailoring": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
    ],
    "extraction": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
    ],
    "browser": [
        "gemini/gemini-3.1-flash-lite",
    ],
}


# ---------------------------------------------------------------------------
# Concurrency semaphores — per-provider
# ---------------------------------------------------------------------------

_semaphores: Dict[int, Dict[str, asyncio.Semaphore]] = {}

# Minimum delay (seconds) between requests per provider to respect RPM limits.
# Groq free: 30 RPM → 1 req per 2s minimum
# Mistral free: ~60 RPM → 1 req per 1s minimum
# Gemini free: ~15 RPM → 1 req per 4s minimum (conservative)
_PROVIDER_MIN_DELAY: Dict[str, float] = {
    "groq": 3.2,
    "mistral": 2.0,
    "gemini": 4.5,
    "default": 1.5,
}

# Track last request timestamp per provider for rate limiting
_provider_last_request: Dict[str, float] = {}

# ---------------------------------------------------------------------------
# Provider health tracking — auto-failover on rate limits
# ---------------------------------------------------------------------------

# Cooldown (seconds) after a 429 before retrying that provider.
_PROVIDER_COOLDOWN: Dict[str, float] = {
    "gemini": 60.0,
    "groq": 30.0,
    "mistral": 15.0,
    "default": 30.0,
}

# When a provider was last rate-limited (monotonic timestamp).
_provider_rate_limited_until: Dict[str, float] = {}

# Rolling error counts for diagnostics.
_provider_error_counts: Dict[str, int] = {}
_provider_success_counts: Dict[str, int] = {}


def _get_semaphore(model: str) -> asyncio.Semaphore:
    """Get or create a concurrency semaphore for the model's provider."""
    settings = get_settings()
    if model.startswith("gemini/"):
        key = "gemini"
        limit = settings.gemini_concurrency
    elif model.startswith("groq/"):
        key = "groq"
        limit = settings.groq_concurrency
    elif model.startswith("mistral/"):
        key = "mistral"
        limit = settings.mistral_concurrency
    else:
        key = "default"
        limit = 5

    loop_key = id(asyncio.get_running_loop())
    sem_map = _semaphores.setdefault(loop_key, {})
    if key not in sem_map:
        sem_map[key] = asyncio.Semaphore(limit)
    return sem_map[key]


def _get_provider_key(model: str) -> str:
    """Extract provider key from model name."""
    if model.startswith("gemini/"):
        return "gemini"
    elif model.startswith("groq/"):
        return "groq"
    elif model.startswith("mistral/"):
        return "mistral"
    return "default"


def _is_provider_available(model: str) -> bool:
    """Check whether a model's provider is currently available (not in cooldown)."""
    provider = _get_provider_key(model)
    now = time.monotonic()
    until = _provider_rate_limited_until.get(provider, 0.0)
    if now < until:
        return False
    return True


def _record_rate_limit(model: str) -> None:
    """Mark a provider as rate-limited with a cooldown period."""
    import time as _time
    provider = _get_provider_key(model)
    cooldown = _PROVIDER_COOLDOWN.get(provider, 30.0)
    _provider_rate_limited_until[provider] = _time.monotonic() + cooldown
    _provider_error_counts[provider] = _provider_error_counts.get(provider, 0) + 1
    log.warning(
        "provider_rate_limited",
        provider=provider,
        cooldown_s=cooldown,
        total_rate_limits=_provider_error_counts.get(provider, 0),
    )


def _record_provider_success(model: str) -> None:
    """Record a successful call for a provider (resets error streak)."""
    provider = _get_provider_key(model)
    _provider_success_counts[provider] = _provider_success_counts.get(provider, 0) + 1
    # Clear any stale cooldown on success
    _provider_rate_limited_until.pop(provider, None)


async def _enforce_rate_limit(model: str) -> None:
    """Sleep if needed to respect the provider's minimum inter-request delay."""
    import time as _time
    provider = _get_provider_key(model)
    min_delay = _PROVIDER_MIN_DELAY.get(provider, 1.0)
    now = _time.monotonic()
    last = _provider_last_request.get(provider, 0.0)
    target = max(now, last + min_delay)
    _provider_last_request[provider] = target
    await asyncio.sleep(max(0.0, target - _time.monotonic()))


# ---------------------------------------------------------------------------
# Disk cache for LLM responses
# ---------------------------------------------------------------------------

_cache = None


def _get_cache():
    """Lazy-initialise disk cache."""
    global _cache
    if _cache is None:
        from diskcache import Cache

        settings = get_settings()
        _cache = Cache(str(settings.cache_full_path / "llm_cache"))
    return _cache


def _cache_key(model: str, messages: list[dict], kwargs: dict) -> str:
    """Build a deterministic cache key from model + messages."""
    blob = json.dumps({"model": model, "messages": messages, **kwargs}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------------------
# API key injection
# ---------------------------------------------------------------------------

def _ensure_api_keys() -> None:
    """Push API keys from settings into env so LiteLLM picks them up."""
    settings = get_settings()
    litellm.drop_params = True
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    if settings.google_api_key:
        os.environ.setdefault("GEMINI_API_KEY", settings.google_api_key)
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
    if settings.groq_api_key:

        os.environ.setdefault("GROQ_API_KEY", settings.groq_api_key)
    if settings.mistral_api_key:
        os.environ.setdefault("MISTRAL_API_KEY", settings.mistral_api_key)


# ---------------------------------------------------------------------------
# Core: get_llm_params
# ---------------------------------------------------------------------------

def get_llm_params(model_name: str) -> Dict[str, Any]:
    """Build the parameter dict for a given model, auto-injecting
    thinking/reasoning config per spec Section 4.

    Returns a dict suitable for passing to litellm.acompletion(**params).
    """
    params: Dict[str, Any] = {"model": model_name}

    # Auto-inject reasoning parameters for thinking models
    if model_name in REASONING_EFFORT_MODELS:
        params["reasoning_effort"] = "low"  # Keep fast for free tier
    elif model_name in THINKING_PARAM_MODELS:
        params["thinking"] = {"type": "enabled", "budget_tokens": 2048}

    return params


# ---------------------------------------------------------------------------
# Core: call_llm (async, with retry + cache + semaphore + logging)
# ---------------------------------------------------------------------------

async def _raw_completion(params: Dict[str, Any]) -> Any:
    """Call LiteLLM with provider-aware rate limiting and retries."""
    import re

    model = params.get("model", "")
    max_attempts = 5

    for attempt in range(max_attempts):
        # Enforce per-provider minimum delay between requests
        await _enforce_rate_limit(model)

        try:
            result = await litellm.acompletion(**params)
            _record_provider_success(model)
            return result
        except Exception as exc:
            err_str = str(exc).lower()
            is_rate_limit = (
                "rate limit" in err_str
                or "429" in err_str
                or "too many requests" in err_str
                or isinstance(exc, (litellm.RateLimitError, litellm.ServiceUnavailableError))
            )
            if is_rate_limit:
                _record_rate_limit(model)
                match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)s", str(exc), re.I)
                delay = float(match.group(1)) if match else min(3.0 * (attempt + 1), 30.0)
                if attempt == max_attempts - 1:
                    raise
                log.warning(
                    "rate_limit_retry",
                    model=model,
                    attempt=attempt + 1,
                    delay=round(delay, 1),
                    error=str(exc)[:200],
                )
                await asyncio.sleep(max(1.5, min(delay, 30.0)))
            else:
                raise



async def call_llm(
    model: str,
    messages: List[Dict[str, str]],
    use_cache: bool = True,
    cache_ttl: int = 3600,
    **kwargs: Any,
) -> Dict[str, Any]:
    """High-level async LLM call with all infrastructure:

    1. Check disk cache
    2. Acquire provider semaphore
    3. Auto-inject thinking params
    4. Call litellm.acompletion with retry
    5. Log token usage
    6. Cache result

    Returns dict with keys: content, tokens_in, tokens_out, model, latency_ms, cache_hit
    """
    _ensure_api_keys()

    # --- Cache check ---
    ck = _cache_key(model, messages, kwargs) if use_cache else None
    if use_cache and ck:
        cache = _get_cache()
        cached = cache.get(ck)
        if cached is not None:
            log.info("llm_cache_hit", model=model)
            return {**cached, "cache_hit": True}

    # --- Build params ---
    params = get_llm_params(model)
    params["messages"] = messages
    params.update(kwargs)

    # Never leak provider-incompatible reasoning fields into Mistral.
    if model.startswith("mistral/"):
        params.pop("thinking", None)
        params.pop("reasoning_effort", None)
    elif model.startswith("gemini/"):
        # Gemini 3+ deprecates temperature, top_p, top_k; move sampling into prompt
        params.pop("temperature", None)
        params.pop("top_p", None)
        params.pop("top_k", None)
    params.setdefault("max_tokens", 768)

    # --- Semaphore + call ---
    sem = _get_semaphore(model)
    async with sem:
        t0 = time.monotonic()
        response = await _raw_completion(params)
    latency_ms = (time.monotonic() - t0) * 1000

    # --- Extract result ---
    choice = response.choices[0]
    content = choice.message.content or ""
    usage = getattr(response, "usage", None)
    tokens_in = usage.prompt_tokens if usage else 0
    tokens_out = usage.completion_tokens if usage else 0

    result = {
        "content": content,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "cache_hit": False,
    }

    log.info(
        "llm_call",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=round(latency_ms, 1),
    )

    # --- Persist token usage to DB so the UI telemetry reflects real totals ---
    try:
        from kuro.config import database as _db
        if _db._db_path:
            import asyncio as _aio
            _log_coro = _db.log_agent_event(
                run_id=ck or "llm",
                agent_name="llm_router",
                event_type="llm_call",
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=model,
                latency_ms=round(latency_ms, 1),
            )
            try:
                loop = _aio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                loop.create_task(_log_coro)
    except Exception as exc:
        log.warning("llm_db_log_failed", error=str(exc), exc_info=True)

    # --- Cache store ---
    if use_cache and ck:
        cache = _get_cache()
        cache.set(ck, result, expire=cache_ttl)

    return result


async def call_llm_with_fallback(
    chain_name: str,
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Try models in a fallback chain until one succeeds.

    Automatically skips providers that are currently rate-limited (in cooldown)
    so subsequent calls fail over immediately without wasting time on retries.

    Args:
        chain_name: Key in FALLBACK_CHAINS (e.g., "fast", "reasoning", "tailoring").
        messages: Chat messages.
        **kwargs: Additional params for litellm.

    Returns:
        Same dict as call_llm.

    Raises:
        Exception: If all models in the chain fail.
    """
    chain = FALLBACK_CHAINS.get(chain_name, FALLBACK_CHAINS["fast"])
    settings = get_settings()
    last_err: Exception | None = None

    for model in chain:
        # Skip models whose provider key is missing
        if model.startswith("gemini/") and not settings.google_api_key:
            continue
        if model.startswith("groq/") and not settings.groq_api_key:
            continue
        if model.startswith("mistral/") and not settings.mistral_api_key:
            continue

        # Skip providers currently in rate-limit cooldown
        if not _is_provider_available(model):
            provider = _get_provider_key(model)
            remaining = max(0, _provider_rate_limited_until.get(provider, 0) - time.monotonic())
            log.info("llm_fallback_skip_cooldown", model=model, provider=provider, cooldown_remaining_s=round(remaining, 1))
            continue

        try:
            return await call_llm(model, messages, **kwargs)
        except Exception as exc:
            log.warning("llm_fallback", model=model, error=str(exc))
            last_err = exc

    raise RuntimeError(
        f"All models in chain '{chain_name}' failed. Last error: {last_err}"
    )
