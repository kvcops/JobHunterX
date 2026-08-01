"""
Vellum OS — Email Drafter Agent

Takes verified contact details from the Contact Finder agent and drafts
accurate, well-written cold email subject lines and bodies using only
the real contact details found. Does not invent or hallucinate any information.
"""

from __future__ import annotations

import json

from vellum.agents.job_llm_validator import call_gemma
from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import email_handoff
from vellum.models import AgentEvent, OutreachDraft

log = get_logger("email_drafter")

OUTREACH_PROMPT = """You are writing a professional outreach email from a job candidate to a hiring contact.

The email should:
1. Be concise (under 150 words)
2. Reference the specific role and company
3. Highlight 1-2 relevant skills or experiences from the candidate profile
4. Include a brief, specific insight about the company or role (proof of research)
5. End with a clear, low-friction call to action
6. Be professional but warm — not generic or spammy

CRITICAL RULES:
- Use ONLY the contact name and role provided. Do NOT invent additional details.
- If the contact is "Hiring Manager" or generic, address them professionally without using a fake name.
- Do NOT fabricate company facts or metrics you don't know.

Candidate Profile:
{profile_summary}

Company: {company}
Role: {role}
Contact: {contact_name} ({contact_role})
Job Description (excerpt):
{jd_excerpt}

Return a JSON object:
{{
  "subject": "Email subject line",
  "body": "Full email body text"
}}

Return valid JSON only. No markdown."""


async def run(state: dict) -> dict:
    """Email Drafter: draft cold outreach emails using verified contact details.

    Input state: {"job": dict, "profile": dict, "contact_result": dict}
    Output: updates with outreach_draft, events
    """
    job = state.get("job", {})
    profile = state.get("profile", {})
    contact_result = state.get("contact_result", {})
    job_id = job.get("id", "")
    company = job.get("company", "")
    role = job.get("role", "")
    jd_text = job.get("jd_text", "")
    events: list[dict] = []
    errors: list[str] = []

    from vellum.api.ws import manager as ws_manager

    async def log_and_broadcast_event(event_type: str, message: str, confidence: float = 0.0, data: dict = None):
        evt = AgentEvent(
            agent="email_drafter",
            event_type=event_type,
            job_id=job_id,
            message=message,
            confidence=confidence,
            data=data
        ).model_dump(mode="json")
        events.append(evt)
        await ws_manager.broadcast(evt)

    # Get contact details from the contact finder result
    contacts = contact_result.get("contacts", [])
    email_guesses = contact_result.get("email_guesses", [])
    manual_lookup_needed = contact_result.get("manual_lookup_needed", False)

    if contacts:
        best_contact = contacts[0]
    else:
        best_contact = {
            "name": "Hiring Manager",
            "role": "Hiring Team",
            "confidence": 0.20,
        }

    await log_and_broadcast_event(
        "progress",
        f"Drafting outreach email for {best_contact['name']} at {company}"
    )

    # ------------------------------------------------------------------
    # Build candidate profile summary
    # ------------------------------------------------------------------
    exp_details = []
    for exp in profile.get("experience", []):
        bullets_str = "\n  * ".join(exp.get("bullets", []))
        exp_details.append(
            f"- {exp.get('role')} at {exp.get('company')} ({exp.get('start')} - {exp.get('end')}):\n  * {bullets_str}"
        )
    edu_details = []
    for edu in profile.get("education", []):
        edu_details.append(
            f"- {edu.get('degree')} from {edu.get('institution')} ({edu.get('start')} - {edu.get('end')})"
        )

    profile_summary = f"""Candidate Profile Context:
Name: {profile.get('name', '')}
Email: {profile.get('email', '')}
Phone: {profile.get('phone', '')}
Location: {profile.get('location', '')}
Suggested Role: {profile.get('suggested_role', '')}
Relevant Experience Level: {profile.get('relevant_experience', '')}
Skills: {', '.join(profile.get('skills', []))}
Professional Summary: {profile.get('summary', '')}

Detailed Work Experience:
{chr(10).join(exp_details)}

Education:
{chr(10).join(edu_details)}"""

    # ------------------------------------------------------------------
    # Draft the email
    # ------------------------------------------------------------------
    draft_messages = [
        {"role": "system", "content": "You are a professional email writer."},
        {
            "role": "user",
            "content": OUTREACH_PROMPT.format(
                profile_summary=profile_summary,
                company=company,
                role=role or "Open position",
                contact_name=best_contact["name"],
                contact_role=best_contact["role"],
                jd_excerpt=jd_text[:1500],
            ),
        },
    ]

    subject = ""
    body = ""
    try:
        result = await call_gemma(draft_messages, fallback_chain="reasoning", require_keys=["subject", "body"])
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        draft_data = json.loads(content.strip())
        subject = draft_data.get("subject", "")
        body = draft_data.get("body", "")
    except Exception as exc:
        errors.append(f"Email draft error: {exc}")
        log.error("outreach_draft_error", job_id=job_id, error=str(exc))

    # ------------------------------------------------------------------
    # Build mailto URI and persist
    # ------------------------------------------------------------------
    primary_email = email_guesses[0]["address"] if email_guesses else ""
    mailto_uri = ""
    if primary_email and subject and body:
        mailto_uri = email_handoff.create_mailto_uri(primary_email, subject, body)

    # Calculate overall confidence
    contact_conf = best_contact.get("confidence", 0)
    email_conf = max((eg.get("confidence", 0) for eg in email_guesses), default=0)
    overall_conf = (contact_conf * 0.6 + email_conf * 0.4) if email_guesses else contact_conf * 0.4

    draft = OutreachDraft(
        job_id=job_id,
        company=company,
        contact_name=best_contact["name"],
        contact_role=best_contact["role"],
        email_guesses=[eg for eg in email_guesses],
        subject=subject,
        body=body,
        mailto_uri=mailto_uri,
        confidence=round(overall_conf, 2),
    )

    draft_dict = draft.model_dump(mode="json")

    # Tag if manual lookup is needed
    if manual_lookup_needed:
        draft_dict["manual_lookup_needed"] = True

    await db.insert_outreach(draft_dict)

    await log_and_broadcast_event(
        "complete",
        f"Outreach draft ready for {best_contact['name']} ({best_contact['role']})"
        + (" — manual contact lookup recommended" if manual_lookup_needed else ""),
        confidence=overall_conf,
        data={
            "contact_role": best_contact["role"],
            "email_count": len(email_guesses),
            "manual_lookup_needed": manual_lookup_needed,
        }
    )

    return {"outreach_draft": draft_dict, "events": events, "errors": errors}
