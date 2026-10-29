"""
Small in-memory sliding-window rate limiter for the endpoints that spend AI calls.

Keyed by the signed-in user (prod mode) or the client address, so one person can't use up a shared free AI budget.
Per process by design: this app runs as one process, and a restart simply clears the counters.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request

_hits: dict[str, deque[float]] = {}
_MAX_KEYS = 5000


def _who(request: Request) -> str:
    from jobhunterx.config import auth_ctx
    user = auth_ctx.current()
    if user is not None:
        return f"u:{user.id}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def check(request: Request, bucket: str, *, limit: int, per_s: float) -> None:
    """Allow `limit` calls per `per_s` seconds for this caller and bucket; otherwise answer 429 with Retry-After."""
    key = f"{bucket}|{_who(request)}"
    now = time.monotonic()
    q = _hits.setdefault(key, deque())
    while q and now - q[0] > per_s:
        q.popleft()
    if len(q) >= limit:
        wait = max(1, int(per_s - (now - q[0])) + 1)
        raise HTTPException(429, f"Too many requests. Please wait {wait} seconds and try again.", headers={"Retry-After": str(wait)})
    q.append(now)
    if len(_hits) > _MAX_KEYS:                      # forget callers that went quiet
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > per_s][:_MAX_KEYS // 2]:
            _hits.pop(k, None)
