"""
Stages 9–12 — Candidate matching, hard constraints, soft relevance, and an
explainable score.

Inputs are already-understood objects (CandidateSnapshot, JobPosting with
verified Requirements, a role-fit judgement). This module contains no
domain vocabulary: it only compares what the candidate has with what the
job asks for, using the tunable `Policy`.

Key property: hard constraints are evaluated first and a failed one caps the
score (`Policy.hard_fail_score_cap`). A Senior role asking for 8+ years can
share every keyword with a 1.5-year candidate's resume and still be
reported as incompatible — for the right, stated reason.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from jobhunterx.domain.candidate import CandidateSnapshot, SkillEvidence, norm_term
from jobhunterx.domain.common import Seniority, WorkMode
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import ConstraintResult, ExperienceFit, MatchAssessment, ScoreComponent
from jobhunterx.intelligence.policy import Policy, get_policy
from jobhunterx.discovery.watchlist import is_mass_recruiter
from jobhunterx.intelligence.reach import assess_reach
from jobhunterx.intelligence.text import term_in_text, tokens

ENGINE_VERSION = "match-v2"

_EDU_ORDER = ["none", "diploma", "bachelor", "master", "phd"]


# ---------------------------------------------------------------------------
# Skill coverage
# ---------------------------------------------------------------------------

# Everyday tools an umbrella skill implies. Someone with years of "Linux" has used SSH, sudo and systemd even if the
# resume never lists them; a job that names them must not read that person as missing them. Credit is "related", not full.
_IMPLIED_BY: dict[str, tuple[str, ...]] = {
    "linux": ("ubuntu", "debian", "centos", "rhel", "red hat", "red hat enterprise linux", "fedora", "suse", "systemd",
              "ssh", "sudo", "bash", "shell", "shell scripting", "rpm", "apt", "yum", "rpm/apt", "cron", "linux administration",
              "linux system administration", "unix"),
    "unix": ("ssh", "bash", "shell", "shell scripting", "cron"),
    "rhel": ("linux", "rpm", "yum", "systemd", "ssh", "sudo"),
    "red hat": ("linux", "rpm", "yum", "systemd", "ssh", "sudo"),
    "jenkins": ("ci/cd", "ci", "continuous integration"),
    "github actions": ("ci/cd", "ci", "continuous integration", "git", "github"),
    "gitlab ci": ("ci/cd", "ci", "continuous integration", "git", "gitlab"),
    "git": ("github", "gitlab", "version control"),
    "kubernetes": ("k8s", "kubectl", "container orchestration", "docker", "containers"),
    "docker": ("containers", "containerization"),
    "aws": ("ec2", "s3", "iam", "cloudwatch", "vpc", "cloud"),
    "azure": ("azure vms", "azure monitor", "cloud"),
    "gcp": ("google cloud", "gce", "cloud"),
    "google cloud": ("gcp", "cloud"),
    "terraform": ("infrastructure as code", "iac"),
    "ansible": ("configuration management", "infrastructure as code"),
    "prometheus": ("monitoring", "observability"),
    "grafana": ("monitoring", "observability", "dashboards"),
    "python": ("scripting",),
    "pytorch": ("deep learning", "machine learning"),
    "tensorflow": ("deep learning", "machine learning"),
    "llm": ("generative ai", "genai", "large language models"),
    "large language models": ("llm", "generative ai", "genai"),
    "rag": ("retrieval augmented generation", "llm", "generative ai"),
    "sql": ("relational databases", "databases"),
    "postgresql": ("sql", "relational databases", "databases"),
    "mysql": ("sql", "relational databases", "databases"),
}


def _skill_credit(name: str, aliases: list[str], snapshot: CandidateSnapshot, pol: Policy,
                  index: dict[str, SkillEvidence], candidate_text: str = "") -> tuple[float, Optional[SkillEvidence], bool]:
    """Return (credit 0–1, candidate skill matched, via_adjacent)."""
    forms = {norm_term(x) for x in [name, *aliases] if x}
    for f in forms:
        if f in index:
            return index[f].strength or pol.credit_listed_only, index[f], False
    for s in snapshot.skills:
        if forms & {norm_term(a) for a in s.adjacent}:
            return pol.credit_adjacent * max(s.strength, pol.credit_listed_only), s, True
    # named in the candidate's own experience / project text, just not in the skills list
    if candidate_text and any(len(f) > 1 and term_in_text(f, candidate_text) for f in forms):
        return pol.credit_listed_only, None, False
    for s in snapshot.skills:
        implied = {norm_term(x) for f in s.forms() for x in _IMPLIED_BY.get(f, ())}
        if forms & implied:
            return pol.credit_adjacent * max(s.strength, pol.credit_listed_only), s, True
    return 0.0, None, False


def _coverage(skills: list[str], aliases: dict[str, list[str]], snapshot: CandidateSnapshot, pol: Policy,
              candidate_text: str = ""):
    index = snapshot.skill_index()
    matched, partial, missing, credits = [], [], [], []
    for name in skills:
        c, ev, adj = _skill_credit(name, aliases.get(name, []), snapshot, pol, index, candidate_text)
        credits.append(c)
        if c and not adj:
            matched.append(name)
        elif c:
            partial.append((name, ev.name if ev else ""))
        else:
            missing.append(name)
    score = sum(credits) / len(credits) if credits else None
    return score, matched, partial, missing


# ---------------------------------------------------------------------------
# Responsibility overlap (TF-IDF cosine; IDF from the job corpus, not a stopword list)
# ---------------------------------------------------------------------------

def build_idf(documents: list[str]) -> dict[str, float]:
    n = max(1, len(documents))
    df: Counter = Counter()
    for d in documents:
        df.update(set(tokens(d)))
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def cosine(a: str, b: str, idf: dict[str, float]) -> float:
    default = max(idf.values()) if idf else 1.0
    va = Counter(tokens(a))
    vb = Counter(tokens(b))
    if not va or not vb:
        return 0.0
    wa = {t: (1 + math.log(c)) * idf.get(t, default) for t, c in va.items()}
    wb = {t: (1 + math.log(c)) * idf.get(t, default) for t, c in vb.items()}
    dot = sum(wa[t] * wb[t] for t in wa.keys() & wb.keys())
    na = math.sqrt(sum(v * v for v in wa.values()))
    nb = math.sqrt(sum(v * v for v in wb.values()))
    return dot / (na * nb) if na and nb else 0.0


def candidate_work_text(profile_dict: dict) -> str:
    parts = []
    for e in profile_dict.get("experience", []) or []:
        parts += [e.get("role", ""), *e.get("bullets", [])]
    for p in profile_dict.get("projects", []) or []:
        parts += [p.get("title", ""), p.get("description", ""), " ".join(p.get("technologies", []))]
    parts.append(profile_dict.get("summary", ""))
    return "\n".join(x for x in parts if x)


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

def _place_forms(snapshot: CandidateSnapshot) -> tuple[set[str], set[str]]:
    cities, countries = set(), set()
    for p in snapshot.locations:
        for f in [p.city, *p.aliases]:
            if f:
                cities.add(norm_term(f))
        if p.country:
            countries.add(norm_term(p.country))
    if snapshot.home_country:
        countries.add(norm_term(snapshot.home_country))
    return cities, countries


_WORLDWIDE = re.compile(r"(?i)\b(anywhere|worldwide|global(ly)?|international|any location|all locations)\b")


def _location_check(snapshot: CandidateSnapshot, job: JobPosting) -> tuple[ConstraintResult, float]:
    cities, countries = _place_forms(snapshot)
    home = norm_term(snapshot.home_country)
    loc_text = "; ".join([job.location_raw, *job.locations])
    job_cities = {norm_term(c) for c in job.locations if c}
    job_countries = {norm_term(c) for c in job.countries if c}
    # Candidate place names (incl. AI-provided aliases) found in the job's location text.
    city_hits = {c for c in cities if term_in_text(c, loc_text)}
    country_hits = {c for c in countries if term_in_text(c, loc_text)} | (job_countries & countries)
    modes = set(snapshot.work_modes)

    def res(status, detail, pref):
        return ConstraintResult(key="location", label="Location & work mode", status=status, detail=detail), pref

    if job.work_mode == WorkMode.REMOTE:
        restricted = {norm_term(c) for c in job.remote_countries}
        named = list(job.remote_countries)
        # "Remote · Belgium" with no "worldwide/anywhere" means remote within Belgium, not open to the world.
        if not restricted and job_countries and not _WORLDWIDE.search(loc_text):
            restricted, named = job_countries, list(job.countries)
        if restricted and home and home not in restricted:
            if snapshot.open_to_international:
                return res("warn", f"Remote, but limited to {', '.join(named)}.", 0.4)
            return res("fail", f"Remote only for {', '.join(named)} — not open to candidates in {snapshot.home_country}.", 0.0)
        if WorkMode.REMOTE not in modes:
            return res("warn", "Remote role, but you prefer on-site/hybrid work.", 0.6)
        return res("pass", "Remote" + (" (eligible from your country)" if restricted else "") + ".", 1.0)

    if not job_cities and not job_countries and not loc_text.strip(" ;"):
        return res("unknown", "The posting does not state a location.", get_policy().unknown_component)

    if job.work_mode in (WorkMode.ONSITE, WorkMode.HYBRID) and job.work_mode not in modes:
        if modes == {WorkMode.REMOTE}:
            return res("fail", f"{job.work_mode.value.title()} role; you only accept remote work.", 0.0)
    if city_hits or job_cities & cities:
        where = ", ".join(sorted(c.title() for c in (city_hits or job_cities & cities)))
        return res("pass", f"{job.work_mode.value.title() if job.work_mode != WorkMode.UNKNOWN else 'Located'} in {where} — one of your locations.", 1.0)
    if not cities and (country_hits or not job_countries):
        return res("pass", "In your country (no preferred cities set).", 0.8)

    label = ", ".join(job.locations or job.countries) or job.location_raw
    if job_countries:
        domestic = bool(country_hits)
    else:
        domestic = True if country_hits else None          # None = country unclear
    if domestic is not False and snapshot.willing_to_relocate:
        return res("warn", f"In {label} — outside your preferred cities, but you are open to relocating.", 0.5)
    if domestic is False and snapshot.open_to_international:
        return res("warn", f"In {label} (abroad) — you are open to international roles.", 0.4)
    if domestic is False:
        return res("fail", f"In {label} (outside {snapshot.home_country or 'your country'}) — you are not open to international roles.", 0.0)
    if domestic is None:
        return res("fail", f"In {label} — not one of your locations.", 0.0)
    return res("fail", f"In {label} — not one of your locations and you are not open to relocating.", 0.0)


# ---------------------------------------------------------------------------
# Main assessment
# ---------------------------------------------------------------------------

def assess(
    snapshot: CandidateSnapshot,
    job: JobPosting,
    *,
    role_fit: tuple[float, str, str, str] = (0.0, "", "", "fallback"),
    candidate_text: str = "",
    idf: Optional[dict[str, float]] = None,
    now: Optional[datetime] = None,
) -> MatchAssessment:
    pol = get_policy()
    now = now or datetime.now(timezone.utc)
    req = job.requirements
    constraints: list[ConstraintResult] = []
    comps: list[ScoreComponent] = []
    strengths: list[str] = []
    gaps: list[str] = []
    unknowns: list[str] = []
    years = snapshot.professional_years
    closeness, track, fit_reason, fit_method = role_fit

    # --- 1. Role track -----------------------------------------------------
    if closeness < pol.role_fail_below:
        constraints.append(ConstraintResult(key="role", label="Career track", status="fail",
                                            detail=f"Different career track: {fit_reason or job.title}"))
    elif closeness < pol.role_warn_below:
        constraints.append(ConstraintResult(key="role", label="Career track", status="warn",
                                            detail=f"Adjacent to your track ({track}): {fit_reason}".strip()))
    else:
        constraints.append(ConstraintResult(key="role", label="Career track", status="pass",
                                            detail=f"Matches your track: {track}. {fit_reason}".strip()))
        strengths.append(f"Role aligns with your {track} track")
    comps.append(ScoreComponent(key="role_alignment", label="Role alignment", weight=pol.weights.role_alignment,
                                score=closeness, detail=fit_reason or track or "—"))

    # --- 2. Experience -----------------------------------------------------
    exp = ExperienceFit(required_min=req.experience_min, required_max=req.experience_max, candidate_years=years)
    if req.experience_min is not None:
        gap = round(req.experience_min - years, 1)
        exp.gap_years = max(0.0, gap)
        band = f"{req.experience_min:g}" + (f"–{req.experience_max:g}" if req.experience_max is not None else "+")
        fail_gap = max(pol.experience_fail_gap_years, pol.experience_fail_gap_ratio * req.experience_min)
        if gap >= fail_gap:
            exp.fit = "under"
            constraints.append(ConstraintResult(key="experience", label="Experience", status="fail",
                                                detail=f"Requires {band} years; you have ~{years:g}."))
        elif gap > pol.experience_warn_gap_years:
            exp.fit = "under"
            constraints.append(ConstraintResult(key="experience", label="Experience", status="warn",
                                                detail=f"Requires {band} years; you have ~{years:g} (stretch)."))
            gaps.append(f"About {gap:g} years short of the {band}-year requirement")
        elif req.experience_max is not None and years > req.experience_max + pol.experience_fail_gap_years:
            exp.fit = "over"
            constraints.append(ConstraintResult(key="experience", label="Experience", status="warn", hard=False,
                                                detail=f"Asks for {band} years; you have ~{years:g} (may be under-levelled)."))
        else:
            exp.fit = "within"
            constraints.append(ConstraintResult(key="experience", label="Experience", status="pass",
                                                detail=f"Requires {band} years; you have ~{years:g}."))
            strengths.append(f"Experience fits ({band} yrs required, you have ~{years:g})")
        if gap <= 0:
            over = years - req.experience_max if req.experience_max is not None else 0
            es = 1.0 if over <= 0 else max(0.6, 1 - 0.08 * over)
        else:
            es = max(0.0, 1 - gap / max(1.0, req.experience_min))
        comps.append(ScoreComponent(key="experience_fit", label="Experience fit", weight=pol.weights.experience_fit,
                                    score=es, detail=f"{band} yrs required · you ~{years:g}"))
    else:
        constraints.append(ConstraintResult(key="experience", label="Experience", status="unknown",
                                            detail="The posting does not state an experience requirement."))
        unknowns.append("Experience requirement not stated")
        comps.append(ScoreComponent(key="experience_fit", label="Experience fit", weight=pol.weights.experience_fit,
                                    score=pol.unknown_component, detail="Not stated — judged by seniority instead"))

    # --- 3. Seniority ------------------------------------------------------
    js, cs = job.seniority, snapshot.seniority
    if js == Seniority.UNKNOWN or cs == Seniority.UNKNOWN:
        constraints.append(ConstraintResult(key="seniority", label="Seniority", status="unknown",
                                            detail="Seniority level could not be determined."))
        sen_score = pol.unknown_component
    else:
        diff = js.rank - cs.rank
        if diff >= pol.seniority_fail_steps:
            constraints.append(ConstraintResult(key="seniority", label="Seniority", status="fail",
                                                detail=f"{js.value.title()}-level role; you are at {cs.value} level."))
            sen_score = 0.1
        elif diff >= pol.seniority_warn_steps:
            constraints.append(ConstraintResult(key="seniority", label="Seniority", status="warn",
                                                detail=f"{js.value.title()}-level role — one step above your {cs.value} level."))
            sen_score = 0.6
        elif -diff >= pol.seniority_overlevel_warn_steps:
            constraints.append(ConstraintResult(key="seniority", label="Seniority", status="warn", hard=False,
                                                detail=f"{js.value.title()}-level role — well below your {cs.value} level."))
            sen_score = 0.5
        else:
            constraints.append(ConstraintResult(key="seniority", label="Seniority", status="pass",
                                                detail=f"{js.value.title()}-level role fits your {cs.value} level."))
            sen_score = 1.0 if diff == 0 else 0.85
    comps.append(ScoreComponent(key="seniority_alignment", label="Seniority alignment",
                                weight=pol.weights.seniority_alignment, score=sen_score,
                                detail=f"Job: {js.value} · You: {cs.value}"))

    # --- 4. Location -------------------------------------------------------
    loc_c, loc_pref = _location_check(snapshot, job)
    constraints.append(loc_c)
    if loc_c.status == "unknown":
        unknowns.append("Location not stated")
    comps.append(ScoreComponent(key="location_preference", label="Location preference",
                                weight=pol.weights.location_preference, score=loc_pref, detail=loc_c.detail))

    # --- 5. Skills ---------------------------------------------------------
    partial_method = req.method != "llm"
    req_score, matched_r, partial_r, missing_r = _coverage(req.required_skills, req.skill_aliases, snapshot, pol, candidate_text or "")
    pref_score, matched_p, partial_p, missing_p = _coverage(req.preferred_skills, req.skill_aliases, snapshot, pol, candidate_text or "")
    if partial_method:
        unknowns.append("Job requirements could not be fully analysed (AI unavailable) — skill coverage is partial")
        comps.append(ScoreComponent(key="skills_required", label="Required skills", weight=pol.weights.skills_required,
                                    score=pol.unknown_component,
                                    detail=f"{len(matched_r)} of your skills appear in the posting; full requirements unknown"))
    elif req_score is None:
        unknowns.append("No explicit skill requirements found")
        comps.append(ScoreComponent(key="skills_required", label="Required skills", weight=pol.weights.skills_required,
                                    score=pol.unknown_component, detail="No explicit skill requirements"))
    else:
        total = len(req.required_skills)
        comps.append(ScoreComponent(key="skills_required", label="Required skills", weight=pol.weights.skills_required,
                                    score=req_score,
                                    detail=f"{len(matched_r)}/{total} matched" + (f", {len(partial_r)} partially" if partial_r else "")))
        if matched_r:
            strengths.append(f"{len(matched_r)}/{total} required skills demonstrated ({', '.join(matched_r[:5])})")
        for name, via in partial_r[:3]:
            gaps.append(f"{name}: not shown directly (related: {via})")
        for name in missing_r[:5]:
            gaps.append(f"{name} not demonstrated in your profile")
    comps.append(ScoreComponent(key="skills_preferred", label="Preferred skills", weight=pol.weights.skills_preferred,
                                score=pref_score if pref_score is not None and not partial_method else pol.unknown_component,
                                detail=f"{len(matched_p)}/{len(req.preferred_skills)} nice-to-haves" if req.preferred_skills else "None listed"))

    must = [m for m in req.must_have_skills]
    if must and not partial_method:
        must_missing = [m for m in must if m in missing_r]
        must_partial = [m for m in must if any(m == n for n, _ in partial_r)]
        # A short must-have list is what the employer really insists on: any gap rules the job out. A long one is usually
        # the whole tool list marked "mandatory" by the job reader — a missing item there is a gap to show (it already
        # lowers the score), and only most of the list missing rules the job out.
        hard = bool(must_missing) and (len(must) <= 3 or (len(must_missing) >= 2 and len(must_missing) / len(must) >= 0.5))
        if must_missing and not hard:
            constraints.append(ConstraintResult(key="must_have", label="Mandatory skills", status="warn",
                                                detail=f"Mandatory: {', '.join(must_missing)} — not found in your profile; "
                                                       f"you have {len(must) - len(must_missing)} of {len(must)}."))
        elif must_missing:
            constraints.append(ConstraintResult(key="must_have", label="Mandatory skills", status="fail",
                                                detail=f"Mandatory: {', '.join(must_missing)} — not found in your profile."))
        elif must_partial:
            constraints.append(ConstraintResult(key="must_have", label="Mandatory skills", status="warn",
                                                detail=f"Mandatory: {', '.join(must_partial)} — only related experience."))
        else:
            constraints.append(ConstraintResult(key="must_have", label="Mandatory skills", status="pass",
                                                detail=f"All {len(must)} mandatory skills demonstrated."))

    # --- 6. Responsibilities -----------------------------------------------
    job_work = "\n".join(req.responsibilities + req.requirement_lines) or job.description[:3000]
    if candidate_text and job_work:
        cos = cosine(job_work, candidate_text, idf or build_idf([job.description, candidate_text]))
        rs = min(1.0, cos / pol.responsibility_full_at)
        comps.append(ScoreComponent(key="responsibility_overlap", label="Responsibility overlap",
                                    weight=pol.weights.responsibility_overlap, score=rs,
                                    detail="Similarity between the job's work and your experience/projects"))
        if rs >= 0.7:
            strengths.append("Day-to-day work closely resembles your past work")
    else:
        comps.append(ScoreComponent(key="responsibility_overlap", label="Responsibility overlap",
                                    weight=pol.weights.responsibility_overlap, score=pol.unknown_component,
                                    detail="Not enough information"))

    # --- 7. Other constraints ---------------------------------------------
    if req.education_level not in ("unknown", "none") and req.education_level in _EDU_ORDER:
        if snapshot.education_level in _EDU_ORDER:
            short = _EDU_ORDER.index(req.education_level) > _EDU_ORDER.index(snapshot.education_level)
            if short and req.education_mandatory:
                constraints.append(ConstraintResult(key="education", label="Education", status="fail",
                                                    detail=f"Requires a {req.education_level} degree."))
            elif short:
                constraints.append(ConstraintResult(key="education", label="Education", status="warn", hard=False,
                                                    detail=f"Prefers a {req.education_level} degree."))
            else:
                constraints.append(ConstraintResult(key="education", label="Education", status="pass",
                                                    detail=f"{req.education_level.title()} requirement met."))
        else:
            constraints.append(ConstraintResult(key="education", label="Education", status="unknown",
                                                detail="Your education level is unclear."))

    status = job.validation.status
    if status in ("closed", "invalid"):
        constraints.append(ConstraintResult(key="active", label="Job is open", status="fail",
                                            detail="; ".join(job.validation.notes[-2:]) or f"Posting is {status}."))
    elif status == "stale":
        constraints.append(ConstraintResult(key="active", label="Job is open", status="warn",
                                            detail="Posting looks old — it may be filled."))
    elif status == "active":
        constraints.append(ConstraintResult(key="active", label="Job is open", status="pass",
                                            detail="Confirmed live at the source."))
    else:
        constraints.append(ConstraintResult(key="active", label="Job is open", status="unknown",
                                            detail="Could not confirm the posting is still open."))
        unknowns.append("Not yet confirmed that the posting is open")

    if req.notice_period_max_days is not None and snapshot.notice_period_days is not None:
        extra = snapshot.notice_period_days - req.notice_period_max_days
        if extra > pol.notice_fail_extra_days:
            constraints.append(ConstraintResult(key="notice", label="Notice period", status="fail",
                                                detail=f"Needs joining within {req.notice_period_max_days} days; your notice is {snapshot.notice_period_days}."))
        elif extra > 0:
            constraints.append(ConstraintResult(key="notice", label="Notice period", status="warn",
                                                detail=f"Prefers ≤{req.notice_period_max_days} days; your notice is {snapshot.notice_period_days}."))

    if job.salary and snapshot.min_annual_salary and job.salary.currency and snapshot.salary_currency \
            and norm_term(job.salary.currency) == norm_term(snapshot.salary_currency):
        top = job.salary.annual_max()
        if top is not None and top < snapshot.min_annual_salary * pol.salary_fail_ratio:
            constraints.append(ConstraintResult(key="salary", label="Compensation", status="fail",
                                                detail=f"Pays up to {top:,.0f} {job.salary.currency}; your minimum is {snapshot.min_annual_salary:,.0f}."))
        elif top is not None and top < snapshot.min_annual_salary:
            constraints.append(ConstraintResult(key="salary", label="Compensation", status="warn",
                                                detail=f"Pays up to {top:,.0f} {job.salary.currency}, a bit below your minimum."))
        elif top is not None:
            constraints.append(ConstraintResult(key="salary", label="Compensation", status="pass",
                                                detail="Stated pay meets your minimum."))
    elif snapshot.min_annual_salary and not job.salary:
        unknowns.append("Compensation not stated")

    if job.company and any(norm_term(job.company) == norm_term(x) for x in snapshot.excluded_companies):
        constraints.append(ConstraintResult(key="company", label="Company", status="fail",
                                            detail=f"{job.company} is on your excluded list."))
    elif is_mass_recruiter(job.company):
        constraints.append(ConstraintResult(key="company", label="Company", status="fail",
                                            detail=f"{job.company} is a mass-recruitment IT services firm — "
                                                   "bulk hiring, little real product AI work."))

    if job.employment_type and snapshot.employment_types and job.employment_type not in snapshot.employment_types:
        constraints.append(ConstraintResult(key="employment_type", label="Employment type", status="warn", hard=False,
                                            detail=f"{job.employment_type.replace('_', ' ')} — you prefer {', '.join(t.replace('_', ' ') for t in snapshot.employment_types)}."))

    # --- Score -------------------------------------------------------------
    wsum = sum(c.weight for c in comps) or 1.0
    raw = 100 * sum(c.weight * max(0.0, min(1.0, c.score)) for c in comps) / wsum
    fails = [c for c in constraints if c.status == "fail" and c.hard]
    warns = [c for c in constraints if c.status == "warn"]
    mult = max(pol.min_warn_multiplier, pol.warn_multiplier ** len(warns))
    score = raw * mult
    if fails:
        # Scale into [0, cap] so incompatible jobs stay ordered by how close they were.
        score = score * pol.hard_fail_score_cap / 100
        verdict = "incompatible"
    elif score >= pol.strong_at:
        verdict = "strong"
    elif score >= pol.good_at:
        verdict = "good"
    elif score >= pol.stretch_at:
        verdict = "stretch"
    else:
        verdict = "weak"

    for w in warns:
        if w.key not in ("experience",) and w.detail not in gaps:
            gaps.append(w.detail)

    if fails:
        headline = "Not a fit: " + "; ".join(f.detail for f in fails[:2])
    elif verdict in ("strong", "good"):
        headline = (strengths[0] if strengths else "Good overall alignment") + (f" · {len(warns)} caution(s)" if warns else "")
    else:
        headline = (gaps[0] if gaps else "Partial alignment")

    return MatchAssessment(
        score=int(round(score)),
        verdict=verdict,
        headline=headline[:200],
        hard_constraints=constraints,
        components=[c.model_copy(update={"score": round(max(0.0, min(1.0, c.score)), 3)}) for c in comps],
        strengths=strengths[:8],
        gaps=gaps[:8],
        unknowns=list(dict.fromkeys(unknowns))[:6],
        matched_required=matched_r,
        missing_required=missing_r + [n for n, _ in partial_r],
        matched_preferred=matched_p,
        missing_preferred=missing_p + [n for n, _ in partial_p],
        experience=exp,
        rejected_reasons=[f.detail for f in fails],
        role_fit=round(closeness, 3),
        role_track=track,
        reach=assess_reach(job, snapshot, now),
        method="llm" if (req.method == "llm" and fit_method == "llm") else "fallback",
        profile_hash=snapshot.profile_hash,
        engine_version=ENGINE_VERSION,
        scored_at=now,
    )
