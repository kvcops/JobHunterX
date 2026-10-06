"""
Direct client for OpenAI-compatible chat APIs: Kilo Gateway and NVIDIA NIM.

Why not LiteLLM here: Kilo's free models must be called with *no* Authorization
header (any token, even a placeholder, is rejected with 401 INVALID_TOKEN), and
LiteLLM always sends one. Both providers speak the same /chat/completions
format, so a small httpx client is simpler and fully under our control.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

KILO_BASE = "https://api.kilo.ai/api/gateway"
NIM_BASE = "https://integrate.api.nvidia.com/v1"


class ChatError(Exception):
    """Raised with the HTTP status in the message so the router can tell rate limits / auth / server errors apart."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"{status} {detail}")
        self.status = status


class EmptyAnswer(ChatError):
    """The model spent its whole output budget thinking. Not the model's fault: retry with more room, never rest it."""

    def __init__(self):
        super().__init__(200, "empty answer: the model used its whole output budget for reasoning")


# Kilo's free models are reasoning models; with thinking on, a short budget often ends before any answer.
# Measured Oct 2026: {"reasoning": {"enabled": false}} gives a real answer on every chosen Kilo model, and faster.
KILO_EXTRA = {"reasoning": {"enabled": False}}


_pool: Optional[tuple[Any, httpx.AsyncClient]] = None


def _client() -> httpx.AsyncClient:
    """Reused per event loop: AI calls to the same provider skip a fresh TLS handshake every time."""
    import asyncio
    global _pool
    loop = asyncio.get_running_loop()
    if _pool is None or _pool[0] is not loop or _pool[1].is_closed:
        _pool = (loop, httpx.AsyncClient(limits=httpx.Limits(max_connections=20, keepalive_expiry=60)))
    return _pool[1]


async def chat(base: str, model: str, messages: list[dict], *, key: Optional[str] = None, max_tokens: int = 1024,
               temperature: Optional[float] = None, json_mode: bool = False, timeout: float = 60.0,
               extra: Optional[dict] = None) -> dict[str, Any]:
    body: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens, **(extra or {})}
    if temperature is not None:
        body["temperature"] = temperature
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    t0 = time.monotonic()
    client = _client()
    r = await client.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout)
    if r.status_code == 400 and json_mode:          # a model without JSON mode: retry plainly (prompts ask for JSON anyway)
        body.pop("response_format", None)
        r = await client.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout)
    if r.status_code >= 400:
        raise ChatError(r.status_code, r.text[:300])
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise ChatError(502, f"no choices in response: {str(data)[:200]}")
    content = (choices[0].get("message") or {}).get("content") or ""
    if not content.strip():
        raise EmptyAnswer()
    usage = data.get("usage") or {}
    return {"content": content, "tokens_in": int(usage.get("prompt_tokens") or 0), "tokens_out": int(usage.get("completion_tokens") or 0),
            "served_by": data.get("model") or model, "latency_ms": round((time.monotonic() - t0) * 1000, 1)}


async def list_models(base: str, key: Optional[str] = None) -> list[dict]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{base}/models", headers=headers)
        r.raise_for_status()
        data = r.json()
    return data.get("data", data) if isinstance(data, dict) else data
