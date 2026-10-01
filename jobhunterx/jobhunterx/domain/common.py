"""Shared enums used across candidate, job and match models."""

from __future__ import annotations

from enum import Enum


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class Seniority(str, Enum):
    """Ordered seniority ladder. Use `Seniority.rank()` for comparisons."""

    INTERN = "intern"
    ENTRY = "entry"          # 0–1 yrs
    JUNIOR = "junior"        # 1–3 yrs
    MID = "mid"              # 3–5 yrs
    SENIOR = "senior"        # 5–8 yrs
    STAFF = "staff"          # 8–12 yrs (staff / lead / architect)
    PRINCIPAL = "principal"  # 12+ yrs, director-level
    UNKNOWN = "unknown"

    @property
    def rank(self) -> int:
        return _RANK[self]

    @classmethod
    def from_years(cls, years: float) -> "Seniority":
        if years < 1:
            return cls.ENTRY
        if years < 3:
            return cls.JUNIOR
        if years < 5:
            return cls.MID
        if years < 8:
            return cls.SENIOR
        if years < 12:
            return cls.STAFF
        return cls.PRINCIPAL


_RANK = {
    Seniority.INTERN: 0,
    Seniority.ENTRY: 1,
    Seniority.JUNIOR: 2,
    Seniority.MID: 3,
    Seniority.SENIOR: 4,
    Seniority.STAFF: 5,
    Seniority.PRINCIPAL: 6,
    Seniority.UNKNOWN: -1,
}

# Typical experience band (years) for each level — used when a posting gives a
# seniority title but no explicit years.
SENIORITY_TYPICAL_YEARS: dict[Seniority, tuple[float, float]] = {
    Seniority.INTERN: (0, 0),
    Seniority.ENTRY: (0, 1),
    Seniority.JUNIOR: (1, 3),
    Seniority.MID: (3, 5),
    Seniority.SENIOR: (5, 8),
    Seniority.STAFF: (8, 12),
    Seniority.PRINCIPAL: (12, 20),
}
