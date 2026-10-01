"""
Stage 7 — Job validation: is the posting real, reachable, current, applicable?

Every check is recorded in `ValidationReport.checks` with an honest status:
verified / inferred / unverified / unknown / failed. Nothing is upgraded to
"verified" without first-party or live evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from jobhunterx.discovery import ats
from jobhunterx.discovery.net import fetch
from jobhunterx.domain.job import FieldCheck, JobPosting
from jobhunterx.intelligence.policy import get_policy

_FIELDS = ("company", "title", "location", "work_mode", "posted_at", "valid_through", "employment_type", "salary")


async def check_liveness(job: JobPosting) -> tuple[str, str]:
    """Return (state, evidence) with state in live | gone | unknown."""
    if job.ats and job.ats.job_id:
        state, _ = await ats.ADAPTERS[job.ats.kind].check(job.ats)
        if state != "unknown":
            return state, f"{job.ats.kind.title()} API: {'listed' if state == 'live' else 'no longer listed'}"
    url = job.apply_url or job.canonical_url
    if not url:
        return "unknown", "No URL"
    res = await fetch(url, timeout=10)
    if res.status in (404, 410):
        return "gone", f"HTTP {res.status}"
    if res.ok:
        return "live", f"HTTP {res.status} (page reachable)"
    return "unknown", res.error or f"HTTP {res.status}"


def finalize(job: JobPosting, liveness: Optional[tuple[str, str]] = None, now: Optional[datetime] = None) -> None:
    """Compute the overall validation status from collected evidence."""
    now = now or datetime.now(timezone.utc)
    pol = get_policy()
    v = job.validation
    checks = v.checks
    v.checked_at = now

    if liveness:
        state, ev = liveness
        checks["url_reachable"] = FieldCheck(status={"live": "verified", "gone": "failed"}.get(state, "unknown"),
                                             value=state, evidence=ev)
        if job.ats and job.ats.job_id:
            checks["ats_confirmed"] = FieldCheck(status={"live": "verified", "gone": "failed"}.get(state, "unknown"),
                                                 value=f"{job.ats.kind}:{job.ats.token}", evidence=ev)

    values = {
        "company": job.company, "title": job.title, "location": job.location_raw or ", ".join(job.locations),
        "work_mode": job.work_mode.value if job.work_mode.value != "unknown" else "",
        "posted_at": job.posted_at.isoformat() if job.posted_at else "",
        "valid_through": job.valid_through.isoformat() if job.valid_through else "",
        "employment_type": job.employment_type, "salary": job.salary.raw if job.salary else "",
    }
    for key in _FIELDS:
        if key not in checks:
            checks[key] = FieldCheck(status="inferred" if values[key] else "unknown", value=values[key] or None,
                                     evidence="read from posting text" if values[key] else "not stated")
    if job.requirements.experience_min is not None:
        checks["experience"] = FieldCheck(status="inferred", value=f"{job.requirements.experience_min:g}+ yrs",
                                          evidence=job.requirements.experience_evidence[:120])
    else:
        checks.setdefault("experience", FieldCheck(status="unknown", evidence="not stated"))

    if v.status in ("closed", "invalid"):
        pass
    elif job.valid_through and job.valid_through < now:
        v.status = "closed"
        v.notes.append(f"Application deadline passed ({job.valid_through.date()}).")
    elif liveness and liveness[0] == "gone":
        v.status = "closed"
        v.notes.append(f"Posting no longer available ({liveness[1]}).")
    elif not job.title or not job.description:
        v.status = "invalid"
        v.notes.append("Missing title or description.")
    elif job.posted_at and (now - job.posted_at).days > pol.stale_after_days:
        v.status = "stale"
        v.notes.append(f"Posted {(now - job.posted_at).days} days ago.")
    elif liveness and liveness[0] == "live" and job.primary_source and job.primary_source.first_party:
        v.status = "active"
    elif liveness and liveness[0] == "live":
        v.status = "likely_active"
    else:
        v.status = "unverified"

    open_ = {"active": "verified", "likely_active": "inferred", "closed": "failed", "stale": "unverified",
             "invalid": "failed"}.get(v.status, "unknown")
    checks["application_open"] = FieldCheck(status=open_, value=v.status, evidence="; ".join(v.notes[-2:]))
    verified = sum(1 for c in checks.values() if c.status == "verified")
    known = sum(1 for c in checks.values() if c.status in ("verified", "inferred"))
    v.confidence = round(min(1.0, (verified * 1.0 + (known - verified) * 0.5) / max(1, len(checks))), 2)
