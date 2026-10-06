"""
Custom company monitors — companies the user picked themselves, watched through their own careers site.

Adding one starts the Company Scout agent once (agents/career_scout.py): it finds the real careers site, applies the
location / keyword filters and stores a recipe. From then on every search and watchlist check lists that company's
jobs with the recipe in seconds — no browser, no AI — and they go through the normal read → match → rank pipeline.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from jobhunterx import storage
from jobhunterx.agents import browser_worker, live_view
from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import recipes

log = get_logger("monitors")

STEPS_KEEP = 14
SAMPLE_KEEP = 40
_scout_lock: Optional[asyncio.Lock] = None      # one scout at a time (created on the browser worker loop)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public(m: dict) -> dict:
    r = m.get("recipe") or {}
    return {k: m.get(k) for k in ("id", "company", "location", "keyword", "status", "message", "steps", "found_via",
                                  "results_url", "jobs", "last_check_at", "last_count", "error", "created_at",
                                  "updated_at", "notes", "url")} | {"kind": r.get("kind", "")}


def _publish(m: dict) -> None:
    """Save and tell the UI — callable from the browser worker thread."""
    snap = dict(m)
    live_view._on_main(storage.save_monitor(snap))
    live_view.broadcast_event({"type": "monitor.updated", "data": {"monitor": public(snap)}})


async def add(company: str, location: str = "", keyword: str = "", default_keyword: str = "") -> dict:
    company, location, keyword = company.strip()[:80], location.strip()[:80], keyword.strip()[:80]
    m = {"id": str(uuid.uuid4()), "person_id": storage.active_person(), "company": company, "location": location,
         "keyword": keyword, "status": "queued", "message": "Waiting for the scout…", "steps": [], "jobs": [],
         "created_at": _now(), "recipe": None, "error": ""}
    known = await storage.find_monitor_recipe(company, location)
    if known and known.get("recipe"):
        m.update(status="ready", recipe=known["recipe"], found_via=known.get("found_via", ""),
                 results_url=known.get("results_url", ""), message="Already scouted — using the saved recipe")
        await storage.save_monitor(m)
        return await check(m["id"], keywords=[keyword] if keyword else None) or public(m)
    await storage.save_monitor(m)
    browser_worker.submit(_scout(m, keyword or default_keyword))
    return public(m)


async def rescout(monitor_id: str, default_keyword: str = "") -> Optional[dict]:
    m = await storage.get_monitor(monitor_id)
    if not m:
        return None
    m.update(status="queued", message="Waiting for the scout…", steps=[], error="")
    await storage.save_monitor(m)
    browser_worker.submit(_scout(m, m.get("keyword") or default_keyword))
    return public(m)


async def _scout(m: dict, keyword: str) -> None:
    """On the browser worker loop: run the Company Scout and store what it learned."""
    from jobhunterx.agents import career_scout
    global _scout_lock
    if _scout_lock is None:
        _scout_lock = asyncio.Lock()
    async with _scout_lock:
        m.update(status="scouting", message=f"Finding {m['company']}'s careers site", steps=[])
        _publish(m)

        async def step(msg: str, url: str = "") -> None:
            m["steps"] = (m.get("steps") or [])[-(STEPS_KEEP - 1):] + [{"ts": _now(), "text": msg, "url": url}]
            m["message"] = msg
            if url:
                m["url"] = url
            _publish(m)

        try:
            res = await career_scout.scout(m["company"], m.get("location", ""), keyword, on_step=step)
        except Exception as exc:                       # never leave a monitor stuck on "scouting"
            res = {"ok": False, "error": f"The scout stopped: {str(exc)[:200]}"}
        if res.get("ok"):
            jobs = res.get("jobs") or []
            m.update(status="ready", recipe=res["recipe"], found_via=res.get("found_via", ""),
                     results_url=res.get("results_url", ""), notes=res.get("notes", ""), jobs=jobs[:SAMPLE_KEEP],
                     last_count=len(jobs), last_check_at=_now(), error="",
                     message=f"Ready — {len(jobs)} open job{'s' if len(jobs) != 1 else ''} found via {res.get('found_via')}")
        else:
            m.update(status="failed", error=res.get("error") or "The scout could not finish.",
                     results_url=res.get("results_url", ""), message="Scouting failed")
        _publish(m)


async def check(monitor_id: str, keywords: Optional[list[str]] = None) -> Optional[dict]:
    """List the company's jobs now with its recipe and keep a sample for the UI."""
    m = await storage.get_monitor(monitor_id)
    if not m or not m.get("recipe"):
        return public(m) if m else None
    try:
        links = await recipes.run(recipes.Recipe(**m["recipe"]), keywords or ([m["keyword"]] if m.get("keyword") else None))
        m.update(jobs=[l.model_dump() for l in links[:SAMPLE_KEEP]], last_count=len(links), last_check_at=_now(),
                 status="ready", error="", message=f"{len(links)} open job{'s' if len(links) != 1 else ''} right now")
    except Exception as exc:
        log.warning("monitor_check_failed", company=m["company"], error=str(exc)[:200])
        m.update(error=f"Check failed: {str(exc)[:160]} — try Re-scout if the site changed.", last_check_at=_now())
    await storage.save_monitor(m)
    live_view.broadcast_event({"type": "monitor.updated", "data": {"monitor": public(m)}})
    return public(m)


async def ready(person_id: Optional[str] = None) -> list[dict]:
    return [m for m in await storage.list_monitors(person_id) if m.get("status") == "ready" and m.get("recipe")]


async def jobs_for_search(keywords: list[str]) -> list[tuple[dict, recipes.JobLink]]:
    """Every ready monitor's current jobs, for a search or watch run → [(monitor, job link)]."""
    out: list[tuple[dict, recipes.JobLink]] = []

    async def one(m: dict) -> None:
        r = recipes.Recipe(**m["recipe"])
        try:
            links = await recipes.run(r, [m["keyword"]] if m.get("keyword") else keywords[:3])
        except Exception as exc:
            log.info("monitor_run_failed", company=m["company"], error=str(exc)[:160])
            return
        out.extend((m, l) for l in links if l.url)
        m.update(last_count=len(links), last_check_at=_now())
        await storage.save_monitor(m)

    await asyncio.gather(*(one(m) for m in await ready()))
    return out
