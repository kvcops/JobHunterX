"""
Vellum OS — Contact Finder Agent

Dedicated agent that accurately searches the web, LinkedIn company pages,
GitHub repos, and public APIs to find relevant hiring contacts or employees
at the target company. If it cannot find reliable contact info, it prompts
the user to find it manually rather than guessing or hallucinating.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import search, email_handoff
from vellum.models import AgentEvent

log = get_logger("contact_finder")


async def scrape_contact_page_emails(domain: str) -> list[dict]:
    """Scrape company contact/about pages for email addresses."""
    from vellum.tools import career_urls, scrape

    if not domain:
        return []

    urls = career_urls.get_contact_urls_for_domain(domain)
    all_emails = []

    for url in urls:
        try:
            page = await scrape.fetch_page(url)
            html = page.get("html", "")
            if not html:
                continue

            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                html
            )
            clean_emails = [
                e for e in emails
                if not e.endswith(('.png', '.jpg', '.gif', '.mp4', '.svg'))
                and not e.startswith(('noreply', 'no-reply', 'donotreply'))
            ]

            for email in clean_emails:
                all_emails.append({
                    "address": email,
                    "pattern": "contact_page",
                    "confidence": 0.6,
                    "source_url": url,
                })
        except Exception:
            continue

    return all_emails[:10]


async def google_dork_for_emails(company: str, domain: str) -> list[dict]:
    """Use Google dorks to find company email addresses."""

    queries = [
        f'"@" + "{domain}" site:linkedin.com',
        f'"{company}" "email" "recruiter"',
        f'site:{domain} "contact" OR "email"',
    ]

    all_emails = []
    seen = set()

    for query in queries:
        try:
            results = await search.search_multi_engine(query, max_results=3)
            for r in results:
                body = r.get("body", "") + " " + r.get("title", "")
                emails = re.findall(
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                    body
                )
                for email in emails:
                    if email not in seen and not email.endswith(('.png', '.jpg', '.gif')):
                        seen.add(email)
                        all_emails.append({
                            "address": email,
                            "pattern": "google_dork",
                            "confidence": 0.5,
                            "source_url": r.get("href", ""),
                        })
        except Exception:
            continue

    return all_emails[:5]


async def extract_github_emails(company_slug: str) -> list[dict]:
    """Extract emails from GitHub organization member commits."""
    import httpx

    if not company_slug:
        return []

    org_name = company_slug.replace("-", "").replace("_", "")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            repos_resp = await client.get(
                f"https://api.github.com/orgs/{org_name}/repos?sort=updated&per_page=3"
            )
            if repos_resp.status_code != 200:
                return []

            repos = repos_resp.json()
            emails = []
            seen = set()

            for repo in repos:
                commits_resp = await client.get(
                    f"https://api.github.com/repos/{org_name}/{repo['name']}/commits?per_page=3"
                )
                if commits_resp.status_code != 200:
                    continue

                commits = commits_resp.json()
                for commit in commits:
                    author = commit.get("commit", {}).get("author", {})
                    email = author.get("email", "")
                    name = author.get("name", "")

                    if (email
                        and email not in seen
                        and "noreply" not in email
                        and "github.com" not in email):
                        seen.add(email)
                        emails.append({
                            "address": email,
                            "pattern": "github_commit",
                            "confidence": 0.4,
                            "name": name,
                            "source_url": f"https://github.com/{org_name}",
                        })

                if len(emails) >= 5:
                    break

            return emails
    except Exception:
        return []


CONTACT_EXTRACTION_PROMPT = """You are analyzing web search results to find real hiring contacts at a company.

Company: {company}
Role being applied for: {role}

Search Results:
{search_results}

CRITICAL RULES:
1. Only extract contacts that are CLEARLY mentioned in the search results with their REAL names and roles.
2. Do NOT invent or guess any names. If a name is not clearly stated in the results, do NOT include it.
3. Prioritize: Hiring Managers > Engineering Managers > Recruiters > Founders/CTOs > HR Team.
4. Include the source URL where you found each contact.
5. Set confidence based on how clearly the person is identified:
   - 0.8-1.0: Full name + role clearly stated on company page or LinkedIn
   - 0.5-0.7: Name found but role is inferred
   - 0.3-0.5: Name found on a third-party source
   - Below 0.3: Do NOT include — too unreliable

Return a JSON object:
{{
  "contacts": [
    {{"name": "Full Name", "role": "Their Title", "source_url": "URL where found", "confidence": 0.8}}
  ],
  "company_domain": "company.com or empty string if unknown",
  "manual_lookup_needed": true/false
}}

If you cannot find ANY reliable contacts with confidence >= 0.3, set "contacts" to an empty array and "manual_lookup_needed" to true.

Return valid JSON only. No markdown."""


async def run(state: dict) -> dict:
    """Contact Finder: search for real hiring contacts at the target company.

    Input state: {"job": dict, "profile": dict}
    Output: updates with contact_result, events
    """
    job = state.get("job", {})
    profile = state.get("profile", {})
    job_id = job.get("id", "")
    company = job.get("company", "")
    role = job.get("role", "")
    events: list[dict] = []
    errors: list[str] = []

    from vellum.api.ws import manager as ws_manager

    async def log_and_broadcast_event(event_type: str, message: str, confidence: float = 0.0, data: dict = None):
        evt = AgentEvent(
            agent="contact_finder",
            event_type=event_type,
            job_id=job_id,
            message=message,
            confidence=confidence,
            data=data
        ).model_dump(mode="json")
        events.append(evt)
        await ws_manager.broadcast(evt)

    await log_and_broadcast_event("progress", f"Searching for hiring contacts at {company}")

    # ------------------------------------------------------------------
    # Step 1: Multi-source search for contacts
    # ------------------------------------------------------------------
    all_search_results = []

    # Search queries targeting different sources
    search_queries = [
        f"{company} hiring manager {role} site:linkedin.com",
        f"{company} recruiter engineering team",
        f"{company} careers team leadership",
        f"{company} CTO founder engineering",
    ]

    for query in search_queries:
        try:
            results = await search.search_multi_engine(query, max_results=5)
            for r in results:
                title = r.get("title", "")
                snippet = r.get("body", "") or r.get("snippet", "")
                href = r.get("href") or r.get("link", "")
                all_search_results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {href}")
        except Exception as exc:
            log.warning("contact_search_failed", query=query, error=str(exc))

    # Also try GitHub org search
    try:
        gh_results = await search.search_multi_engine(f"{company} site:github.com", max_results=3)
        for r in gh_results:
            all_search_results.append(f"GitHub: {r.get('title', '')} — {r.get('href', '')}")
    except Exception:
        pass

    if not all_search_results:
        await log_and_broadcast_event(
            "progress",
            f"Could not find contacts for {company}. Manual lookup needed.",
            data={"manual_lookup_needed": True}
        )
        return {
            "contact_result": {
                "contacts": [],
                "company_domain": "",
                "manual_lookup_needed": True,
            },
            "events": events,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Step 2: LLM extraction of contacts from search results
    # ------------------------------------------------------------------
    search_block = "\n---\n".join(all_search_results[:20])  # Cap to avoid token overflow

    messages = [
        {"role": "system", "content": "You are a professional contact research analyst."},
        {
            "role": "user",
            "content": CONTACT_EXTRACTION_PROMPT.format(
                company=company,
                role=role or "Software Engineer",
                search_results=search_block[:6000],
            ),
        },
    ]

    contact_result = {"contacts": [], "company_domain": "", "manual_lookup_needed": True}

    try:
        result = await call_llm_with_fallback("fast", messages)
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        contact_result = json.loads(content.strip())
    except Exception as exc:
        errors.append(f"Contact extraction error: {exc}")
        log.error("contact_extraction_error", job_id=job_id, error=str(exc))

    # ------------------------------------------------------------------
    # Step 3: Determine company domain for email permutation
    # ------------------------------------------------------------------
    domain = contact_result.get("company_domain", "")

    if not domain:
        career_url = job.get("career_page_url", "")
        if career_url:
            parsed = urlparse(career_url)
            domain = parsed.netloc.replace("www.", "")
            ats_strip = [
                "boards.greenhouse.io", "jobs.lever.co", "jobs.ashbyhq.com",
                "myworkdayjobs.com", "smartrecruiters.com", "bamboohr.com",
                "recruitee.com", "breezy.hr", "freshteam.com", "zoho.com"
            ]
            for ats in ats_strip:
                if ats in domain:
                    domain = ""
                    break

    if not domain and company:
        try:
            results = await search.search_multi_engine(f"{company} official website", max_results=3)
            for r in results:
                url = r.get("href") or r.get("link", "")
                if url:
                    parsed = urlparse(url)
                    d = parsed.netloc.replace("www.", "")
                    is_ats = any(ats in d for ats in search.ATS_DOMAINS)
                    is_penalty = any(p in d for p in search.PENALTY_DOMAINS)
                    if not is_ats and not is_penalty:
                        domain = d
                        break
        except Exception:
            pass

    if not domain and company:
        company_slug = re.sub(r"[^a-z0-9]", "", company.lower())
        domain = f"{company_slug}.com"

    contact_result["company_domain"] = domain

    # ------------------------------------------------------------------
    # Step 4: Multi-method email finding waterfall
    # ------------------------------------------------------------------
    contacts = contact_result.get("contacts", [])
    email_guesses_all = []

    # Method 1: ATS page email (already checked in step 1)

    # Method 2: Contact page scraping
    if domain:
        contact_emails = await scrape_contact_page_emails(domain)
        email_guesses_all.extend(contact_emails)

    # Method 3: Email permutation for found contacts
    if contacts and not email_guesses_all:
        best_contact = contacts[0]
        name_parts = best_contact["name"].split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        if domain and first_name and first_name.lower() not in ["hiring", "recruiting", "team"]:
            email_guesses_all = email_handoff.generate_email_permutations(first_name, last_name, domain)

    # Method 4: Google dorking
    if not email_guesses_all:
        dork_emails = await google_dork_for_emails(company, domain)
        email_guesses_all.extend(dork_emails)

    # Method 5: GitHub commit emails
    if not email_guesses_all:
        gh_emails = await extract_github_emails(company)
        email_guesses_all.extend(gh_emails)

    # Add generic fallback emails
    if domain:
        generic_emails = [
            f"careers@{domain}",
            f"jobs@{domain}",
            f"hr@{domain}",
            f"info@{domain}",
        ]
        seen = {eg["address"].lower() for eg in email_guesses_all}
        for g_email in generic_emails:
            if g_email.lower() not in seen:
                email_guesses_all.append({
                    "address": g_email,
                    "pattern": "generic_fallback",
                    "confidence": 0.20,
                    "mx_valid": None,
                    "unverified_guess": True,
                })

        # MX validation
        email_guesses_all = await email_handoff.enrich_with_mx(email_guesses_all)

        # SMTP verification for top guesses
        if hasattr(email_handoff, "smtp_verify"):
            email_guesses_all = await email_handoff.smtp_verify(email_guesses_all)

    # Log contacts found
    if contacts:
        best_contact = contacts[0]
        await log_and_broadcast_event(
            "progress",
            f"Found: {best_contact['name']} ({best_contact['role']}) — confidence {best_contact.get('confidence', 0):.0%}",
            confidence=best_contact.get("confidence", 0)
        )
    else:
        await log_and_broadcast_event(
            "progress",
            f"No reliable contacts found for {company}. Please find contacts manually.",
            data={"manual_lookup_needed": True}
        )

    contact_result["email_guesses"] = email_guesses_all

    await log_and_broadcast_event(
        "complete",
        f"Contact search complete for {company}" + (
            f" — found {len(contacts)} contact(s)" if contacts
            else " — manual lookup recommended"
        ),
        confidence=contacts[0].get("confidence", 0) if contacts else 0,
        data={"contact_count": len(contacts), "email_count": len(email_guesses_all)}
    )

    return {"contact_result": contact_result, "events": events, "errors": errors}
