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
from typing import Any, Dict, List

os.environ.setdefault("LITELLM_LOCAL_RESOURCES", "true")
import litellm

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings

log = get_logger("llm_router")

# ---------------------------------------------------------------------------
# Models: catalog, chains and limits live in config/models.py; user choices in app_state.
# ---------------------------------------------------------------------------
import re as _re

from jobhunterx.config import app_state
from jobhunterx.config import models as M

# Groq GPT-OSS models take a reasoning_effort parameter; keep it low for free-tier latency.
REASONING_EFFORT_MODELS = {"groq/openai/gpt-oss-120b", "groq/openai/gpt-oss-20b"}
# Qwen3 on Groq: hide the reasoning trace so callers only see the answer.
HIDDEN_REASONING_MODELS = {"groq/qwen/qwen3-32b", "groq/qwen/qwen3.6-27b"}
THINKING_MODELS = REASONING_EFFORT_MODELS | HIDDEN_REASONING_MODELS
THINKING_PARAM_MODELS: set[str] = set()

FALLBACK_CHAINS: Dict[str, List[str]] = M.CHAINS
_THINK_RE = _re.compile(r"<think>.*?</think>\s*", _re.S | _re.I)


def _overrides() -> Dict[str, str]:
    return app_state.get("llm.overrides") or {}


def get_model_config() -> Dict[str, Any]:
    """Model config for the UI: providers (configured/enabled/reachable), chains and every model with its limits."""
    avail = M.availability()
    providers = {}
    for p in app_state.LLM_PROVIDERS:
        info = avail.get(p)
        providers[p] = {"configured": bool(M.provider_key(p)), "enabled": app_state.llm_provider_enabled(p),
                        "reachable": None if info is None else info["ok"], "error": info and info["error"],
                        "models_listed": info["count"] if info else 0}
    all_models = []
    for m in M.CATALOG:
        listed = M.is_listed(m["id"])
        reason = _skip_reason(m["id"])
        all_models.append({"id": m["id"], "name": m["name"] if m["name"].endswith(")") else f"{m['name']} ({m['provider'].title()})", "provider": m["provider"],
                           "note": m.get("note", ""), "limits": M.limits(m["id"]), "listed": listed,
                           "usable": reason is None, "reason": reason})
    over = _overrides()
    chains = {}
    for key, default_list in FALLBACK_CHAINS.items():
        options = list(default_list) + [m["id"] for m in M.CATALOG if m["id"] not in default_list]
        chains[key] = {"name": M.CHAIN_LABELS.get(key, key.title()), "selected": over.get(key) or default_list[0],
                       "default": default_list[0], "options": options, "order": _effective_chain(key)}
    return {"providers": providers, "chains": chains, "all_models": all_models, "budgets": M.budgets_status()}


async def set_model_config(chain_key: str, model_id: str) -> None:
    """Persist the preferred first model for a task chain."""
    if chain_key in FALLBACK_CHAINS:
        over = _overrides()
        over[chain_key] = model_id
        await app_state.set("llm.overrides", over)
        log.info("model_override_updated", chain=chain_key, selected_model=model_id)


def _effective_chain(chain_name: str) -> List[str]:
    chain = list(FALLBACK_CHAINS.get(chain_name, FALLBACK_CHAINS["fast"]))
    override = _overrides().get(chain_name)
    if override:
        if override in chain:
            chain.remove(override)
        chain.insert(0, override)
    return chain


# A model that would make a call wait longer than this is passed over for the next free model in the chain:
# one busy free tier (e.g. Flash Lite at 15 requests/minute) must not queue every call while Kilo, NIM and Groq sit idle.
SPILL_WAIT_S = 2.0
MAX_INFLIGHT = 3          # calls one model handles at once before the next free model takes the overflow
_inflight: Dict[str, int] = {}


def _eta(model: str) -> float:
    wait = M.budget(model).eta()
    if model.startswith("nim/"):
        wait = max(wait, M.budget(M.NIM_ACCOUNT).eta())     # NIM's 40/min is shared by all its models
    return wait


def _skip_reason(model: str) -> str | None:
    provider = M.provider_of(model)
    if not M.provider_key(provider):
        return "no API key"
    if M.key_rejected(provider):
        return "API key rejected — replace it in Settings"
    if not app_state.llm_provider_enabled(provider):
        return "provider turned off"
    if M.is_listed(model) is False:
        return "not available on this account"
    return M.budget(model).exhausted() or M.resting(model)


# ---------------------------------------------------------------------------
# Concurrency semaphores — per-provider
# ---------------------------------------------------------------------------

_semaphores: Dict[int, Dict[str, asyncio.Semaphore]] = {}

# Minimum delay (seconds) between requests per provider to respect RPM limits.
# Groq free: 30 RPM → 1 req per 2s minimum
# Mistral free: ~60 RPM → 1 req per 1s minimum
# Gemini 3.5 Flash Lite free: 15 RPM (250K TPM / 500 RPD) → 1 req per 4.0s minimum
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
    "nvidia": 20.0,
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
    if model.startswith("kilo/"):
        return model                    # Kilo limits are per model: a busy one hands over to the next free model
    if model.startswith("nim/"):
        return "nvidia"
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


async def _enforce_rate_limit(model: str, est_tokens: int = 1000) -> None:
    """Respect the model's free-tier RPM / TPM before sending a request."""
    await M.budget(model).acquire(est_tokens)


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
    elif model_name in HIDDEN_REASONING_MODELS:
        params["reasoning_format"] = "hidden"
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

    est = sum(len(str(m.get("content", ""))) for m in params.get("messages", [])) // 4 + int(params.get("max_tokens") or 768)
    for attempt in range(max_attempts):
        # Respect the model's RPM / TPM budget
        await _enforce_rate_limit(model, est)

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
    from google.genai import types
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120_000))

    system_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
    user_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") != "system")

    contents = []
    if system_content:
        contents.append(f"SYSTEM INSTRUCTIONS:\n{system_content}")
    contents.append(f"USER:\n{user_content}")
    prompt_str = "\n\n".join(contents)

    cfg: Dict[str, Any] = {"automatic_function_calling": {"disable": True}}   # no tools; also stops the "AFC is enabled" log
    max_tokens = kwargs.get("max_tokens") or kwargs.get("max_output_tokens")
    if max_tokens:
        cfg["max_output_tokens"] = max_tokens

    t0 = time.monotonic()

    def _sync_generate():
        return client.models.generate_content(
            model=raw_model,
            contents=prompt_str,
            config=cfg,
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

    # Inject current date system prompt for all agent calls
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_prefix = (
        f"Today's date is {today_str}. Judge dates, freshness and deadlines relative to it.\n\n"
    )

    has_system = False
    formatted_messages = []
    for m in messages:
        if m.get("role") == "system":
            has_system = True
            content = m.get("content", "")
            if "Today's date is" not in content:
                m = {**m, "content": date_prefix + content}
        formatted_messages.append(m)

    if not has_system:
        formatted_messages.insert(0, {"role": "system", "content": date_prefix.strip()})
    messages = formatted_messages

    # --- Cache check ---
    ck = _cache_key(model, messages, kwargs) if use_cache else None
    if use_cache and ck:
        cache = _get_cache()
        cached = cache.get(ck)
        if cached is not None:
            log.info("llm_cache_hit", model=model)
            return {**cached, "cache_hit": True}

    # --- Kilo Gateway / NVIDIA NIM: direct OpenAI-compatible calls (Kilo's free pool must get no auth header) ---
    if model.startswith(("kilo/", "nim/")):
        from jobhunterx.config import openai_compat as oc
        provider = M.provider_of(model)
        key = M.provider_key(provider)
        base = oc.KILO_BASE if provider == "kilo" else oc.NIM_BASE
        json_mode = any("JSON object" in (m.get("content") or "") for m in messages if m.get("role") == "system")
        est = sum(len(m.get("content", "")) for m in messages) // 4 + int(kwargs.get("max_tokens") or 1024)
        if provider == "nvidia":
            await M.budget(M.NIM_ACCOUNT).acquire(0)       # 40 requests/minute shared by every NIM model
        await _enforce_rate_limit(model, est)
        # thinking models need room: a tiny budget can end before the answer starts
        budget_out = max(1500, int(kwargs.get("max_tokens") or 1024))
        try:
            for attempt in range(2):
                try:
                    out = await oc.chat(base, model.split("/", 1)[1], messages, key=None if key == M.KILO_FREE else key,
                                        max_tokens=budget_out, temperature=kwargs.get("temperature"), json_mode=json_mode,
                                        timeout=75, extra=oc.KILO_EXTRA if provider == "kilo" else None)
                    break
                except oc.EmptyAnswer:
                    if attempt:
                        raise
                    budget_out = min(8192, budget_out * 3)      # one retry with more room before moving on
        except oc.ChatError as exc:
            if exc.status == 429:
                _record_rate_limit(model)
            raise
        content = _THINK_RE.sub("", out["content"])
        result = {"content": content, "tokens_in": out["tokens_in"] or max(1, est // 2), "tokens_out": out["tokens_out"] or max(1, len(content) // 4),
                  "model": model, "latency_ms": out["latency_ms"], "cache_hit": False}
        M.budget(model).record(result["tokens_in"] + result["tokens_out"])
        log.info("llm_call", model=model, served_by=out["served_by"], latency_ms=out["latency_ms"])
        try:
            from jobhunterx.config import database as _db
            if _db._db_path:
                await _db.log_agent_event(run_id=ck or "llm", agent_name="openai_compat", event_type="llm_call",
                                          tokens_in=result["tokens_in"], tokens_out=result["tokens_out"], model=model,
                                          latency_ms=result["latency_ms"])
        except Exception as exc:
            log.warning("llm_db_log_failed", error=str(exc))
        if use_cache and ck:
            _get_cache().set(ck, result, expire=cache_ttl)
        return result

    # --- Direct Google GenAI SDK routing for ALL Gemini & Gemma models ---
    if model.startswith("gemini/") or model.startswith("google/") or "gemma" in model:
        if "gemma" in model:
            from jobhunterx.config.gemma import call_gemma
            system_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
            user_content = "\n\n".join(m.get("content", "") for m in messages if m.get("role") != "system")
            t0 = time.monotonic()
            await _enforce_rate_limit(model, (len(system_content) + len(user_content)) // 4 + int(kwargs.get("max_tokens", 1024)))
            content = await call_gemma(
                model=model.split("/", 1)[-1],
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
            await _enforce_rate_limit(model, sum(len(m.get("content", "")) for m in messages) // 4 + int(kwargs.get("max_tokens") or 1024))
            result = await _call_google_genai(model, messages, **kwargs)
        M.budget(model).record(result["tokens_in"] + result["tokens_out"])

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
    content = _THINK_RE.sub("", choice.message.content or "")
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
    M.budget(model).record(result["tokens_in"] + result["tokens_out"])

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
    chain = _effective_chain(chain_name)
    if not any(M.is_listed(m) is not None for m in chain):
        try:   # first use: learn which models this account can call (cached for hours)
            await asyncio.wait_for(M.refresh_available(), timeout=20)
        except Exception:
            pass
    last_err: Exception | None = None
    skipped: list[str] = []
    rested: list[str] = []
    usable: list[str] = []

    for model in chain:
        reason = _skip_reason(model)
        if reason:
            skipped.append(f"{model} ({reason})")
            if reason.startswith("resting"):
                rested.append(model)
            continue

        # Skip providers currently in rate-limit cooldown
        if not _is_provider_available(model):
            provider = _get_provider_key(model)
            remaining = max(0, _provider_rate_limited_until.get(provider, 0) - time.monotonic())
            log.info("llm_fallback_skip_cooldown", model=model, provider=provider, cooldown_remaining_s=round(remaining, 1))
            continue
        usable.append(model)

    # Chain order among models that can answer now; busy ones go last, least busy first.
    etas = {m: _eta(m) for m in usable}
    ready = [m for m in usable if etas[m] <= SPILL_WAIT_S and _inflight.get(m, 0) < MAX_INFLIGHT]
    order = ready + sorted((m for m in usable if m not in ready), key=lambda m: (etas[m], _inflight.get(m, 0)))
    if order and usable and order[0] != usable[0]:
        log.info("llm_spill", chain=chain_name, busy=usable[0], wait_s=round(etas[usable[0]], 1), to=order[0])

    for model in order:
        _inflight[model] = _inflight.get(model, 0) + 1
        try:
            result = await call_llm(model, messages, **kwargs)
            M.mark_success(model)
            return result
        except Exception as exc:
            rest = M.mark_failure(model, str(exc))
            log.warning("llm_fallback", model=model, error=str(exc)[:200], next_try_in_s=int(rest) if rest else None)
            last_err = exc
        finally:
            _inflight[model] -= 1

    for model in rested if last_err is None else []:   # everything is resting: better to try than to fail
        try:
            result = await call_llm(model, messages, **kwargs)
            M.mark_success(model)
            return result
        except Exception as exc:
            M.mark_failure(model, str(exc))
            last_err = exc

    if last_err is None:
        raise RuntimeError(f"No AI model is usable for '{chain_name}': " + "; ".join(skipped)
                           + ". Add an API key or turn a provider on in Settings.")
    raise RuntimeError(f"All models in chain '{chain_name}' failed. Last error: {last_err}")
