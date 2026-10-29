"""Job service — views, serialization (API contract) and per-job actions."""

from __future__ import annotations

from typing import Optional

from jobhunterx import storage
from jobhunterx.discovery import validate, watchlist
from jobhunterx.domain.candidate import CandidateSnapshot
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment
from jobhunterx.intelligence import job as job_ai
from jobhunterx.intelligence import skill_links
from jobhunterx.intelligence.matching import assess, build_idf, candidate_work_text

_MAIN = "COALESCE(json_extract(match_json, '$.track'), 'main') != 'floor'"   # safety-net jobs have their own view
VIEWS = {
    "recommended": "verdict IN ('strong','good','stretch') AND COALESCE(validation_status,'') NOT IN ('closed','invalid') "
                   f"AND {_MAIN}",
    "all": "",
    "rejected": "(verdict = 'incompatible' OR validation_status IN ('closed','invalid'))",
    "saved": "saved_at IS NOT NULL",
    "applied": "tracking_status IN ('applied','interviewing','offer')",
    # first seen in the last 48 hours and worth a look — new watchlist postings land here
    "fresh": "created_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 days') AND verdict IN ('strong','good','stretch') "
             f"AND COALESCE(validation_status,'') NOT IN ('closed','invalid') AND {_MAIN}",
    # early career: large IT-services fresher programmes (national tests, off-campus drives), kept apart from the main list
    "safety_net": "json_extract(match_json, '$.track') = 'floor' AND verdict != 'incompatible' "
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
            "track": m.track,
            "scam": m.scam.model_dump(mode="json") if m.scam else None,
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
        "outcome": _outcome(row),
    }


def _outcome(row: dict) -> Optional[dict]:
    import json
    try:
        return json.loads(row["outcome_json"]) if row.get("outcome_json") else None
    except (TypeError, ValueError):
        return None


async def list_jobs(view: str, current_hash: Optional[str], *, run_id: str = "", q: str = "", work_mode: str = "",
                    min_score: int = 0, sort: str = "chance", limit: int = 200,
                    offset: int = 0) -> tuple[list[dict], dict]:
    # Filters shared by the list and the tab counts, so a tab's number always matches what it shows.
    filters, params = [], []
    if run_id:
        filters.append("run_id = ?")
        params.append(run_id)
    if q:
        filters.append("(role LIKE ? OR company LIKE ? OR location LIKE ?)")
        params += [f"%{q}%"] * 3
    if min_score:
        filters.append("COALESCE(fit_score, 0) >= ?")
        params.append(int(min_score))
    if work_mode:
        filters.append("json_extract(posting_json, '$.work_mode') = ?")
        params.append(work_mode)
    base = VIEWS.get(view, VIEWS["recommended"])
    clauses = ([f"({base})"] if base else []) + filters
    order = SORTS.get(sort, SORTS["chance"])
    rows = await storage.list_rows(" AND ".join(clauses), tuple(params), order=order, limit=limit, offset=offset)
    docs = await storage.latest_document_ids([r["id"] for r in rows])
    items = [summary(r, current_hash, docs.get(r["id"])) for r in rows]
    counts = await storage.count_many(VIEWS, " AND ".join(filters), tuple(params))
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
        "connection": storage.connection_of(row),
    })
    return out


def _company_profile(p: JobPosting) -> Optional[dict]:
    c = watchlist.find(p)
    return watchlist.public_view(c) if c else None


def _norm_style(style_id: str) -> str:
    from jobhunterx.generation import styles
    return styles.normalize(style_id)


def document_summary(d, current_hash: Optional[str], job: Optional[JobPosting] = None) -> dict:
    return {
        "id": d.id, "kind": d.kind, "job_id": d.job_id, "title": d.title, "focus": d.focus,
        "created_at": _iso(d.created_at), "updated_at": _iso(d.updated_at), "profile_hash": d.profile_hash,
        "manually_edited": d.manually_edited, "style": _norm_style(getattr(d, "style", "classic")),
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
    if use_llm:
        await skill_links.resolve(snapshot, [p], text)
        await storage.update_posting(p)
    m = assess(snapshot, p, role_fit=fits[p.id], candidate_text=text, idf=build_idf([p.description, text]))
    await storage.update_match(job_id, m)
    return True


async def reassess_outdated(snapshot: CandidateSnapshot, profile_dict: dict, limit: int = 500) -> int:
    """Re-score jobs that an older matcher version scored for this same profile — no AI calls: the stored requirements
    and role fit are reused, only the rules change (e.g. the early-career experience bands). Returns how many changed."""
    from jobhunterx.intelligence.matching import ENGINE_VERSION
    rows = await storage.list_rows("match_json IS NOT NULL", order="updated_at DESC", limit=limit)
    text = candidate_work_text(profile_dict)
    done = 0
    for row in rows:
        p, m = storage.row_to_objects(row)
        if m is None or m.engine_version == ENGINE_VERSION or m.profile_hash != snapshot.profile_hash:
            continue
        fit = (m.role_fit, m.role_track, "", m.method or "fallback")
        new = assess(snapshot, p, role_fit=fit, candidate_text=text, idf=build_idf([p.description, text]))
        await storage.update_match(p.id, new)
        done += 1
    return done


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
        await skill_links.resolve(snapshot, [p], text)
        await storage.update_posting(p)
        await storage.update_match(job_id, assess(snapshot, p, role_fit=role_fit, candidate_text=text,
                                                  idf=build_idf([p.description, text])))
    return True
