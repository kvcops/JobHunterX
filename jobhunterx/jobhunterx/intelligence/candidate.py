"""
Stage 1 — Candidate understanding.

Builds a `CandidateSnapshot` from the user's `CandidateProfile`:

  * Facts that can be computed are computed: years of experience come from
    the experience dates (overlaps merged, internships counted separately).
  * Interpretation comes from the LLM as a schema-validated object: role
    families (with closeness of adjacent careers), concrete titles to search,
    skills with their alternative names, normalized locations.
  * Every LLM claim is checked against the profile: a skill is kept only if
    it (or one of its stated names) literally appears in the profile, and its
    strength is decided by *where* it appears, not by what the model says.

If the LLM is unavailable the snapshot is still built from the profile's own
data, marked `method="fallback"` so the UI can say so.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import (
    CandidateProfile,
    CandidateSnapshot,
    PlaceRef,
    RoleFamilyFit,
    SkillEvidence,
    norm_term,
)
from jobhunterx.domain.common import Seniority
from jobhunterx.intelligence.llm_structured import call_structured, fence
from jobhunterx.intelligence.policy import get_policy
from jobhunterx.intelligence.text import any_term_in_text, merged_years, parse_month

log = get_logger("candidate")

VERSION = "candidate-v1"


class _SkillOut(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list, description="other names/abbreviations for the same skill")
    adjacent: list[str] = Field(default_factory=list, description="closely related skills a recruiter would accept as partial evidence")


class _FamilyOut(BaseModel):
    label: str = Field(description="short role-family name, e.g. a career track")
    closeness: float = Field(ge=0, le=1, description="1.0 = the candidate's main track; lower for adjacent tracks they could credibly move into")
    evidence: str = ""


class _PlaceOut(BaseModel):
    city: str = ""
    region: str = ""
    country: str = ""
    aliases: list[str] = Field(default_factory=list, description="other spellings/old names of the city")


class _ExpOut(BaseModel):
    index: int
    is_internship: bool = False
    is_academic_or_volunteer: bool = False


class CandidateUnderstanding(BaseModel):
    role_families: list[_FamilyOut] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list, description="concrete job titles to search for, realistic for this candidate's level")
    adjacent_titles: list[str] = Field(default_factory=list)
    skills: list[_SkillOut] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list, description="problem/technology domains, short lowercase phrases")
    seniority: Seniority = Seniority.UNKNOWN
    education_level: Literal["none", "diploma", "bachelor", "master", "phd", "unknown"] = "unknown"
    locations: list[_PlaceOut] = Field(default_factory=list)
    home_country: str = ""
    experiences: list[_ExpOut] = Field(default_factory=list)


_SYSTEM = """You are a senior technical recruiter building an accurate, honest model of a candidate.
Use ONLY the profile provided. Do not invent experience, skills, employers or achievements.

Produce:
- role_families: the candidate's main career track (closeness 1.0) and 2-5 adjacent tracks they could credibly be hired into now, with closeness reflecting how transferable their actual experience is. Respect the candidate's stated preferences and career direction.
- target_titles: 4-8 concrete job titles that employers use for roles this candidate can realistically get at their current level (do not inflate seniority). adjacent_titles: up to 6 more.
- skills: every skill/technology/tool the profile mentions, using the name as written in the profile, plus aliases (abbreviations, alternative spellings) and adjacent skills.
- seniority: the level this candidate can credibly be hired at today, based on the work history and its dates.
- education_level: highest completed or in-progress degree.
- locations: the acceptable work locations from the preferences (and the profile location if none), normalized to canonical English city/region/country names with common alternative names as aliases. home_country: the candidate's country.
- experiences: for each experience index, whether it is an internship/trainee role and whether it is academic/volunteer work."""


def _profile_text(p: CandidateProfile) -> str:
    parts = [p.summary, p.suggested_role, ", ".join(p.skills), ", ".join(p.certifications), ", ".join(p.achievements),
             ", ".join(p.competitions)]
    for e in p.experience:
        parts += [e.role, e.company, *e.bullets]
    for pr in p.projects:
        parts += [pr.title, pr.description, ", ".join(pr.technologies)]
    for ed in p.education:
        parts += [ed.degree, ed.details]
    return "\n".join(x for x in parts if x)


def _experience_years(p: CandidateProfile, internships: set[int], excluded: set[int]) -> tuple[float, float, list[str], list[dict]]:
    """Total (incl. internships) and professional years from dates, overlaps merged; plus a per-role breakdown."""
    today = date.today()
    all_iv, pro_iv, notes, rows = [], [], [], []
    for i, e in enumerate(p.experience):
        kind = "excluded" if i in excluded else "internship" if i in internships else "professional"
        row = {"role": e.role, "company": e.company, "start": e.start, "end": e.end or "Present", "kind": kind, "months": None}
        rows.append(row)
        s = parse_month(e.start)
        if not s:
            if e.start or e.end:
                notes.append(f"Could not read dates for '{e.role} @ {e.company}' ({e.start} – {e.end}); not counted.")
            row["kind"] = "undated"
            continue
        end = parse_month(e.end)
        if end is None:
            end = today        # "Present", "Current", empty → ongoing
        end = min(end, today)
        row["months"] = max(0, (end.year - s.year) * 12 + end.month - s.month + 1)
        if i in excluded:
            continue
        all_iv.append((s, end))
        if i not in internships:
            pro_iv.append((s, end))
    return merged_years(all_iv), merged_years(pro_iv), notes, rows


def _skill_strength(forms: list[str], p: CandidateProfile) -> tuple[float, list[str]]:
    pol = get_policy()
    sources: list[str] = []
    strength = 0.0
    for e in p.experience:
        blob = "\n".join([e.role, *e.bullets])
        if any_term_in_text(forms, blob):
            sources.append(f"experience: {e.role or 'role'} @ {e.company or 'company'}")
            strength = max(strength, pol.credit_professional)
    for pr in p.projects:
        blob = "\n".join([pr.title, pr.description, ", ".join(pr.technologies)])
        if any_term_in_text(forms, blob):
            sources.append(f"project: {pr.title or 'project'}")
            strength = max(strength, pol.credit_project)
    if any_term_in_text(forms, "\n".join(p.certifications)):
        sources.append("certification")
        strength = max(strength, pol.credit_project)
    if any(norm_term(s) in {norm_term(f) for f in forms} for s in p.skills) or any_term_in_text(forms, p.summary):
        sources.append("skills list")
        strength = max(strength, pol.credit_listed_only)
    return strength, sources


def _fallback_understanding(p: CandidateProfile) -> CandidateUnderstanding:
    titles = list(dict.fromkeys([*p.preferences.target_roles, p.suggested_role, *[e.role for e in p.experience[:3]]]))
    titles = [t for t in titles if t]
    fams = [_FamilyOut(label=t, closeness=1.0 if i == 0 else 0.8) for i, t in enumerate(titles[:3])]
    places = [_PlaceOut(city=loc) for loc in (p.preferences.locations or ([p.location] if p.location else []))]
    internships = [
        _ExpOut(index=i, is_internship=(e.employment_type or "").lower() == "internship")
        for i, e in enumerate(p.experience)
    ]
    return CandidateUnderstanding(
        role_families=fams,
        target_titles=titles[:6],
        skills=[_SkillOut(name=s) for s in p.skills],
        seniority=p.preferences.seniority_override or Seniority.UNKNOWN,
        locations=places,
        home_country=p.preferences.home_country,
        experiences=internships,
    )


async def understand_candidate(profile: CandidateProfile) -> tuple[Optional[CandidateUnderstanding], str]:
    payload = profile.model_dump(mode="json", exclude={"qa_memory"})
    for e in payload.get("experience", []):
        e["bullets"] = e.get("bullets", [])[:12]
    user = "Candidate profile (JSON):\n" + fence(json.dumps(payload, ensure_ascii=False), max_chars=16000)
    obj, model = await call_structured(
        task="candidate_understanding", version=VERSION, model=CandidateUnderstanding,
        system=_SYSTEM, user=user, chain="reasoning", max_tokens=3000,
        cache_parts=(profile.content_hash(),),
    )
    return obj, model


async def build_snapshot(profile: CandidateProfile, use_llm: bool = True) -> CandidateSnapshot:
    understanding, model = (await understand_candidate(profile)) if use_llm and not profile.is_empty() else (None, "")
    method = "llm" if understanding else "fallback"
    u = understanding or _fallback_understanding(profile)
    notes: list[str] = []
    if method == "fallback":
        notes.append("AI understanding unavailable — using your profile fields directly (lower confidence).")

    internships = {x.index for x in u.experiences if x.is_internship}
    internships |= {i for i, e in enumerate(profile.experience) if (e.employment_type or "").lower() == "internship"}
    excluded = {x.index for x in u.experiences if x.is_academic_or_volunteer}
    total, professional, date_notes, breakdown = _experience_years(profile, internships, excluded)
    notes += date_notes

    prefs = profile.preferences
    if prefs.years_experience_override is not None:
        years, source = float(prefs.years_experience_override), "override"
        notes.append(f"Experience set manually to {years:g} years.")
    elif profile.experience and (total or professional):
        years, source = professional, "dates"
        notes.append(f"{professional:g} years professional experience computed from your work dates"
                     + (f" (+{max(0.0, round(total - professional, 1)):g} yrs internships)" if total > professional else "") + ".")
    else:
        years, source = 0.0, "unknown" if not profile.experience else "dates"

    profile_text = _profile_text(profile)
    skills: list[SkillEvidence] = []
    seen: set[str] = set()
    candidates = list(u.skills) + [_SkillOut(name=s) for s in profile.skills]
    for s in candidates:
        forms = [x for x in [s.name, *s.aliases] if x and x.strip()]
        key = norm_term(s.name)
        if not key or key in seen:
            continue
        # Verification: the skill must actually be in the profile.
        if not any_term_in_text(forms, profile_text) and key not in {norm_term(x) for x in profile.skills}:
            continue
        strength, sources = _skill_strength(forms, profile)
        if not sources:
            continue
        seen.add(key)
        skills.append(SkillEvidence(name=s.name.strip(), key=key, aliases=[a for a in s.aliases if a],
                                    adjacent=[a for a in s.adjacent if a], sources=sources, strength=strength))
    skills.sort(key=lambda x: -x.strength)

    seniority = prefs.seniority_override or u.seniority
    families = [RoleFamilyFit(label=f.label, closeness=f.closeness, evidence=f.evidence)
                for f in sorted(u.role_families, key=lambda f: -f.closeness)]
    for t in prefs.target_roles:  # the user's own targets are always primary
        if not any(norm_term(f.label) == norm_term(t) for f in families):
            families.insert(0, RoleFamilyFit(label=t, closeness=1.0, evidence="your preferences"))

    places = [PlaceRef(**pl.model_dump()) for pl in u.locations if pl.city or pl.country]
    snap = CandidateSnapshot(
        profile_hash=profile.content_hash(),
        total_years=total if source == "dates" else years,
        professional_years=years,
        internship_years=round(max(0.0, total - professional), 1) if source == "dates" else 0.0,
        experience_breakdown=breakdown,
        years_source=source,
        seniority=seniority,
        role_families=families,
        target_titles=list(dict.fromkeys([*prefs.target_roles, *u.target_titles]))[:10],
        adjacent_titles=u.adjacent_titles[:8],
        skills=skills,
        domains=[d for d in u.domains if d][:10],
        education_level=u.education_level,
        locations=places,
        home_country=u.home_country or prefs.home_country,
        work_modes=prefs.work_modes,
        open_to_international=prefs.open_to_international,
        willing_to_relocate=prefs.willing_to_relocate,
        min_annual_salary=prefs.min_annual_salary,
        salary_currency=prefs.salary_currency,
        notice_period_days=prefs.notice_period_days,
        employment_types=prefs.employment_types,
        excluded_companies=prefs.excluded_companies,
        career_direction=prefs.career_direction,
        method=method,
        llm_model=model,
        notes=notes,
    )
    return snap
