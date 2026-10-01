"""Document generation service — orchestrates generation, rendering, storage and status events."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.documents import GeneratedDocument
from jobhunterx.generation import render
from jobhunterx.generation.content import header_for
from jobhunterx.generation.cover_letter import generate_cover_letter
from jobhunterx.generation.cv import generate_cv
from jobhunterx.generation.resume import generate_resume

Emit = Callable[[dict], Awaitable[None]]

_inflight: set[tuple[str, str]] = set()


class AlreadyGenerating(RuntimeError):
    pass


class JobNotFound(LookupError):
    pass


async def _with_guard(key: tuple[str, str], emit: Emit, job_id: Optional[str], kind: str, work) -> GeneratedDocument:
    if key in _inflight:
        raise AlreadyGenerating(f"A {kind.replace('_', ' ')} is already being generated" + (" for this job." if job_id else "."))
    _inflight.add(key)
    await emit({"type": "document.status", "job_id": job_id, "data": {"job_id": job_id, "kind": kind, "status": "generating"}})
    try:
        doc = await work()
    except Exception as exc:
        await emit({"type": "document.status", "job_id": job_id,
                    "data": {"job_id": job_id, "kind": kind, "status": "failed", "error": str(exc)[:200]}})
        raise
    finally:
        _inflight.discard(key)
    await emit({"type": "document.status", "job_id": job_id,
                "data": {"job_id": job_id, "kind": kind, "status": "ready", "document_id": doc.id}})
    return doc


async def _store(doc: GeneratedDocument, pdf: bytes, pages: int) -> GeneratedDocument:
    doc.page_count = pages
    await storage.save_document(doc, pdf)
    return doc


async def generate_for_job(job_id: str, kind: str, profile: CandidateProfile, snapshot: CandidateSnapshot,
                           emit: Emit) -> GeneratedDocument:
    row = await storage.get_row(job_id)
    if not row:
        raise JobNotFound(job_id)
    posting, match = storage.row_to_objects(row)

    async def work():
        if kind == "resume":
            doc = await generate_resume(profile, snapshot, posting)
            pdf, pages = await asyncio.to_thread(render.render_resume, doc.content)
        else:
            doc = await generate_cover_letter(profile, snapshot, posting, match)
            pdf, pages = await asyncio.to_thread(render.render_cover_letter, doc.content,
                                                 header_for(profile).model_dump())
        return await _store(doc, pdf, pages)

    return await _with_guard((job_id, kind), emit, job_id, kind, work)


async def generate_cv_doc(profile: CandidateProfile, snapshot: CandidateSnapshot, focus: str, emit: Emit) -> GeneratedDocument:
    async def work():
        doc = await generate_cv(profile, snapshot, focus=focus)
        pdf, pages = await asyncio.to_thread(render.render_cv, doc.content)
        return await _store(doc, pdf, pages)

    return await _with_guard(("profile", "cv"), emit, None, "cv", work)
