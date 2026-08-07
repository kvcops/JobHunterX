"""
JobHunterX — Unified LLM Router (LiteLLM 1.93.x)

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

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings

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

# Provider → model fallback chains using updated August 2026 model IDs.
# Google AI Studio models (Gemma 4 26B, Gemini 3.1 Flash Lite) are primary;
# Groq (Llama 3.3 70B, Llama 3.1 8B) and Mistral (mistral-small-2603, mistral-large-2512, codestral-2508)
# provide cross-provider failover.
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "fast": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
        "groq/llama-3.1-8b-instant",
        "mistral/mistral-small-2603",
    ],
    "reasoning": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
        "groq/llama-3.3-70b-versatile",
        "mistral/mistral-large-2512",
    ],
    "tailoring": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
        "groq/llama-3.3-70b-versatile",
        "mistral/codestral-2508",
    ],
    "extraction": [
        "gemini/gemma-4-26b-a4b-it",
        "gemini/gemini-3.1-flash-lite",
        "groq/llama-3.1-8b-instant",
        "mistral/mistral-small-2603",
    ],
    "browser": [
        "gemini/gemini-3.1-flash-lite",
        "groq/llama-3.3-70b-versatile",
        "mistral/mistral-small-2603",
    ],
}


# ---------------------------------------------------------------------------
# Concurrency semaphores — per-provider
# ---------------------------------------------------------------------------

_semaphores: Dict[int, Dict[str, asyncio.Semaphore]] = {}

# Minimum delay (seconds) between requests per provider to respect RPM limits.
# Groq free: 30 RPM → 1 req per 2s minimum
# Mistral free: ~60 RPM → 1 req per 1s minimum
# Gemini 3.1 Flash Lite free: 15 RPM (250K TPM / 500 RPD) → 1 req per 4.0s minimum
_PROVIDER_MIN_DELAY: Dict[str, float] = {
    "groq": 3.2,
    "mistral": 2.0,
    "gemini": 4.0,
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
                or isinstance(exc, litellm.RateLimitError)
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


async def _call_google_genai(
    model_name: str,
    messages: List[Dict[str, str]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Direct Google GenAI SDK call for all Gemini & Gemma models (bypasses LiteLLM completely)."""
    settings = get_settings()
    api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No Google API key configured")

    raw_model = model_name.split("/", 1)[-1] if "/" in model_name else model_name

    from google import genai
    client = genai.Client(api_key=api_key)

    system_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
    user_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") != "system")

    contents = []
    if system_content:
        contents.append(f"SYSTEM INSTRUCTIONS:\n{system_content}")
    contents.append(f"USER:\n{user_content}")
    prompt_str = "\n\n".join(contents)

    cfg: Dict[str, Any] = {}
    max_tokens = kwargs.get("max_tokens") or kwargs.get("max_output_tokens")
    if max_tokens:
        cfg["max_output_tokens"] = max_tokens

    t0 = time.monotonic()

    def _sync_generate():
        return client.models.generate_content(
            model=raw_model,
            contents=prompt_str,
            config=cfg if cfg else None,
        )

    response = await asyncio.to_thread(_sync_generate)
    latency_ms = (time.monotonic() - t0) * 1000

    content = getattr(response, "text", "") or ""
    usage_meta = getattr(response, "usage_metadata", None)
    t_in = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
    t_out = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0

    if not t_in and not t_out:
        t_in = max(1, len(prompt_str) // 4)
        t_out = max(1, len(content) // 4)

    return {
        "content": content,
        "tokens_in": int(t_in or 0),
        "tokens_out": int(t_out or 0),
        "model": model_name,
        "latency_ms": round(latency_ms, 1),
        "cache_hit": False,
    }


async def call_llm(
    model: str,
    messages: List[Dict[str, str]],
    use_cache: bool = True,
    cache_ttl: int = 3600,
    **kwargs: Any,
) -> Dict[str, Any]:
    """High-level async LLM call with all infrastructure:

    1. Check disk cache
    2. Direct Google GenAI SDK for Gemini/Gemma models
    3. Acquire provider semaphore for LiteLLM models (Groq, Mistral)
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

    # --- Direct Google GenAI SDK routing for ALL Gemini & Gemma models ---
    if model.startswith("gemini/") or model.startswith("google/") or "gemma" in model:
        if model in ("gemini/gemma-4-26b-a4b-it", "gemma-4-26b-a4b-it"):
            from jobhunterx.config.gemma import call_gemma
            system_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
            user_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") != "system")
            t0 = time.monotonic()
            content = await call_gemma(
                system=system_content,
                user=user_content,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature"),
            )
            latency_ms = (time.monotonic() - t0) * 1000
            result = {
                "content": content,
                "tokens_in": max(1, (len(system_content) + len(user_content)) // 4),
                "tokens_out": max(1, len(content) // 4),
                "model": model,
                "latency_ms": round(latency_ms, 1),
                "cache_hit": False,
            }
        else:
            await _enforce_rate_limit(model)
            result = await _call_google_genai(model, messages, **kwargs)

        # Log token usage to database
        try:
            from jobhunterx.config import database as _db
            if _db._db_path:
                await _db.log_agent_event(
                    run_id=ck or "llm",
                    agent_name="google_genai_direct",
                    event_type="llm_call",
                    tokens_in=result["tokens_in"],
                    tokens_out=result["tokens_out"],
                    model=model,
                    latency_ms=result["latency_ms"],
                )
        except Exception as exc:
            log.warning("google_db_log_failed", error=str(exc))

        if use_cache and ck:
            cache = _get_cache()
            cache.set(ck, result, expire=cache_ttl)
        return result

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
    tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
    tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

    if not tokens_in and not tokens_out:
        prompt_len = sum(len(m.get("content", "")) for m in messages)
        tokens_in = max(1, prompt_len // 4)
        tokens_out = max(1, len(content) // 4)

    result = {
        "content": content,
        "tokens_in": int(tokens_in or 0),
        "tokens_out": int(tokens_out or 0),
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
        from jobhunterx.config import database as _db
        if _db._db_path:
            await _db.log_agent_event(
                run_id=ck or "llm",
                agent_name="llm_router",
                event_type="llm_call",
                tokens_in=int(tokens_in or 0),
                tokens_out=int(tokens_out or 0),
                model=model,
                latency_ms=round(latency_ms, 1),
            )
    except Exception as exc:
        log.warning("llm_db_log_failed", error=str(exc))

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
