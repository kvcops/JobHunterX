"""
Stage 8 — Job description understanding (+ role fit, part of Stage 11).

`understand_job` turns an untrusted JD into `Requirements` and normalized
fields. The LLM does the reading; the code verifies:

  * a skill is accepted only if its name or one of its stated aliases
    literally occurs in the JD text;
  * experience / salary / education values are accepted only if the quoted
    evidence occurs in the JD and contains the stated number;
  * anything that fails verification becomes "unknown", never a guess.

Results are cached by JD content hash, so a job seen again (another run,
another source) costs nothing.

`assess_role_fit` asks, in batches, how close each job's actual role is to
the candidate's own career tracks (labels come from the candidate snapshot,
not from a fixed list). It is cached per (profile, job).
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import CandidateSnapshot, norm_term
from jobhunterx.domain.common import Seniority, WorkMode
from jobhunterx.domain.job import JobPosting, Requirements, Salary
from jobhunterx.intelligence.llm_structured import call_structured, fence
from jobhunterx.intelligence.text import any_term_in_text, number_in_text, parse_inr_salary, tokens

log = get_logger("job_understanding")

VERSION = "job-v1"
ROLE_FIT_VERSION = "rolefit-v1"


class _Skill(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    must_have: bool = Field(False, description="true only if the JD explicitly says it is mandatory/required/must")


class _Place(BaseModel):
    city: str = ""
    region: str = ""
    country: str = ""


class _Money(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: str = ""
    period: Literal["year", "month", "hour"] = "year"


class JobUnderstanding(BaseModel):
    is_job_posting: bool = Field(True, description="false if the page is not a single job posting (listing page, article, error page)")
    appears_closed: bool = Field(False, description="true only if the text explicitly says the job is closed/filled/expired")
    closed_evidence: str = ""
    normalized_title: str = ""
    company: str = ""
    role_family: str = Field("", description="short career-track label for this role")
    seniority: Seniority = Seniority.UNKNOWN
    employment_type: Literal["full_time", "part_time", "contract", "internship", "temporary", "unknown"] = "unknown"
    work_mode: WorkMode = WorkMode.UNKNOWN
    places: list[_Place] = Field(default_factory=list, description="work locations, canonical English names")
    remote_eligible_countries: list[str] = Field(default_factory=list, description="if remote is restricted to certain countries")
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    experience_evidence: str = Field("", description="verbatim quote from the JD stating the experience requirement")
    required_skills: list[_Skill] = Field(default_factory=list)
    preferred_skills: list[_Skill] = Field(default_factory=list)
    education_level: Literal["none", "diploma", "bachelor", "master", "phd", "unknown"] = "unknown"
    education_mandatory: bool = False
    education_evidence: str = ""
    notice_period_max_days: Optional[int] = None
    notice_evidence: str = ""
    salary: Optional[_Money] = None
    salary_evidence: str = ""
    application_deadline: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


_SYSTEM = """You are an expert technical recruiter extracting the facts of ONE job posting.
Extract only what the posting states. Never infer requirements that are not written.
- required_skills: skills/technologies the posting requires; preferred_skills: nice-to-have/bonus ones.
  Use the posting's own wording for `name`; add common aliases. must_have=true only for explicit mandatory language.
- experience_*: the overall professional experience requirement (not years of a company's history).
  experience_evidence must be copied verbatim from the posting.
- seniority: the level of the role as titled/described.
- work_mode/places: where the work happens; remote_eligible_countries if remote is limited by country.
- salary only if explicitly stated, with salary_evidence copied verbatim.
- education_mandatory=true only if a degree is strictly required (not 'or equivalent experience' / 'preferred').
- responsibilities: up to 10 short lines describing the actual work.
If the page is not a single job posting or explicitly says the job is closed, set the flags accordingly."""


def content_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(re.sub(r"\s+", " ", p or "").strip().encode("utf-8", "ignore"))
        h.update(b"\x00")
    return h.hexdigest()[:24]


def _evidence_ok(evidence: str, text: str) -> bool:
    if not evidence or len(evidence) < 4:
        return False
    a = re.sub(r"\s+", " ", evidence).strip().lower()
    b = re.sub(r"\s+", " ", text).lower()
    return a[:120] in b


def _verify_skills(items: list[_Skill], text: str) -> list[_Skill]:
    out, seen = [], set()
    for s in items:
        forms = [s.name, *s.aliases]
        hit = any_term_in_text(forms, text)
        if not hit:
            continue
        key = norm_term(s.name)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def apply_understanding(job: JobPosting, u: JobUnderstanding, model: str) -> None:
    """Merge a verified understanding into the posting (structured source fields win)."""
    text = f"{job.title}\n{job.description}"
    req = Requirements(method="llm", llm_model=model)

    required = _verify_skills(u.required_skills, text)
    preferred = [s for s in _verify_skills(u.preferred_skills, text)
                 if norm_term(s.name) not in {norm_term(r.name) for r in required}]
    req.required_skills = [s.name for s in required]
    req.must_have_skills = [s.name for s in required if s.must_have]
    req.preferred_skills = [s.name for s in preferred]
    req.skill_aliases = {s.name: [a for a in s.aliases if a] for s in [*required, *preferred]}

    if u.experience_min_years is not None and _evidence_ok(u.experience_evidence, text) \
            and number_in_text(u.experience_min_years, u.experience_evidence):
        req.experience_min = u.experience_min_years
        if u.experience_max_years is not None and number_in_text(u.experience_max_years, u.experience_evidence):
            req.experience_max = u.experience_max_years
        req.experience_evidence = u.experience_evidence.strip()[:200]

    if u.education_level not in ("unknown",) and (u.education_level == "none" or _evidence_ok(u.education_evidence, text)):
        req.education_level = u.education_level
        req.education_mandatory = u.education_mandatory and u.education_level != "none"
        req.education_evidence = u.education_evidence.strip()[:200]
    else:
        req.education_level = "unknown"

    if u.notice_period_max_days is not None and _evidence_ok(u.notice_evidence, text):
        req.notice_period_max_days = u.notice_period_max_days
    req.responsibilities = [r for r in u.responsibilities if r][:10]
    req.domain_keywords = [d for d in u.domains if d][:8]
    job.requirements = req

    if job.salary is None and u.salary_evidence and _evidence_ok(u.salary_evidence, text):
        # Indian notation ("12-18 LPA") is read by code, not by the model, so lakhs never become rupees or vice versa.
        job.salary = inr_salary(u.salary_evidence)
    if u.salary and u.salary.min is not None and job.salary is None and _evidence_ok(u.salary_evidence, text):
        ev = u.salary_evidence.replace(",", "")
        if number_in_text(u.salary.min, ev) or number_in_text(u.salary.min, u.salary_evidence):
            job.salary = Salary(min=u.salary.min, max=u.salary.max, currency=u.salary.currency,
                                period=u.salary.period, raw=u.salary_evidence.strip()[:120])
            top = job.salary.annual_max()
            if job.salary.currency == "INR" and top is not None and top < 50_000:
                job.salary = None              # "12" from "12 LPA" read as rupees — unusable, not a real figure

    if job.seniority == Seniority.UNKNOWN:
        job.seniority = u.seniority
    if not job.role_family:
        job.role_family = u.role_family
    if job.work_mode == WorkMode.UNKNOWN:
        job.work_mode = u.work_mode
    if not job.employment_type and u.employment_type != "unknown":
        job.employment_type = u.employment_type
    if not job.locations:
        job.locations = [p.city for p in u.places if p.city]
    if not job.countries:
        job.countries = list(dict.fromkeys([p.country for p in u.places if p.country]))
    if u.remote_eligible_countries:
        job.remote_countries = list(dict.fromkeys(u.remote_eligible_countries))
    if u.appears_closed and _evidence_ok(u.closed_evidence, text):
        job.validation.notes.append(f"Posting text says it is closed: “{u.closed_evidence[:100]}”")
        job.validation.status = "closed"
    if not u.is_job_posting:
        job.validation.notes.append("Page does not look like a single job posting.")
        job.validation.status = "invalid"


_YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*)?(?:years?|yrs?)", re.I)


def fallback_requirements(job: JobPosting, snapshot: Optional[CandidateSnapshot]) -> Requirements:
    """No-LLM fallback: only facts we can read without domain knowledge.

    Skills: the candidate's own skills that literally appear in the JD (we
    cannot know the JD's other requirements without understanding it, so
    `method="fallback"` tells the matcher and UI that coverage is partial).
    """
    text = f"{job.title}\n{job.description}"
    req = Requirements(method="fallback")
    if snapshot:
        req.required_skills = [s.name for s in snapshot.skills if any_term_in_text([s.name, *s.aliases], text)]
    mins = []
    for m in _YEARS_RE.finditer(job.description or ""):
        window = (job.description[max(0, m.start() - 60): m.end() + 60]).lower()
        if "experience" in window:
            mins.append((float(m.group(1)), float(m.group(2)) if m.group(2) else None, m.group(0)))
    if mins:
        lo = max(mins, key=lambda x: x[0])
        if lo[0] <= 30:
            req.experience_min, req.experience_max, req.experience_evidence = lo[0], lo[1], lo[2]
    req.education_level = "unknown"
    return req


async def understand_job(job: JobPosting, snapshot: Optional[CandidateSnapshot] = None, use_llm: bool = True) -> str:
    """Populate job.requirements (and missing normalized fields). Returns method used."""
    if use_llm and job.description and len(job.description) > 200:
        user = (f"Job title (from source): {job.title}\nCompany (from source): {job.company}\n"
                f"Location (from source): {job.location_raw}\n\nPosting text:\n{fence(job.description, 14000)}")
        u, model = await call_structured(
            task="job_understanding", version=VERSION, model=JobUnderstanding, system=_SYSTEM, user=user,
            chain="extraction", max_tokens=2500,
            cache_parts=(content_hash(job.title, job.description),),
        )
        if u is not None:
            apply_understanding(job, u, model)
            _salary_from_text(job)
            return "llm"
    job.requirements = fallback_requirements(job, snapshot)
    _salary_from_text(job)
    return "fallback"


def inr_salary(text: str, require_context: bool = False) -> Optional[Salary]:
    found = parse_inr_salary(text, require_context=require_context)
    if not found:
        return None
    lo, hi, period, raw = found
    return Salary(min=lo, max=hi, currency="INR", period=period, raw=raw[:120])


def _salary_from_text(job: JobPosting) -> None:
    """Last resort: stated Indian pay in the JD text, even when the model missed it or was unavailable."""
    if job.salary is None:
        job.salary = inr_salary(job.description or "", require_context=True)


# ---------------------------------------------------------------------------
# Role fit (candidate-specific, batched)
# ---------------------------------------------------------------------------

class _Fit(BaseModel):
    id: str
    closeness: float = Field(ge=0, le=1, description="how close the job's real work is to the candidate's tracks")
    matched_track: str = ""
    reason: str = ""


class RoleFitBatch(BaseModel):
    fits: list[_Fit] = Field(default_factory=list)


_FIT_SYSTEM = """You judge whether job roles match a candidate's career tracks.
For each job, compare the job's ACTUAL work (title + responsibilities), not shared buzzwords, against the candidate's tracks
(each with a closeness weight: 1.0 = main track, lower = adjacent). Return closeness 0-1:
1.0 = same track as the main one; scale down for adjacent tracks per their weight; below 0.3 = a different career.
Ignore seniority and location here — they are judged separately. reason: one short sentence."""


def _fallback_fit(snapshot: CandidateSnapshot, job: JobPosting) -> tuple[float, str, str]:
    """Token overlap of the job title against the candidate's own titles/tracks."""
    jt = set(tokens(job.title))
    best, track = 0.0, ""
    pool = [(f.label, f.closeness) for f in snapshot.role_families] + [(t, 1.0) for t in snapshot.target_titles] \
        + [(t, 0.7) for t in snapshot.adjacent_titles]
    for label, w in pool:
        lt = set(tokens(label))
        if not jt or not lt:
            continue
        sim = len(jt & lt) / len(jt | lt) * w
        if sim > best:
            best, track = sim, label
    return min(1.0, best * 1.6), track, "Estimated from title overlap (AI unavailable)."


async def assess_role_fit(snapshot: CandidateSnapshot, jobs: list[JobPosting], use_llm: bool = True,
                          batch_size: int = 12) -> dict[str, tuple[float, str, str, str]]:
    """Return {job_id: (closeness, matched_track, reason, method)}."""
    out: dict[str, tuple[float, str, str, str]] = {}
    tracks = "\n".join(f"- {f.label} (weight {f.closeness:.2f})" for f in snapshot.role_families) or "- (none)"
    pending = list(jobs)
    if use_llm and snapshot.role_families:
        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            lines = []
            for j in batch:
                resp = "; ".join(j.requirements.responsibilities[:4]) or (j.description or "")[:300]
                lines.append(f"[{j.id}] title: {j.title} | track per posting: {j.role_family or '?'} | work: {resp}")
            user = f"Candidate tracks:\n{tracks}\n\nJobs:\n{fence(chr(10).join(lines), 9000)}"
            key = content_hash(snapshot.profile_hash, *[f"{j.id}:{j.title}:{j.role_family}" for j in batch])
            res, model = await call_structured(
                task="role_fit", version=ROLE_FIT_VERSION, model=RoleFitBatch, system=_FIT_SYSTEM, user=user,
                chain="fast", max_tokens=1600, cache_parts=(key,),
            )
            if res:
                ids = {j.id for j in batch}
                for f in res.fits:
                    if f.id in ids:
                        out[f.id] = (f.closeness, f.matched_track, f.reason, "llm")
    for j in jobs:
        if j.id not in out:
            c, t, r = _fallback_fit(snapshot, j)
            out[j.id] = (c, t, r, "fallback")
    return out
