"""
Model catalog, free-tier limits, live availability and per-model rate limiting.

Limits are the providers' published free-tier numbers (Google AI Studio, Groq
free plan, Mistral free/Experiment plan) as of October 2026. They change often,
so three safety nets keep the app working when they drift:

* every limit can be overridden with MODEL_LIMITS_JSON in .env, e.g.
  MODEL_LIMITS_JSON={"gemini/gemma-4-31b-it": {"rpm": 30, "rpd": 14400}}
* the provider's own /models endpoint is queried with your key, and models the
  account cannot use are skipped instead of failing every call;
* a 429 puts that provider in cooldown and the chain moves on.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings

log = get_logger("models")

# rpm / rpd = requests per minute / day; tpm / tpd = tokens per minute / day. None = not limited (or unknown).
CATALOG: list[dict[str, Any]] = [
    # Google AI Studio — Gemma runs on the Gemini API (no system role: instructions are sent inline).
    {"id": "gemini/gemma-4-31b-it", "name": "Gemma 4 31B", "provider": "google", "rpm": 15, "rpd": 1500, "tpm": None, "tpd": None,
     "note": "Dense 31B, 256K context. Strong reasoning; slower than the MoE models."},
    {"id": "gemini/gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite", "provider": "google", "rpm": 15, "rpd": 500, "tpm": 250_000, "tpd": None,
     "note": "Fast, low latency."},
    # Groq — production/preview open models (Llama deliberately not used).
    {"id": "groq/openai/gpt-oss-120b", "name": "GPT-OSS 120B", "provider": "groq", "rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000,
     "note": "Best open reasoning model on Groq; low TPM on the free plan."},
    {"id": "groq/moonshotai/kimi-k2-instruct-0905", "name": "Kimi K2 (0905)", "provider": "groq", "rpm": 60, "rpd": 1000, "tpm": 10_000, "tpd": 300_000,
     "note": "Strong writing and instruction following."},
    {"id": "groq/moonshotai/kimi-k2-instruct", "name": "Kimi K2", "provider": "groq", "rpm": 60, "rpd": 1000, "tpm": 10_000, "tpd": 300_000,
     "note": "Used if the 0905 build is not on your account."},
    {"id": "groq/qwen/qwen3.6-27b", "name": "Qwen3.6 27B", "provider": "groq", "rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000,
     "note": "Newest Qwen on Groq; strong structured output."},
    {"id": "groq/qwen/qwen3-32b", "name": "Qwen3 32B", "provider": "groq", "rpm": 60, "rpd": 1000, "tpm": 6000, "tpd": 500_000,
     "note": "Used if Qwen3.6 is not on your account; large daily token budget."},
    {"id": "groq/openai/gpt-oss-20b", "name": "GPT-OSS 20B", "provider": "groq", "rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000,
     "note": "Fast and light."},
    # Mistral — free-plan limits are per model and per account (Admin console → Limits); these match the
    # project's documented account limits (requests/second converted to RPM).
    {"id": "mistral/mistral-medium-latest", "name": "Mistral Medium (latest)", "provider": "mistral", "rpm": 50, "rpd": None, "tpm": 25_000, "tpd": None,
     "note": "Flagship; reasoning toggle."},
    {"id": "mistral/mistral-small-latest", "name": "Mistral Small (latest)", "provider": "mistral", "rpm": 50, "rpd": None, "tpm": 50_000, "tpd": None,
     "note": "Fast, multimodal."},
    {"id": "mistral/mistral-large-latest", "name": "Mistral Large (latest)", "provider": "mistral", "rpm": 4, "rpd": None, "tpm": 250_000, "tpd": None,
     "note": "Heavy reasoning; very low request rate on the free plan."},
]
BY_ID = {m["id"]: m for m in CATALOG}

# Task → ordered preferences. Unavailable/disabled models are skipped at call time.
CHAINS: dict[str, list[str]] = {
    "fast": ["gemini/gemma-4-31b-it", "gemini/gemini-3.5-flash-lite", "groq/openai/gpt-oss-20b", "groq/qwen/qwen3.6-27b",
             "groq/qwen/qwen3-32b", "mistral/mistral-small-latest"],
    "reasoning": ["gemini/gemma-4-31b-it", "gemini/gemini-3.5-flash-lite", "groq/openai/gpt-oss-120b",
                  "groq/moonshotai/kimi-k2-instruct-0905", "groq/moonshotai/kimi-k2-instruct", "mistral/mistral-medium-latest"],
    "tailoring": ["gemini/gemma-4-31b-it", "gemini/gemini-3.5-flash-lite", "groq/moonshotai/kimi-k2-instruct-0905",
                  "groq/moonshotai/kimi-k2-instruct", "groq/openai/gpt-oss-120b", "mistral/mistral-medium-latest"],
    "extraction": ["gemini/gemma-4-31b-it", "gemini/gemini-3.5-flash-lite", "groq/openai/gpt-oss-120b", "groq/qwen/qwen3.6-27b",
                   "groq/qwen/qwen3-32b", "mistral/mistral-medium-latest"],
    "browser": ["gemini/gemini-3.5-flash-lite", "groq/openai/gpt-oss-120b", "mistral/mistral-small-latest"],
}
CHAIN_LABELS = {"fast": "Quick tasks", "reasoning": "Matching & analysis", "tailoring": "Resume & letter writing",
                "extraction": "Resume reading", "browser": "Browser agent"}


def provider_of(model: str) -> str:
    return {"gemini": "google", "groq": "groq", "mistral": "mistral"}.get(model.split("/", 1)[0], "other")


def limits(model: str) -> dict[str, Optional[int]]:
    base = {k: BY_ID.get(model, {}).get(k) for k in ("rpm", "rpd", "tpm", "tpd")}
    raw = os.getenv("MODEL_LIMITS_JSON") or getattr(get_settings(), "model_limits_json", "") or ""
    if raw:
        try:
            base.update({k: v for k, v in (json.loads(raw).get(model) or {}).items() if k in base})
        except (ValueError, AttributeError):
            log.warning("model_limits_json_invalid")
    return base


def provider_key(provider: str) -> Optional[str]:
    s = get_settings()
    if provider == "google":
        return s.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if provider == "groq":
        return s.groq_api_key or os.getenv("GROQ_API_KEY")
    if provider == "mistral":
        return s.mistral_api_key or os.getenv("MISTRAL_API_KEY")
    return None


# ---------------------------------------------------------------------------
# Live availability (provider /models endpoints, cached)
# ---------------------------------------------------------------------------

_available: dict[str, dict[str, Any]] = {}   # provider -> {"ids": set, "at": monotonic, "error": str|None, "all": [...]}
_TTL_S = 6 * 3600
_refresh_lock: Optional[asyncio.Lock] = None


async def _list_provider(provider: str, key: str) -> list[str]:
    if provider == "google":
        from google import genai

        def _sync() -> list[str]:
            client = genai.Client(api_key=key)
            return [m.name.split("/", 1)[-1] for m in client.models.list()]
        return [f"gemini/{n}" for n in await asyncio.to_thread(_sync)]
    import httpx
    url = {"groq": "https://api.groq.com/openai/v1/models", "mistral": "https://api.mistral.ai/v1/models"}[provider]
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {key}"})
        r.raise_for_status()
        data = r.json().get("data", [])
    out = []
    for m in data:
        mid = m.get("id")
        if mid and m.get("active", True) is not False:
            out.append(f"{provider}/{mid}")
            for alias in m.get("aliases") or []:          # Mistral exposes *-latest as aliases
                out.append(f"{provider}/{alias}")
    return out


async def refresh_available(force: bool = False) -> dict[str, dict[str, Any]]:
    """Ask each configured provider which models this key can use (cached for 6 h)."""
    global _refresh_lock
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    async with _refresh_lock:
        now = time.monotonic()
        for provider in ("google", "groq", "mistral"):
            key = provider_key(provider)
            if not key:
                _available.pop(provider, None)
                continue
            cur = _available.get(provider)
            if cur and not force and now - cur["at"] < _TTL_S and not cur.get("error"):
                continue
            try:
                ids = await _list_provider(provider, key)
                _available[provider] = {"ids": set(ids), "all": sorted(set(ids)), "at": now, "error": None}
                log.info("models_discovered", provider=provider, count=len(ids))
            except Exception as exc:   # network / auth problems must never block calls
                _available[provider] = {"ids": set(), "all": [], "at": now, "error": str(exc)[:200]}
                log.warning("models_discovery_failed", provider=provider, error=str(exc)[:200])
    return _available


def is_listed(model: str) -> Optional[bool]:
    """True/False when the provider's list is known, None when unknown (then we just try)."""
    info = _available.get(provider_of(model))
    if not info or info.get("error") or not info["ids"]:
        return None
    return model in info["ids"]


def availability() -> dict[str, Any]:
    return {p: {"ok": not v.get("error"), "error": v.get("error"), "count": len(v["ids"]), "models": v["all"][:200]}
            for p, v in _available.items()}


# ---------------------------------------------------------------------------
# Per-model limiter: RPM spacing, rolling TPM window, daily RPD/TPD counters
# ---------------------------------------------------------------------------

class _ModelBudget:
    def __init__(self, model: str):
        self.model = model
        self.lock = asyncio.Lock()
        self.last = 0.0
        self.window: deque[tuple[float, int]] = deque()
        self.day = ""
        self.req_today = 0
        self.tok_today = 0

    def _roll_day(self) -> None:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if d != self.day:
            self.day, self.req_today, self.tok_today = d, 0, 0

    def exhausted(self) -> Optional[str]:
        self._roll_day()
        lim = limits(self.model)
        if lim["rpd"] and self.req_today >= lim["rpd"]:
            return "daily request limit reached"
        if lim["tpd"] and self.tok_today >= lim["tpd"]:
            return "daily token limit reached"
        return None

    async def acquire(self, est_tokens: int) -> None:
        lim = limits(self.model)
        async with self.lock:
            now = time.monotonic()
            if lim["rpm"]:
                wait = self.last + 60.0 / lim["rpm"] - now
                if wait > 0:
                    await asyncio.sleep(wait)
            if lim["tpm"]:
                while True:
                    now = time.monotonic()
                    while self.window and now - self.window[0][0] > 60:
                        self.window.popleft()
                    used = sum(t for _, t in self.window)
                    if used + est_tokens <= lim["tpm"] or not self.window:
                        break
                    await asyncio.sleep(max(0.5, 60 - (now - self.window[0][0])))
            self.last = time.monotonic()
            self.window.append((self.last, est_tokens))
            self._roll_day()
            self.req_today += 1

    def record(self, tokens: int) -> None:
        self._roll_day()
        self.tok_today += tokens

    def status(self) -> dict[str, Any]:
        self._roll_day()
        return {"requests_today": self.req_today, "tokens_today": self.tok_today, **limits(self.model)}


_budgets: dict[str, _ModelBudget] = {}


def budget(model: str) -> _ModelBudget:
    if model not in _budgets:
        _budgets[model] = _ModelBudget(model)
    return _budgets[model]


def budgets_status() -> dict[str, dict[str, Any]]:
    return {m: b.status() for m, b in _budgets.items()}
