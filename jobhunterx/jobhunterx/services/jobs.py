"""Job service — views, serialization (API contract) and per-job actions."""

from __future__ import annotations

from typing import Optional

from jobhunterx import storage
from jobhunterx.discovery import validate, watchlist
from jobhunterx.domain.candidate import CandidateSnapshot
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment
from jobhunterx.intelligence import job as job_ai
from jobhunterx.intelligence.matching import assess, build_idf, candidate_work_text

VIEWS = {
    "recommended": "verdict IN ('strong','good','stretch') AND COALESCE(validation_status,'') NOT IN ('closed','invalid')",
    "all": "",
    "rejected": "(verdict = 'incompatible' OR validation_status IN ('closed','invalid'))",
    "saved": "saved_at IS NOT NULL",
    "applied": "tracking_status IN ('applied','interviewing','offer')",
    # first seen in the last 48 hours and worth a look — new watchlist postings land here
    "fresh": "created_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 days') AND verdict IN ('strong','good','stretch') "
             "AND COALESCE(validation_status,'') NOT IN ('closed','invalid')",
}

SORTS = {
    # fit decides if you should apply; reach decides if anyone will read it — "chance" weighs both
    "chance": "(COALESCE(fit_score, 0) * 0.6 + COALESCE(reach_score, 50) * 0.4) DESC, updated_at DESC",
    "score": "COALESCE(fit_score, -1) DESC, updated_at DESC",
    "reach": "COALESCE(reach_score, -1) DESC, COALESCE(fit_score, -1) DESC",
    "recent": "updated_at DESC",
}


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def summary(row: dict, current_hash: Optional[str], docs: Optional[dict] = None) -> dict:
    posting, match = storage.row_to_objects(row)
    return _summary(posting, match, row, current_hash, docs or {})


def _summary(p: JobPosting, m: Optional[MatchAssessment], row: dict, current_hash: Optional[str], docs: dict) -> dict:
    src = p.primary_source
    req_total = len(p.requirements.required_skills)
    return {
        "id": p.id,
        "run_id": row.get("run_id"),
        "title": p.title,
        "company": p.company,
        "location": p.location_raw or ", ".join(p.locations),
        "locations": p.locations,
        "countries": p.countries,
        "work_mode": p.work_mode.value,
        "employment_type": p.employment_type,
        "seniority": p.seniority.value,
        "role_family": p.role_family,
        "posted_at": _iso(p.posted_at),
        "valid_through": _iso(p.valid_through),
        "discovered_at": _iso(p.discovered_at) or row.get("created_at"),
        "apply_url": p.apply_url,
        "source": {"name": src.name, "kind": src.kind, "url": src.url, "first_party": src.first_party} if src else None,
        "sources_count": len(p.sources),
        "salary": p.salary.model_dump(mode="json") if p.salary else None,
        "validation": {"status": p.validation.status, "confidence": p.validation.confidence,
                       "checked_at": _iso(p.validation.checked_at)},
        "match": {
            "score": m.score, "verdict": m.verdict, "headline": m.headline,
            "required_matched": len(m.matched_required), "required_total": req_total,
            "missing_required": m.missing_required[:4],
            "experience": m.experience.model_dump(mode="json"),
            "rejected_reasons": m.rejected_reasons,
        } if m else None,
        "reach": {
            "score": m.reach.score, "level": m.reach.level, "headline": m.reach.headline,
            "application_email": m.reach.application_email, "company_verdict": m.reach.company_verdict,
        } if m and m.reach else None,
        "match_stale": bool(m and current_hash and m.profile_hash != current_hash),
        "saved": bool(row.get("saved_at")),
        "tracking_status": row.get("tracking_status") or "new",
        "pipeline_status": row.get("status") or "discovered",
        "documents": {"resume": docs.get("resume"), "cover_letter": docs.get("cover_letter")},
    }


async def list_jobs(view: str, current_hash: Optional[str], *, run_id: str = "", q: str = "", work_mode: str = "",
                    min_score: int = 0, sort: str = "chance", limit: int = 200) -> tuple[list[dict], dict]:
    clauses, params = [], []
    base = VIEWS.get(view, VIEWS["recommended"])
    if base:
        clauses.append(f"({base})")
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if q:
        clauses.append("(role LIKE ? OR company LIKE ? OR location LIKE ?)")
        params += [f"%{q}%"] * 3
    if min_score:
        clauses.append("COALESCE(fit_score, 0) >= ?")
        params.append(int(min_score))
    order = SORTS.get(sort, SORTS["chance"])
    rows = await storage.list_rows(" AND ".join(clauses), tuple(params), order=order, limit=limit)
    docs = await storage.latest_document_ids([r["id"] for r in rows])
    items = [summary(r, current_hash, docs.get(r["id"])) for r in rows]
    if work_mode:
        items = [i for i in items if i["work_mode"] == work_mode]
    counts = await storage.count_many(VIEWS)
    return items, counts


async def detail(job_id: str, current_hash: Optional[str]) -> Optional[dict]:
    row = await storage.get_row(job_id)
    if not row:
        return None
    p, m = storage.row_to_objects(row)
    docs = await storage.list_documents(job_id=job_id)
    latest = {}
    for d in reversed(docs):
        latest[d.kind] = d.id
    out = _summary(p, m, row, current_hash, latest)
    out.update({
        "description": p.description,
        "requirements": p.requirements.model_dump(mode="json"),
        "validation": p.validation.model_dump(mode="json"),
        "match": m.model_dump(mode="json") if m else None,
        "sources": [s.model_dump(mode="json") for s in p.sources],
        "company_profile": _company_profile(p),
        "document_list": [document_summary(d, current_hash, p) for d in docs],
    })
    return out


def _company_profile(p: JobPosting) -> Optional[dict]:
    c = watchlist.find(p)
    return watchlist.public_view(c) if c else None


def document_summary(d, current_hash: Optional[str], job: Optional[JobPosting] = None) -> dict:
    return {
        "id": d.id, "kind": d.kind, "job_id": d.job_id, "title": d.title, "focus": d.focus,
        "created_at": _iso(d.created_at), "profile_hash": d.profile_hash,
        "stale": bool(current_hash and d.profile_hash != current_hash),
        "page_count": d.page_count, "has_pdf": d.has_pdf, "warnings_count": len(d.provenance.warnings),
        "job": {"title": job.title, "company": job.company} if job else None,
    }


async def rescore(job_id: str, snapshot: CandidateSnapshot, profile_dict: dict, *, use_llm: bool = True) -> bool:
    row = await storage.get_row(job_id)
    if not row:
        return False
    p, _ = storage.row_to_objects(row)
    if p.requirements.method in ("pending", "fallback") and use_llm:
        await job_ai.understand_job(p, snapshot)
        await storage.update_posting(p)
    fits = await job_ai.assess_role_fit(snapshot, [p], use_llm=use_llm)
    text = candidate_work_text(profile_dict)
    m = assess(snapshot, p, role_fit=fits[p.id], candidate_text=text, idf=build_idf([p.description, text]))
    await storage.update_match(job_id, m)
    return True


async def verify(job_id: str, snapshot: Optional[CandidateSnapshot], profile_dict: Optional[dict]) -> bool:
    row = await storage.get_row(job_id)
    if not row:
        return False
    p, m = storage.row_to_objects(row)
    if p.validation.status in ("closed", "invalid", "stale"):
        p.validation.status = "unverified"     # re-evaluate from fresh evidence
    live = await validate.check_liveness(p)
    validate.finalize(p, live)
    await storage.update_posting(p)
    if snapshot and profile_dict:
        text = candidate_work_text(profile_dict)
        role_fit = (m.role_fit, m.role_track, "", m.method) if m else (await job_ai.assess_role_fit(snapshot, [p]))[p.id]
        await storage.update_match(job_id, assess(snapshot, p, role_fit=role_fit, candidate_text=text,
                                                  idf=build_idf([p.description, text])))
    return True
