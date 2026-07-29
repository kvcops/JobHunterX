"""
Vellum OS — Pydantic Data Models

Every component that touches external data uses a typed model.
Confidence scores (0.0–1.0) are present on all best-effort results.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    MATCHED = "matched"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_ATTENTION = "needs_attention"


class HITLType(str, Enum):
    LOGIN = "needs_login"
    CAPTCHA = "needs_captcha"
    MFA = "needs_mfa"
    MANUAL_FORM = "needs_manual_form"
    TOO_COMPLEX = "too_complex"


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class Experience(BaseModel):
    role: Optional[str] = ""
    company: Optional[str] = ""
    start: Optional[str] = ""
    end: Optional[str] = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: Optional[str] = ""
    institution: Optional[str] = ""
    start: Optional[str] = ""
    end: Optional[str] = ""
    grade: Optional[str] = ""
    details: Optional[str] = ""


class Project(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    url: Optional[str] = ""
    technologies: list[str] = Field(default_factory=list)


class QAMemory(BaseModel):
    """Pre-filled answers for common application questionnaire fields."""
    expected_salary: Optional[str] = ""
    notice_period: Optional[str] = ""
    work_authorization: Optional[str] = ""  # e.g. "Yes", "No", "Citizen"
    requires_sponsorship: Optional[str] = ""  # e.g. "Yes", "No"
    preferred_work_mode: Optional[str] = ""  # e.g. "Remote", "Hybrid", "Onsite"
    willing_to_relocate: Optional[str] = ""
    years_of_experience: Optional[str] = ""
    custom_answers: dict[str, str] = Field(default_factory=dict)


class CandidateProfile(BaseModel):
    """Ground truth from resume extraction.  `skills` is never modified."""
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    present_address: Optional[str] = ""
    permanent_address: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    portfolio: Optional[str] = ""
    summary: Optional[str] = ""
    suggested_role: Optional[str] = ""
    relevant_experience: Optional[str] = ""
    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    qa_memory: QAMemory = Field(default_factory=QAMemory)



# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class FreshnessResult(BaseModel):
    is_fresh: Optional[bool] = None   # None = uncertain
    confidence: float = 0.0
    evidence: str = "unknown"         # e.g. "HTTP Last-Modified", "regex date"
    detected_date: Optional[str] = None


class ValidationResult(BaseModel):
    match_score: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0


class JobListing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company: str = ""
    role: Optional[str] = None
    career_page_url: str = ""
    apply_url: Optional[str] = None
    jd_text: str = ""
    source: str = ""               # "osm", "ddgs", "curated"
    discovery_confidence: float = 0.0
    freshness: FreshnessResult = Field(default_factory=FreshnessResult)
    validation: Optional[ValidationResult] = None
    status: JobStatus = JobStatus.DISCOVERED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Outreach
# ---------------------------------------------------------------------------

class EmailGuess(BaseModel):
    address: str
    pattern: str = ""              # "first@domain", "first.last@domain", etc.
    mx_valid: Optional[bool] = None
    confidence: float = 0.0
    unverified_guess: bool = True  # Always True — never assume valid


class ContactResult(BaseModel):
    name: str = ""
    role: str = ""                 # "Hiring Manager", "EM", "Recruiter", etc.
    source_url: str = ""
    confidence: float = 0.0


class OutreachDraft(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: Optional[str] = None
    company: str = ""
    contact_name: str = ""
    contact_role: str = ""
    email_guesses: list[EmailGuess] = Field(default_factory=list)
    subject: str = ""
    body: str = ""
    mailto_uri: str = ""
    confidence: float = 0.0
    status: str = "drafted"


# ---------------------------------------------------------------------------
# HITL
# ---------------------------------------------------------------------------

class HITLRequest(BaseModel):
    type: HITLType
    job_id: str
    url: str = ""
    screenshot_path: Optional[str] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Agent Events (WebSocket payload)
# ---------------------------------------------------------------------------

class AgentEvent(BaseModel):
    agent: str
    event_type: str                 # "progress", "discovery", "error", "hitl_request", "complete"
    job_id: Optional[str] = None
    message: str = ""
    data: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# Graph State (TypedDict for LangGraph)
# ---------------------------------------------------------------------------

from typing import TypedDict, Annotated
import operator


class DiscoveryState(TypedDict, total=False):
    """State for the discovery graph."""
    location: str
    profile: dict
    role: str
    limit: int
    discovered_jobs: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
    events: Annotated[list[dict], operator.add]


class JobPipelineState(TypedDict, total=False):
    """State for a per-job validation/apply/outreach pipeline."""
    job: dict
    profile: dict
    freshness: dict
    validation: dict
    tailored_pdf: bytes
    outreach_draft: dict
    hitl_request: dict
    browser_result: dict
    errors: Annotated[list[str], operator.add]
    events: Annotated[list[dict], operator.add]
