"""
Board registry — every employer job board JobHunterX has ever found, polled again on later runs.

The researched watchlist is a fixed list. Searches keep turning up more employers (an ATS link in a search result,
a LinkedIn post resolved to the company's own Greenhouse / Lever / Ashby board, Deep Search's company resolution).
Each of those boards is remembered here, and every run checks a rotating slice of them — least recently checked
first — so coverage grows with every search instead of returning the same companies.

Boards that keep giving nothing relevant (wrong country, wrong field) rest for a while instead of being polled
every time.
"""

from __future__ import annotations

import time
from typing import Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.job import AtsRef

log = get_logger("board_registry")

KEY = "boards"
EMPTY_REST_S = 7 * 86400          # a board that gave nothing useful 3 times in a row rests a week
EMPTY_STREAK = 3

_store = None


def _cache():
    global _store
    if _store is None:
        from diskcache import Cache
        from jobhunterx.config.settings import get_settings
        _store = Cache(str(get_settings().cache_full_path / "board_registry"))
    return _store


def _key(kind: str, token: str) -> str:
    return f"{kind}:{token.lower()}"


def _all() -> dict[str, dict]:
    return _cache().get(KEY) or {}


def remember(boards: list[tuple[AtsRef, str]], source: str) -> int:
    """Add (board, company name) pairs. Returns how many were new."""
    if not boards:
        return 0
    from jobhunterx.discovery import ats
    data, new = _all(), 0
    for ref, company in boards:
        if not ref or not ref.token or ref.kind not in ats.ADAPTERS:
            continue
        k = _key(ref.kind, ref.token)
        if k in data:
            if company and not data[k].get("name"):
                data[k]["name"] = company
            continue
        data[k] = {"kind": ref.kind, "token": ref.token, "name": company or "", "source": source, "added": time.time(),
                   "polled": 0.0, "empty": 0, "rest_until": 0.0, "found": 0}
        new += 1
    if new:
        _cache().set(KEY, data)
        log.info("boards_remembered", new=new, total=len(data), source=source)
    return new


def pick(n: int, exclude: set[tuple[str, str]]) -> list[tuple[AtsRef, str]]:
    """Up to n boards to poll this run: never polled first, then least recently polled; resting boards skipped."""
    now = time.time()
    rows = [r for r in _all().values() if r.get("rest_until", 0) <= now and (r["kind"], r["token"].lower()) not in exclude]
    rows.sort(key=lambda r: (r.get("polled", 0), -r.get("found", 0)))
    return [(AtsRef(kind=r["kind"], token=r["token"]), r.get("name") or "") for r in rows[:n]]


def polled(results: dict[tuple[str, str], int]) -> None:
    """Record a poll: board → number of relevant local jobs it gave."""
    if not results:
        return
    data, now = _all(), time.time()
    for (kind, token), n in results.items():
        r = data.get(_key(kind, token))
        if not r:
            continue
        r["polled"] = now
        r["found"] = n
        r["empty"] = 0 if n else r.get("empty", 0) + 1
        if r["empty"] >= EMPTY_STREAK:
            r["rest_until"], r["empty"] = now + EMPTY_REST_S, 0
    _cache().set(KEY, data)


def size() -> int:
    return len(_all())


def name_of(ref: AtsRef) -> Optional[str]:
    r = _all().get(_key(ref.kind, ref.token))
    return (r or {}).get("name") or None
