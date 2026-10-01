"""
Generated application documents.

Resume, CV and cover letter are distinct document kinds with independent
generation logic (see jobhunterx/generation/). Every document records:
  * which profile version it was generated from (stale detection),
  * which job it targets (resumes / cover letters only),
  * provenance — the profile items it used and every rewritten line with
    its original, plus fact-check warnings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.domain.job import utcnow

DocumentKind = Literal["resume", "cv", "cover_letter"]


class RewriteRecord(BaseModel):
    section: str               # e.g. "experience[0]" or "summary"
    original: str
    rewritten: str
    accepted: bool             # False → fact check failed, original kept
    reason: str = ""


class Provenance(BaseModel):
    used_experience: list[int] = Field(default_factory=list)
    used_projects: list[int] = Field(default_factory=list)
    omitted_experience: list[int] = Field(default_factory=list)
    omitted_projects: list[int] = Field(default_factory=list)
    rewrites: list[RewriteRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    llm_model: str = ""
    llm_calls: int = 0


class GeneratedDocument(BaseModel):
    id: str = ""
    kind: DocumentKind
    job_id: Optional[str] = None
    title: str = ""
    focus: str = ""                       # e.g. target role family for CVs
    profile_hash: str = ""
    content: dict[str, Any] = Field(default_factory=dict)   # structured, renderer-agnostic
    provenance: Provenance = Field(default_factory=Provenance)
    page_count: int = 0
    has_pdf: bool = False
    created_at: datetime = Field(default_factory=utcnow)
