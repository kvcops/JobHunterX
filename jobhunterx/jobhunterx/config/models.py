"""
Model catalog, free-tier limits, live availability and per-model rate limiting.

Limits are the providers' published free-tier numbers (Google AI Studio, Groq
free plan, Mistral free/Experiment plan) as of October 2026. They change often,
so three safety nets keep the app working when they drift:

* every limit can be overridden with MODEL_LIMITS_JSON in .env, e.g.
  MODEL_LIMITS_JSON={"gemini/gemini-3.5-flash-lite": {"rpm": 30, "rpd": 1000}}
* the provider's own /models endpoint is queried with your key, and models the
  account cannot use are skipped instead of failing every call;
* a 429 puts that provider in cooldown and the chain moves on.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings, is_real_key

log = get_logger("models")

# rpm / rph / rpd = requests per minute / hour / day; tpm / tpd = tokens per minute / day. None = not limited (or unknown).
CATALOG: list[dict[str, Any]] = [
    # Kilo Gateway free pool — no API key, no card. 200 requests/hour per model. Measured Oct 2026 (JSON answers):
    # kilo-auto/free ~1-2 s, Nemotron 3 Super ~1.2-3 s, Laguna S ~2.7 s, Ling 3.1 Flash ~3.6 s, Nemotron 3 Nano Omni ~3.4 s.
    # Avoided: thinking models that spend the whole budget reasoning (Step 3.7 Flash, Dots, Apodex, LFM, openrouter/free)
    # and slow ones (Qwen3.8 27B ~23 s, Nemotron 3.5 Lightning ~20 s). NOTE: every free model here may use prompts for training.
    {"id": "kilo/kilo-auto/free", "name": "Kilo Auto (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Kilo routes each request to a fast free model. ~1-2 s. No key."},
    {"id": "kilo/nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Strong MoE (12B active), clean JSON, ~1-3 s. No key."},
    {"id": "kilo/poolside/laguna-s-2.1:free", "name": "Laguna S 2.1 (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Fast, reliable JSON, ~2.7 s. No key."},
    # Added 17 Oct 2026 (live JSON test, thinking off): Nemotron 3.5 Super VL 1.2-2.6 s (first call can be a slow cold
    # start), Dots 3 Note 2-4 s, North Mini Code 2-5 s, Xing 4.0 5-9 s. Ling 3.1 Flash was removed by Kilo. Tried and left
    # out: Nemotron 3 Ultra (empty answers), Inkling Small (tiny daily limit), Laguna XS (thinks, rate-limited),
    # Nemotron 3.5 Lightning (70-90 s), LFM 2.5 (400), openrouter/free (unreliable JSON).
    {"id": "kilo/nvidia/nemotron-3.5-super-vl:free", "name": "Nemotron 3.5 Super VL (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Newest Nemotron, clean JSON, ~1-3 s. No key."},
    {"id": "kilo/dots-studio/dots-3-note-preview:free", "name": "Dots 3 Note (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Preview model, clean JSON, ~2-4 s. No key."},
    {"id": "kilo/cohere/north-mini-code:free", "name": "North Mini Code (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Small and quick, clean JSON, ~2-5 s. No key."},
    {"id": "kilo/xingchen-agi/xing4.0-29b-a4b:free", "name": "Xing 4.0 29B (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Small MoE (4B active), ~5-9 s. No key."},
    {"id": "kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "name": "Nemotron 3 Nano Omni (Kilo, free)", "provider": "kilo", "rpm": None, "rph": 200, "rpd": None, "tpm": None, "tpd": None,
     "note": "Small MoE (3B active), ~3.4 s. No key."},
    # LLM7.io free tier — no API key, no account. Limits are not published: one request at a time per client, short
    # per-minute caps and a small daily token quota per client. Re-measured 17 Oct 2026: DeepSeek V4 Pro and MiniMax M3
    # became paid-only ("Missing API key"); the free ones answer in 10-60 s and sometimes wrongly — so LLM7 is the very
    # last resort in every chain. Paid-only models are dropped automatically from LLM7's own list (usage_based_only).
    {"id": "llm7/GLM-5.3-Flash", "name": "GLM 5.3 Flash (LLM7, free)", "provider": "llm7", "rpm": None, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Last-resort backup, ~10 s. No key."},
    {"id": "llm7/DeepSeek-V4-Flash-0731", "name": "DeepSeek V4 Flash (LLM7, free)", "provider": "llm7", "rpm": None, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Last-resort backup, slow (30-60 s). No key."},
    # NVIDIA NIM (build.nvidia.com) — free key, 40 requests/minute per ACCOUNT across all models. Chosen from a live test with a
    # real free key on 29 Oct 2026 (JSON extraction + a fact-keeping rewrite, thinking off):
    #   Nemotron 3 Ultra 550B 1-7 s, kept every fact · Nemotron 3.5 Lightning / Bolt ~1 s (fast, but dropped a number when
    #   rewriting, so not used for writing) · GPT-OSS 20B 2-6 s (reasoning effort low) · Nemotron 3 Nano Omni 1.4 s but often
    #   "16/16 requests" busy · MiniMax M3.1 Flash 3-25 s, always thinks a little.
    # Left out: Nemotron 3 Super, Nemotron Nano 3, Kimi K2.6 (listed, but "Not found for account" on the free key), DeepSeek V4.1
    # Flash, GLM 5.3 Flash, Step 5 (no answer within 150 s), Llama models (not used), Gemma (dropped app-wide).
    {"id": "nim/nvidia/nemotron-3-ultra-550b-a55b", "name": "Nemotron 3 Ultra 550B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Strongest free NVIDIA model; 1-7 s, clean JSON, keeps facts when rewriting. Thinking off."},
    # Second round, 29 Oct 2026 (same four tasks: extraction, fit judgment, fact-keeping rewrite, cover-letter paragraph; x2):
    #   Mistral Large 4 8/8, 1-6 s, the only one that kept the "2,000" figure AND invented nothing — the best writer here ·
    #   Nemotron 3.5 Super VL 8/8, 0.8-2.3 s (dropped the figure, invented nothing) · Muse Glimmer 30B 7/8, kept facts, 7-21 s ·
    #   DiffusionGemma 26B judged well but added the job's tools in both rewrites (never used for writing), 3-15 s.
    #   Still left out: Laguna XS 2.1 (busy 503 on every call), DeepSeek V4.1 Flash / GLM 5.3 Flash / Step 5 (45 s timeouts).
    {"id": "nim/mistralai/mistral-large-4-1t-a52b", "name": "Mistral Large 4 (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Best writer in the tests: keeps every fact, invents nothing; 1-6 s. Reasoning effort low."},
    {"id": "nim/nvidia/nemotron-3.5-super-vl-120b-a12b", "name": "Nemotron 3.5 Super VL 120B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Fastest of the strong models (0.8-2.3 s), clean JSON. Thinking off."},
    {"id": "nim/meta/muse-glimmer-30b", "name": "Muse Glimmer 30B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Keeps facts, but slow (7-21 s). Backup. Reasoning effort low."},
    {"id": "nim/google/diffusiongemma-26b-a4b-it", "name": "DiffusionGemma 26B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Judges well, 3-15 s; adds unused tools when rewriting, so never used for writing. Late backup."},
    {"id": "nim/nvidia/nemotron-3.5-lightning-30b-a3b", "name": "Nemotron 3.5 Lightning 30B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "3B active, ~1 s, clean JSON. Quick tasks. Thinking off."},
    {"id": "nim/nvidia/nemotron-3.5-bolt-e4b", "name": "Nemotron 3.5 Bolt (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Tiny and ~1 s. Quick tasks only."},
    {"id": "nim/openai/gpt-oss-20b", "name": "GPT-OSS 20B (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "2-6 s, reliable JSON, keeps facts. Reasoning effort low."},
    {"id": "nim/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "name": "Nemotron 3 Nano Omni (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Fast when free, often busy (503). Backup. Thinking off."},
    # MiniMax M3.1 Flash, tested separately (reasoning effort low): the most thorough job-fit judgments of the three and good
    # cover-letter prose, 3-13 s; but in resume-bullet rewrites it added the job's tools the candidate never used (both runs) —
    # the fact-checker rejects that — so it is second for analysis and third for writing. Its shared endpoint often answers 429.
    {"id": "nim/minimaxai/minimax-m3.1-flash", "name": "MiniMax M3.1 Flash (NIM)", "provider": "nvidia", "rpm": 40, "rph": None, "rpd": None, "tpm": None, "tpd": None,
     "note": "Thorough analysis and good prose, 3-13 s with reasoning effort low. Second for matching, third for writing."},
    # Google AI Studio.
    {"id": "gemini/gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite", "provider": "google", "rpm": 15, "rpd": 500, "tpm": 250_000, "tpd": None,
     "note": "Fast (~1 s) and reliable — first choice for every task."},
    # Groq — production/preview open models (Llama deliberately not used).
    {"id": "groq/openai/gpt-oss-120b", "name": "GPT-OSS 120B", "provider": "groq", "rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000,
     "note": "Best open reasoning model on Groq; low TPM on the free plan."},
    {"id": "groq/moonshotai/kimi-k2-instruct-0905", "name": "Kimi K2 (0905)", "provider": "groq", "rpm": 60, "rpd": 1000, "tpm": 10_000, "tpd": 300_000,
     "note": "Strong writing and instruction following."},
    {"id": "groq/moonshotai/kimi-k2-instruct", "name": "Kimi K2", "provider": "groq", "rpm": 60, "rpd": 1000, "tpm": 10_000, "tpd": 300_000,
     "note": "Used if the 0905 build is not on your account."},
    {"id": "groq/qwen/qwen3.8-27b", "name": "Qwen3.8 27B", "provider": "groq", "rpm": 30, "rpd": 1000, "tpm": None, "tpd": None,
     "note": "Newest Qwen on Groq (replaced Qwen3.6 / Qwen3 32B). Measured 17 Oct 2026: ~0.2 s, clean JSON, no thinking."},
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
# Live tests (Oct 2026): Gemini 3.5 Flash Lite answers in ~1 s, so it leads every chain.
# Order: Gemini Flash Lite (fastest, if you have a key) -> Kilo free pool (no key) -> NVIDIA NIM -> Groq -> Mistral -> LLM7.
# Kilo models are spread across chains so their 200 req/hour per-model budgets add up.
# NVIDIA NIM (free key): 40 requests/minute for the whole account — about 2,400 an hour against Kilo's 200 an hour per model —
# so with a key NIM leads right after Gemini. Without a key these entries are skipped. Thinking is off / low on all of them.
_NIM_FAST = ["nim/nvidia/nemotron-3.5-lightning-30b-a3b", "nim/nvidia/nemotron-3.5-super-vl-120b-a12b",
             "nim/nvidia/nemotron-3.5-bolt-e4b", "nim/openai/gpt-oss-20b", "nim/google/diffusiongemma-26b-a4b-it"]
_NIM_SMART = ["nim/mistralai/mistral-large-4-1t-a52b", "nim/nvidia/nemotron-3-ultra-550b-a55b", "nim/nvidia/nemotron-3.5-super-vl-120b-a12b",
              "nim/minimaxai/minimax-m3.1-flash", "nim/openai/gpt-oss-20b", "nim/nvidia/nemotron-3.5-lightning-30b-a3b",
              "nim/meta/muse-glimmer-30b", "nim/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "nim/google/diffusiongemma-26b-a4b-it"]
_NIM_READ = ["nim/mistralai/mistral-large-4-1t-a52b", "nim/nvidia/nemotron-3.5-super-vl-120b-a12b", "nim/nvidia/nemotron-3-ultra-550b-a55b",
             "nim/openai/gpt-oss-20b", "nim/minimaxai/minimax-m3.1-flash", "nim/nvidia/nemotron-3.5-lightning-30b-a3b",
             "nim/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"]
# writing: only models that never invented a tool in the rewrite test lead; MiniMax (keyword-stuffs rewrites) comes last.
# DiffusionGemma is never used for writing.
_NIM_WRITE = ["nim/mistralai/mistral-large-4-1t-a52b", "nim/nvidia/nemotron-3-ultra-550b-a55b", "nim/openai/gpt-oss-20b",
              "nim/meta/muse-glimmer-30b", "nim/minimaxai/minimax-m3.1-flash"]
_KILO_FAST = ["kilo/kilo-auto/free", "kilo/nvidia/nemotron-3-super-120b-a12b:free", "kilo/dots-studio/dots-3-note-preview:free",
              "kilo/cohere/north-mini-code:free", "kilo/poolside/laguna-s-2.1:free"]
_KILO_SMART = ["kilo/nvidia/nemotron-3-super-120b-a12b:free", "kilo/nvidia/nemotron-3.5-super-vl:free", "kilo/kilo-auto/free",
               "kilo/dots-studio/dots-3-note-preview:free", "kilo/poolside/laguna-s-2.1:free", "kilo/xingchen-agi/xing4.0-29b-a4b:free",
               "kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"]
# No-key backup after Kilo: LLM7 (one call at a time, small daily quota).
_LLM7 = ["llm7/GLM-5.3-Flash", "llm7/DeepSeek-V4-Flash-0731"]
CHAINS: dict[str, list[str]] = {
    # quick tasks want speed; LLM7 last (slow)
    "fast": ["gemini/gemini-3.5-flash-lite", *_NIM_FAST, *_KILO_FAST, "groq/qwen/qwen3.8-27b",
             "groq/openai/gpt-oss-20b", "mistral/mistral-small-latest", *_LLM7],
    "reasoning": ["gemini/gemini-3.5-flash-lite", *_NIM_SMART, *_KILO_SMART, "groq/qwen/qwen3.8-27b",
                  "groq/openai/gpt-oss-120b", "groq/moonshotai/kimi-k2-instruct-0905",
                  "groq/moonshotai/kimi-k2-instruct", "mistral/mistral-medium-latest", *_LLM7],
    "tailoring": ["gemini/gemini-3.5-flash-lite", *_NIM_WRITE, "kilo/nvidia/nemotron-3-super-120b-a12b:free", "kilo/kilo-auto/free", "groq/qwen/qwen3.8-27b",
                  "groq/moonshotai/kimi-k2-instruct-0905", "groq/moonshotai/kimi-k2-instruct", "groq/openai/gpt-oss-120b",
                  "mistral/mistral-medium-latest", *_LLM7],
    "extraction": ["gemini/gemini-3.5-flash-lite", *_NIM_READ, *_KILO_SMART, "groq/qwen/qwen3.8-27b",
                   "mistral/mistral-medium-latest", "groq/openai/gpt-oss-120b",
                   *_LLM7],
    # chat editor for resumes / CVs / letters: Gemini 3.5 Flash Lite or Kilo's free models only, thinking off
    "editor": ["gemini/gemini-3.5-flash-lite", *_KILO_FAST],
    "browser": ["gemini/gemini-3.5-flash-lite", "nim/nvidia/nemotron-3.5-super-vl-120b-a12b", "nim/mistralai/mistral-large-4-1t-a52b",
                "nim/nvidia/nemotron-3-ultra-550b-a55b", "kilo/nvidia/nemotron-3-super-120b-a12b:free", "groq/openai/gpt-oss-120b",
                "mistral/mistral-small-latest", "llm7/GLM-5.3-Flash"],
}
CHAIN_LABELS = {"fast": "Quick tasks", "reasoning": "Matching & analysis", "tailoring": "Resume & letter writing",
                "extraction": "Resume reading", "editor": "Resume chat editor", "browser": "Browser agent"}


def provider_of(model: str) -> str:
    return {"gemini": "google", "groq": "groq", "mistral": "mistral", "kilo": "kilo", "nim": "nvidia", "llm7": "llm7"}.get(model.split("/", 1)[0], "other")


KILO_FREE = "free"                # Kilo's free pool needs no key; a Kilo account key (optional) is used when set
NIM_ACCOUNT = "nim/__account__"   # one shared limiter: NIM's 40 requests/minute counts across all models
NIM_ACCOUNT_RPM = 36              # 10% under the documented 40/min, so retries and parallel searches stay inside it
# Shared limiters for providers whose limits count per client, not per model.
# LLM7: about one call every 5 s keeps clear of its short per-minute caps.
ACCOUNT_LIMITERS = {"llm7": ("llm7/__account__", 12)}


def account_limiter(model: str) -> Optional[str]:
    """The shared limiter id for a model whose provider limits calls per account / IP (None when limits are per model)."""
    if model.startswith("nim/"):
        return NIM_ACCOUNT
    hit = ACCOUNT_LIMITERS.get(provider_of(model))
    return hit[0] if hit else None


def limits(model: str) -> dict[str, Optional[int]]:
    if model == NIM_ACCOUNT:
        return {"rpm": NIM_ACCOUNT_RPM, "rph": None, "rpd": None, "tpm": None, "tpd": None}
    for lid, rpm in ACCOUNT_LIMITERS.values():
        if model == lid:
            return {"rpm": rpm, "rph": None, "rpd": None, "tpm": None, "tpd": None}
    base = {k: BY_ID.get(model, {}).get(k) for k in ("rpm", "rph", "rpd", "tpm", "tpd")}
    raw = os.getenv("MODEL_LIMITS_JSON") or getattr(get_settings(), "model_limits_json", "") or ""
    if raw:
        try:
            base.update({k: v for k, v in (json.loads(raw).get(model) or {}).items() if k in base})
        except (ValueError, AttributeError):
            log.warning("model_limits_json_invalid")
    return base


def provider_key(provider: str) -> Optional[str]:
    from jobhunterx.config import auth_ctx
    if provider in auth_ctx.SHARED_POOLS and not auth_ctx.shared_pools_allowed():
        return None                     # prod mode: the IP-limited free pools are kept for the admin
    s = get_settings()
    env = {"google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"), "groq": ("GROQ_API_KEY",), "mistral": ("MISTRAL_API_KEY",),
           "nvidia": ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"), "kilo": ("KILO_API_KEY",)}.get(provider)
    if provider == "llm7":
        return KILO_FREE                # used without any key
    if env is None:
        return None
    candidates = [getattr(s, f"{provider}_api_key", None)] + [auth_ctx.env_key(n) for n in env]
    real = next((k for k in candidates if is_real_key(k)), None)
    if provider == "kilo":
        return real or KILO_FREE       # works without a key
    return real


# ---------------------------------------------------------------------------
# Live availability (provider /models endpoints, cached)
# ---------------------------------------------------------------------------

_available: dict[str, dict[str, Any]] = {}   # provider -> {"ids": set, "at": monotonic, "error": str|None, "all": [...]}
_TTL_S = 6 * 3600
_refresh_lock: Optional[asyncio.Lock] = None


async def _list_provider(provider: str, key: str) -> list[str]:
    if provider == "google":
        # plain REST: listing models must not load the whole Google SDK (tens of MB) at startup
        import httpx
        names: list[str] = []
        token = ""
        async with httpx.AsyncClient(timeout=20) as client:
            for _ in range(10):
                r = await client.get("https://generativelanguage.googleapis.com/v1beta/models",
                                     params={"pageSize": 1000, **({"pageToken": token} if token else {})},
                                     headers={"x-goog-api-key": key})
                r.raise_for_status()
                data = r.json()
                names += [m["name"].split("/", 1)[-1] for m in data.get("models", []) if m.get("name")]
                token = data.get("nextPageToken") or ""
                if not token:
                    break
        return [f"gemini/{n}" for n in names]
    if provider in ("kilo", "nvidia", "llm7"):
        from jobhunterx.config import openai_compat as oc
        base, prefix = {"kilo": (oc.KILO_BASE, "kilo"), "nvidia": (oc.NIM_BASE, "nim"),
                        "llm7": (oc.LLM7_BASE, "llm7")}[provider]
        data = await oc.list_models(base, None if key == KILO_FREE else key)
        # LLM7 marks paid models (usage_based_only): without a key they answer 401, so they are never "available"
        return [f"{prefix}/{m['id']}" for m in data if isinstance(m, dict) and m.get("id")
                and not (provider == "llm7" and m.get("usage_based_only"))]
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
    from jobhunterx.config import auth_ctx
    if auth_ctx.restricted() is not None:
        return _available               # the shared list is learned with the server's keys, never a user's
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    async with _refresh_lock:
        now = time.monotonic()
        for provider in ("google", "groq", "mistral", "kilo", "nvidia", "llm7"):
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
        self.hour: deque[float] = deque()      # request times in the last hour (per-hour limits like Kilo's)
        self.day = ""
        self.req_today = 0
        self.tok_today = 0
        self.waiting = 0                       # calls queued for this model right now

    def _roll_day(self) -> None:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if d != self.day:
            self.day, self.req_today, self.tok_today = d, 0, 0

    def exhausted(self) -> Optional[str]:
        self._roll_day()
        lim = limits(self.model)
        if lim["rpd"] and self.req_today >= lim["rpd"]:
            return "daily request limit reached"
        if lim.get("rph"):
            now = time.monotonic()
            while self.hour and now - self.hour[0] > 3600:
                self.hour.popleft()
            if len(self.hour) >= lim["rph"]:
                return "hourly request limit reached"
        if lim["tpd"] and self.tok_today >= lim["tpd"]:
            return "daily token limit reached"
        return None

    def eta(self, est_tokens: int = 0) -> float:
        """Seconds a new call would wait for this model's free-tier limits (queued calls included)."""
        lim = limits(self.model)
        now = time.monotonic()
        wait = 0.0
        if lim["rpm"]:
            gap = 60.0 / lim["rpm"]
            wait = max(0.0, self.last + gap - now) + self.waiting * gap
        if lim["tpm"] and self.window:
            used = sum(t for ts, t in self.window if now - ts <= 60)
            if used + est_tokens > lim["tpm"]:
                wait = max(wait, 60 - (now - self.window[0][0]))
        return wait

    async def acquire(self, est_tokens: int) -> None:
        self.waiting += 1
        try:
            await self._acquire(est_tokens)
        finally:
            self.waiting -= 1

    async def _acquire(self, est_tokens: int) -> None:
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
            self.hour.append(self.last)
            self._roll_day()
            self.req_today += 1

    def record(self, tokens: int) -> None:
        self._roll_day()
        self.tok_today += tokens

    def status(self) -> dict[str, Any]:
        self._roll_day()
        return {"requests_today": self.req_today, "tokens_today": self.tok_today, **limits(self.model)}


_budgets: dict[str, _ModelBudget] = {}


def _scope() -> str:
    from jobhunterx.config import auth_ctx
    return auth_ctx.scope()


def budget(model: str) -> _ModelBudget:
    key = model + _scope()              # a user's own key has its own limits (prod mode)
    if key not in _budgets:
        _budgets[key] = _ModelBudget(model)
    return _budgets[key]


def budgets_status() -> dict[str, dict[str, Any]]:
    sc = _scope()
    return {k[:len(k) - len(sc)] if sc else k: b.status() for k, b in _budgets.items()
            if (k.endswith(sc) if sc else "@" not in k)}


# ---------------------------------------------------------------------------
# Model health: rest a model for a while after server errors (per model, not per provider)
# ---------------------------------------------------------------------------
# A free endpoint can answer "500 INTERNAL" for minutes at a time. Without this, every
# call would first wait on it before falling back. With it, the first failure rests only that model
# (other Google models keep working), and the rest grows if it keeps failing: 2 → 4 → 8 → 16 → 30 min.

_SERVER_ERR = ("500", "502", "503", "504", "internal", "unavailable", "deadline", "overloaded", "timed out", "timeout",
               "having trouble")
_RATE_ERR = ("429", "resource_exhausted", "rate limit", "rate_limit", "quota", "too many requests")
_AUTH_ERR = ("401", "403", "api key not valid", "api_key_invalid", "invalid api key", "invalid_api_key", "incorrect api key",
             "unauthorized", "authentication", "permission_denied", "permission denied")
_health: dict[str, dict[str, Any]] = {}
# provider -> (fingerprint of the rejected key, until). A rejected key is skipped for every model of that
# provider instead of being retried on each call; pasting a new key clears it at once.
_bad_keys: dict[str, tuple[str, float]] = {}
BAD_KEY_REST_S = 1800.0


def _fingerprint(key: Optional[str]) -> str:
    import hashlib
    return hashlib.sha256((key or "").encode()).hexdigest()[:16]


def key_rejected(provider: str) -> bool:
    slot = provider + _scope()
    hit = _bad_keys.get(slot)
    if not hit:
        return False
    fp, until = hit
    if fp != _fingerprint(provider_key(provider)) or time.monotonic() >= until:
        _bad_keys.pop(slot, None)            # key changed or the rest is over: try again
        return False
    return True


def mark_success(model: str) -> None:
    _health.pop(model, None)


def mark_failure(model: str, error: str) -> Optional[float]:
    """Record a failed call. Returns the rest period in seconds (None if the error is not the model's fault)."""
    e = (error or "").lower()
    if "not found for account" in e or ("404" in e and "function" in e):
        # NIM lists models a free key cannot call ("Function …: Not found for account"): rest that model, not the provider
        _health[model] = {"trips": 1, "until": time.monotonic() + 12 * 3600, "why": "not available on this account"}
        log.warning("model_not_on_account", model=model)
        return 12 * 3600.0
    if "402" in e or "usage credits" in e or "payment required" in e or "insufficient credit" in e:
        # a pay-per-token provider or key with no credits left: skip every model of it for a while
        provider = provider_of(model)
        _bad_keys[provider + _scope()] = (_fingerprint(provider_key(provider)), time.monotonic() + BAD_KEY_REST_S)
        _health[model] = {"trips": 1, "until": time.monotonic() + BAD_KEY_REST_S, "why": "the account has no usage credits"}
        log.warning("provider_needs_credits", provider=provider)
        return BAD_KEY_REST_S
    if any(k in e for k in _AUTH_ERR) and not any(k in e for k in _RATE_ERR) and provider_key(provider_of(model)) == KILO_FREE:
        # a no-key pool (LLM7) answers 401 for a model that became paid: rest that model, not the whole provider
        _health[model] = {"trips": 1, "until": time.monotonic() + 6 * 3600, "why": "now needs a paid key"}
        log.warning("model_needs_key", model=model)
        return 6 * 3600.0
    if any(k in e for k in _AUTH_ERR) and not any(k in e for k in _RATE_ERR):
        provider = provider_of(model)
        _bad_keys[provider + _scope()] = (_fingerprint(provider_key(provider)), time.monotonic() + BAD_KEY_REST_S)
        log.warning("api_key_rejected", provider=provider, rest_s=int(BAD_KEY_REST_S))
        return BAD_KEY_REST_S
    if "request limit reached" in e or "resourceexhausted" in e:
        # NIM: "503 ResourceExhausted: Worker local total request limit reached (16/16)" — that endpoint is full right now.
        # It frees up in seconds, so a short flat rest (no growing back-off) and the next model answers meanwhile.
        _health[model] = {"trips": 0, "until": time.monotonic() + 60, "why": "the free endpoint is busy"}
        log.info("model_busy", model=model)
        return 60.0
    if any(k in e for k in _RATE_ERR) and model.startswith("nim/") and _nim_account_limited(model):
        # several different NIM models answered 429 within a minute: the key itself is limited, not one busy endpoint —
        # rest all of NIM briefly so the chain moves to Kilo / Groq instead of trying every NIM model in turn
        _provider_rest["nvidia" + _scope()] = time.monotonic() + NIM_ACCOUNT_REST_S
        log.warning("nim_account_rate_limited", rest_s=int(NIM_ACCOUNT_REST_S))
    if any(k in e for k in _RATE_ERR):
        # the provider says how long ("retry after 86464 seconds", "retryDelay": "33s"): a used-up daily quota rests
        # for hours instead of failing once a minute; capped at 6 h so a restarted day is picked up again
        hint = re.search(r"retry[ _-]?(?:after|delay)\D{0,6}(\d+)", e)
        rest = min(6 * 3600.0, max(60.0, float(hint.group(1)))) if hint else 60.0
    elif any(k in e for k in _SERVER_ERR):
        h = _health.get(model, {})
        trips = h.get("trips", 0) + 1
        rest = min(1800.0, 120.0 * 2 ** (trips - 1))
        _health[model] = {"trips": trips, "until": time.monotonic() + rest, "why": "Google server errors" if model.startswith("gemini/") else "server errors"}
        log.warning("model_resting", model=model, rest_s=int(rest), trips=trips)
        return rest
    else:
        return None
    slot = model + _scope()                  # a used-up quota belongs to the key that used it
    _health[slot] = {**_health.get(slot, {}), "until": time.monotonic() + rest, "why": "rate limited"}
    log.warning("model_resting", model=model, rest_s=int(rest), reason="rate limited")
    return rest


_provider_rest: dict[str, float] = {}           # provider+scope -> until (a whole provider rate limited)
_nim_429s: dict[str, deque] = {}                 # scope -> recent (time, model) NIM 429s
NIM_ACCOUNT_REST_S = 45.0


def _nim_account_limited(model: str) -> bool:
    """Three 429s from at least two different NIM models inside 60 s mean the key's limit, not one busy endpoint."""
    q = _nim_429s.setdefault(_scope(), deque(maxlen=20))
    now = time.monotonic()
    q.append((now, model))
    recent = [(t, m) for t, m in q if now - t <= 60]
    return len(recent) >= 3 and len({m for _, m in recent}) >= 2


def resting(model: str) -> Optional[str]:
    """Why this model is being skipped right now, e.g. 'resting 3 min after Google server errors'."""
    now = time.monotonic()
    sc = _scope()
    until = _provider_rest.get(provider_of(model) + sc, 0.0)
    if until > now:
        return f"resting {max(1, round((until - now) / 60))} min — the provider is rate limiting this key"
    hits = [h for h in (_health.get(model), _health.get(model + sc) if sc else None) if h and h["until"] > now]
    if not hits:
        return None          # rest is over: try it again (trips are kept, so a new failure rests it longer)
    h = max(hits, key=lambda x: x["until"])
    return f"resting {max(1, round((h['until'] - now) / 60))} min after {h['why']}"
