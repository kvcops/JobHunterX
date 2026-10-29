"""
JobHunterX — REST API (v2 contract, see docs/API.md).

Thin HTTP layer: validation, error mapping and event publishing. Business
logic lives in jobhunterx.services.*.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator

from jobhunterx import auth, storage
from jobhunterx.agents import extractor
from jobhunterx.api import ratelimit
from jobhunterx.api.ws import manager as ws_manager
from jobhunterx.config import auth_ctx
from jobhunterx.config import database as db
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import is_real_key
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.generation import chat_edit
from jobhunterx.generation import styles as gen_styles
from jobhunterx.generation.cover_letter import GenerationUnavailable
from jobhunterx.services import apply as apply_svc
from jobhunterx.services import documents as docs_svc
from jobhunterx.services import jobs as jobs_svc
from jobhunterx.services import profile as profile_svc
from jobhunterx.services.search import manager as search_manager

log = get_logger("routes")

# Every id in a URL (or ?job_id=) names something that belongs to one person. With login on (prod mode) it must be
# one of the signed-in user's own; anything else answers 404, exactly like an id that does not exist.
_OWNED_PARAMS = {"job_id": "job", "doc_id": "document", "monitor_id": "monitor", "run_id": "run", "person_id": "person"}


async def _owner_guard(request: Request) -> None:
    if auth_ctx.current() is None:
        return
    for name, kind in _OWNED_PARAMS.items():
        val = request.path_params.get(name) or (request.query_params.get(name) if name == "job_id" else None)
        if val and not await storage.owns(kind, val):
            raise HTTPException(404, "Not found")


router = APIRouter(prefix="/api", dependencies=[Depends(_owner_guard)])


def _uid() -> Optional[str]:
    user = auth_ctx.current()
    return user.id if user else None

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def emit(event: dict) -> None:
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    await ws_manager.broadcast(event)


async def _profile_or_400() -> CandidateProfile:
    p = await profile_svc.get_profile()
    if p is None or p.is_empty():
        raise HTTPException(400, "Upload a resume or fill in your profile first.")
    return p


async def _current_hash() -> Optional[str]:
    p = await profile_svc.get_profile()
    return p.content_hash() if p else None


# ---------------------------------------------------------------------------
# Meta & profile
# ---------------------------------------------------------------------------

@router.get("/meta")
async def meta():
    from jobhunterx.config import app_state
    user = auth_ctx.current()
    return {"tracking_statuses": storage.TRACKING_STATUSES, "setup": _setup_status(),
            "office_ai": app_state.office_ai_enabled(),
            "auth": {"enabled": auth.enabled(), "user": {"id": user.id, "username": user.username, "is_admin": user.is_admin,
                                                          "self_signup": user.self_signup} if user else None},
            "browser": _browser_status()}


def _browser_status() -> dict:
    """How auto-apply will open its browser for this user (shown before they start, with a warning when blocked)."""
    from jobhunterx.agents import browser_agent as ba
    has_key = bool(ba.browser_use_key())
    required = ba.cloud_required()
    return {"cloud": has_key, "cloud_required": required, "ready": has_key or not required, "key_url": ba.BU_KEY_URL}


# ---------------------------------------------------------------------------
# First-run setup: API keys
# ---------------------------------------------------------------------------

_LLM_KEYS = ("google", "nvidia", "groq", "mistral")
_SEARCH_KEYS = ("tavily", "exa", "tinyfish", "brave")


def _setup_status() -> dict:
    from jobhunterx.config import app_state
    from jobhunterx.config.settings import get_settings
    s = get_settings()
    have = {name: bool(getattr(s, f"{name}_api_key")) for name in (*_LLM_KEYS, *_SEARCH_KEYS, "kilo")}
    kilo_on = app_state.llm_provider_enabled("kilo")
    free_on = sum(app_state.llm_provider_enabled(p) for p in ("kilo", "llm7"))   # no-key providers turned on
    free_allowed = auth_ctx.shared_pools_allowed()            # prod mode: users bring their own keys
    free_ok = bool(app_state.get("setup.free_ok")) and free_allowed
    return {"llm_ready": any(have[n] for n in _LLM_KEYS) or (free_on > 0 and free_ok), "keys": have,
            "llm_count": sum(have[n] for n in _LLM_KEYS) + free_on, "kilo_on": kilo_on, "free_ok": free_ok,
            "free_allowed": free_allowed, "desktop": s.desktop}


@router.get("/setup")
async def setup_status():
    return _setup_status()


@router.post("/setup/free")
async def setup_free():
    """Start without any key: free no-key models (Kilo, LLM7) do the AI work (they may use prompts for training — the UI says so)."""
    from jobhunterx.config import app_state
    if not auth_ctx.shared_pools_allowed():
        raise HTTPException(403, "On this server the free shared models are not available to users. Add your own free key.")
    auth.require_admin()
    cur = app_state.get("llm.providers")
    cur.update({"kilo": True, "llm7": True})
    await app_state.set("llm.providers", cur)
    await app_state.set("setup.free_ok", True)
    return _setup_status()


class KeyTest(BaseModel):
    provider: Literal["google", "nvidia", "groq", "mistral", "tavily", "exa", "tinyfish", "brave", "browser_use"]
    key: str = Field(..., max_length=256)


@router.post("/setup/test-key")
async def test_key(body: KeyTest):
    """Check a key with one free call (listing the provider's models). Search keys are only format-checked —
    testing them would spend a search credit."""
    import httpx
    key = body.key.strip()
    if not is_real_key(key) or not re.fullmatch(r"[A-Za-z0-9_\-.:]{12,256}", key):
        return {"ok": False, "message": "That doesn't look like an API key — copy the whole key again."}
    checks = {
        # Browser Use: listing your cloud browsers is free and answers 401 for a wrong key
        "browser_use": ("https://api.browser-use.com/api/v2/browsers", {"X-Browser-Use-API-Key": key}),
        "google": ("https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": key}),
        "groq": ("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {key}"}),
        "mistral": ("https://api.mistral.ai/v1/models", {"Authorization": f"Bearer {key}"}),
    }
    if body.provider == "nvidia":           # NIM lists models without a key, so check with a one-token answer
        from jobhunterx.config import openai_compat as oc
        last = "unreachable"
        for model in ("nvidia/nemotron-3.5-bolt-e4b", "nvidia/nemotron-3.5-lightning-30b-a3b"):   # two fast free endpoints
            try:
                await oc.chat(oc.NIM_BASE, model, [{"role": "user", "content": "hi"}], key=key, max_tokens=16, timeout=25,
                              extra=oc.nim_extra(model))
                return {"ok": True, "message": "Key works."}
            except oc.EmptyAnswer:
                return {"ok": True, "message": "Key works."}
            except oc.ChatError as exc:
                if exc.status in (401, 403):
                    return {"ok": False, "message": "NVIDIA rejected this key. Create a new key and paste it again."}
                if exc.status == 429:
                    return {"ok": True, "message": "Key accepted (NVIDIA is rate-limiting right now, that's fine)."}
                last = f"error {exc.status}"
            except Exception:
                last = "busy"
        return {"ok": False, "message": f"NVIDIA did not answer ({last}). Its free endpoints get busy — try again in a minute."}
    if body.provider not in checks:
        return {"ok": True, "message": "Saved format looks right — it is checked on the first search."}
    url, headers = checks[body.provider]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, headers=headers)
    except httpx.HTTPError:
        return {"ok": False, "message": "Could not reach the provider — check your internet connection and try again."}
    if r.status_code == 200:
        return {"ok": True, "message": "Key works."}
    if r.status_code in (400, 401, 403):
        return {"ok": False, "message": "The provider rejected this key. Create a new key and paste it again."}
    if r.status_code == 429:
        return {"ok": True, "message": "Key accepted (the provider is rate-limiting right now, that's fine)."}
    return {"ok": False, "message": f"The provider answered with an error ({r.status_code}). Try again in a minute."}


@router.get("/profile")
async def get_profile():
    return await _envelope_now(await profile_svc.get_profile())


@router.put("/profile")
@router.post("/profile")
async def put_profile(profile: CandidateProfile):
    """Save at once. The AI understanding of a changed profile can take a while on free models, so the answer carries
    the previous one (snapshot_pending) and the new one follows as a profile.updated event."""
    old = await profile_svc.get_profile()
    await profile_svc.save_profile(profile)
    env = await _envelope_now(profile, old)
    await emit({"type": "profile.updated", "data": env})
    return env


_building: set[str] = set()      # profile versions whose AI understanding is being built in the background


async def _envelope_now(profile: Optional[CandidateProfile], previous: Optional[CandidateProfile] = None) -> dict:
    """The profile with the best understanding available right now; when it is missing or from an older release, the
    previous one is shown (snapshot_pending) and the new one is built in the background, then sent as profile.updated."""
    env = await profile_svc.envelope(profile, build=False)
    if profile is None or profile.is_empty():
        return env
    cached = await storage.get_snapshot(profile.content_hash())
    if cached and not profile_svc._outdated(cached, True):
        return env
    prev = cached or (await storage.get_snapshot(previous.content_hash()) if previous else None)
    env["snapshot"] = prev.model_dump(mode="json") if prev else None
    env["snapshot_pending"] = True
    h = profile.content_hash()
    if h not in _building:
        _building.add(h)

        async def _understand() -> None:
            try:
                await emit({"type": "profile.updated", "data": await profile_svc.envelope(profile)})
            except Exception as exc:
                log.warning("snapshot_build_failed", error=str(exc)[:200])
            finally:
                _building.discard(h)
        asyncio.create_task(_understand())
    return env


_uploads: dict[str, dict] = {}   # upload id -> status (kept for the session so a reload can resume)
_upload_owner: dict[str, Optional[str]] = {}   # upload id -> login user (prod mode)


async def _process_upload(up: dict, data: bytes) -> dict:
    """Read a resume PDF into the active profile, publishing each stage as it happens."""
    async def stage(name: str, **extra) -> None:
        up.update(stage=name, **extra)
        await emit({"type": "profile.upload", "data": {"upload": {k: v for k, v in up.items() if k != "result"}}})

    try:
        await stage("extracting")
        profile, info = await extractor.extract_profile(data)
        if info["status"] == "failed":
            raise HTTPException(502, info["warnings"][0] if info["warnings"] else "Could not read the resume.")
        existing = await profile_svc.get_profile()
        if existing:  # keep what the user set that a resume cannot contain
            profile.preferences = existing.preferences
            profile.qa_memory = existing.qa_memory
        await profile_svc.save_profile(profile)
        await stage("understanding")
        env = await _envelope_now(profile, existing)        # the review opens now; the AI analysis follows as an event
        await emit({"type": "profile.updated", "data": env})
        up["result"] = {**env, "extraction": info}
        await stage("done", status="done", finished_at=datetime.now(timezone.utc).isoformat())
        return up["result"]
    except HTTPException as exc:
        await stage("failed", status="failed", error=str(exc.detail))
        raise
    except Exception as exc:
        log.error("resume_upload_failed", error=str(exc)[:300])
        await stage("failed", status="failed", error="Could not read the resume. The AI provider may be busy — please try again.")
        raise HTTPException(502, up["error"])
    finally:
        from jobhunterx.config import capacity
        capacity.release_memory()            # the PDF reader's pages and the long AI answer are no longer needed


@router.post("/profile/upload")
@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), background: bool = Query(False)):
    """Read a resume. With ?background=1 it returns at once and streams `profile.upload` events
    (extracting → understanding → done/failed); AI reading can take minutes on free tiers."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The file is larger than 10 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(422, "Please upload a PDF resume.")
    if not _setup_status()["llm_ready"]:
        raise HTTPException(400, "Add at least one AI key first (Google AI Studio, NVIDIA, Groq or Mistral — all free), "
                                 "or choose “Start free with Kilo”. Without AI, the resume cannot be read.")
    up = {"id": str(uuid.uuid4()), "status": "running", "stage": "received", "file_name": (file.filename or "resume.pdf")[:120],
          "started_at": datetime.now(timezone.utc).isoformat(), "error": None}
    if len(_uploads) > 200:
        for old in list(_uploads)[:100]:
            _uploads.pop(old, None)
            _upload_owner.pop(old, None)
    _upload_owner[up["id"]] = _uid()
    _uploads[up["id"]] = up
    if not background:
        return await _process_upload(up, data)

    async def _run():
        try:
            await _process_upload(up, data)
        except Exception:
            pass   # status already published
    asyncio.create_task(_run())
    return {"upload": up}


@router.get("/profile/upload/{upload_id}")
async def upload_status(upload_id: str):
    up = _uploads.get(upload_id)
    if not up or _upload_owner.get(upload_id) != _uid():
        raise HTTPException(404, "Upload not found")
    return {"upload": {k: v for k, v in up.items() if k != "result"}, "result": up.get("result")}


# ---------------------------------------------------------------------------
# Place suggestions (cities while typing) — Open-Meteo's free geocoder, called from here so the page only ever
# talks to this server
# ---------------------------------------------------------------------------

_places_cache: dict[tuple[str, str], list[dict]] = {}


@router.get("/places")
async def places(q: str = Query("", max_length=60), country: str = Query("", max_length=2)):
    import httpx
    q, country = q.strip(), country.strip().upper()
    if len(q) < 2:
        return {"places": []}
    key = (q.lower(), country)
    if key in _places_cache:
        return {"places": _places_cache[key]}
    params = {"name": q, "count": 10, "language": "en", "format": "json"}
    if re.fullmatch(r"[A-Z]{2}", country):
        params["countryCode"] = country
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get("https://geocoding-api.open-meteo.com/v1/search", params=params)
            r.raise_for_status()
            rows = r.json().get("results") or []
    except (httpx.HTTPError, ValueError):
        return {"places": []}                # suggestions are a nicety: typing still works without them
    out, seen = [], set()
    for x in sorted(rows, key=lambda x: -(x.get("population") or 0)):
        if not str(x.get("feature_code", "")).startswith("PPL"):
            continue                         # towns and cities only (no rivers, districts, airports)
        label = ", ".join(p for p in (x.get("name"), x.get("admin1"), x.get("country")) if p)
        if label not in seen:
            seen.add(label)
            out.append({"name": x.get("name"), "label": label, "country": x.get("country"), "country_code": x.get("country_code")})
    if len(_places_cache) > 500:
        _places_cache.clear()
    _places_cache[key] = out[:8]
    return {"places": out[:8]}


# ---------------------------------------------------------------------------
# People (switchable profiles)
# ---------------------------------------------------------------------------

class PersonBody(BaseModel):
    name: str = Field("", max_length=80)


async def _people_payload() -> dict:
    return {"people": await storage.list_people(), "active": storage.active_person()}


@router.get("/people")
async def list_people():
    return await _people_payload()


@router.post("/people", status_code=201)
async def create_person(body: PersonBody):
    await search_manager.cancel()
    pid = await storage.create_person(body.name or "New profile")
    await storage.activate_person(pid)
    await emit({"type": "people.changed", "data": {"active": pid}})
    return await _people_payload()


@router.post("/people/{person_id}/activate")
async def activate_person(person_id: str):
    if not await storage.get_person(person_id):
        raise HTTPException(404, "Profile not found")
    if storage.active_person() != person_id:
        await search_manager.cancel()     # a running search belongs to the previous person
    await storage.activate_person(person_id)
    await emit({"type": "people.changed", "data": {"active": person_id}})
    return await _people_payload()


@router.patch("/people/{person_id}")
async def rename_person(person_id: str, body: PersonBody):
    if not body.name.strip() or not await storage.rename_person(person_id, body.name):
        raise HTTPException(404 if body.name.strip() else 422, "Profile not found" if body.name.strip() else "Name is required")
    return await _people_payload()


@router.delete("/people/{person_id}")
async def delete_person(person_id: str):
    if not await storage.get_person(person_id):
        raise HTTPException(404, "Profile not found")
    if storage.active_person() == person_id:
        await search_manager.cancel()
    await storage.delete_person(person_id)
    await emit({"type": "people.changed", "data": {"active": storage.active_person()}})
    return await _people_payload()


# ---------------------------------------------------------------------------
# Searches
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    locations: list[str] = Field(default_factory=list)
    work_modes: list[Literal["remote", "hybrid", "onsite"]] = Field(default_factory=list)
    role_focus: list[str] = Field(default_factory=list)
    include_international: bool = False
    max_jobs: Optional[int] = Field(None, ge=5, le=200)


@router.post("/searches", status_code=202)
async def start_search(req: SearchRequest):
    profile = await _profile_or_400()
    run = await search_manager.start(profile, req.model_dump(), emit)
    return {"run": run}


@router.get("/searches/current")
async def current_search():
    run = search_manager.current
    if run and run.get("person_id") != storage.active_person():
        run = None                       # belongs to another profile
    return {"run": run or await storage.latest_run()}


@router.get("/searches/{run_id}")
async def get_search(run_id: str):
    run = search_manager.find(run_id) or await storage.get_run(run_id)
    if not run:
        raise HTTPException(404, "Search run not found")
    return {"run": run}


@router.post("/searches/{run_id}/cancel")
async def cancel_search(run_id: str):
    run = await search_manager.cancel(run_id)
    if not run:
        raise HTTPException(404, "Search run not found")
    return {"run": run}


# ---------------------------------------------------------------------------
# Watchlist — researched companies whose own job boards are checked directly
# ---------------------------------------------------------------------------

@router.get("/watchlist")
async def get_watchlist(scope: Literal["mine", "all"] = "mine"):
    from jobhunterx.discovery import watchlist
    from jobhunterx.services.watcher import watcher
    cities: list[str] = []
    companies = list(watchlist.load())
    if scope == "mine":
        profile = await profile_svc.get_profile()
        if profile and not profile.is_empty():
            snap = await profile_svc.get_snapshot(profile)
            cities = watchlist.cities_for(snap)
            companies = watchlist.for_candidate(snap)
    return {"cities": cities, "covered_cities": list(watchlist.CITY_FORMS), "total": len(watchlist.load()),
            "companies": [watchlist.public_view(c) for c in companies], "status": watcher.status()}


# ---------------------------------------------------------------------------
# Custom company monitors — the Company Scout agent learns each company's careers site once
# ---------------------------------------------------------------------------

class MonitorIn(BaseModel):
    company: str = Field(min_length=2, max_length=80)
    location: str = Field(default="", max_length=80)
    keyword: str = Field(default="", max_length=80)


async def _default_keyword() -> str:
    """The role word the scout types when the user gave none: the profile's first target title."""
    profile = await profile_svc.get_profile()
    if not profile or profile.is_empty():
        return ""
    snap = await profile_svc.get_snapshot(profile)
    return snap.target_titles[0] if snap.target_titles else ""


@router.get("/monitors")
async def list_monitors():
    from jobhunterx.services import monitors
    return {"monitors": [monitors.public(m) for m in await storage.list_monitors()]}


@router.post("/monitors", status_code=201)
async def add_monitor(body: MonitorIn):
    from jobhunterx.services import monitors
    if any(m["company"].lower() == body.company.strip().lower() and m.get("location", "").lower() == body.location.strip().lower()
           for m in await storage.list_monitors()):
        raise HTTPException(409, f"{body.company} is already watched for that location.")
    return {"monitor": await monitors.add(body.company, body.location, body.keyword, await _default_keyword())}


@router.post("/monitors/{monitor_id}/check")
async def check_monitor(monitor_id: str):
    from jobhunterx.services import monitors
    m = await storage.get_monitor(monitor_id)
    if not m:
        raise HTTPException(404, "Monitor not found")
    if not m.get("recipe"):
        raise HTTPException(409, "This company has not been scouted yet.")
    kw = [m["keyword"]] if m.get("keyword") else ([k] if (k := await _default_keyword()) else None)
    return {"monitor": await monitors.check(monitor_id, kw)}


@router.post("/monitors/{monitor_id}/rescout", status_code=202)
async def rescout_monitor(monitor_id: str):
    from jobhunterx.services import monitors
    m = await monitors.rescout(monitor_id, await _default_keyword())
    if not m:
        raise HTTPException(404, "Monitor not found")
    return {"monitor": m}


@router.delete("/monitors/{monitor_id}")
async def delete_monitor(monitor_id: str):
    if not await storage.delete_monitor(monitor_id):
        raise HTTPException(404, "Monitor not found")
    return {"deleted": True}


@router.post("/watchlist/check", status_code=202)
async def check_watchlist():
    from jobhunterx.services.watcher import watcher
    await _profile_or_400()
    asyncio.create_task(watcher.check_now(emit))
    return {"status": watcher.status()}


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

_reassessed: set[str] = set()      # profiles whose jobs were brought up to the current matcher in this process


async def _refresh_outdated_once() -> None:
    """Jobs scored by an older matcher version are re-scored once (no AI, a few ms each), so rule changes such as the
    early-career experience bands reach jobs found before them."""
    profile = await profile_svc.get_profile()
    if profile is None or profile.is_empty():
        return
    h = profile.content_hash()
    key = f"{storage.active_person() or ''}:{h}"
    if key in _reassessed:
        return
    _reassessed.add(key)
    snap = await storage.get_snapshot(h)          # only an understanding that already exists — never starts an AI build
    if snap is None:
        return
    try:
        n = await jobs_svc.reassess_outdated(snap, profile.model_dump(mode="json"))
        if n:
            log.info("jobs_reassessed", count=n)
    except Exception as exc:
        log.warning("jobs_reassess_failed", error=str(exc)[:160])


@router.get("/jobs")
async def list_jobs(view: str = "recommended", run_id: str = "", q: str = "", work_mode: str = "",
                    min_score: int = 0, sort: Literal["chance", "score", "reach", "recent"] = "chance", limit: int = 200,
                    offset: int = 0):
    """One page of jobs (page through with offset; has_more says whether another page exists) plus the tab counts."""
    if view not in jobs_svc.VIEWS:
        raise HTTPException(400, f"Unknown view '{view}'")
    await _refresh_outdated_once()
    items, counts = await jobs_svc.list_jobs(view, await _current_hash(), run_id=run_id, q=q.strip()[:100],
                                             work_mode=work_mode, min_score=min_score, sort=sort,
                                             limit=max(1, min(limit, 500)) + 1, offset=max(0, offset))
    lim = max(1, min(limit, 500))
    return {"jobs": items[:lim], "counts": counts, "has_more": len(items) > lim, "offset": max(0, offset)}


async def _detail_or_404(job_id: str) -> dict:
    d = await jobs_svc.detail(job_id, await _current_hash())
    if not d:
        raise HTTPException(404, "Job not found")
    return d


async def _summary_and_publish(job_id: str) -> dict:
    row = await storage.get_row(job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    s = jobs_svc.summary(row, await _current_hash())
    await emit({"type": "job.updated", "job_id": job_id, "data": {"job": s}})
    return s


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    return {"job": await _detail_or_404(job_id)}


@router.put("/jobs/{job_id}/saved")
async def save_job(job_id: str):
    if not await storage.set_saved(job_id, True):
        raise HTTPException(404, "Job not found")
    return {"job": await _summary_and_publish(job_id)}


@router.delete("/jobs/{job_id}/saved")
async def unsave_job(job_id: str):
    if not await storage.set_saved(job_id, False):
        raise HTTPException(404, "Job not found")
    return {"job": await _summary_and_publish(job_id)}


class TrackingUpdate(BaseModel):
    tracking_status: str
    # results tracking (services/outcomes.py): how you applied, whether a person was involved, what happened since
    channel: Optional[str] = Field(None, max_length=32)
    human_path: Optional[bool] = None
    event: Optional[Literal["reply", "screen", "interview", "offer", "rejected"]] = None


@router.patch("/jobs/{job_id}")
async def update_job(job_id: str, body: TrackingUpdate):
    from jobhunterx.services import outcomes
    if body.tracking_status not in storage.TRACKING_STATUSES:
        raise HTTPException(422, f"tracking_status must be one of {storage.TRACKING_STATUSES}")
    if body.channel is not None and body.channel not in outcomes.CHANNELS:
        raise HTTPException(422, f"channel must be one of {outcomes.CHANNELS}")
    if not await storage.set_tracking(job_id, body.tracking_status):
        raise HTTPException(404, "Job not found")
    row = await storage.get_row(job_id)
    if row:
        posting, match = storage.row_to_objects(row)
        try:
            current = json.loads(row.get("outcome_json") or "null")
        except ValueError:
            current = None
        tailored = bool(await storage.list_documents(job_id, "resume"))
        await outcomes.record_status(job_id, body.tracking_status, posting, match, current, channel=body.channel,
                                     human_path=body.human_path, tailored=tailored, event=body.event)
    return {"job": await _summary_and_publish(job_id)}


@router.get("/outcomes")
async def get_outcomes():
    """Interviews per 10 applications, per channel and overall, and what to change when nothing is working."""
    from jobhunterx.services import outcomes
    return {**outcomes.summarize(await storage.list_outcomes()), "channels": outcomes.CHANNEL_LABELS,
            "events": outcomes.EVENTS}


@router.get("/funding")
async def get_funding(refresh: bool = False):
    """Startups whose funding round was in the news in the last 120 days, with their open roles in the employer-boards index."""
    from jobhunterx.config.settings import get_settings
    from jobhunterx.discovery import ats_index, funding
    if not get_settings().enable_funding_signals:
        return {"enabled": False, "events": [], "status": funding.status()}
    places = None
    profile = await profile_svc.get_profile()
    if profile and not profile.is_empty():
        places = list(getattr(profile.preferences, "locations", None) or [])
    try:
        await asyncio.wait_for(funding.refresh(places, force=refresh), 25)
    except Exception as exc:                 # feeds down: show what is already known
        log.info("funding_refresh_failed", error=str(exc)[:120])
    events = funding.recent()[:80]
    keys = {funding.company_key(e["company"]) for e in events}
    openings: dict[str, list] = {}
    for r in ats_index._load() if get_settings().enable_ats_index else []:
        k = funding.company_key(r.company)
        if k in keys:
            openings.setdefault(k, []).append(r)
    out = []
    for e in events:
        rows = openings.get(funding.company_key(e["company"]), [])
        out.append({**e, "openings": len(rows), "entry_openings": sum(1 for r in rows if ats_index.LEVELS.get(r.level, 9) <= 1),
                    "board_url": rows[0].url if rows else ""})
    return {"enabled": True, "events": out, "status": funding.status()}


@router.post("/jobs/{job_id}/verify")
async def verify_job(job_id: str):
    profile = await profile_svc.get_profile()
    snap = await profile_svc.get_snapshot(profile) if profile and not profile.is_empty() else None
    if not await jobs_svc.verify(job_id, snap, profile.model_dump(mode="json") if profile else None):
        raise HTTPException(404, "Job not found")
    await _summary_and_publish(job_id)
    return {"job": await _detail_or_404(job_id)}


@router.post("/jobs/{job_id}/rescore")
async def rescore_job(job_id: str):
    profile = await _profile_or_400()
    snap = await profile_svc.get_snapshot(profile)
    if not await jobs_svc.rescore(job_id, snap, profile.model_dump(mode="json")):
        raise HTTPException(404, "Job not found")
    await _summary_and_publish(job_id)
    return {"job": await _detail_or_404(job_id)}


class OfficeChatIn(BaseModel):
    a: str
    b: str
    scene: str = ""
    a_knows: list[str] = Field(default_factory=list)
    b_knows: list[str] = Field(default_factory=list)
    moods: dict[str, str] = Field(default_factory=dict)
    drama: str = "banter"
    relation: str = ""
    recent: list[str] = Field(default_factory=list, max_length=30)
    working: bool = False


class OfficeAskIn(BaseModel):
    agent: str
    question: str = Field(min_length=1, max_length=400)


@router.post("/office/chat")
async def office_chat(body: OfficeChatIn):
    """A break-time conversation from the dialogue bank — no AI call (204 when none fits yet: the office uses scripted talk)."""
    from jobhunterx.services import office
    out = await office.chat(body.a, body.b, body.scene, body.a_knows, body.b_knows, body.moods,
                            drama=body.drama, relation=body.relation, recent=body.recent, working=body.working)
    return out or Response(status_code=204)


@router.get("/office/bank")
async def office_bank():
    """How many conversations are ready, by kind, and when the next batch is written."""
    from jobhunterx.services import office
    return await office.bank_status()


@router.post("/office/ask")
async def office_ask(body: OfficeAskIn):
    from jobhunterx.services import office
    return await office.ask(body.agent, body.question)


@router.post("/jobs/{job_id}/connect")
async def connect_job(job_id: str):
    """The Connector for one job: routes to a real person there and a referral note (made again on request)."""
    from jobhunterx.intelligence import connect
    profile = await _profile_or_400()
    row = await storage.get_row(job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    p, m = storage.row_to_objects(row)
    snap = await profile_svc.get_snapshot(profile)
    kit = await connect.build(p, m, profile, snap)
    await storage.set_connection(job_id, kit.model_dump(mode="json"))
    return {"job": await _detail_or_404(job_id)}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    if not await db.delete_job(job_id):
        raise HTTPException(404, "Job not found")
    await emit({"type": "job.deleted", "data": {"ids": [job_id]}})
    return {"ok": True}


@router.delete("/jobs")
async def delete_jobs(scope: Literal["unsaved", "all"] = "unsaved"):
    n = await storage.delete_jobs(scope)
    await emit({"type": "job.deleted", "data": {"ids": [], "scope": scope}})
    return {"deleted": n}


@router.post("/jobs/{job_id}/apply")
async def apply_job(job_id: str):
    """Check the kit → write what is missing → open the browser agent (all in the background)."""
    await _profile_or_400()
    if not await storage.get_row(job_id):
        raise HTTPException(404, "Job not found")
    try:
        session = await apply_svc.start(job_id, emit)
    except apply_svc.ApplyError as exc:
        raise HTTPException(409, str(exc))
    return {"status": "started", "session": session}


# ---------------------------------------------------------------------------
# Auto-apply session controls
# ---------------------------------------------------------------------------

@router.get("/apply/current")
async def apply_current():
    return {"session": await apply_svc.current()}


def _session_or_404(snap):
    if snap is None:
        raise HTTPException(404, "No auto-apply session for this job")
    return {"session": snap}


@router.post("/apply/{job_id}/stop")
async def apply_stop(job_id: str):
    return _session_or_404(await apply_svc.stop(job_id))


@router.post("/apply/{job_id}/take-over")
async def apply_take_over(job_id: str):
    from jobhunterx.agents import browser_agent as ba
    return _session_or_404(await ba.take_over(job_id))


@router.post("/apply/{job_id}/release")
async def apply_release(job_id: str):
    from jobhunterx.agents import browser_agent as ba
    return _session_or_404(await ba.release(job_id))


@router.post("/apply/{job_id}/continue")
async def apply_continue(job_id: str):
    """Let the agent pick up from where it stopped (same browser if it is still open)."""
    await _profile_or_400()
    if not await storage.get_row(job_id):
        raise HTTPException(404, "Job not found")
    try:
        return {"status": "started", "session": await apply_svc.start(job_id, emit, continuing=True)}
    except apply_svc.ApplyError as exc:
        raise HTTPException(409, str(exc))


@router.post("/apply/{job_id}/close")
async def apply_close(job_id: str):
    from jobhunterx.agents import browser_agent as ba
    snap = await ba.close(job_id)
    if snap is None:
        snap = await storage.get_apply_session(job_id)
    return _session_or_404(snap)


@router.post("/apply/{job_id}/done")
async def apply_mark_done(job_id: str):
    """You finished the application yourself."""
    from jobhunterx.agents import browser_agent as ba
    await storage.set_tracking(job_id, "applied")
    await db.update_job(job_id, status="applied")
    await db.resolve_job_interventions(job_id, "resolved")
    sess = ba.get_session(job_id)
    if sess:
        sess.update(status="applied", message="You submitted it 🎉", notice="")
        return {"session": sess.snapshot()}
    snap = await storage.get_apply_session(job_id)
    if snap:
        snap.update(status="applied", message="You submitted it 🎉", notice="", live=False)
        await storage.save_apply_session(snap)
        await emit({"type": "apply.session", "job_id": job_id, "data": {"session": snap}})
    return {"session": snap}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class JobDocumentRequest(BaseModel):
    kind: Literal["resume", "cover_letter"]


class CvRequest(BaseModel):
    focus: str = Field("", max_length=120)


MAX_DOC_BYTES = 300_000          # a resume is a few KB; this only stops abuse


def _doc_size_ok(content: dict) -> dict:
    if len(json.dumps(content, ensure_ascii=False)) > MAX_DOC_BYTES:
        raise ValueError("The document is too large.")
    return content


class DocumentUpdateRequest(BaseModel):
    content: dict

    @field_validator("content")
    @classmethod
    def _small(cls, v):
        return _doc_size_ok(v)


class StyleRequest(BaseModel):
    style: str = Field(..., max_length=32)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field("", max_length=600)


class ChatRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=600)
    content: Optional[dict] = None            # the draft the user is looking at (unsaved edits included)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)

    @field_validator("content")
    @classmethod
    def _small(cls, v):
        return _doc_size_ok(v) if v is not None else v


async def _doc_detail(doc) -> dict:
    current = await _current_hash()
    job = None
    if doc.job_id:
        row = await storage.get_row(doc.job_id)
        if row:
            job, _ = storage.row_to_objects(row)
    return {**jobs_svc.document_summary(doc, current, job), "content": doc.content,
            "provenance": doc.provenance.model_dump(mode="json")}


@router.post("/jobs/{job_id}/documents")
async def create_job_document(job_id: str, body: JobDocumentRequest):
    profile = await _profile_or_400()
    snap = await profile_svc.get_snapshot(profile)
    try:
        doc = await docs_svc.generate_for_job(job_id, body.kind, profile, snap, emit)
    except docs_svc.JobNotFound:
        raise HTTPException(404, "Job not found")
    except docs_svc.AlreadyGenerating as exc:
        raise HTTPException(409, str(exc))
    except GenerationUnavailable as exc:
        raise HTTPException(502, str(exc))
    await _summary_and_publish(job_id)
    return {"document": await _doc_detail(doc)}


@router.post("/documents/cv")
async def create_cv(body: CvRequest):
    profile = await _profile_or_400()
    snap = await profile_svc.get_snapshot(profile)
    try:
        doc = await docs_svc.generate_cv_doc(profile, snap, body.focus.strip(), emit)
    except docs_svc.AlreadyGenerating as exc:
        raise HTTPException(409, str(exc))
    return {"document": await _doc_detail(doc)}


@router.get("/documents")
async def list_documents(job_id: str = "", kind: str = ""):
    docs = await storage.list_documents(job_id or None, kind or None)
    current = await _current_hash()
    rows = await storage.get_rows([d.job_id for d in docs if d.job_id])      # one query, not one per document
    jobs = {jid: storage.row_to_objects(r)[0] for jid, r in rows.items()}
    return {"documents": [jobs_svc.document_summary(d, current, jobs.get(d.job_id)) for d in docs]}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = await storage.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"document": await _doc_detail(doc)}


@router.patch("/documents/{doc_id}")
async def update_document(doc_id: str, body: DocumentUpdateRequest):
    doc = await storage.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    profile = await _profile_or_400()
    try:
        updated = await docs_svc.update_document(doc, body.content, profile)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except LookupError:
        raise HTTPException(404, "Document not found")
    await _summary_and_publish(doc.job_id) if doc.job_id else None
    return {"document": await _doc_detail(updated)}


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "", (s or "").strip().replace(" ", "_"))[:40]


@router.get("/document-styles")
async def document_styles():
    """The visual styles a resume / CV / cover letter can be shown and downloaded in (same content, different look)."""
    return {"default": gen_styles.DEFAULT_STYLE, "styles": gen_styles.listing()}


@router.patch("/documents/{doc_id}/style")
async def set_document_style(doc_id: str, body: StyleRequest, request: Request):
    """Save the chosen style and re-render the stored PDF in it. The preview switches instantly in the browser; this is
    what makes a later plain download (and Auto-apply's attachment) use the same style."""
    ratelimit.check(request, "doc-style", limit=30, per_s=60)
    if not gen_styles.valid(body.style):
        raise HTTPException(422, "Unknown style")
    doc = await storage.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    profile = await _profile_or_400()
    try:
        updated = await docs_svc.set_style(doc, body.style, profile)
    except LookupError:
        raise HTTPException(404, "Document not found")
    return {"document": await _doc_detail(updated)}


@router.post("/documents/{doc_id}/chat")
async def chat_edit_document(doc_id: str, body: ChatRequest, request: Request):
    """Ask the AI for a change to this document. Returns a PROPOSAL (small fact-checked edits applied to a copy);
    nothing is saved until the user keeps it, which goes through PATCH /documents/{id}."""
    ratelimit.check(request, "doc-chat-min", limit=10, per_s=60)
    ratelimit.check(request, "doc-chat-hour", limit=80, per_s=3600)
    doc = await storage.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    profile = await _profile_or_400()
    try:
        out = await chat_edit.chat_edit(doc.kind, body.content if body.content is not None else doc.content, body.instruction,
                                        profile, [t.model_dump() for t in body.history])
    except chat_edit.ChatEditError as exc:
        raise HTTPException(422, str(exc))
    return out.model_dump(mode="json")


@router.get("/documents/{doc_id}/pdf")
async def get_document_pdf(doc_id: str, request: Request, style: str = ""):
    doc = await storage.get_document(doc_id)
    pdf = await storage.get_document_pdf(doc_id) if doc else None
    if not doc or not pdf:
        raise HTTPException(404, "Document not found")
    profile = await profile_svc.get_profile()
    if style and style != doc.style:
        if not gen_styles.valid(style):
            raise HTTPException(422, "Unknown style")
        ratelimit.check(request, "doc-pdf-style", limit=20, per_s=60)       # a re-render costs CPU
        pdf = await docs_svc.pdf_in_style(doc, profile, style)
    parts = [_slug(profile.name if profile else ""), {"resume": "Resume", "cv": "CV", "cover_letter": "Cover_Letter"}[doc.kind]]
    if doc.job_id:
        row = await storage.get_row(doc.job_id)
        if row:
            parts.append(_slug(row.get("company") or ""))
    fname = "_".join(p for p in parts if p) + ".pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if not await storage.delete_document(doc_id):
        raise HTTPException(404, "Document not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Settings, models, usage (system)
# ---------------------------------------------------------------------------

def _mask(key: Optional[str]) -> str:
    v = (key or "").strip()
    if not v:
        return ""
    return "******" if len(v) <= 6 else "********" + v[-4:]


_KEY_FIELDS = {  # payload key → (settings attr, env var names)
    "tinyfish_api_key": ("tinyfish_api_key", ["TINYFISH_API_KEY"]),
    "tavily_api_key": ("tavily_api_key", ["TAVILY_API_KEY"]),
    "exa_api_key": ("exa_api_key", ["EXA_API_KEY"]),
    "brave_api_key": ("brave_api_key", ["BRAVE_API_KEY"]),
    "google_api_key": ("google_api_key", ["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
    "gemini_api_key": ("google_api_key", ["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
    "groq_api_key": ("groq_api_key", ["GROQ_API_KEY"]),
    "mistral_api_key": ("mistral_api_key", ["MISTRAL_API_KEY"]),
    "nvidia_api_key": ("nvidia_api_key", ["NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"]),
    "kilo_api_key": ("kilo_api_key", ["KILO_API_KEY"]),
    "browser_use_api_key": ("browser_use_api_key", ["BROWSER_USE_API_KEY"]),
    "adzuna_api_key": ("adzuna_api_key", ["ADZUNA_API_KEY"]),
}
_BOOL_FIELDS = {"enable_web_search_apis": "ENABLE_WEB_SEARCH_APIS", "brave_enabled": "BRAVE_ENABLED",
                "strict_zero_spend_protection": "STRICT_ZERO_SPEND_PROTECTION", "enable_hn_source": "ENABLE_HN_SOURCE",
                "enable_yc_source": "ENABLE_YC_SOURCE", "enable_reddit_source": "ENABLE_REDDIT_SOURCE",
                "enable_founder_posts": "ENABLE_FOUNDER_POSTS", "enable_funding_signals": "ENABLE_FUNDING_SIGNALS",
                "enable_domain_age_check": "ENABLE_DOMAIN_AGE_CHECK"}
_SEARCH_PROVIDERS = ("tinyfish", "tavily", "exa", "brave", "deep", "ddgs")


def _env_file_keys() -> dict[str, str]:
    from jobhunterx.config.settings import _BASE_DIR
    path = _BASE_DIR / ".env"
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _source(env_names: list[str], file_keys: dict[str, str]) -> str:
    if any(file_keys.get(n) for n in env_names):
        return ".env file"
    if any(os.environ.get(n) for n in env_names):
        return "system environment"
    return ""


# Non-secret settings that can be edited from the UI (and are written back to .env).
_TUNABLES = {
    "max_jobs_per_search": ("MAX_JOBS_PER_SEARCH", int, 5, 200),
    "watch_interval_hours": ("WATCH_INTERVAL_HOURS", float, 0, 24),
    "max_llm_jd_extractions_per_search": ("MAX_LLM_JD_EXTRACTIONS_PER_SEARCH", int, 0, 200),
    "fetch_timeout_s": ("FETCH_TIMEOUT_S", float, 3, 60),
    "tavily_search_depth": ("TAVILY_SEARCH_DEPTH", str, None, None),
    "exa_search_num_results": ("EXA_SEARCH_NUM_RESULTS", int, 1, 50),
    "browser_show_window": ("BROWSER_SHOW_WINDOW", bool, None, None),
    "browser_max_steps": ("BROWSER_MAX_STEPS", int, 10, 150),
    "browser_step_delay_s": ("BROWSER_STEP_DELAY_S", float, 0, 20),
    "apply_with_cover_letter": ("APPLY_WITH_COVER_LETTER", bool, None, None),
    "apply_with_cv": ("APPLY_WITH_CV", bool, None, None),
    "fresher_floor_track": ("FRESHER_FLOOR_TRACK", bool, None, None),
}


@router.get("/settings")
async def get_settings_masked():
    from jobhunterx.config import app_state
    from jobhunterx.config.settings import get_settings
    s = get_settings()
    user = auth_ctx.restricted()
    file_keys = {} if user else _env_file_keys()
    out = {k: getattr(s, k) for k in _BOOL_FIELDS}
    out["primary_search_provider"] = s.primary_search_provider
    out["search_providers"] = list(_SEARCH_PROVIDERS)
    names = {"google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"], "groq": ["GROQ_API_KEY"], "mistral": ["MISTRAL_API_KEY"],
             "nvidia": ["NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"], "kilo": ["KILO_API_KEY"], "tinyfish": ["TINYFISH_API_KEY"], "tavily": ["TAVILY_API_KEY"], "exa": ["EXA_API_KEY"], "brave": ["BRAVE_API_KEY"],
             "browser_use": ["BROWSER_USE_API_KEY"], "adzuna": ["ADZUNA_API_KEY"]}
    for name, env_names in names.items():
        val = getattr(s, f"{name}_api_key")
        out[f"{name}_configured"] = bool(val)
        out[f"{name}_key_masked"] = _mask(val)
        out[f"{name}_source"] = ("your account" if user else _source(env_names, file_keys)) if val else ""
    out["tunables"] = {k: getattr(s, k) for k in _TUNABLES}
    from jobhunterx.tools import deep_search
    out["deep_engines"] = deep_search.engine_status()
    out["providers"] = {"llm": app_state.get("llm.providers"), "search": app_state.get("search.providers"),
                        "search_order": app_state.get("search.order"), "search_strategy": app_state.get("search.strategy")}
    out["office_ai_enabled"] = app_state.office_ai_enabled()
    out["browser"] = _browser_status()
    out["restricted"] = user is not None        # prod mode, not the admin: own keys only, server settings read-only
    out["auth"] = auth.enabled()
    if user is not None:
        out["providers"]["llm"] = {p: p not in auth_ctx.SHARED_POOLS for p in app_state.LLM_PROVIDERS}
        return out
    from jobhunterx.config.settings import _BASE_DIR
    out["env_file"] = str(_BASE_DIR / ".env")
    out["env_file_exists"] = (_BASE_DIR / ".env").exists()
    return out


def _persist_env(updates: dict[str, str]) -> None:
    from jobhunterx.config.settings import _BASE_DIR
    path = _BASE_DIR / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    done, out = set(), []
    for line in lines:
        k = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if k in updates:
            out.append(f"{k}={updates[k]}")
            done.add(k)
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in updates.items() if k not in done]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


_KEY_PROVIDER = {"gemini_api_key": "google", **{f"{p}_api_key": p for p in auth_ctx.USER_KEY_PROVIDERS}}


async def _save_own_keys(payload: dict) -> dict:
    """Prod mode, a normal user: only their own keys can be saved (encrypted in their account, never in .env)."""
    user = auth_ctx.restricted()
    extra = [k for k in payload if k not in _KEY_PROVIDER]
    if extra:
        raise HTTPException(403, "Only the admin can change server settings. You can add or remove your own keys.")
    updates = {_KEY_PROVIDER[k]: str(v or "") for k, v in payload.items()}
    user.keys = await auth.save_user_keys(user.id, updates)
    user._settings = None                     # this request sees the new keys at once
    return await get_settings_masked()


@router.post("/settings")
async def update_settings(payload: dict):
    from jobhunterx.config import models as M
    from jobhunterx.config.settings import get_settings
    if auth_ctx.restricted() is not None:
        return await _save_own_keys(payload)
    auth.require_admin()
    if "office_ai_enabled" in payload:
        from jobhunterx.config import app_state
        await app_state.set("office.ai", bool(payload.pop("office_ai_enabled")))
    s = get_settings()
    env: dict[str, str] = {}
    keys_changed = False
    for field, (attr, env_names) in _KEY_FIELDS.items():
        if field in payload:
            key = str(payload[field] or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_\-.:]{0,256}", key):
                raise HTTPException(422, f"{field} contains invalid characters")
            setattr(s, attr, key if is_real_key(key) else None)
            keys_changed = True
            for n in env_names:
                if key:
                    os.environ[n] = key
                else:
                    os.environ.pop(n, None)
                env[n] = key
    for field, env_name in _BOOL_FIELDS.items():
        if field in payload:
            val = bool(payload[field])
            setattr(s, field, val)
            env[env_name] = "true" if val else "false"
    if "primary_search_provider" in payload:
        val = str(payload["primary_search_provider"]).lower()
        if val not in _SEARCH_PROVIDERS:
            raise HTTPException(422, "Unknown search provider")
        s.primary_search_provider = val
        env["PRIMARY_SEARCH_PROVIDER"] = val
    for field, (env_name, typ, lo, hi) in _TUNABLES.items():
        if field in (payload.get("tunables") or {}):
            raw = payload["tunables"][field]
            try:
                val = (raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes")) if typ is bool else typ(raw)
            except (TypeError, ValueError):
                raise HTTPException(422, f"{field} must be a {typ.__name__}")
            if lo is not None and not (lo <= val <= hi):
                raise HTTPException(422, f"{field} must be between {lo} and {hi}")
            setattr(s, field, val)
            env[env_name] = ("true" if val else "false") if typ is bool else str(val)
    if env:
        try:
            _persist_env(env)
        except OSError as exc:
            log.warning("persist_env_failed", error=str(exc))
    if keys_changed:
        asyncio.create_task(M.refresh_available(force=True))
    return await get_settings_masked()


class ProvidersBody(BaseModel):
    llm: Optional[dict[str, bool]] = None
    search: Optional[dict[str, bool]] = None
    search_order: Optional[list[str]] = None
    search_strategy: Optional[Literal["smart", "fallback", "spread", "combine"]] = None


@router.post("/providers")
async def update_providers(body: ProvidersBody):
    """Turn LLM / search providers on or off, reorder search providers, choose the search strategy."""
    from jobhunterx.config import app_state
    auth.require_admin()
    if body.llm is not None:
        cur = app_state.get("llm.providers")
        cur.update({k: bool(v) for k, v in body.llm.items() if k in app_state.LLM_PROVIDERS})
        await app_state.set("llm.providers", cur)
    if body.search is not None:
        cur = app_state.get("search.providers")
        cur.update({k: bool(v) for k, v in body.search.items() if k in app_state.SEARCH_PROVIDERS})
        await app_state.set("search.providers", cur)
    if body.search_order is not None:
        order = [p for p in body.search_order if p in app_state.SEARCH_PROVIDERS]
        order += [p for p in app_state.SEARCH_PROVIDERS if p not in order]
        await app_state.set("search.order", order)
    if body.search_strategy is not None:
        await app_state.set("search.strategy", body.search_strategy)
    return await get_settings_masked()


@router.get("/models")
async def get_models(refresh: bool = Query(False)):
    from jobhunterx.config import models as M
    from jobhunterx.config.llm_router import get_model_config
    if refresh:
        await M.refresh_available(force=True)
    return {**get_model_config(), "availability": M.availability()}


class ModelSelection(BaseModel):
    chain: str
    model_id: str


@router.post("/models")
async def set_model(body: ModelSelection):
    from jobhunterx.config.llm_router import FALLBACK_CHAINS, get_model_config, set_model_config
    auth.require_admin()
    if body.chain not in FALLBACK_CHAINS or body.model_id not in {m["id"] for m in get_model_config()["all_models"]}:
        raise HTTPException(422, "Unknown chain or model")
    await set_model_config(body.chain, body.model_id)
    return {"status": "ok", "config": get_model_config()}


# ---------------------------------------------------------------------------
# Database health
# ---------------------------------------------------------------------------

@router.get("/system/health")
async def system_health():
    from jobhunterx import db_health
    auth.require_admin()
    return await db_health.check(db.get_db_path(), repair=False)


@router.post("/system/repair")
async def system_repair():
    from jobhunterx import db_health
    auth.require_admin()
    report = await db_health.check(db.get_db_path(), repair=True)
    return report


@router.post("/system/backup")
async def system_backup():
    from jobhunterx import db_health
    auth.require_admin()
    path = await db_health.backup(db.get_db_path())
    return {"path": path}


@router.get("/usage")
async def usage():
    from jobhunterx.config.llm_router import get_model_config
    from jobhunterx.tools.usage_ledger import get_usage_report
    auth.require_admin()                      # server-wide numbers
    search_report = await get_usage_report()
    llm = await db.get_token_usage_summary()
    by_model = llm.get("by_model", {})
    models = {m["id"]: m for m in get_model_config()["all_models"]}
    rows = [{"model": mid, "label": models.get(mid, {}).get("name", mid), "provider": models.get(mid, {}).get("provider", ""),
             **{k: u.get(k, 0) for k in ("calls", "tokens_in", "tokens_out", "total_tokens")}}
            for mid, u in by_model.items()]
    rows.sort(key=lambda r: -r["calls"])
    return {
        "web_search": {"providers": [{"name": n, **search_report.get(n, {})} for n in _SEARCH_PROVIDERS]},
        "llm": {"rows": rows, "totals": {"calls": llm.get("total_calls", 0), "tokens_in": llm.get("total_in", 0),
                                         "tokens_out": llm.get("total_out", 0), "total_tokens": llm.get("grand_total", 0)}},
        "now": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def status():
    run = search_manager.current
    out = {"search": run["status"] if run else "idle", "jobs": await storage.count()}
    user = auth_ctx.current()
    if user is None or user.is_admin:          # server-wide AI usage: the admin's business only
        out["token_usage"] = await db.get_token_usage_summary()
    return out


# ---------------------------------------------------------------------------
# Browser agent, interventions, reset
# ---------------------------------------------------------------------------

_pipeline_mode = "manual"


@router.get("/pipeline-mode")
async def get_pipeline_mode():
    return {"mode": _pipeline_mode}


@router.post("/pipeline-mode")
async def set_pipeline_mode(mode: Optional[str] = None):
    global _pipeline_mode
    auth.require_admin()
    if mode:
        if mode not in ("automatic", "manual"):
            raise HTTPException(422, "mode must be 'automatic' or 'manual'")
        _pipeline_mode = mode
    return {"mode": _pipeline_mode}


class ResumeAgentRequest(BaseModel):
    job_id: str
    action: Literal["done", "skip"] = "done"


@router.post("/resume-agent")
async def resume_agent(body: ResumeAgentRequest):
    if not await storage.owns("job", body.job_id):
        raise HTTPException(404, "Not found")
    if body.action == "skip":
        from jobhunterx.agents import browser_agent as ba
        await ba.close(body.job_id)
        await db.update_job(body.job_id, status="skipped")
        return {"status": "ok"}
    try:
        return {"status": "started", "session": await apply_svc.start(body.job_id, emit, continuing=True)}
    except apply_svc.ApplyError as exc:
        raise HTTPException(409, str(exc))


@router.post("/stop-browser")
async def stop_browser():
    from jobhunterx.agents import browser_agent as ba
    sess = _own(ba.current_session())
    if sess:
        await apply_svc.stop(sess.data["job_id"])
    return {"status": "ok"}


def _own(sess):
    """The session if it is the signed-in user's (prod mode); None otherwise."""
    return sess if sess and sess.data.get("user_id") == _uid() else None


@router.post("/browser/takeover")
async def browser_takeover(job_id: str = ""):
    from jobhunterx.agents import browser_agent as ba
    sess = _own(ba.get_session(job_id) if job_id else ba.current_session())
    if sess:
        await ba.take_over(sess.data["job_id"])
    return {"status": "ok"}


@router.post("/browser/release")
async def browser_release(job_id: str = ""):
    from jobhunterx.agents import browser_agent as ba
    sess = _own(ba.get_session(job_id) if job_id else ba.current_session())
    if sess:
        await ba.release(sess.data["job_id"])
    return {"status": "ok"}


async def _my_interventions() -> list[dict]:
    return await storage.pending_interventions()       # the open profile's own (and so the signed-in user's)


@router.get("/interventions")
async def interventions():
    return {"interventions": await _my_interventions()}


@router.post("/interventions/{session_id}/resolve")
async def resolve_intervention(session_id: int, status: Literal["resolved", "skipped"] = "resolved"):
    sessions = await _my_interventions()
    target = next((s for s in sessions if s.get("id") == session_id), None)
    if not target:
        raise HTTPException(404, "Intervention not found")
    await db.resolve_intervention(session_id, status)
    return {"status": "ok"}


@router.post("/interventions/{job_id}/focus")
async def focus_intervention(job_id: str):
    from jobhunterx.agents import browser_agent as ba
    return {"status": "ok", "focused": await ba.focus_browser_session(job_id)}


@router.get("/screenshots/{job_id}")
async def screenshot(job_id: str):
    from jobhunterx.config.settings import get_settings
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
        raise HTTPException(404, "Screenshot not found")
    path = Path(get_settings().screenshots_full_path) / f"{job_id}.png"
    if not path.exists():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(str(path), media_type="image/png")


@router.post("/reset")
async def reset():
    auth.require_admin()
    await search_manager.cancel_all()
    await apply_svc.cancel_all()
    await db.clear_database()
    await db.init_db()
    from jobhunterx.config import app_state
    await app_state.load(db.get_db_path())
    await app_state.set("people.active", None)
    await auth.init()                         # prod mode: the database was wiped; the admin from .env comes back
    await emit({"type": "log", "message": "All data was reset.", "data": {"level": "warn", "source": "system"}})
    return {"status": "ok"}
