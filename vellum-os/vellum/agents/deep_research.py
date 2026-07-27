"""
Vellum OS — Deep Research & Outreach Agent (Agent D)

Per-job: contact search (role-priority) → email permutation → draft email.
Contacts are searched in priority order: HMs > EMs > Recruiters > Founders.
All email guesses labeled as unverified.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import search, email_handoff
from vellum.models import AgentEvent, OutreachDraft

log = get_logger("deep_research")

OUTREACH_PROMPT = """You are writing a professional outreach email from a job candidate to a hiring contact.

The email should:
1. Be concise (under 150 words)
2. Reference the specific role and company
3. Highlight 1-2 relevant skills or experiences from the candidate profile
4. Include a brief, specific insight about the company or role (proof of research)
5. End with a clear, low-friction call to action
6. Be professional but warm — not generic or spammy

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
    """Agent D: Deep research and outreach for a specific job.

    Input state: {"job": dict, "profile": dict}
    Output: updates with outreach_draft, events
    """
    job = state.get("job", {})
    profile = state.get("profile", {})
    job_id = job.get("id", "")
    company = job.get("company", "")
    role = job.get("role", "")
    jd_text = job.get("jd_text", "")
    events: list[dict] = []
    errors: list[str] = []

    events.append(AgentEvent(
        agent="deep_research",
        event_type="progress",
        job_id=job_id,
        message=f"Researching contacts at {company}",
    ).model_dump(mode="json"))

    # ------------------------------------------------------------------
    # Step 1: Find contacts (role-priority)
    # ------------------------------------------------------------------
    location = profile.get("location", "")
    contacts = await search.search_contacts(company, location)

    if not contacts:
        events.append(AgentEvent(
            agent="deep_research",
            event_type="progress",
            job_id=job_id,
            message="No contacts found via search",
        ).model_dump(mode="json"))
        return {"outreach_draft": None, "events": events, "errors": errors}

    # Pick the best contact (first in priority order)
    best_contact = contacts[0]

    events.append(AgentEvent(
        agent="deep_research",
        event_type="progress",
        job_id=job_id,
        message=f"Found: {best_contact['name']} ({best_contact['role']}) — confidence {best_contact['confidence']:.0%}",
        confidence=best_contact["confidence"],
    ).model_dump(mode="json"))

    # ------------------------------------------------------------------
    # Step 2: Email permutation with MX check
    # ------------------------------------------------------------------
    # Extract domain from career page URL
    career_url = job.get("career_page_url", "")
    domain = ""
    if career_url:
        parsed = urlparse(career_url)
        domain = parsed.netloc.replace("www.", "")
        # Strip ATS domains to get company domain
        ats_strip = [
            "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com",
        ]
        for ats in ats_strip:
            if ats in domain:
                domain = ""
                break

    # Try to extract name parts
    name_parts = best_contact["name"].split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""

    email_guesses = []
    if first_name and domain:
        email_guesses = email_handoff.generate_email_permutations(first_name, last_name, domain)
        email_guesses = await email_handoff.enrich_with_mx(email_guesses)

        # If MX check fails, note it
        if email_guesses and email_guesses[0].get("mx_valid") is False:
            events.append(AgentEvent(
                agent="deep_research",
                event_type="progress",
                job_id=job_id,
                message=f"Warning: {domain} has no MX records — emails may not be deliverable",
            ).model_dump(mode="json"))
    else:
        events.append(AgentEvent(
            agent="deep_research",
            event_type="progress",
            job_id=job_id,
            message="Could not determine company email domain",
        ).model_dump(mode="json"))

    # ------------------------------------------------------------------
    # Step 3: Draft outreach email
    # ------------------------------------------------------------------
    profile_summary = f"""Name: {profile.get('name', '')}
Skills: {', '.join(profile.get('skills', [])[:10])}
Recent role: {profile.get('experience', [{}])[0].get('role', '')} at {profile.get('experience', [{}])[0].get('company', '')}"""

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
        result = await call_llm_with_fallback("reasoning", draft_messages)
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
    # Step 4: Build mailto URI and persist
    # ------------------------------------------------------------------
    primary_email = email_guesses[0]["address"] if email_guesses else ""
    mailto_uri = ""
    if primary_email and subject and body:
        mailto_uri = email_handoff.create_mailto_uri(primary_email, subject, body)

    # Calculate overall confidence
    contact_conf = best_contact["confidence"]
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
    await db.insert_outreach(draft_dict)

    events.append(AgentEvent(
        agent="deep_research",
        event_type="complete",
        job_id=job_id,
        message=f"Outreach draft ready for {best_contact['name']} ({best_contact['role']})",
        confidence=overall_conf,
        data={"contact_role": best_contact["role"], "email_count": len(email_guesses)},
    ).model_dump(mode="json"))

    return {"outreach_draft": draft_dict, "events": events, "errors": errors}
