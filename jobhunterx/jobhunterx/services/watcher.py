"""
Watchlist watcher — checks researched companies' own job boards every few hours.

The first applicants to a post are the ones who get read. While the app is
open, this runs a light "watch" search (no web search, only the watchlist
companies in the candidate's cities), keeps only postings never seen before,
scores them, and tells the UI how many new roles fit.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.config import app_state
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.discovery import watchlist
from jobhunterx.services import profile as profile_svc
from jobhunterx.services.search import manager as search_manager

log = get_logger("watcher")

Emit = Callable[[dict], Awaitable[None]]

STARTUP_DELAY_S = 90         # let the app finish booting before the first check
TICK_S = 300                 # how often we look at the clock


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Watcher:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.checking = False

    def start(self, emit: Emit) -> None:
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._loop(emit))

    def last_check(self) -> Optional[dict]:
        return (app_state.get("watch.last") or {}).get(storage.active_person() or "")

    async def _record(self, result: dict) -> None:
        last = app_state.get("watch.last") or {}
        last[storage.active_person() or ""] = result
        await app_state.set("watch.last", last)

    def status(self) -> dict:
        hours = get_settings().watch_interval_hours
        return {"interval_hours": hours, "enabled": hours > 0, "checking": self.checking, "last": self.last_check()}

    def _due(self) -> bool:
        hours = get_settings().watch_interval_hours
        if hours <= 0:
            return False
        last = self.last_check()
        if not last or not last.get("at"):
            return True
        try:
            at = datetime.fromisoformat(last["at"])
        except ValueError:
            return True
        return (_now() - at).total_seconds() >= hours * 3600

    async def _loop(self, emit: Emit) -> None:
        await asyncio.sleep(STARTUP_DELAY_S)
        while True:
            try:
                if self._due():
                    await self.check_now(emit)
            except asyncio.CancelledError:
                raise
            except Exception as exc:              # the watcher must never die
                log.warning("watch_tick_failed", error=str(exc)[:200])
            await asyncio.sleep(TICK_S)

    async def check_now(self, emit: Emit) -> dict:
        """Run one watchlist check. Skips (never interrupts) a search the user started."""
        if self._lock.locked():
            return {"status": "already_checking"}
        cur = search_manager.current
        if cur and cur.get("status") in ("queued", "running"):
            return {"status": "busy"}
        async with self._lock:
            profile = await profile_svc.get_profile()
            if profile is None or profile.is_empty():
                return {"status": "no_profile"}
            snap = await profile_svc.get_snapshot(profile)
            companies = watchlist.for_candidate(snap)
            if not watchlist.board_refs(companies):
                result = {"status": "no_watchlist", "at": _now().isoformat(), "cities": watchlist.cities_for(snap)}
                await self._record(result)
                return result
            self.checking = True
            await emit({"type": "watch.status", "data": self.status()})
            try:
                run = await search_manager.start(profile, {"mode": "watch"}, emit)
                await search_manager.wait()
                done = search_manager.current or run
                counts = done.get("counts", {})
                result = {"status": done.get("status", "completed"), "at": _now().isoformat(), "run_id": done.get("id"),
                          "new_fits": counts.get("recommended", 0), "new_jobs": counts.get("scored", 0),
                          "companies": len(companies)}
            finally:
                self.checking = False
            await self._record(result)
            await emit({"type": "watch.done", "data": {**result, "status_info": self.status()}})
            log.info("watch_check_done", **{k: v for k, v in result.items() if k != "at"})
            return result


watcher = Watcher()
