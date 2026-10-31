"""Document generation service — orchestrates generation, rendering, storage and status events."""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.documents import GeneratedDocument
from jobhunterx.generation import render, styles
from jobhunterx.generation.content import header_for
from jobhunterx.generation.cover_letter import generate_cover_letter
from jobhunterx.generation.cv import generate_cv
from jobhunterx.generation.resume import generate_resume
from jobhunterx.generation.content import LAYOUTS, CoverLetterContent, ResumeContent
from jobhunterx.domain.job import JobPosting

Emit = Callable[[dict], Awaitable[None]]

_inflight: set[tuple[str, str]] = set()


def _who() -> str:
    """The profile in use: the in-flight guard is per person, so one user's CV never blocks another's."""
    return storage.active_person() or "local"


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
            pdf, pages, doc.fit = await asyncio.to_thread(render.render_resume_fit, doc.content)
        else:
            doc = await generate_cover_letter(profile, snapshot, posting, match)
            pdf, pages = await asyncio.to_thread(render.render_cover_letter, doc.content,
                                                 header_for(profile).model_dump())
        return await _store(doc, pdf, pages)

    return await _with_guard((f"{_who()}:{job_id}", kind), emit, job_id, kind, work)


async def generate_cv_doc(profile: CandidateProfile, snapshot: CandidateSnapshot, focus: str, emit: Emit) -> GeneratedDocument:
    async def work():
        doc = await generate_cv(profile, snapshot, focus=focus)
        pdf, pages = await asyncio.to_thread(render.render_cv, doc.content)
        return await _store(doc, pdf, pages)

    return await _with_guard((_who(), "cv"), emit, None, "cv", work)


class BadTarget(ValueError):
    """The pasted text or link doesn't give a usable job description (message is shown to the user)."""


_LINKEDIN = re.compile(r"(^|\.)linkedin\.com$", re.I)


async def job_from_input(jd_text: str, url: str, title: str, company: str,
                         snapshot: CandidateSnapshot) -> JobPosting:
    """A JobPosting for a job the user brings: pasted description text, a link to the posting, or both (the pasted
    text wins; the link is kept for reference). Requirements are read exactly as for discovered jobs."""
    from urllib.parse import urlparse

    from jobhunterx.discovery.page import posting_from_url
    from jobhunterx.intelligence.job import understand_job

    jd_text, url = (jd_text or "").strip(), (url or "").strip()
    posting: Optional[JobPosting] = None
    if url:
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise BadTarget("That link doesn't look like a web address (it should start with https://).")
        if _LINKEDIN.search(parts.hostname):
            raise BadTarget("LinkedIn pages can't be read. Open the job, copy its description and paste it here.")
        if not jd_text:
            posting, _ = await posting_from_url(url)
            if posting is None or len(posting.description) < 200:
                raise BadTarget("Couldn't read a job description from that page. Copy the description and paste it here.")
    if posting is None:
        if len(jd_text) < 80:
            raise BadTarget("Paste the whole job description (at least a few lines), or give a link to the posting.")
        posting = JobPosting(description=jd_text[:20000], canonical_url=url, apply_url=url)
    posting.title = (title or "").strip()[:120] or posting.title
    posting.company = (company or "").strip()[:120] or posting.company
    await understand_job(posting, snapshot)
    if not posting.title or not posting.company:
        t, c = _title_company_guess(posting.description)
        posting.title = posting.title or t or "Target role"
        if not posting.company and c and c.lower() in posting.description.lower():
            posting.company = c
    posting.id = "custom-" + hashlib.sha1(f"{posting.title}|{posting.company}|{posting.description}".encode()).hexdigest()[:16]
    return posting


def _title_company_guess(text: str) -> tuple[str, str]:
    """From a description's first line: "AI Engineer at Zeta Labs, Hyderabad. …" -> ("AI Engineer", "Zeta Labs")."""
    first = next((ln.strip(" -:*#\t") for ln in (text or "").splitlines() if ln.strip()), "")
    head = re.split(r"(?<=[a-z0-9)])[.!?|](?:\s|$)|\s[–—|]\s", first)[0].strip()
    m = re.match(r"^(.{2,80}?)\s+(?:at|@)\s+([A-Z][\w&.'\- ]{1,60}?)\s*(?:[,(]|$)", head)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (head if 2 <= len(head) <= 80 else ""), ""


def keyword_report(content: dict, job: JobPosting) -> tuple[list[str], list[str]]:
    """The job's named skills, and which of them the finished resume shows (ATS keyword coverage)."""
    from jobhunterx.generation.richtext import plain
    from jobhunterx.intelligence.text import any_term_in_text

    text = plain(" ".join(_strings(content)))
    req = job.requirements
    terms = list(dict.fromkeys([*req.required_skills, *req.preferred_skills]))[:30]
    matched = [t for t in terms if any_term_in_text([t, *req.skill_aliases.get(t, [])], text)]
    return terms, matched


def _strings(v: Any) -> list[str]:
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [x for k, val in v.items() if k not in ("item_links",) for x in _strings(val)]
    if isinstance(v, list):
        return [x for val in v for x in _strings(val)]
    return []


async def generate_custom(profile: CandidateProfile, snapshot: CandidateSnapshot, *, jd_text: str, url: str,
                          title: str, company: str, layout: str, style: str, emit: Emit) -> GeneratedDocument:
    """A one-page resume tailored to a job the user brings (not one of the found jobs)."""
    async def work():
        job = await job_from_input(jd_text, url, title, company, snapshot)
        doc = await generate_resume(profile, snapshot, job)
        doc.job_id = None
        doc.content["layout"] = layout if layout in LAYOUTS else "single"
        doc.style = styles.normalize(style)
        doc.title = f"Resume — {job.title}" + (f" @ {job.company}" if job.company else "")
        doc.focus = job.title
        terms, matched = keyword_report(doc.content, job)
        doc.target = {"title": job.title, "company": job.company, "url": url.strip(), "keywords": terms,
                      "aliases": {t: job.requirements.skill_aliases.get(t, []) for t in terms},
                      "matched": matched, "method": job.requirements.method}
        pdf, pages, doc.fit = await asyncio.to_thread(render.render_resume_fit, doc.content, doc.style)
        return await _store(doc, pdf, pages)

    return await _with_guard((_who(), "custom-resume"), emit, None, "resume", work)


async def update_document(doc: GeneratedDocument, content: dict[str, Any], profile: CandidateProfile,
                          *, manual: bool = True) -> GeneratedDocument:
    """Validate user-authored structured content, render it, and replace the saved artifact."""
    if doc.kind == "resume":
        validated = ResumeContent.model_validate(content)
        normalized = validated.model_dump(mode="json")
        pdf, pages, doc.fit = await asyncio.to_thread(render.render_resume_fit, normalized, doc.style)
    elif doc.kind == "cv":
        validated = ResumeContent.model_validate(content)
        normalized = validated.model_dump(mode="json")
        pdf, pages = await asyncio.to_thread(render.render_cv, normalized, doc.style)
    elif doc.kind == "cover_letter":
        validated = CoverLetterContent.model_validate(content)
        normalized = validated.model_dump(mode="json")
        pdf, pages = await asyncio.to_thread(
            render.render_cover_letter, normalized, header_for(profile).model_dump(mode="json"), doc.style)
    else:
        raise ValueError(f"Unsupported document kind: {doc.kind}")
    doc.content = normalized
    if doc.target.get("keywords"):          # a custom resume: keep its keyword coverage true to the edited text
        from jobhunterx.generation.richtext import plain
        from jobhunterx.intelligence.text import any_term_in_text
        text = plain(" ".join(_strings(normalized)))
        aliases = doc.target.get("aliases") or {}
        doc.target["matched"] = [t for t in doc.target["keywords"] if any_term_in_text([t, *aliases.get(t, [])], text)]
    doc.page_count = pages
    doc.has_pdf = bool(pdf)
    doc.updated_at = datetime.now(timezone.utc)
    doc.manually_edited = doc.manually_edited or manual
    if not await storage.update_document(doc, pdf):
        raise LookupError(doc.id)
    return doc


# Rendered PDFs in a style other than the saved one (a download that picks a style). Small and in memory: a style
# switch is a re-render of the same content, so the key is (document, its last change, style).
_pdf_cache: "dict[tuple[str, str, str], bytes]" = {}
_PDF_CACHE_MAX = 24


async def pdf_in_style(doc: GeneratedDocument, profile: CandidateProfile, style: str) -> bytes:
    key = (doc.id, doc.updated_at.isoformat(), style)
    hit = _pdf_cache.get(key)
    if hit is not None:
        return hit
    pdf, _ = await asyncio.to_thread(render.render_document, doc.kind, doc.content, header_for(profile).model_dump(mode="json"), style)
    while len(_pdf_cache) >= _PDF_CACHE_MAX:
        _pdf_cache.pop(next(iter(_pdf_cache)))
    _pdf_cache[key] = pdf
    return pdf


async def set_style(doc: GeneratedDocument, style: str, profile: CandidateProfile) -> GeneratedDocument:
    """Save the document's style and re-render its stored PDF (content untouched)."""
    if not styles.valid(style):
        raise ValueError("Unknown style")
    doc.style = style
    return await update_document(doc, doc.content, profile, manual=False)
