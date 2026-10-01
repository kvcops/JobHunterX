"""
Auto-apply: get the application kit ready, then hand it to the browser agent.

Order (shown to the user as a checklist):
  1. Resume       — job-specific, one page. Reused if one exists for the current profile.
  2. Cover letter — job-specific (optional, see APPLY_WITH_COVER_LETTER).
  3. CV           — the longer, general document; also kept to one page when possible
                    (optional, see APPLY_WITH_CV).
  4. Browser      — the agent opens the application page and fills it in, live in the app.

The session (kit, steps, last page) is saved, so a stopped or interrupted run can
be continued from where it left off.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.config import database as db
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.domain.documents import GeneratedDocument
from jobhunterx.services import documents as docs_svc
from jobhunterx.services import profile as profile_svc

log = get_logger("apply")

Emit = Callable[[dict], Awaitable[None]]

_tasks: dict[str, asyncio.Task] = {}

KIT_LABELS = {"resume": "Resume", "cover_letter": "Cover letter", "cv": "CV"}


class ApplyError(RuntimeError):
    pass


def running(job_id: str) -> bool:
    t = _tasks.get(job_id)
    return bool(t and not t.done())


def _wanted() -> list[str]:
    s = get_settings()
    kinds = ["resume"]
    if getattr(s, "apply_with_cover_letter", True):
        kinds.append("cover_letter")
    if getattr(s, "apply_with_cv", True):
        kinds.append("cv")
    return kinds


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:40] or "candidate"


async def _job_dict(job_id: str) -> dict:
    row = await storage.get_row(job_id)
    if not row:
        raise ApplyError("Job not found.")
    posting, _ = storage.row_to_objects(row)
    url = (posting.apply_url or posting.canonical_url) if posting else (row.get("apply_url") or "")
    if not url:
        raise ApplyError("This job has no application link.")
    return {"id": job_id, "company": posting.company if posting else row.get("company", ""),
            "role": posting.title if posting else row.get("role", ""), "apply_url": url,
            "career_page_url": posting.canonical_url if posting else url, "person_id": storage.active_person()}


async def _existing(kind: str, job_id: str, profile_hash: str) -> Optional[GeneratedDocument]:
    docs = await storage.list_documents(job_id=None if kind == "cv" else job_id, kind=kind)
    current = [d for d in docs if d.profile_hash == profile_hash and d.has_pdf]
    if kind == "resume":                         # prefer a version that already fits on one page
        current.sort(key=lambda d: d.page_count != 1)
    return current[0] if current else None


async def _prepare_kit(sess, job_id: str, emit: Emit) -> tuple[dict, dict[str, str]]:
    """Check → generate what is missing → write the PDFs the agent will upload."""
    profile = await profile_svc.get_profile()
    if not profile:
        raise ApplyError("Add your resume first.")
    snapshot = await profile_svc.get_snapshot(profile)
    phash = profile.content_hash()
    kinds = _wanted()
    kit = {k: {"label": KIT_LABELS[k], "status": "checking", "pages": 0, "doc_id": None, "note": ""} for k in kinds}
    sess.update(kit=kit, message="Checking your documents…")

    folder = Path(get_settings().screenshots_full_path) / "apply" / job_id
    folder.mkdir(parents=True, exist_ok=True)
    who = _safe_name(profile.name or "")
    files: dict[str, str] = {}

    for kind in kinds:
        item = kit[kind]
        doc = await _existing(kind, job_id, phash)
        if doc:
            item.update(status="found", note="Already made for this profile")
        else:
            item.update(status="generating", note="Writing it now…")
            sess.update(kit=kit, message=f"Writing your {KIT_LABELS[kind] if kind == 'cv' else KIT_LABELS[kind].lower()}…")
            try:
                if kind == "cv":
                    doc = await docs_svc.generate_cv_doc(profile, snapshot, "", emit)
                else:
                    doc = await docs_svc.generate_for_job(job_id, kind, profile, snapshot, emit)
            except docs_svc.AlreadyGenerating:
                await asyncio.sleep(2)
                for _ in range(90):              # someone else is writing it — wait for theirs
                    doc = await _existing(kind, job_id, phash)
                    if doc:
                        break
                    await asyncio.sleep(2)
            except Exception as exc:
                if kind == "resume":
                    item.update(status="failed", note=str(exc)[:140])
                    sess.update(kit=kit)
                    raise ApplyError(f"Could not write your resume: {str(exc)[:140]}")
                item.update(status="skipped", note="Could not be written — applying without it")
                sess.update(kit=kit)
                continue
            if not doc:
                item.update(status="skipped" if kind != "resume" else "failed", note="Not ready in time")
                if kind == "resume":
                    raise ApplyError("Your resume was not ready in time. Try again.")
                continue
            item.update(status="made", note="Freshly written")
        pdf = await storage.get_document_pdf(doc.id)
        if not pdf:
            item.update(status="skipped", note="No PDF available")
            continue
        path = folder / f"{who}_{'Cover_Letter' if kind == 'cover_letter' else kind.upper() if kind == 'cv' else 'Resume'}.pdf"
        path.write_bytes(pdf)
        files[kind] = str(path.resolve())
        item.update(pages=doc.page_count, doc_id=doc.id)
        if kind in ("resume", "cv") and doc.page_count > 1:
            item["note"] = f"{doc.page_count} pages — the content could not be squeezed onto one"
        sess.update(kit=kit)

    profile_dict = profile.model_dump(mode="json")
    return profile_dict, files


async def _restore(job_id: str):
    """Get the in-memory session, or rebuild one from what was saved."""
    from jobhunterx.agents import browser_agent as ba
    sess = ba.get_session(job_id)
    if sess:
        return sess
    saved = await storage.get_apply_session(job_id)
    job = await _job_dict(job_id)
    sess = ba.new_session(job)
    if saved:
        keep = {k: saved[k] for k in ("steps", "url", "title", "kit", "runs", "started_at") if k in saved}
        sess.data.update(keep)
    return sess


async def start(job_id: str, emit: Emit, continuing: bool = False) -> dict:
    """Prepare the kit and launch the agent in the background. Returns the session snapshot."""
    from jobhunterx.agents import browser_agent as ba
    if running(job_id):
        raise ApplyError("This application is already being prepared.")
    existing = ba.get_session(job_id)
    if existing and existing.data["status"] in ("launching", "running", "paused", "stopping"):
        raise ApplyError("The agent is already working on this job.")

    if continuing:
        sess = await _restore(job_id)
        sess.update(status="preparing", message="Getting ready to continue…", notice="", result="")
    else:
        sess = ba.new_session(await _job_dict(job_id))
    await db.update_job(job_id, status="preparing")

    async def go():
        try:
            profile, files = await _prepare_kit(sess, job_id, emit)
            await ba.launch(sess, profile, files, continuing=continuing)
        except asyncio.CancelledError:
            sess.update(status="stopped", message="Stopped", notice="Stopped before the browser opened.")
        except Exception as exc:
            log.error("apply_failed", job_id=job_id, error=str(exc)[:200])
            await db.update_job(job_id, status="apply_failed")
            sess.update(status="failed", message="Could not start", notice=str(exc)[:200])
        finally:
            row = await storage.get_row(job_id)
            if row:
                from jobhunterx.services.jobs import summary
                await emit({"type": "job.updated", "job_id": job_id, "data": {"job": summary(row, None)}})

    _tasks[job_id] = asyncio.create_task(go())
    return sess.snapshot()


async def stop(job_id: str) -> Optional[dict]:
    from jobhunterx.agents import browser_agent as ba
    t = _tasks.get(job_id)
    if t and not t.done():
        t.cancel()                        # still preparing documents
    return await ba.stop(job_id)


async def current() -> Optional[dict]:
    from jobhunterx.agents import browser_agent as ba
    sess = ba.current_session()
    if sess and sess.data.get("person_id") in (None, storage.active_person()):
        return sess.snapshot()
    return await storage.latest_apply_session()


async def cancel_all() -> None:
    from jobhunterx.agents import browser_agent as ba
    for t in list(_tasks.values()):
        if not t.done():
            t.cancel()
    _tasks.clear()
    await ba.stop_all_active_browsers()
