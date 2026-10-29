"""
MatchAssessment — an explainable verdict on candidate↔job fit.

Design rules (see jobhunterx/intelligence/matching.py):
  * Hard constraints are evaluated first. A failed hard constraint caps the
    score — no amount of keyword overlap can lift an incompatible job.
  * Soft components are weighted and each carries a human-readable detail.
  * The score is computed deterministically. An LLM may add a narrative
    review, but never sets the number.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.domain.job import utcnow

ConstraintStatus = Literal["pass", "warn", "fail", "unknown"]
Verdict = Literal["strong", "good", "stretch", "weak", "incompatible"]


class ConstraintResult(BaseModel):
    key: str
    label: str
    status: ConstraintStatus
    detail: str
    hard: bool = True


class ScoreComponent(BaseModel):
    key: str
    label: str
    weight: float
    score: float          # 0–1
    detail: str


class ExperienceFit(BaseModel):
    required_min: Optional[float] = None
    required_max: Optional[float] = None
    candidate_years: float = 0.0
    fit: Literal["under", "within", "over", "unknown"] = "unknown"
    gap_years: float = 0.0
    # Early career (under ~3 years): how reachable the posting is despite its stated years (intelligence/matching.py).
    # reachable · direct (apply on the company site / with a referral) · stretch (referral preferred) · out_of_range
    band: Literal["reachable", "direct", "stretch", "out_of_range", ""] = ""
    advice: str = ""
    candidate_label: str = ""          # "1 yr 4 mo (incl. internships)" — counted the way recruiters' systems count


class ScamFlag(BaseModel):
    rule: str
    severity: Literal["critical", "high", "medium"]
    detail: str


class ScamCheck(BaseModel):
    """Fraud signals in a posting (intelligence/scam.py). critical → never recommended; high → shown with a warning."""

    level: Literal["none", "medium", "high", "critical"] = "none"
    flags: list[ScamFlag] = Field(default_factory=list)


class ReachSignal(BaseModel):
    key: str
    points: int
    detail: str


class Reach(BaseModel):
    """How likely a person actually reads the application (see intelligence/reach.py)."""

    score: int = 50                    # 0–100
    level: Literal["high", "medium", "low"] = "medium"
    headline: str = ""
    signals: list[ReachSignal] = Field(default_factory=list)
    application_email: str = ""        # only an address the posting itself gives
    watchlist_company: str = ""
    company_verdict: str = ""


class MatchAssessment(BaseModel):
    score: int = 0                     # 0–100
    verdict: Verdict = "weak"
    headline: str = ""                 # one-line summary
    hard_constraints: list[ConstraintResult] = Field(default_factory=list)
    components: list[ScoreComponent] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    matched_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    experience: ExperienceFit = Field(default_factory=ExperienceFit)
    rejected_reasons: list[str] = Field(default_factory=list)
    role_fit: float = 0.0
    role_track: str = ""
    reach: Optional[Reach] = None      # chance of being seen — separate from fit, never mixed into `score`
    # main = ranked with everything else · floor = safety-net track (large IT-services fresher programmes)
    track: Literal["main", "floor"] = "main"
    scam: Optional[ScamCheck] = None
    method: str = ""                   # llm | fallback — how the JD/role fit were understood
    profile_hash: str = ""
    engine_version: str = ""
    scored_at: datetime = Field(default_factory=utcnow)

    @property
    def is_rejected(self) -> bool:
        return self.verdict == "incompatible"
