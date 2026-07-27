"""
Vellum OS — Unified LLM Router (LiteLLM 1.93.x)

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

from vellum.config.logging import get_logger
from vellum.config.settings import get_settings

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

# Provider → model fallback chains
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "fast": [
        "gemini/gemini-3.1-flash-lite",
        "groq/openai/gpt-oss-20b",
    ],
    "reasoning": [
        "groq/openai/gpt-oss-120b",
        "mistral/mistral-large-2512",
        "gemini/gemini-3.1-flash-lite",
    ],
    "tailoring": [
        "mistral/mistral-large-2512",
        "groq/openai/gpt-oss-120b",
        "gemini/gemini-3.1-flash-lite",
    ],
    "extraction": [
        "gemini/gemma-4-31b-it",
        "groq/openai/gpt-oss-120b",
        "gemini/gemini-3.1-flash-lite",
    ],
}

# ---------------------------------------------------------------------------
# Concurrency semaphores — per-provider
# ---------------------------------------------------------------------------

_semaphores: Dict[str, asyncio.Semaphore] = {}


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

    if key not in _semaphores:
        _semaphores[key] = asyncio.Semaphore(limit)
    return _semaphores[key]


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
    if settings.google_api_key:
        os.environ.setdefault("GEMINI_API_KEY", settings.google_api_key)
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
    """Call LiteLLM with provider-aware, reset-respecting retries."""
    for attempt in range(4):
        try:
            return await litellm.acompletion(**params)
        except (litellm.RateLimitError, litellm.ServiceUnavailableError) as exc:
            # Mistral's 429 response has no reset duration. Retrying it four
            # times only delays the configured fallback providers.
            if (
                params.get("model", "").startswith("mistral/")
                and isinstance(exc, litellm.RateLimitError)
            ):
                raise
            if attempt == 3:
                raise
            import re
            match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)s", str(exc), re.I)
            delay = float(match.group(1)) if match else min(2 ** (attempt + 1), 30)
            await asyncio.sleep(max(1.0, min(delay, 30.0)))


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
    params.setdefault("max_tokens", 768)

    # --- Semaphore + call ---
    sem = _get_semaphore(model)
    t0 = time.monotonic()
    async with sem:
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

        try:
            return await call_llm(model, messages, **kwargs)
        except Exception as exc:
            log.warning("llm_fallback", model=model, error=str(exc))
            last_err = exc

    raise RuntimeError(
        f"All models in chain '{chain_name}' failed. Last error: {last_err}"
    )
