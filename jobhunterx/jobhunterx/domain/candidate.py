"""
Candidate profile — the single source of truth about the person we are
helping.

`CandidateProfile` is what the user owns and edits (extracted from their
resume, then corrected by them). It is the *only* evidence base for resume /
CV generation: nothing may appear in a generated document that cannot be
traced back to it.

`CandidateSnapshot` is derived from the profile deterministically
(`jobhunterx.intelligence.profile.build_snapshot`) and is what search,
validation and matching consume: total years of experience computed from
dates, seniority, canonical skills with evidence, role families, etc.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from jobhunterx.domain.common import Seniority, WorkMode


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v if x is not None)
    return str(v).strip()


def _coerce_str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        parts = [p.strip() for p in v.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(v, (list, tuple, set)):
        out = []
        for item in v:
            if item is None:
                continue
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    return [str(v)]


class _Lenient(BaseModel):
    """Profiles come from LLM extraction and hand edits — be tolerant."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Experience(_Lenient):
    role: str = ""
    company: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    employment_type: str = ""   # full_time | internship | contract | freelance | part_time
    bullets: list[str] = Field(default_factory=list)

    _s = field_validator("role", "company", "location", "start", "end", "employment_type", mode="before")(_coerce_str)
    _l = field_validator("bullets", mode="before")(_coerce_str_list)


class Education(_Lenient):
    degree: str = ""
    institution: str = ""
    start: str = ""
    end: str = ""
    grade: str = ""
    details: str = ""

    _s = field_validator("degree", "institution", "start", "end", "grade", "details", mode="before")(_coerce_str)


class Link(_Lenient):
    """A clickable link as it appeared in the resume (label = the text on the button/link, e.g. "Live demo")."""

    label: str = ""
    url: str = ""

    _s = field_validator("label", "url", mode="before")(_coerce_str)


def _coerce_links(v: Any) -> Any:
    if v is None:
        return []
    if isinstance(v, (str, dict, BaseModel)):
        v = [v]
    out = []
    for x in v if isinstance(v, list) else []:
        if isinstance(x, str):
            x = {"url": x}
        if isinstance(x, (dict, BaseModel)):
            out.append(x)
    return out


class ItemLink(_Lenient):
    """A link that belongs to one certification / achievement / competition (e.g. a credential page)."""

    section: str = ""      # certification | achievement | competition
    item: str = ""         # the entry's text, as written in the profile
    label: str = ""
    url: str = ""

    _s = field_validator("section", "item", "label", "url", mode="before")(_coerce_str)


class Project(_Lenient):
    title: str = ""
    description: str = ""
    url: str = ""                                          # main link (kept for older profiles)
    links: list[Link] = Field(default_factory=list)        # every link of the project: code, live demo, paper…
    technologies: list[str] = Field(default_factory=list)

    _s = field_validator("title", "description", "url", mode="before")(_coerce_str)
    _l = field_validator("technologies", mode="before")(_coerce_str_list)
    _k = field_validator("links", mode="before")(_coerce_links)

    def all_links(self) -> list[Link]:
        """`url` + `links`, without duplicates or empty entries."""
        out: list[Link] = []
        index: dict[str, int] = {}
        for link in ([Link(url=self.url)] if self.url else []) + list(self.links):
            key = link.url.strip().rstrip("/").lower()
            if not key:
                continue
            if key in index:
                if link.label and not out[index[key]].label:      # keep the text that was on the button
                    out[index[key]] = Link(label=link.label, url=out[index[key]].url)
                continue
            index[key] = len(out)
            out.append(Link(label=link.label, url=link.url.strip()))
        return out


class QAMemory(_Lenient):
    """Pre-filled answers for common application questionnaire fields."""

    expected_salary: str = ""
    current_ctc: str = ""
    expected_ctc: str = ""
    notice_period: str = ""
    work_authorization: str = ""
    requires_sponsorship: str = ""
    preferred_work_mode: str = ""
    willing_to_relocate: str = ""
    years_of_experience: str = ""
    custom_answers: dict[str, str] = Field(default_factory=dict)

    _s = field_validator(
        "expected_salary", "current_ctc", "expected_ctc", "notice_period",
        "work_authorization", "requires_sponsorship", "preferred_work_mode",
        "willing_to_relocate", "years_of_experience", mode="before",
    )(_coerce_str)


class CandidatePreferences(_Lenient):
    """What the candidate wants. Drives search scope and hard constraints."""

    target_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)        # acceptable cities
    work_modes: list[WorkMode] = Field(
        default_factory=lambda: [WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ONSITE]
    )
    willing_to_relocate: bool = False
    open_to_international: bool = False                         # roles outside home country
    home_country: str = ""
    min_annual_salary: Optional[float] = None                   # in salary_currency, per year
    salary_currency: str = "INR"
    notice_period_days: Optional[int] = None
    employment_types: list[str] = Field(default_factory=lambda: ["full_time"])
    excluded_companies: list[str] = Field(default_factory=list)
    career_direction: str = ""                                   # free text
    years_experience_override: Optional[float] = None
    seniority_override: Optional[Seniority] = None

    _l = field_validator("target_roles", "locations", "employment_types", "excluded_companies", mode="before")(_coerce_str_list)
    _s = field_validator("career_direction", "home_country", "salary_currency", mode="before")(_coerce_str)

    @field_validator("work_modes", mode="before")
    @classmethod
    def _modes(cls, v: Any) -> Any:
        vals = _coerce_str_list(v)
        out = []
        for m in vals:
            m = m.lower().replace("-", "").replace(" ", "")
            if m in ("remote", "wfh"):
                out.append(WorkMode.REMOTE)
            elif m == "hybrid":
                out.append(WorkMode.HYBRID)
            elif m in ("onsite", "office", "inoffice"):
                out.append(WorkMode.ONSITE)
        return out or [WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ONSITE]

    @field_validator("seniority_override", mode="before")
    @classmethod
    def _sen(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v

    @field_validator("min_annual_salary", "years_experience_override", mode="before")
    @classmethod
    def _num(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v

    @field_validator("notice_period_days", mode="before")
    @classmethod
    def _int(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v

    @model_validator(mode="after")
    def _lpa(self) -> "CandidatePreferences":
        # "14" in an INR salary box means 14 LPA (₹14,00,000) — nobody asks for ₹14 a year.
        if self.min_annual_salary and self.salary_currency.upper() == "INR" and 0 < self.min_annual_salary < 1000:
            self.min_annual_salary = self.min_annual_salary * 100_000
        return self


class CandidateProfile(_Lenient):
    """Ground truth from resume extraction + the user's own edits."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    present_address: str = ""
    permanent_address: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    links: list[Link] = Field(default_factory=list)        # other profiles shown in the header: blog, Kaggle, Scholar…
    item_links: list[ItemLink] = Field(default_factory=list)
    summary: str = ""
    suggested_role: str = ""
    relevant_experience: str = ""
    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    qa_memory: QAMemory = Field(default_factory=QAMemory)
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)

    _s = field_validator(
        "name", "email", "phone", "location", "present_address", "permanent_address",
        "linkedin", "github", "portfolio", "summary", "suggested_role", "relevant_experience",
        mode="before",
    )(_coerce_str)
    _l = field_validator("languages", "skills", "certifications", "competitions", "achievements", mode="before")(_coerce_str_list)

    _k = field_validator("links", mode="before")(_coerce_links)

    @field_validator("item_links", mode="before")
    @classmethod
    def _item_links(cls, v: Any) -> Any:
        return [x for x in v if isinstance(x, (dict, BaseModel))] if isinstance(v, list) else []

    @field_validator("experience", "education", "projects", mode="before")
    @classmethod
    def _list_of_dicts(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            return [x for x in v if isinstance(x, (dict, BaseModel))]
        return []

    @field_validator("qa_memory", "preferences", mode="before")
    @classmethod
    def _dict_or_default(cls, v: Any) -> Any:
        return v if isinstance(v, (dict, BaseModel)) else {}

    def content_hash(self) -> str:
        """Stable hash of the profile — used to detect stale match scores
        and stale generated documents."""
        data = self.model_dump(mode="json")
        # Fields added later are left out while empty, so older profiles keep their hash (documents stay "current").
        for key in ("links", "item_links"):
            if not data.get(key):
                data.pop(key, None)
        for proj in data.get("projects", []):
            if not proj.get("links"):
                proj.pop("links", None)
        blob = json.dumps(data, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def is_empty(self) -> bool:
        return not (self.name or self.skills or self.experience or self.projects)


class SkillEvidence(BaseModel):
    """A skill the candidate has, with where it was demonstrated."""

    name: str
    key: str                                   # normalized lowercase name
    aliases: list[str] = Field(default_factory=list)
    adjacent: list[str] = Field(default_factory=list)   # closely related skills (partial credit)
    sources: list[str] = Field(default_factory=list)    # e.g. "experience: ML Engineer @ Acme"
    strength: float = 0.0                       # 0–1: listed < project < professional use

    def forms(self) -> set[str]:
        return {norm_term(x) for x in [self.name, self.key, *self.aliases] if x}


class RoleFamilyFit(BaseModel):
    label: str
    closeness: float = 1.0                      # 1 = primary career direction
    evidence: str = ""


class PlaceRef(BaseModel):
    city: str = ""
    region: str = ""
    country: str = ""
    aliases: list[str] = Field(default_factory=list)


def norm_term(s: str) -> str:
    """Generic normalization for comparing names produced by different sources."""
    import re as _re
    s = (s or "").lower().strip()
    s = _re.sub(r"[\s_]+", " ", s)
    s = _re.sub(r"(?<=\w)[\-](?=\w)", " ", s)
    s = s.strip(" .,;:()")
    return s


class CandidateSnapshot(BaseModel):
    """Derived view of the profile used by search, matching and generation."""

    profile_hash: str
    total_years: float = 0.0
    professional_years: float = 0.0             # excludes internships
    internship_years: float = 0.0               # internship time not overlapping professional work
    experience_breakdown: list[dict] = Field(default_factory=list)   # per role: role, company, start, end, months, kind
    years_source: str = "unknown"               # dates | override | stated | unknown
    seniority: Seniority = Seniority.ENTRY
    role_families: list[RoleFamilyFit] = Field(default_factory=list)
    target_titles: list[str] = Field(default_factory=list)
    adjacent_titles: list[str] = Field(default_factory=list)
    skills: list[SkillEvidence] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    education_level: str = "none"               # none | diploma | bachelor | master | phd
    locations: list[PlaceRef] = Field(default_factory=list)
    home_country: str = ""
    work_modes: list[WorkMode] = Field(default_factory=list)
    open_to_international: bool = False
    willing_to_relocate: bool = False
    min_annual_salary: Optional[float] = None
    salary_currency: str = ""
    notice_period_days: Optional[int] = None
    employment_types: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    career_direction: str = ""
    method: str = "fallback"                    # llm | fallback
    llm_model: str = ""
    notes: list[str] = Field(default_factory=list)

    def skill_index(self) -> dict[str, SkillEvidence]:
        idx: dict[str, SkillEvidence] = {}
        for s in self.skills:
            for f in s.forms():
                idx.setdefault(f, s)
        return idx
