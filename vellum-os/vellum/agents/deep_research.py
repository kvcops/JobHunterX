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

    from vellum.api.ws import manager as ws_manager

    async def log_and_broadcast_event(event_type: str, message: str, confidence: float = 0.0, data: dict = None):
        evt = AgentEvent(
            agent="deep_research",
            event_type=event_type,
            job_id=job_id,
            message=message,
            confidence=confidence,
            data=data
        ).model_dump(mode="json")
        events.append(evt)
        await ws_manager.broadcast(evt)

    await log_and_broadcast_event("progress", f"Researching contacts at {company}")

    # ------------------------------------------------------------------
    # Step 1: Find contacts (role-priority)
    # ------------------------------------------------------------------
    location = profile.get("location", "")
    contacts = await search.search_contacts(company, location)

    if not contacts:
        await log_and_broadcast_event("progress", "No specific contacts found. Falling back to generic company contact...")
        best_contact = {
            "name": "Hiring Manager",
            "role": "Hiring Team",
            "confidence": 0.40,
        }
    else:
        best_contact = contacts[0]
        await log_and_broadcast_event(
            "progress",
            f"Found: {best_contact['name']} ({best_contact['role']}) — confidence {best_contact['confidence']:.0%}",
            confidence=best_contact["confidence"]
        )

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
            "myworkdayjobs.com", "smartrecruiters.com", "bamboohr.com",
            "recruitee.com", "breezy.hr", "freshteam.com", "zoho.com"
        ]
        for ats in ats_strip:
            if ats in domain:
                domain = ""
                break

    # If domain is not resolved, search for the official website domain
    if not domain and company:
        await log_and_broadcast_event("progress", f"Searching for {company} official website domain...")
        search_query = f"{company} official website"
        try:
            results = await search.search_multi_engine(search_query, max_results=3)
            for r in results:
                url = r.get("href") or r.get("link", "")
                if url:
                    parsed = urlparse(url)
                    d = parsed.netloc.replace("www.", "")
                    # Filter out penalised domains and ATS domains
                    is_ats = any(ats in d for ats in search.ATS_DOMAINS)
                    is_penalty = any(p in d for p in search.PENALTY_DOMAINS)
                    if not is_ats and not is_penalty:
                        domain = d
                        await log_and_broadcast_event("progress", f"Determined company domain from search: {domain}")
                        break
        except Exception as exc:
            log.warning("failed_to_resolve_domain_via_search", error=str(exc))

    if not domain and company:
        # Fall back to slug.com
        company_slug = re.sub(r"[^a-z0-9]", "", company.lower())
        domain = f"{company_slug}.com"
        await log_and_broadcast_event("progress", f"Using fallback company domain: {domain}")

    # Try to extract name parts
    name_parts = best_contact["name"].split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""

    email_guesses = []
    if domain:
        # Generate contact name permutations if we have a real first name
        if first_name and first_name.lower() not in ["hiring", "recruiting", "team"]:
            email_guesses = email_handoff.generate_email_permutations(first_name, last_name, domain)

        # Always append general fallback emails
        generic_emails = [
            f"careers@{domain}",
            f"jobs@{domain}",
            f"hr@{domain}",
            f"info@{domain}",
            f"contact@{domain}",
        ]
        
        seen_addresses = {eg["address"].lower() for eg in email_guesses}
        for g_email in generic_emails:
            if g_email.lower() not in seen_addresses:
                email_guesses.append({
                    "address": g_email,
                    "pattern": "generic_fallback",
                    "confidence": 0.20,
                    "mx_valid": None,
                    "unverified_guess": True,
                })
        
        # Enrich all permutations (including fallbacks) with MX validation
        email_guesses = await email_handoff.enrich_with_mx(email_guesses)

        # If MX check fails for the primary email, note it in logs
        if email_guesses and email_guesses[0].get("mx_valid") is False:
            await log_and_broadcast_event(
                "progress",
                f"Warning: {domain} has no MX records — emails may not be deliverable"
            )
    else:
        await log_and_broadcast_event("progress", "Could not determine company email domain")

    # ------------------------------------------------------------------
    # Step 3: Draft outreach email
    # ------------------------------------------------------------------
    # Generate full candidate memory summary
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
Present Address: {profile.get('present_address', '')}
Permanent Address: {profile.get('permanent_address', '')}
Suggested Role: {profile.get('suggested_role', '')}
Relevant Experience Level: {profile.get('relevant_experience', '')}
Languages: {', '.join(profile.get('languages', [])) if isinstance(profile.get('languages'), list) else profile.get('languages', '')}
Skills: {', '.join(profile.get('skills', []))}
Professional Summary: {profile.get('summary', '')}

Detailed Work Experience:
{chr(10).join(exp_details)}

Education:
{chr(10).join(edu_details)}"""

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

    await log_and_broadcast_event(
        "complete",
        f"Outreach draft ready for {best_contact['name']} ({best_contact['role']})",
        confidence=overall_conf,
        data={"contact_role": best_contact["role"], "email_count": len(email_guesses)}
    )

    return {"outreach_draft": draft_dict, "events": events, "errors": errors}
