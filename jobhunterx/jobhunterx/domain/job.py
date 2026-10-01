"""
JobPosting — the one internal representation every job source is normalized
into (ATS JSON APIs, JSON-LD job pages, generic HTML pages, search results).

Every field that matters for a decision carries provenance through
`ValidationReport.checks`: a value is either *verified* (read from a
first-party structured source or confirmed live), *inferred* (parsed from
free text), *unverified* or *unknown*. The UI renders these honestly instead
of pretending everything is confirmed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.domain.common import Seniority, WorkMode

SourceKind = Literal["ats_api", "career_page", "job_board", "aggregator", "search_result"]
CheckStatus = Literal["verified", "inferred", "unverified", "unknown", "failed"]
ValidationStatus = Literal["active", "likely_active", "unverified", "stale", "closed", "invalid"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceRef(BaseModel):
    """Where we saw this job. A job may have several (deduplicated) sources."""

    name: str                      # e.g. "greenhouse", "lever", "linkedin", "company_site"
    kind: SourceKind
    url: str
    fetched_at: datetime = Field(default_factory=utcnow)
    first_party: bool = False      # the hiring company's own ATS/career page
    confidence: float = 0.5        # how much we trust this source's data


class AtsRef(BaseModel):
    """Identifies a posting on a public ATS board — allows API re-verification."""

    kind: str                      # greenhouse | lever | ashby | smartrecruiters | workable | recruitee
    token: str                     # board / company token
    job_id: str = ""


class Salary(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: str = ""
    period: str = "year"           # year | month | hour
    raw: str = ""

    def annual_min(self) -> Optional[float]:
        if self.min is None:
            return None
        mult = {"year": 1, "month": 12, "hour": 2080}.get(self.period, 1)
        return self.min * mult

    def annual_max(self) -> Optional[float]:
        if self.max is None:
            return self.annual_min()
        mult = {"year": 1, "month": 12, "hour": 2080}.get(self.period, 1)
        return self.max * mult


class FieldCheck(BaseModel):
    status: CheckStatus = "unknown"
    value: Optional[str] = None
    evidence: str = ""


class ValidationReport(BaseModel):
    """Answers: is this job real, reachable, current and applicable?"""

    status: ValidationStatus = "unverified"
    confidence: float = 0.0
    checks: dict[str, FieldCheck] = Field(default_factory=dict)
    checked_at: Optional[datetime] = None
    notes: list[str] = Field(default_factory=list)

    def check(self, key: str) -> FieldCheck:
        return self.checks.get(key) or FieldCheck()


class Requirements(BaseModel):
    """Structured requirements extracted from the JD."""

    required_skills: list[str] = Field(default_factory=list)      # canonical keys
    preferred_skills: list[str] = Field(default_factory=list)     # canonical keys
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None
    experience_evidence: str = ""
    education_level: str = "none"          # none | diploma | bachelor | master | phd
    education_mandatory: bool = False
    education_evidence: str = ""
    notice_period_max_days: Optional[int] = None
    responsibilities: list[str] = Field(default_factory=list)
    requirement_lines: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)
    method: str = "heuristic"              # heuristic | llm+heuristic | structured
    llm_model: str = ""


class JobPosting(BaseModel):
    id: str = ""
    fingerprint: str = ""                 # dedupe identity (company|title|location)
    canonical_url: str = ""
    title: str = ""
    company: str = ""
    company_domain: str = ""
    location_raw: str = ""
    locations: list[str] = Field(default_factory=list)   # normalized city names
    countries: list[str] = Field(default_factory=list)
    work_mode: WorkMode = WorkMode.UNKNOWN
    employment_type: str = ""             # full_time | part_time | contract | internship | temporary
    seniority: Seniority = Seniority.UNKNOWN
    role_family: str = ""
    department: str = ""
    salary: Optional[Salary] = None
    posted_at: Optional[datetime] = None
    valid_through: Optional[datetime] = None
    description: str = ""
    apply_url: str = ""
    sources: list[SourceRef] = Field(default_factory=list)
    ats: Optional[AtsRef] = None
    requirements: Requirements = Field(default_factory=Requirements)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    discovered_at: datetime = Field(default_factory=utcnow)
    discovered_by_query: str = ""

    @property
    def primary_source(self) -> Optional[SourceRef]:
        if not self.sources:
            return None
        return sorted(self.sources, key=lambda s: (not s.first_party, -s.confidence))[0]

    def summary_text(self) -> str:
        return f"{self.title} @ {self.company} ({self.location_raw or 'location unknown'})"
