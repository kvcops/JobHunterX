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
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"          # staff / lead / architect
    PRINCIPAL = "principal"  # principal / director-level
    UNKNOWN = "unknown"

    @property
    def rank(self) -> int:
        """Position on the ladder (declaration order); UNKNOWN is -1."""
        if self is Seniority.UNKNOWN:
            return -1
        return list(Seniority).index(self)
