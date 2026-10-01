"""
Matching policy — the only place where scoring weights and tolerances live.

These are product decisions (how strict to be), not domain knowledge. They
can be overridden without code changes via the MATCH_POLICY_JSON setting,
e.g. MATCH_POLICY_JSON='{"weights": {"skills_required": 0.3}}'.
"""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic import BaseModel, Field


class Weights(BaseModel):
    role_alignment: float = 0.22
    skills_required: float = 0.28
    skills_preferred: float = 0.05
    experience_fit: float = 0.17
    responsibility_overlap: float = 0.13
    seniority_alignment: float = 0.08
    location_preference: float = 0.07


class Policy(BaseModel):
    weights: Weights = Field(default_factory=Weights)
    # Experience: years short of the stated minimum that are tolerated as a
    # "stretch" (warn) before becoming incompatible (fail). Relative part
    # scales with the requirement (asking 8 yrs from someone with 6 is closer
    # than asking 3 from someone with 1).
    experience_warn_gap_years: float = 0.75
    experience_fail_gap_years: float = 2.0
    experience_fail_gap_ratio: float = 0.4
    # Seniority ladder steps above the candidate that are a stretch / a mismatch.
    seniority_warn_steps: int = 1
    seniority_fail_steps: int = 2
    seniority_overlevel_warn_steps: int = 3
    # Role family closeness below which the role is a different career track.
    role_fail_below: float = 0.3
    role_warn_below: float = 0.55
    # Credit for skills.
    credit_professional: float = 1.0
    credit_project: float = 0.85
    credit_listed_only: float = 0.65
    credit_adjacent: float = 0.4
    # Any failed hard constraint caps the score here; each warning multiplies.
    hard_fail_score_cap: int = 35
    warn_multiplier: float = 0.9
    min_warn_multiplier: float = 0.7
    # Verdict thresholds on the final 0–100 score.
    strong_at: int = 75
    good_at: int = 60
    stretch_at: int = 45
    # Salary below the candidate minimum by more than this ratio is a hard fail.
    salary_fail_ratio: float = 0.7
    # Notice period difference (days) beyond which it is a hard fail.
    notice_fail_extra_days: int = 30
    # Postings older than this are considered stale when no deadline is given.
    stale_after_days: int = 60
    # TF-IDF cosine at which responsibility overlap counts as full.
    responsibility_full_at: float = 0.25
    # Neutral component value when the information is unknown.
    unknown_component: float = 0.5


@lru_cache(maxsize=1)
def get_policy() -> Policy:
    from jobhunterx.config.settings import get_settings
    raw = getattr(get_settings(), "match_policy_json", "") or ""
    if not raw.strip():
        return Policy()
    try:
        return Policy.model_validate(json.loads(raw))
    except Exception:
        return Policy()
