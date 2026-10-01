"""
Browser auto-apply — runs the (unchanged) browser agent for one job.

The application uses the job's latest generated *resume* (generating one
first if none exists), so the uploaded file is always the job-specific,
fact-checked document the user can review in the Documents workspace.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from jobhunterx import storage
from jobhunterx.config import database as db
from jobhunterx.config.logging import get_logger
from jobhunterx.services import documents as docs_svc
from jobhunterx.services import profile as profile_svc

log = get_logger("apply")

Emit = Callable[[dict], Awaitable[None]]

_tasks: dict[str, asyncio.Task] = {}


def running(job_id: str) -> bool:
    t = _tasks.get(job_id)
    return bool(t and not t.done())


async def _run(job_id: str, emit: Emit) -> None:
    from jobhunterx.agents import browser_agent

    profile = await profile_svc.get_profile()
    row = await storage.get_row(job_id)
    if not profile or not row:
        return
    snapshot = await profile_svc.get_snapshot(profile)
    resumes = await storage.list_documents(job_id=job_id, kind="resume")
    current = [d for d in resumes if d.profile_hash == profile.content_hash()]
    doc = current[0] if current else await docs_svc.generate_for_job(job_id, "resume", profile, snapshot, emit)
    pdf = await storage.get_document_pdf(doc.id)
    posting, _ = storage.row_to_objects(row)
    job = {"id": job_id, "company": posting.company, "role": posting.title,
           "apply_url": posting.apply_url or posting.canonical_url, "career_page_url": posting.canonical_url}
    result = await browser_agent.run({"job": job, "profile": profile.model_dump(mode="json"), "tailored_pdf": pdf})
    status = (result.get("browser_result") or {}).get("status", "error")
    if status == "applied":
        await storage.set_tracking(job_id, "applied")
        await db.update_job(job_id, status="applied")
    elif status != "needs_attention":      # the agent records needs_attention itself
        await db.update_job(job_id, status="apply_failed")


async def start(job_id: str, emit: Emit) -> None:
    if running(job_id):
        raise RuntimeError("An application is already running for this job.")

    async def go():
        try:
            await _run(job_id, emit)
        except Exception as exc:
            log.error("apply_failed", job_id=job_id, error=str(exc)[:200])
            await db.update_job(job_id, status="apply_failed")
            await emit({"type": "log", "job_id": job_id, "message": f"Apply failed: {str(exc)[:160]}",
                        "data": {"level": "error", "source": "apply"}})
        finally:
            row = await storage.get_row(job_id)
            if row:
                from jobhunterx.services.jobs import summary
                await emit({"type": "job.updated", "job_id": job_id, "data": {"job": summary(row, None)}})

    _tasks[job_id] = asyncio.create_task(go())


async def cancel_all() -> None:
    for t in list(_tasks.values()):
        if not t.done():
            t.cancel()
    _tasks.clear()
