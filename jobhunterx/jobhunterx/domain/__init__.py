"""
JobHunterX — Domain model.

These are the shared data contracts used by every stage of the product:

    CandidateProfile  →  CandidateSnapshot (derived, deterministic)
    JobPosting        (one normalized representation for every source)
    MatchAssessment   (explainable candidate↔job fit)
    GeneratedDocument (resume / CV / cover letter with provenance)

Nothing outside this package should invent its own ad-hoc dict shapes for
these concepts.
"""

from jobhunterx.domain.candidate import (  # noqa: F401
    CandidatePreferences,
    CandidateProfile,
    CandidateSnapshot,
    Education,
    Experience,
    Project,
    QAMemory,
    SkillEvidence,
)
from jobhunterx.domain.common import Seniority, WorkMode  # noqa: F401
from jobhunterx.domain.job import (  # noqa: F401
    AtsRef,
    FieldCheck,
    JobPosting,
    Salary,
    SourceRef,
    ValidationReport,
)
from jobhunterx.domain.match import (  # noqa: F401
    ConstraintResult,
    MatchAssessment,
    ScoreComponent,
)
from jobhunterx.domain.documents import GeneratedDocument  # noqa: F401
