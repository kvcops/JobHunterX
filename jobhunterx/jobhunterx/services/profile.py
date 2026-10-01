"""Candidate profile service — the single entry point for reading/writing the profile."""

from __future__ import annotations

import asyncio
from typing import Optional

from jobhunterx import storage
from jobhunterx.config import database as db
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.intelligence.candidate import build_snapshot

_locks: dict[str, asyncio.Lock] = {}


async def get_profile() -> Optional[CandidateProfile]:
    raw = await db.get_latest_profile()
    if not raw:
        return None
    return CandidateProfile.model_validate(raw)


async def save_profile(profile: CandidateProfile) -> CandidateProfile:
    await db.insert_profile(profile.model_dump(mode="json"))
    return profile


async def get_snapshot(profile: CandidateProfile, *, use_llm: bool = True) -> CandidateSnapshot:
    """Snapshot for this exact profile version (cached per profile hash).

    A per-hash lock means concurrent callers (e.g. a search starting while the
    profile page loads) share one LLM call instead of racing.
    """
    h = profile.content_hash()
    cached = await storage.get_snapshot(h)
    if cached and (cached.method == "llm" or not use_llm):
        return cached
    lock = _locks.setdefault(h, asyncio.Lock())
    async with lock:
        cached = await storage.get_snapshot(h)
        if cached and (cached.method == "llm" or not use_llm):
            return cached
        snap = await build_snapshot(profile, use_llm=use_llm)
        await storage.put_snapshot(snap)
        return snap


async def envelope(profile: Optional[CandidateProfile], *, build: bool = True) -> dict:
    if profile is None:
        return {"profile": None, "snapshot": None, "profile_hash": None}
    snap = await get_snapshot(profile) if build else await storage.get_snapshot(profile.content_hash())
    return {
        "profile": profile.model_dump(mode="json"),
        "snapshot": snap.model_dump(mode="json") if snap else None,
        "profile_hash": profile.content_hash(),
    }
