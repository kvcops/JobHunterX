"""
Vellum OS — REST API Routes

All endpoints for resume upload, search control, job listing,
outreach management, and HITL resume.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from vellum.config import database as db
from vellum.config.logging import get_logger
from vellum.agents import extractor, graph
from vellum.api.ws import manager as ws_manager
from vellum.tools.email_handoff import open_mail_client

log = get_logger("routes")

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartSearchRequest(BaseModel):
    location: str = "Bengaluru"
    role: str | None = None


class ResumeAgentRequest(BaseModel):
    job_id: str
    action: str = "done"  # "done" or "skip"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_current_profile: dict | None = None
_search_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF. Extracts profile and stores in SQLite."""
    global _current_profile

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) < 100:
        raise HTTPException(400, "File appears to be empty")

    log.info("resume_upload", filename=file.filename, size=len(pdf_bytes))

    profile = await extractor.extract_profile(pdf_bytes)
    profile_dict = profile.model_dump()

    # Store in SQLite
    profile_id = await db.insert_profile(profile_dict)
    _current_profile = profile_dict

    # Broadcast to WebSocket
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "profile_loaded",
        "message": f"Profile extracted: {profile.name}",
        "data": {
            "name": profile.name,
            "skills_count": len(profile.skills),
            "experience_count": len(profile.experience),
        },
    })

    return {
        "status": "ok",
        "profile_id": profile_id,
        "profile": profile_dict,
    }


@router.post("/start-search")
async def start_search(request: StartSearchRequest):
    """Start the discovery + per-job pipeline flow."""
    global _search_task

    if _current_profile is None:
        # Try loading from DB
        profile = await db.get_latest_profile()
        if profile is None:
            raise HTTPException(400, "No resume uploaded yet")
    else:
        profile = _current_profile

    # Cancel any running search
    if _search_task and not _search_task.done():
        _search_task.cancel()

    async def event_callback(event: dict):
        await ws_manager.broadcast(event)

    # Run in background
    async def _run():
        try:
            result = await graph.run_full_search(
                location=request.location,
                profile=profile,
                role=request.role,
                event_callback=event_callback,
            )
            log.info("search_complete", result=result)
        except Exception as exc:
            log.error("search_error", error=str(exc))
            await ws_manager.broadcast({
                "agent": "system",
                "event_type": "error",
                "message": f"Search error: {str(exc)[:200]}",
            })

    _search_task = asyncio.create_task(_run())

    return {"status": "started", "location": request.location}


@router.post("/resume-agent")
async def resume_agent(request: ResumeAgentRequest):
    """Resume a HITL-interrupted agent pipeline."""
    result = await graph.resume_job_pipeline(request.job_id, request.action)
    return {"status": "ok", "result": result}


@router.get("/jobs")
async def list_jobs(status: str = "", limit: int = 100):
    """List discovered jobs with optional status filter."""
    jobs = await db.get_jobs(status=status or None, limit=limit)
    # Don't send PDF blob in list response
    for j in jobs:
        j.pop("tailored_pdf", None)
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a single job detail."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    # Don't send binary PDF in JSON
    job.pop("tailored_pdf", None)
    return {"job": job}


@router.get("/jobs/{job_id}/resume-pdf")
async def download_resume_pdf(job_id: str):
    """Download the tailored resume PDF for a job."""
    from fastapi.responses import Response

    job = await db.get_job(job_id)
    if not job or not job.get("tailored_pdf"):
        raise HTTPException(404, "No tailored resume for this job")

    return Response(
        content=job["tailored_pdf"],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume_{job_id[:8]}.pdf"},
    )


@router.get("/outreach")
async def list_outreach(limit: int = 100):
    """List outreach drafts."""
    drafts = await db.get_outreach_drafts(limit=limit)
    return {"drafts": drafts}


@router.post("/outreach/{draft_id}/open-mail")
async def trigger_open_mail(draft_id: str):
    """Open the user's mail client with the outreach email."""
    drafts = await db.get_outreach_drafts()
    draft = next((d for d in drafts if d.get("id") == draft_id), None)
    if not draft:
        raise HTTPException(404, "Draft not found")

    mailto_uri = draft.get("mailto_uri", "")
    if not mailto_uri:
        raise HTTPException(400, "No mailto URI available")

    success = open_mail_client(mailto_uri)
    return {"status": "opened" if success else "failed"}


@router.post("/outreach/{draft_id}/discard")
async def discard_outreach(draft_id: str):
    """Mark an outreach draft as discarded."""
    # Simple update via raw SQL
    import aiosqlite
    from vellum.config.database import _db_path

    async with aiosqlite.connect(_db_path) as conn:
        await conn.execute(
            "UPDATE outreach_drafts SET status = 'discarded' WHERE id = ?",
            (draft_id,),
        )
        await conn.commit()
    return {"status": "discarded"}


@router.get("/status")
async def get_status():
    """Overall system status and token usage summary."""
    token_usage = await db.get_token_usage_summary()
    jobs = await db.get_jobs(limit=1000)
    status_counts = {}
    for j in jobs:
        s = j.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "status": "running" if _search_task and not _search_task.done() else "idle",
        "job_counts": status_counts,
        "total_jobs": len(jobs),
        "token_usage": token_usage,
    }


@router.post("/reset")
async def reset_system():
    """Cancel any active search task and clear the entire database."""
    global _search_task, _current_profile
    if _search_task and not _search_task.done():
        _search_task.cancel()
        _search_task = None
    
    # Clear active pipelines cache
    graph._active_pipelines.clear()
    
    await db.clear_database()
    _current_profile = None
    
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "reset",
        "message": "System halted and database successfully reset.",
    })
    return {"status": "ok"}


@router.get("/profile")
async def get_profile():
    """Get the current loaded profile details."""
    global _current_profile
    if _current_profile is None:
        _current_profile = await db.get_latest_profile()
    return {"profile": _current_profile}


@router.post("/profile")
async def update_profile(profile_data: dict):
    """Save/update the candidate profile details."""
    global _current_profile
    profile_id = await db.insert_profile(profile_data)
    _current_profile = profile_data
    
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "profile_updated",
        "message": f"Profile updated: {profile_data.get('name', 'Candidate')}",
    })
    return {"status": "ok", "profile_id": profile_id, "profile": profile_data}
