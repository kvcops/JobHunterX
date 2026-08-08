"""
JobHunterX — REST API Routes

Endpoints for resume upload, company tracking, job sync, job listing,
per-job apply (browser), and HITL resume.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from jobhunterx.config import database as db
from jobhunterx.config.logging import get_logger
from jobhunterx.agents import extractor, graph
from jobhunterx.agents.browser_agent import stop_all_active_browsers
from jobhunterx.api.ws import manager as ws_manager

log = get_logger("routes")

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartSearchRequest(BaseModel):
    location: str = "Bengaluru"
    role: str | None = None
    limit: int = 5000


class ResumeAgentRequest(BaseModel):
    job_id: str
    action: str = "done"  # "done" or "skip"


class CompanyInput(BaseModel):
    name: str
    website: str = ""
    careers_url: str = ""
    hub: str = ""


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_current_profile: dict | None = None
_sync_task: asyncio.Task | None = None
_apply_tasks: dict[str, asyncio.Task] = {}  # Track per-job apply tasks
_pipeline_mode: str = "manual"  # "automatic" or "manual"


# ---------------------------------------------------------------------------
# Company tracking (board-first discovery)
# ---------------------------------------------------------------------------

@router.get("/companies")
async def list_companies():
    """All tracked companies with detected ATS status."""
    companies = await db.get_companies()
    return {"companies": companies}


@router.post("/companies")
async def add_company(company: CompanyInput):
    """Add a company (probes its ATS board immediately)."""
    from jobhunterx.agents.job_sync import add_company as sync_add_company

    try:
        result = await sync_add_company(
            name=company.name,
            website=company.website,
            careers_url=company.careers_url,
            hub=company.hub,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "company_added",
        "message": f"Company added: {company.name}",
        "data": result,
    })
    return {"status": "ok", "company": result}


@router.post("/companies/load-seed")
async def load_seed_companies():
    """Load the bundled Indian-startup seed list into the DB."""
    from jobhunterx.agents.job_sync import load_seed_companies as seed_fn, ensure_companies_in_db

    rows = seed_fn()
    count = await ensure_companies_in_db(rows)
    return {"status": "ok", "loaded": count, "total_in_csv": len(rows)}


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str):
    """Remove a tracked company."""
    ok = await db.delete_company(company_id)
    if not ok:
        raise HTTPException(404, "Company not found")
    return {"status": "ok"}


@router.post("/companies/sync")
async def sync_companies():
    """Run one sync pass: probe ATS → fetch jobs → Gemma score → store."""
    global _sync_task

    profile = await db.get_latest_profile()
    if profile is None and _current_profile is not None:
        profile = _current_profile

    if _sync_task and not _sync_task.done():
        raise HTTPException(409, "A sync is already running")

    async def _run():
        try:
            from jobhunterx.agents.job_sync import run_sync

            result = await run_sync(
                profile=profile,
                event_cb=lambda e: ws_manager.broadcast(e),
            )
            log.info("sync_complete", result=result)
        except Exception as exc:
            log.error("sync_error", error=str(exc))
            await ws_manager.broadcast({
                "agent": "system",
                "event_type": "error",
                "message": f"Sync error: {str(exc)[:200]}",
            })

    _sync_task = asyncio.create_task(_run())
    return {"status": "started", "profile_loaded": profile is not None}


@router.get("/locations")
async def list_locations():
    """Supported target locations for the frontend dropdown."""
    SUPPORTED_LOCS = [
        ("bengaluru", "Bengaluru"),
        ("hyderabad", "Hyderabad"),
        ("mumbai", "Mumbai"),
        ("pune", "Pune"),
        ("chennai", "Chennai"),
        ("delhi ncr", "Delhi NCR"),
        ("kolkata", "Kolkata"),
        ("ahmedabad", "Ahmedabad"),
        ("kochi", "Kochi"),
        ("visakhapatnam", "Visakhapatnam"),
        ("coimbatore", "Coimbatore"),
        ("indore", "Indore"),
        ("jaipur", "Jaipur"),
        ("chandigarh", "Chandigarh"),
        ("lucknow", "Lucknow"),
        ("remote", "Remote"),
    ]
    return {"locations": [
        {"key": key, "label": label}
        for key, label in SUPPORTED_LOCS
    ]}


def _mask_api_key(key: Optional[str]) -> str:
    if not key or not key.strip():
        return ""
    val = key.strip()
    if len(val) <= 6:
        return "******"
    return "********" + val[-4:]


@router.get("/settings")
async def get_settings_masked():
    """Return application settings with masked API keys for privacy/security."""
    from jobhunterx.config.settings import get_settings
    s = get_settings()

    return {
        "enable_web_search_apis": getattr(s, "enable_web_search_apis", True),
        "search_router_mode": s.search_router_mode,
        "primary_search_provider": s.primary_search_provider,
        "strict_zero_spend_protection": s.strict_zero_spend_protection,
        "quality_score_threshold": s.quality_score_threshold,
        "tinyfish_configured": bool(s.tinyfish_api_key),
        "tinyfish_key_masked": _mask_api_key(s.tinyfish_api_key),
        "tavily_configured": bool(s.tavily_api_key),
        "tavily_key_masked": _mask_api_key(s.tavily_api_key),
        "exa_configured": bool(s.exa_api_key),
        "exa_key_masked": _mask_api_key(s.exa_api_key),
        "brave_configured": bool(s.brave_api_key),
        "brave_enabled": s.brave_enabled,
        "brave_key_masked": _mask_api_key(s.brave_api_key),
    }


def _persist_to_env_file(env_path: Path, updates: dict) -> None:
    """Persist updated configuration settings into the .env file."""
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            k, _ = line.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.post("/settings")
async def update_settings(payload: dict):
    """Update search API provider configuration settings."""
    from jobhunterx.config.settings import get_settings, _BASE_DIR
    s = get_settings()

    env_updates = {}

    if "enable_web_search_apis" in payload:
        val = bool(payload["enable_web_search_apis"])
        s.enable_web_search_apis = val
        env_updates["ENABLE_WEB_SEARCH_APIS"] = "true" if val else "false"

    if "tinyfish_api_key" in payload:
        key = str(payload["tinyfish_api_key"]).strip()
        s.tinyfish_api_key = key
        os.environ["TINYFISH_API_KEY"] = key
        env_updates["TINYFISH_API_KEY"] = key

    if "tavily_api_key" in payload:
        key = str(payload["tavily_api_key"]).strip()
        s.tavily_api_key = key
        os.environ["TAVILY_API_KEY"] = key
        env_updates["TAVILY_API_KEY"] = key

    if "exa_api_key" in payload:
        key = str(payload["exa_api_key"]).strip()
        s.exa_api_key = key
        os.environ["EXA_API_KEY"] = key
        env_updates["EXA_API_KEY"] = key

    if "brave_api_key" in payload:
        key = str(payload["brave_api_key"]).strip()
        s.brave_api_key = key
        os.environ["BRAVE_API_KEY"] = key
        env_updates["BRAVE_API_KEY"] = key

    if "brave_enabled" in payload:
        val = bool(payload["brave_enabled"])
        s.brave_enabled = val
        env_updates["BRAVE_ENABLED"] = "true" if val else "false"

    if "primary_search_provider" in payload:
        val = str(payload["primary_search_provider"])
        s.primary_search_provider = val
        env_updates["PRIMARY_SEARCH_PROVIDER"] = val

    if "strict_zero_spend_protection" in payload:
        val = bool(payload["strict_zero_spend_protection"])
        s.strict_zero_spend_protection = val
        env_updates["STRICT_ZERO_SPEND_PROTECTION"] = "true" if val else "false"

    if env_updates:
        try:
            _persist_to_env_file(_BASE_DIR / ".env", env_updates)
        except Exception as exc:
            log.warning("failed_to_persist_env_settings", error=str(exc))

    return {
        "status": "updated",
        "enable_web_search_apis": s.enable_web_search_apis,
        "primary_search_provider": s.primary_search_provider,
    }


@router.get("/budget")
async def get_budget():
    """Gemma budget usage (15k RPD / 30 RPM)."""
    from jobhunterx.config.gemma import budget_status
    return {"budget": budget_status()}


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
    """Start the discovery flow (company sync → ATS fetch → Gemma scoring)."""
    global _sync_task

    # Always fetch the latest profile from DB to avoid stale state
    profile = await db.get_latest_profile()
    if profile is None:
        if _current_profile is not None:
            profile = _current_profile
        else:
            raise HTTPException(400, "No resume uploaded yet")

    # Cancel any running sync and wait for it to finish
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_sync_task), timeout=2.0)
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

    _sync_task = asyncio.create_task(_run())

    return {"status": "started", "location": request.location}


@router.post("/stop-browser")
async def stop_browser_endpoint():
    """Explicitly halt any running Playwright/browser-use sessions."""
    log.info("received_stop_browser_request")
    await stop_all_active_browsers()
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_sync_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    return {"status": "ok", "message": "Browser session stopped successfully."}


@router.get("/browser/cdp-url")
async def get_browser_cdp_url():
    """Return the CDP websocket URL of the currently active browser session."""
    from jobhunterx.agents.browser_agent import get_active_cdp_url
    return {"cdp_url": get_active_cdp_url()}


@router.post("/browser/takeover")
async def browser_takeover(job_id: str = ""):
    """User is taking over the live browser window.

    Pauses URL streaming so the UI doesn't fight the user, and attempts to
    bring the real Chrome window to the foreground (Windows).
    Returns the active CDP url for display.
    """
    from jobhunterx.agents import browser_agent as ba
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
    from jobhunterx.agents import browser_agent as ba
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
async def list_jobs(status: str = "", limit: int = 100, include_closed: bool = False):
    """List discovered jobs with optional status filter.

    Dead jobs (status='closed') are hidden by default — they waste the
    user's time. Pass include_closed=true to see them.
    """
    if not status and not include_closed:
        jobs = await db.get_jobs_excluding(["closed"], limit=limit)
    else:
        jobs = await db.get_jobs(status=status or None, limit=limit)
    # Don't send PDF blob in list response; parse validation_json
    for j in jobs:
        j["has_tailored_pdf"] = bool(j.get("tailored_pdf"))
        j.pop("tailored_pdf", None)
        # Parse freshness_json (eligibility gate + liveness)
        fj = j.get("freshness_json")
        if fj and isinstance(fj, str):
            try:
                j["freshness"] = json.loads(fj)
            except (json.JSONDecodeError, TypeError):
                j["freshness"] = None
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
    job["has_tailored_pdf"] = bool(job.get("tailored_pdf"))
    job.pop("tailored_pdf", None)
    fj = job.get("freshness_json")
    if fj and isinstance(fj, str):
        try:
            job["freshness"] = json.loads(fj)
            job.pop("freshness_json", None)
        except (json.JSONDecodeError, TypeError):
            pass
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
    from jobhunterx.agents.graph import run_single_job_apply

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


@router.get("/status")
async def get_status():
    """Overall system status and token usage summary."""
    token_usage = await db.get_token_usage_summary()
    jobs = await db.get_jobs(limit=1000)
    companies = await db.get_companies()
    status_counts = {}
    for j in jobs:
        s = j.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "status": "running" if _sync_task and not _sync_task.done() else "idle",
        "job_counts": status_counts,
        "total_jobs": len(jobs),
        "total_companies": len(companies),
        "companies_with_ats": sum(1 for c in companies if c.get("ats") not in ("", "none")),
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


class ModelSelectionInput(BaseModel):
    chain: str
    model_id: str


@router.get("/models")
async def get_models_endpoint():
    """Get model configuration, active chain models, and provider statuses."""
    from jobhunterx.config.llm_router import get_model_config
    return get_model_config()


@router.post("/models")
async def set_model_endpoint(input_data: ModelSelectionInput):
    """Set model selection for a specific agent chain."""
    from jobhunterx.config.llm_router import set_model_config, get_model_config
    set_model_config(input_data.chain, input_data.model_id)
    await ws_manager.broadcast({
        "agent": "system",
        "event_type": "model_config_updated",
        "message": f"Model for agent '{input_data.chain}' changed to: {input_data.model_id}",
        "data": {"chain": input_data.chain, "model_id": input_data.model_id},
    })
    return {"status": "ok", "config": get_model_config()}



@router.post("/reset")
async def reset_system():
    """Cancel any active search task and clear the entire database."""
    global _sync_task, _current_profile, _apply_tasks
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_sync_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        _sync_task = None
    
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

class OutreachSaveInput(BaseModel):
    contact_name: str = ""
    contact_role: str = ""
    subject: str = ""
    body: str = ""


@router.get("/outreach")
async def get_outreach():
    """Get active outreach drafts."""
    drafts = await db.get_outreach_drafts()
    return {"drafts": drafts}


@router.post("/outreach/{draft_id}/discard")
async def discard_outreach(draft_id: str):
    """Discard an outreach draft."""
    conn = await db.get_connection()
    try:
        await conn.execute("UPDATE outreach_drafts SET status = 'discarded' WHERE id = ?", (draft_id,))
        await conn.commit()
    finally:
        await conn.close()
    return {"status": "ok"}


@router.post("/outreach/{draft_id}/save")
async def save_outreach(draft_id: str, data: OutreachSaveInput):
    """Save changes to an outreach draft."""
    conn = await db.get_connection()
    try:
        await conn.execute(
            "UPDATE outreach_drafts SET contact_name = ?, contact_role = ?, subject = ?, body = ? WHERE id = ?",
            (data.contact_name, data.contact_role, data.subject, data.body, draft_id)
        )
        await conn.commit()
    finally:
        await conn.close()
    return {"status": "ok"}


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
    """Mark an intervention session as resolved and clean up paused session."""
    from jobhunterx.agents import browser_agent as ba
    sessions = await db.get_pending_interventions()
    target = next((s for s in sessions if s.get("id") == session_id), None)
    if target and target.get("job_id"):
        await ba.clear_paused_session(target["job_id"])
    await db.resolve_intervention(session_id, status)
    return {"status": "ok"}


@router.post("/interventions/{job_id}/focus")
async def focus_intervention_browser(job_id: str):
    """Bring active browser window/tab for job_id to the front for manual intervention."""
    from jobhunterx.agents import browser_agent as ba
    focused = await ba.focus_browser_session(job_id)
    return {"status": "ok", "focused": focused}


@router.get("/screenshots/{job_id}")
async def get_screenshot(job_id: str):
    """Serve a browser screenshot for a given job ID."""
    from pathlib import Path
    import re as _re
    from fastapi.responses import FileResponse
    from jobhunterx.config.settings import get_settings

    if not _re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
        raise HTTPException(status_code=404, detail="Screenshot not found")

    screenshot_path = Path(get_settings().screenshots_full_path) / f"{job_id}.png"
    if screenshot_path.exists():
        return FileResponse(str(screenshot_path), media_type="image/png")
    raise HTTPException(status_code=404, detail="Screenshot not found")
