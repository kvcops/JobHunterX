"""
Browser-agent event models.

The product's domain model (candidate, job posting, match, documents) lives
in `jobhunterx.domain`. This module only holds the event shapes used by the
browser auto-apply agent, which are wrapped as `{type: "browser"}` messages
on the WebSocket (see docs/API.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HITLType(str, Enum):
    LOGIN = "needs_login"
    CAPTCHA = "needs_captcha"
    MFA = "needs_mfa"
    MANUAL_FORM = "needs_manual_form"
    TOO_COMPLEX = "too_complex"


class AgentEvent(BaseModel):
    agent: str
    event_type: str                 # progress | browser_step | hitl_request | job_status_changed | complete | error
    job_id: Optional[str] = None
    message: str = ""
    data: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Optional[float] = None
