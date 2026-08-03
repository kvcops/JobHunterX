"""
Vellum OS — Job Liveness Checker

Proves a job still exists before the user wastes time on it. For the top
matches we hit the apply URL and check it still returns a real page
(200, and the body isn't an explicit "job expired/not found" page).

Rules:
  - HEAD first (cheap), fall back to GET.
  - 200 + no "expired/not found" marker → live
  - 404/410/301-to-404 → gone
  - network error / timeout / 403 anti-bot → unknown (don't kill it)
Zero LLM tokens. Rate-light: only top-N jobs get checked per sync.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("liveness")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_GONE_MARKERS = (
    "job expired", "job no longer", "no longer accepting", "position has been filled",
    "position is no longer", "this job is no longer", "job has been filled",
    "vacancy closed", "job posting is closed", "we are no longer hiring",
    "not found", "404", "page not found", "no longer available",
)


def _looks_gone(body: str) -> bool:
    b = (body or "").lower()
    b = re.sub(r"\s+", " ", b)[:3000]
    return any(m in b for m in _GONE_MARKERS)


def _check_url(url: str, timeout: float = 12.0) -> str:
    """Return 'live' | 'gone' | 'unknown'."""
    if not url or not url.startswith("http"):
        return "unknown"
    import httpx
    headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"}
    # 1. HEAD
    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as c:
            r = c.head(url)
            if r.status_code in (404, 410):
                return "gone"
            if r.status_code == 200:
                # HEAD 200 isn't proof — a shell page can still be an error page
                return "unknown"
            if r.status_code >= 500:
                return "unknown"
    except Exception:
        pass
    # 2. GET (final word)
    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as c:
            r = c.get(url)
            if r.status_code in (404, 410):
                return "gone"
            if r.status_code == 200:
                return "gone" if _looks_gone(r.text) else "live"
            if r.status_code >= 500:
                return "unknown"
            return "unknown"
    except Exception as exc:
        log.debug("liveness_check_error", url=url[:80], error=str(exc)[:100])
        return "unknown"


async def verify_job(job: dict, timeout: float = 12.0) -> str:
    """Async wrapper — returns 'live' | 'gone' | 'unknown' for one job."""
    url = job.get("apply_url") or job.get("career_page_url") or ""
    return await asyncio.to_thread(_check_url, url, timeout)


async def verify_top_jobs(
    jobs: list[dict],
    max_checks: int = 25,
    concurrency: int = 5,
) -> dict[str, str]:
    """Check the highest-match jobs first. Returns {job_id: verdict}."""
    to_check = sorted(jobs, key=lambda j: -(j.get("match_score") or 0))[:max_checks]
    sem = asyncio.Semaphore(concurrency)

    async def one(job: dict):
        async with sem:
            verdict = await verify_job(job)
            return job.get("id") or job.get("id_key") or "", verdict

    results = await asyncio.gather(*(one(j) for j in to_check))
    verdicts = {jid: v for jid, v in results if jid and v != "unknown"}
    live = sum(1 for v in verdicts.values() if v == "live")
    gone = sum(1 for v in verdicts.values() if v == "gone")
    log.info("liveness_checked", checked=len(results), live=live, gone=gone,
             unknown=len(results) - live - gone)
    return verdicts