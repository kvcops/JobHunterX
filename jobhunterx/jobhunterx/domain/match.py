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
    profile_hash: str = ""
    engine_version: str = ""
    scored_at: datetime = Field(default_factory=utcnow)

    @property
    def is_rejected(self) -> bool:
        return self.verdict == "incompatible"
