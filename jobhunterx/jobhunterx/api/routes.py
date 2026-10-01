"""
JobHunterX — REST API (v2 contract, see docs/API.md).

Thin HTTP layer: validation, error mapping and event publishing. Business
logic lives in jobhunterx.services.*.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from jobhunterx import storage
from jobhunterx.agents import extractor
from jobhunterx.agents.browser_agent import stop_all_active_browsers
from jobhunterx.api.ws import manager as ws_manager
from jobhunterx.config import database as db
from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.generation.cover_letter import GenerationUnavailable
from jobhunterx.services import apply as apply_svc
from jobhunterx.services import documents as docs_svc
from jobhunterx.services import jobs as jobs_svc
from jobhunterx.services import profile as profile_svc
from jobhunterx.services.search import manager as search_manager

log = get_logger("routes")

router = APIRouter(prefix="/api")

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
    return {"tracking_statuses": storage.TRACKING_STATUSES}


@router.get("/profile")
async def get_profile():
    return await profile_svc.envelope(await profile_svc.get_profile())


@router.put("/profile")
@router.post("/profile")
async def put_profile(profile: CandidateProfile):
    await profile_svc.save_profile(profile)
    env = await profile_svc.envelope(profile)
    await emit({"type": "profile.updated", "data": env})
    return env


@router.post("/profile/upload")
@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The file is larger than 10 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(422, "Please upload a PDF resume.")
    profile, info = await extractor.extract_profile(data)
    if info["status"] == "failed":
        raise HTTPException(502, info["warnings"][0] if info["warnings"] else "Could not read the resume.")
    existing = await profile_svc.get_profile()
    if existing:  # keep what the user set that a resume cannot contain
        profile.preferences = existing.preferences
        profile.qa_memory = existing.qa_memory
    await profile_svc.save_profile(profile)
    env = await profile_svc.envelope(profile)
    await emit({"type": "profile.updated", "data": env})
    return {**env, "extraction": info}


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
    return {"run": search_manager.current or await storage.latest_run()}


@router.get("/searches/{run_id}")
async def get_search(run_id: str):
    run = search_manager.current if search_manager.current and search_manager.current["id"] == run_id \
        else await storage.get_run(run_id)
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
# Jobs
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(view: str = "recommended", run_id: str = "", q: str = "", work_mode: str = "",
                    min_score: int = 0, sort: Literal["score", "recent"] = "score", limit: int = 200):
    if view not in jobs_svc.VIEWS:
        raise HTTPException(400, f"Unknown view '{view}'")
    items, counts = await jobs_svc.list_jobs(view, await _current_hash(), run_id=run_id, q=q.strip()[:100],
                                             work_mode=work_mode, min_score=min_score, sort=sort,
                                             limit=max(1, min(limit, 500)))
    return {"jobs": items, "counts": counts}


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


@router.patch("/jobs/{job_id}")
async def update_job(job_id: str, body: TrackingUpdate):
    if body.tracking_status not in storage.TRACKING_STATUSES:
        raise HTTPException(422, f"tracking_status must be one of {storage.TRACKING_STATUSES}")
    if not await storage.set_tracking(job_id, body.tracking_status):
        raise HTTPException(404, "Job not found")
    return {"job": await _summary_and_publish(job_id)}


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
    await _profile_or_400()
    if not await storage.get_row(job_id):
        raise HTTPException(404, "Job not found")
    try:
        await apply_svc.start(job_id, emit)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    return {"status": "started"}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class JobDocumentRequest(BaseModel):
    kind: Literal["resume", "cover_letter"]


class CvRequest(BaseModel):
    focus: str = Field("", max_length=120)


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
    out = []
    for d in docs:
        job = None
        if d.job_id:
            row = await storage.get_row(d.job_id)
            job = storage.row_to_objects(row)[0] if row else None
        out.append(jobs_svc.document_summary(d, current, job))
    return {"documents": out}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = await storage.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"document": await _doc_detail(doc)}


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "", (s or "").strip().replace(" ", "_"))[:40]


@router.get("/documents/{doc_id}/pdf")
async def get_document_pdf(doc_id: str):
    doc = await storage.get_document(doc_id)
    pdf = await storage.get_document_pdf(doc_id) if doc else None
    if not doc or not pdf:
        raise HTTPException(404, "Document not found")
    profile = await profile_svc.get_profile()
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
}
_BOOL_FIELDS = {"enable_web_search_apis": "ENABLE_WEB_SEARCH_APIS", "brave_enabled": "BRAVE_ENABLED",
                "strict_zero_spend_protection": "STRICT_ZERO_SPEND_PROTECTION"}
_SEARCH_PROVIDERS = ("tinyfish", "tavily", "exa", "brave", "ddgs")


@router.get("/settings")
async def get_settings_masked():
    from jobhunterx.config.settings import get_settings
    s = get_settings()
    out = {k: getattr(s, k) for k in _BOOL_FIELDS}
    out["primary_search_provider"] = s.primary_search_provider
    out["search_providers"] = list(_SEARCH_PROVIDERS)
    for name in ("tinyfish", "tavily", "exa", "brave", "google", "groq", "mistral"):
        val = getattr(s, f"{name}_api_key")
        out[f"{name}_configured"] = bool(val)
        out[f"{name}_key_masked"] = _mask(val)
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


@router.post("/settings")
async def update_settings(payload: dict):
    from jobhunterx.config.settings import get_settings
    s = get_settings()
    env: dict[str, str] = {}
    for field, (attr, env_names) in _KEY_FIELDS.items():
        if field in payload:
            key = str(payload[field] or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_\-.:]{0,256}", key):
                raise HTTPException(422, f"{field} contains invalid characters")
            setattr(s, attr, key or None)
            for n in env_names:
                os.environ[n] = key
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
    if env:
        try:
            _persist_env(env)
        except OSError as exc:
            log.warning("persist_env_failed", error=str(exc))
    return await get_settings_masked()


@router.get("/models")
async def get_models():
    from jobhunterx.config.llm_router import get_model_config
    return get_model_config()


class ModelSelection(BaseModel):
    chain: str
    model_id: str


@router.post("/models")
async def set_model(body: ModelSelection):
    from jobhunterx.config.llm_router import FALLBACK_CHAINS, get_model_config, set_model_config
    if body.chain not in FALLBACK_CHAINS or body.model_id not in {m["id"] for m in get_model_config()["all_models"]}:
        raise HTTPException(422, "Unknown chain or model")
    set_model_config(body.chain, body.model_id)
    return {"status": "ok", "config": get_model_config()}


@router.get("/usage")
async def usage():
    from jobhunterx.config import gemma
    from jobhunterx.config.llm_router import get_model_config
    from jobhunterx.tools.usage_ledger import get_usage_report
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
        "gemma_budget": gemma.budget_status(),
        "now": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def status():
    run = search_manager.current
    return {"search": run["status"] if run else "idle", "jobs": await storage.count(),
            "token_usage": await db.get_token_usage_summary()}


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
    from jobhunterx.agents import browser_agent as ba
    await ba.clear_paused_session(body.job_id)
    if body.action == "skip":
        await db.update_job(body.job_id, status="skipped")
        return {"status": "ok"}
    try:
        await apply_svc.start(body.job_id, emit)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    return {"status": "started"}


@router.post("/stop-browser")
async def stop_browser():
    await apply_svc.cancel_all()
    await stop_all_active_browsers()
    return {"status": "ok"}


@router.post("/browser/takeover")
async def browser_takeover(job_id: str = ""):
    from jobhunterx.agents import browser_agent as ba
    if job_id:
        ba.pause_streaming(job_id)
    return {"status": "ok"}


@router.post("/browser/release")
async def browser_release(job_id: str = ""):
    from jobhunterx.agents import browser_agent as ba
    if job_id:
        ba.resume_streaming(job_id)
    return {"status": "ok"}


@router.get("/interventions")
async def interventions():
    return {"interventions": await db.get_pending_interventions()}


@router.post("/interventions/{session_id}/resolve")
async def resolve_intervention(session_id: int, status: Literal["resolved", "skipped"] = "resolved"):
    from jobhunterx.agents import browser_agent as ba
    sessions = await db.get_pending_interventions()
    target = next((s for s in sessions if s.get("id") == session_id), None)
    if not target:
        raise HTTPException(404, "Intervention not found")
    await ba.clear_paused_session(target["job_id"])
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
    await search_manager.cancel()
    await apply_svc.cancel_all()
    await db.clear_database()
    await storage.migrate()
    await emit({"type": "log", "message": "All data was reset.", "data": {"level": "warn", "source": "system"}})
    return {"status": "ok"}
