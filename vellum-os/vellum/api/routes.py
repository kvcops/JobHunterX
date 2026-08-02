"""
Vellum OS — REST API Routes

All endpoints for resume upload, search control, job listing,
outreach management, and HITL resume.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from vellum.config import database as db
from vellum.config.logging import get_logger
from vellum.agents import extractor, graph
from vellum.agents.browser_agent import stop_all_active_browsers
from vellum.api.ws import manager as ws_manager
from vellum.tools.email_handoff import open_mail_client, create_gmail_compose_url

log = get_logger("routes")

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartSearchRequest(BaseModel):
    location: str = "Bengaluru"
    role: str | None = None
    limit: int = 50


class ResumeAgentRequest(BaseModel):
    job_id: str
    action: str = "done"  # "done" or "skip"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_current_profile: dict | None = None
_search_task: asyncio.Task | None = None
_apply_tasks: dict[str, asyncio.Task] = {}  # Track per-job apply tasks
_pipeline_mode: str = "manual"  # "automatic" or "manual"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/locations")
async def get_available_locations():
    """Get list of all Indian tech hub locations configured in ats_api.py."""
    from vellum.tools.ats_api import TECH_HUB_STARTUPS
    keys = list(TECH_HUB_STARTUPS.keys())
    locations = []
    for k in keys:
        display = k.replace("-", " ").title()
        if k == "ncr":
            display = "NCR (Delhi / Gurgaon / Noida)"
        elif k == "remote":
            display = "Remote India"
        locations.append({"key": k, "label": display, "company_count": len(TECH_HUB_STARTUPS[k])})
    return {"locations": locations}


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

    # Always fetch the latest profile from DB to avoid stale state
    profile = await db.get_latest_profile()
    if profile is None:
        if _current_profile is not None:
            profile = _current_profile
        else:
            raise HTTPException(400, "No resume uploaded yet")

    # Cancel any running search and wait for it to finish
    if _search_task and not _search_task.done():
        _search_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_search_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    await stop_all_active_browsers()

    async def event_callback(event: dict):
        await ws_manager.broadcast(event)

    # Run in background
    async def _run():
        try:
            result = await graph.run_full_search(
                location=request.location,
                profile=profile,
                role=request.role,
                limit=request.limit,
                event_callback=event_callback,
                auto_apply=(_pipeline_mode == "automatic"),
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


@router.post("/stop-browser")
async def stop_browser_endpoint():
    """Explicitly halt any running Playwright/browser-use sessions."""
    log.info("received_stop_browser_request")
    await stop_all_active_browsers()
    global _search_task
    if _search_task and not _search_task.done():
        _search_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_search_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    return {"status": "ok", "message": "Browser session stopped successfully."}


@router.get("/browser/cdp-url")
async def get_browser_cdp_url():
    """Return the CDP websocket URL of the currently active browser session."""
    from vellum.agents.browser_agent import get_active_cdp_url
    return {"cdp_url": get_active_cdp_url()}


@router.post("/browser/takeover")
async def browser_takeover(job_id: str = ""):
    """User is taking over the live browser window.

    Pauses URL streaming so the UI doesn't fight the user, and attempts to
    bring the real Chrome window to the foreground (Windows).
    Returns the active CDP url for display.
    """
    from vellum.agents import browser_agent as ba
    if job_id:
        ba.pause_streaming(job_id)
    # Best-effort: bring Chrome to foreground on Windows.
    try:
        _focus_chrome_window()
    except Exception as exc:
        log.warning("focus_chrome_failed", error=str(exc))
    return {"status": "ok", "cdp_url": ba.get_active_cdp_url()}


@router.post("/browser/release")
async def browser_release(job_id: str = ""):
    """User finished manual control — resume URL streaming."""
    from vellum.agents import browser_agent as ba
    if job_id:
        ba.resume_streaming(job_id)
    return {"status": "ok"}


def _focus_chrome_window() -> None:
    """Bring the automation Chrome window to the foreground (Windows only)."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import subprocess
        # Focus by window title substring. The persistent profile launches
        # Chromium; "Chrome" / "Chromium" / "Edge" title fragments cover it.
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(New-Object -ComObject WScript.Shell).AppActivate('Chrome')"],
            capture_output=True, timeout=4,
        )
    except Exception:
        pass


def sanitize_for_json(data: Any) -> Any:
    """Recursively clean data for JSON serialization, replacing binary bytes with info strings."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if isinstance(v, bytes):
                cleaned[k] = f"<binary_bytes: {len(v)} bytes>"
            else:
                cleaned[k] = sanitize_for_json(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, bytes):
        return f"<binary_bytes: {len(data)} bytes>"
    return data


@router.post("/resume-agent")
async def resume_agent(request: ResumeAgentRequest):
    """Resume a HITL-interrupted agent pipeline."""
    result = await graph.resume_job_pipeline(request.job_id, request.action)
    clean_result = sanitize_for_json(result)
    return {"status": "ok", "result": clean_result}



@router.get("/jobs")
async def list_jobs(status: str = "", limit: int = 100):
    """List discovered jobs with optional status filter."""
    jobs = await db.get_jobs(status=status or None, limit=limit)
    # Don't send PDF blob in list response; parse validation_json
    for j in jobs:
        j.pop("tailored_pdf", None)
        # Fix match_score NA: ensure it's always a number
        if j.get("match_score") is None:
            # Try to extract from validation_json
            vj = j.get("validation_json")
            if vj and isinstance(vj, str):
                try:
                    v = json.loads(vj)
                    j["match_score"] = v.get("match_score", 0.0)
                    j["validation"] = v
                except (json.JSONDecodeError, TypeError):
                    j["match_score"] = 0.0
            else:
                j["match_score"] = 0.0
        # Parse validation_json into dict for frontend
        if "validation_json" in j and isinstance(j["validation_json"], str):
            try:
                j["validation"] = json.loads(j["validation_json"])
            except (json.JSONDecodeError, TypeError):
                j["validation"] = None
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a single job detail."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    # Don't send binary PDF in JSON
    job.pop("tailored_pdf", None)
    # Fix match_score NA
    if job.get("match_score") is None:
        vj = job.get("validation_json")
        if vj and isinstance(vj, str):
            try:
                v = json.loads(vj)
                job["match_score"] = v.get("match_score", 0.0)
                job["validation"] = v
            except (json.JSONDecodeError, TypeError):
                job["match_score"] = 0.0
        else:
            job["match_score"] = 0.0
    if "validation_json" in job and isinstance(job["validation_json"], str):
        try:
            job["validation"] = json.loads(job["validation_json"])
        except (json.JSONDecodeError, TypeError):
            job["validation"] = None
    return {"job": job}


@router.delete("/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Delete a single job listing by ID."""
    success = await db.delete_job(job_id)
    if not success:
        raise HTTPException(404, "Job not found or already deleted")
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "job_deleted",
        "job_id": job_id,
        "message": f"Job {job_id[:8]} deleted.",
    })
    return {"status": "ok", "job_id": job_id}


@router.post("/jobs/clear")
@router.delete("/jobs")
async def clear_jobs_endpoint(status: str = ""):
    """Clear all jobs (or jobs matching optional status filter) from the database."""
    count = await db.clear_jobs(status=status or None)
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "jobs_cleared",
        "message": f"Cleared {count} jobs.",
    })
    return {"status": "ok", "cleared_count": count}


@router.post("/jobs/{job_id}/apply")
async def apply_single_job(job_id: str):
    """Run the per-job pipeline when the user clicks 'Apply' on a job card.

    Clicking Apply is an explicit request to apply, so the full pipeline runs
    in both modes: validate/tailor (resume PDF) → contact search → email
    draft → browser agent. The pipeline mode ('manual' vs 'automatic') only
    controls whether discovery auto-applies without a click.
    """
    from vellum.agents.graph import run_single_job_apply

    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def _run():
        try:
            result = await run_single_job_apply(
                job_id,
                include_browser=True,
            )
            log.info("single_job_apply_complete", job_id=job_id, result_keys=list(result.keys()) if isinstance(result, dict) else str(result))
        except Exception as exc:
            log.error("single_job_apply_error", job_id=job_id, error=str(exc))
            await ws_manager.broadcast({
                "agent": "system",
                "event_type": "error",
                "job_id": job_id,
                "message": f"Apply error: {str(exc)[:200]}",
            })

    # Run in background so the HTTP response returns immediately
    task = asyncio.create_task(_run())
    _apply_tasks[job_id] = task
    # Clean up reference when done
    task.add_done_callback(lambda _: _apply_tasks.pop(job_id, None))

    return {"status": "started", "job_id": job_id, "message": "Application pipeline launched."}


@router.get("/jobs/{job_id}/resume-pdf")
async def download_resume_pdf(job_id: str):
    """Download the tailored resume PDF for a job, named after candidate + company."""
    from fastapi.responses import Response
    import re as _re

    job = await db.get_job(job_id)
    if not job or not job.get("tailored_pdf"):
        raise HTTPException(404, "No tailored resume for this job")

    # Build a readable filename: <Name>_<Company>_<Role>.pdf
    def _slug(s: str) -> str:
        s = (s or "").strip().replace(" ", "_")
        return _re.sub(r"[^A-Za-z0-9_\-]", "", s)[:40] or "resume"

    parts = [_slug(job.get("company", "")), _slug(job.get("role", ""))]
    fname = "_".join(p for p in parts if p) or f"resume_{job_id[:8]}"
    fname = fname + ".pdf"

    return Response(
        content=job["tailored_pdf"],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
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


@router.get("/outreach/{draft_id}/gmail-url")
async def get_gmail_url(draft_id: str):
    """Get direct Gmail web compose URL for an outreach draft."""
    drafts = await db.get_outreach_drafts()
    draft = next((d for d in drafts if d.get("id") == draft_id), None)
    if not draft:
        raise HTTPException(404, "Draft not found")

    email_guesses = draft.get("email_guesses", [])
    to_addr = email_guesses[0].get("address", "") if email_guesses else ""
    subject = draft.get("subject", "")
    body = draft.get("body", "")

    gmail_url = create_gmail_compose_url(to_addr, subject, body)
    return {"url": gmail_url, "to": to_addr, "subject": subject}



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
        "pipeline_mode": _pipeline_mode,
    }


@router.api_route("/pipeline-mode", methods=["GET", "POST"])
async def pipeline_mode_endpoint(mode: str | None = None):
    """Get or set the pipeline execution mode ('automatic' or 'manual')."""
    global _pipeline_mode
    if mode:
        target_mode = mode.lower()
        if target_mode in ("automatic", "manual"):
            _pipeline_mode = target_mode
            await ws_manager.broadcast({
                "agent": "system",
                "event_type": "pipeline_mode_changed",
                "message": f"Pipeline mode set to: {target_mode}",
                "data": {"mode": target_mode},
            })
            return {"status": "ok", "mode": _pipeline_mode}
        else:
            raise HTTPException(400, "Mode must be 'automatic' or 'manual'")
    return {"mode": _pipeline_mode}



@router.post("/reset")
async def reset_system():
    """Cancel any active search task and clear the entire database."""
    global _search_task, _current_profile, _apply_tasks
    if _search_task and not _search_task.done():
        _search_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_search_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        _search_task = None
    
    # Cancel active application tasks
    for job_id, task in list(_apply_tasks.items()):
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
            except Exception:
                pass
    _apply_tasks.clear()
    
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
    # Always try DB first for fresh data, fall back to in-memory
    profile = await db.get_latest_profile()
    if profile is not None:
        _current_profile = profile
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


# ---------------------------------------------------------------------------
# Intervention Sessions
# ---------------------------------------------------------------------------

@router.get("/interventions")
async def get_interventions():
    """Get all pending intervention sessions."""
    sessions = await db.get_pending_interventions()
    return {"interventions": sessions}


@router.post("/interventions/{session_id}/resolve")
async def resolve_intervention(session_id: int, status: str = "resolved"):
    """Mark an intervention session as resolved."""
    await db.resolve_intervention(session_id, status)
    return {"status": "ok"}


@router.get("/screenshots/{job_id}")
async def get_screenshot(job_id: str):
    """Serve a browser screenshot for a given job ID."""
    from pathlib import Path
    import re as _re
    from fastapi.responses import FileResponse
    from vellum.config.settings import get_settings

    if not _re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
        raise HTTPException(status_code=404, detail="Screenshot not found")

    screenshot_path = Path(get_settings().screenshots_full_path) / f"{job_id}.png"
    if screenshot_path.exists():
        return FileResponse(str(screenshot_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Screenshot not found")
