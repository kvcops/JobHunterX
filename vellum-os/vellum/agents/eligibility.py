"""
Vellum OS — Eligibility Gate

The STRICT, zero-token filter that runs BEFORE any LLM scoring. This is the
part that makes the system honest: a fresher never sees a Senior role, a
Bengaluru candidate never sees Pune-only roles, a software engineer never
sees sales/marketing gigs.

Every rule is deterministic and explains itself:
  verdict: "pass" | "reject"
  reason : one short human-readable line

The gate runs on the *raw* JD + role + location. It does not look at
skills overlap (that's the scorer's job) — it only rejects what is
provably wrong for this candidate.
"""

from __future__ import annotations

import re
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("eligibility")

SENIORITY_CEILING = {"entry": 1, "mid": 3, "senior": 8}
_SENIOR_WORDS = ("senior", "lead", "principal", "staff", "architect", "sr ",
                 "manager", "head of", "director", "vp", "chief", "expert",
                 "10+", "8+", "7+")
_JUNIOR_WORDS = ("junior", "fresher", "entry", "trainee", "intern", "0-1",
                 "0 to 1", "graduate", "new grad", "early career")


def _extract_required_years(text: str) -> Optional[float]:
    """Min years the JD asks for, from explicit patterns.

    First-match wins; each pattern returns the MINIMUM of any range it sees
    (a JD asking "3 to 5 years" requires 3). "Minimum 3 years of professional
    experience" is caught even with an adjective between "of" and "experience".
    """
    s = re.sub(r"\s+", " ", text or "").lower()
    # 1. "minimum / at least / requires N years..." — the N is the floor.
    m = re.search(
        r"(?:minimum|min\.|at least|requires?|requiring|needs?|looking for|"
        r"we (?:want|need|seek|require)|must have|must possess)\s+(?:of\s+)?"
        r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years|yrs|year)",
        s,
    )
    if m:
        return float(m.group(1))
    # 2. Range with an explicit separator: "3 to 5 years", "3-5 yrs", "3 – 5".
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|[-–—])\s*\d+(?:\.\d+)?\s*(?:years|yrs|year)",
        s,
    )
    if m:
        return float(m.group(1))
    # 3. "N+ years of <anything> experience" — word between "of" and experience ok.
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs|year)s?\s+(?:of\s+)?"
        r"(?:[\w\-]+\s+){0,3}?(?:experience|exp|experience\s+required)",
        s,
    )
    if m:
        return float(m.group(1))
    # 4. "N years" with no qualifier (fallback — explicit number still signals).
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|plus|to)\s*(?:years|yrs|year)", s)
    if m:
        return float(m.group(1))
    return None


def _has_senior_halo(role: str) -> bool:
    """Seniority signal from the ROLE TITLE only.

    Deliberately NOT scanned against the JD: JD prose like "work with senior
    engineers" or "we are a senior team" is context, not a requirement, and
    scanning it false-rejects good entry jobs. Explicit year requirements in
    the JD are handled separately by _extract_required_years.
    """
    blob = (role or "").lower()
    return any(w in blob for w in _SENIOR_WORDS)


def _has_junior_marker(role: str, jd: str) -> bool:
    """Junior markers may come from the JD too ('freshers welcome') — this
    only ever PREVENTS a senior-halo rejection, never causes one."""
    blob = f"{role or ''} {jd or ''}".lower()
    return any(w in blob for w in _JUNIOR_WORDS)


_CITY_ALIASES = {
    "bengaluru": "bengaluru", "bangalore": "bengaluru",
    "hyderabad": "hyderabad", "secunderabad": "hyderabad",
    "chennai": "chennai", "madras": "chennai",
    "mumbai": "mumbai", "bombay": "mumbai", "pune": "pune",
    "delhi": "delhi ncr", "noida": "delhi ncr", "gurugram": "delhi ncr",
    "gurgaon": "delhi ncr", "kolkata": "kolkata", "calcutta": "kolkata",
    "ahmedabad": "ahmedabad", "kochi": "kochi", "cochin": "kochi",
    "indore": "indore", "jaipur": "jaipur", "remote": "remote",
    "anywhere": "remote", "india": "india", "work from home": "remote",
    "wfh": "remote", "onsite": "", "hybrid": "",
}


def _norm_city(raw: str) -> str:
    s = (raw or "").lower().strip()
    if not s:
        return ""
    return _CITY_ALIASES.get(s, s.split(",")[0].strip())


def _location_conflict(job_location: str, plan_locations: list[str]) -> Optional[str]:
    """Return reason if job location provably excludes the candidate."""
    jl = (job_location or "").lower()
    if not jl:
        return None  # unknown location → let the scorer judge
    if any(w in jl for w in ("remote", "anywhere", "work from home", "wfh")):
        return None
    jl_norm = _norm_city(jl)
    if jl_norm in ("remote", "india"):
        return None
    for want in plan_locations:
        w = _norm_city(want)
        if w and w in (jl_norm, jl):
            return None
    # Candidate city explicitly absent + job is tied to a specific other city
    known_cities = set(_CITY_ALIASES.keys()) - {"remote", "anywhere", "india", "onsite", "hybrid", "wfh", "work from home"}
    if any(c in jl for c in known_cities):
        return f"Location: job is in {jl_norm or jl}, not in your accepted cities"
    return None


def _role_family_conflict(role: str, plan: dict) -> Optional[str]:
    rl = (role or "").lower()
    non_dev = ("sales", "marketing", "business development", "recruiter",
               "hr ", "support", "customer success", "content", "designer",
               "accountant", "finance", "operations", "campus ambassador",
               "teacher", "trainer", "moderator", "administrative")
    for bad in non_dev:
        if bad in rl:
            return f"Role family: '{rl.strip()}' is not your field"
    return None


def _reject_term_hit(role: str, plan: dict) -> Optional[str]:
    """Plan reject terms apply to the ROLE TITLE only, never the JD body.

    A reject term like 'senior' appearing inside a JD description is prose
    context ("build features with our senior team") — rejecting on it throws
    away good jobs. If the role title itself carries the term, it is a true
    signal (title = "Senior X" or "Sales Y").
    """
    blob = (role or "").lower()
    for term in plan.get("reject_terms") or []:
        t = str(term).lower()
        if t and t in blob:
            return f"Reject term: title contains '{term}'"
    return None


def check_eligibility(
    job: dict,
    plan: dict,
    *,
    strict_seniority: bool = True,
) -> dict:
    """Run the full gate. Returns {"verdict": "pass"|"reject", "reason": str}.

    job: {role, location, jd_text}
    plan: from search_planner.build_search_plan(profile)
    """
    role = job.get("role") or ""
    jd = job.get("jd_text") or ""
    loc = job.get("location") or ""

    # 1. Role family — provably wrong domain
    r = _role_family_conflict(role, plan)
    if r:
        return {"verdict": "reject", "reason": r}

    # 2. Explicit reject terms (sales, campus, etc.) — title only
    r = _reject_term_hit(role, plan)
    if r:
        return {"verdict": "reject", "reason": r}

    # 3. Location conflict
    if strict_seniority:
        r = _location_conflict(loc, plan.get("locations") or [])
        if r:
            return {"verdict": "reject", "reason": r}

    # 4. Years required vs candidate years
    req_years = _extract_required_years(jd)
    cand_years = float(plan.get("years_experience") or 0)
    ceiling = SENIORITY_CEILING.get(plan.get("seniority_max"), 1)

    senior_halo = _has_senior_halo(role)
    junior_marker = _has_junior_marker(role, jd)

    if senior_halo and not junior_marker:
        if cand_years < 1:
            return {"verdict": "reject",
                    "reason": f"Seniority: role is senior/lead, you have {cand_years:.0f} yrs"}
        if req_years is None and cand_years < 3:
            return {"verdict": "reject",
                    "reason": f"Seniority: senior-level role, you have {cand_years:.0f} yrs"}
        if req_years is not None and req_years > cand_years + 1:
            return {"verdict": "reject",
                    "reason": f"Experience: needs {req_years:g}+ yrs, you have {cand_years:g}"}

    if req_years is not None and req_years > cand_years + 1:
        return {"verdict": "reject",
                "reason": f"Experience: needs {req_years:g}+ yrs, you have {cand_years:g}"}

    # Fresher guard: any explicit multi-year requirement kills entry-level
    if cand_years < 1 and req_years is not None and req_years >= 2:
        return {"verdict": "reject",
                "reason": f"Experience: needs {req_years:g}+ yrs, you are entry-level"}

    # No explicit years but senior halo beyond ceiling
    if req_years is None and senior_halo and ceiling < 3:
        return {"verdict": "reject",
                "reason": f"Seniority: senior-level role, ceiling is '{plan.get('seniority_max')}'"}

    return {"verdict": "pass", "reason": ""}


def filter_jobs(jobs: list[dict], plan: dict) -> tuple[list[dict], list[dict]]:
    """Return (passed, rejected_with_reasons). Zero LLM tokens."""
    passed: list[dict] = []
    rejected: list[dict] = []
    for job in jobs:
        verdict = check_eligibility(job, plan)
        out = dict(job)
        out["eligibility"] = verdict
        if verdict["verdict"] == "pass":
            passed.append(out)
        else:
            rejected.append(out)
    return passed, rejected