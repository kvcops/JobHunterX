"""
Vellum OS — Contact Finder Agent

Dedicated agent that accurately searches the web, LinkedIn company pages,
GitHub repos, and public APIs to find relevant hiring contacts or employees
at the target company. If it cannot find reliable contact info, it prompts
the user to find it manually rather than guessing or hallucinating.
"""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse

from vellum.agents.job_llm_validator import call_gemma
from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import search, email_handoff
from vellum.models import AgentEvent

log = get_logger("contact_finder")

# ---------------------------------------------------------------------------
# Email sanity guards — never surface placeholder/fake addresses
# ---------------------------------------------------------------------------

PLACEHOLDER_DOMAINS = {
    "example.com", "yourdomain.com", "domain.com", "company.com",
    "email.com", "user.com", "mail.com", "test.com", "test.net",
    "acme.com", "yourcompany.com", "mydomain.com", "companyname.com",
    "domain.tld", "sentry.io", "mailinator.com", "yopmail.com",
    "guerrillamail.com", "example.org", "example.net", "somedomain.com",
    "business.com", "sample.com", "demo.com", "demo.org",
}

PLACEHOLDER_LOCALPARTS = {
    "example", "yourname", "your-email", "user", "test", "demo",
    "mail", "email", "yourcompany", "name", "fullname",
}

# Real emails found on pages / in search results get high confidence and
# rank above permutations. Permutations rank above generic fallbacks.
FOUND_PATTERNS = {
    "contact_page", "site_crawl", "job_page", "social_post", "google_dork",
    "github_commit", "wayback", "linkedin_about", "linkedin_profile",
    "person_search",
}


def _is_placeholder_email(address: str) -> bool:
    """Reject emails that are obviously sample/placeholder addresses."""
    if not address or "@" not in address:
        return True
    local, _, domain = address.partition("@")
    domain = domain.lower().strip().lstrip(".")
    local = local.lower().strip()

    # IP-literal or nonsense TLDs
    if not re.match(r"^[a-z0-9.-]+$", domain) or "." not in domain:
        return True

    if domain in PLACEHOLDER_DOMAINS:
        return True
    # RFC 2606/6761 reserved names — never real destinations
    if domain.endswith((".invalid", ".localhost", ".test", ".example")):
        return True
    # e.g. "careers@acme.example.com" style subdomains of placeholder TLDs
    if domain.endswith(".example.com") or domain.endswith(".test"):
        return True
    if any(ph in local for ph in PLACEHOLDER_LOCALPARTS):
        # "hello@..." is fine; "yourname@..." is not
        if local in PLACEHOLDER_LOCALPARTS or local.startswith("your"):
            return True
    if re.search(r"(\d{4,})", local) and not re.search(r"^[a-z0-9]{1,4}\d{4,}$", local):
        return True
    return False


# Local parts that are company ROLE inboxes, not employees — excluded from
# referral/cold-outreach results (user wants PEOPLE, not careers@/info@).
ROLE_LOCALPARTS = {
    "info", "careers", "jobs", "hr", "hrd", "sales", "hello", "support",
    "contact", "contactus", "press", "media", "team", "admin", "admin1",
    "recruiting", "talent", "recruitment", "privacy", "legal", "dpo",
    "marketing", "office", "reception", "help", "enquiries", "inquiries",
    "enquiry", "enquire", "mail", "email", "connect", "getintouch", "work",
    "workwithus", "join", "joinus", "career", "corp", "corporate", "service",
    "services", "query", "queries", "accounts", "info1", "feedback",
    "newsletter", "subscribe", "notice", "operations", "projects", "project",
    "business", "vendor", "partners",
}


def _keep_personal_only(items: list[dict]) -> list[dict]:
    """Drop company role-inboxes (connect@/careers@/admin@) — keep only
    personal-looking addresses and people-derived permutations."""
    kept = []
    for item in items:
        addr = item.get("address", "")
        local = addr.split("@")[0].lower() if "@" in addr else ""
        # 'flast' permutations of real employees are personal by design
        if item.get("pattern") == "permutation" or not local:
            kept.append(item)
            continue
        if local not in ROLE_LOCALPARTS and not local.startswith(("no", "donot")):
            kept.append(item)
    return kept


def _dedupe_emails(items: list[dict]) -> list[dict]:
    """Deduplicate email guesses by address, keeping the highest confidence."""
    best: dict[str, dict] = {}
    for item in items:
        addr = (item.get("address") or "").strip().lower()
        if not addr or _is_placeholder_email(addr):
            continue
        existing = best.get(addr)
        if existing is None or item.get("confidence", 0) > existing.get("confidence", 0):
            best[addr] = item
    return list(best.values())


def rank_email_guesses(items: list[dict]) -> list[dict]:
    """Rank emails: real found emails first, then permutations, generic last.

    Within each tier, higher confidence wins. MX-valid real emails lead.
    """
    def _tier(item: dict) -> int:
        pattern = (item.get("pattern") or "").lower()
        if pattern in FOUND_PATTERNS:
            return 0
        if pattern == "permutation":
            return 1
        return 2

    def _key(item: dict) -> tuple:
        mx = item.get("mx_valid")
        return (
            _tier(item),
            0 if mx is True else (1 if mx is None else 2),
            -float(item.get("confidence", 0) or 0),
        )

    return sorted(items, key=_key)


async def scrape_contact_page_emails(domain: str) -> list[dict]:
    """Scrape company contact/about/team pages for email addresses.

    Delegates to email_enrichment.scrape_company_email_pages which covers the
    email-rich page set (contact, privacy, terms, press, media-kit, newsroom,
    imprint) and also decodes mailto:, JSON-LD ContactPoint and (at)/(dot)
    obfuscation.
    """
    from vellum.tools.email_enrichment import scrape_company_email_pages

    if not domain:
        return []

    found = await scrape_company_email_pages(domain)
    for item in found:
        item["pattern"] = "site_crawl"
    return _dedupe_emails(found)[:10]


async def scrape_job_page_for_emails(apply_url: str, career_page_url: str = "") -> list[dict]:
    """Scrape the job posting page itself for a contact email.

    Many JDs contain "questions about this role? email <x@company.com>"
    lines — these are the most relevant (directly tied to the posting).
    """
    from vellum.tools import scrape

    all_emails = []
    for url in dict.fromkeys(filter(None, [apply_url, career_page_url])):
        try:
            page = await scrape.fetch_page(url)
            html = page.get("html", "")
            if not html:
                continue
            text = re.sub(r"<[^>]+>", " ", html)
            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                text,
            )
            for email in emails:
                if email.endswith(('.png', '.jpg', '.gif', '.svg')):
                    continue
                if email.startswith(('noreply', 'no-reply', 'donotreply')):
                    continue
                all_emails.append({
                    "address": email,
                    "pattern": "job_page",
                    "confidence": 0.85,  # Directly tied to the posting = very relevant
                    "source_url": url,
                })
        except Exception:
            continue
    return _dedupe_emails(all_emails)[:5]


async def search_person_emails(
    people: list[dict],
    company: str,
    domain: str = "",
    location: str = "",
    max_people: int = 4,
) -> list[dict]:
    """People-first email search: for each known employee, web-search
    '"Name" "Company" (<location>)' and harvest any published address.

    The classic Hunter-style flow — names first, then a targeted per-person
    query. One query per person (all parallel) surfaces the emails people
    publish in bios, press pages and directories, and replaces the slow
    full-site crawl as the primary source.
    """
    if not people:
        return []

    loc = location.strip() if location else ""
    seen: set[str] = set()
    emails: list[dict] = []
    sem = asyncio.Semaphore(3)

    async def _query(name: str, query: str) -> None:
        async with sem:
            try:
                results = await search.search_multi_engine(query, max_results=8)
            except Exception:
                return
            for r in results:
                blob = " ".join(filter(None, [
                    r.get("title", ""),
                    r.get("body", "") or r.get("snippet", ""),
                ]))
                for email in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', blob):
                    key = email.lower()
                    if key in seen or _is_placeholder_email(email):
                        continue
                    # Company domain or personal providers only — never a
                    # random third-party domain from a partner listing.
                    if domain and domain not in key and "gmail.com" not in key and "yahoo.com" not in key:
                        continue
                    seen.add(key)
                    emails.append({
                        "address": email,
                        "pattern": "person_search",
                        "confidence": 0.6,
                        "source_url": r.get("href", ""),
                        "name": name,
                        "unverified_guess": False,
                    })

    tasks = []
    for person in people[:max_people]:
        name = (person.get("name") or "").strip()
        if not name or len(name.split()) < 2:
            continue
        query = f'"{name}" "{company}"'
        if loc:
            query += f' "{loc}"'
        tasks.append((name, _query(name, query)))

    await asyncio.gather(*(t for _, t in tasks))

    # Second pass: explicit email keyword for people who surfaced nothing
    if len(emails) < 3:
        for name, _ in tasks:
            query = f'"{name}" "{company}" email'
            if loc:
                query += f' "{loc}"'
            await _query(name, query)

    return _dedupe_emails(emails)[:8]


async def google_dork_for_emails(company: str, domain: str) -> list[dict]:
    """Use search dorks to find real, published company email addresses.

    Research-tested (Aug 2026) high-yield patterns:
    - `site:domain "@domain" -noreply -info` — any published email
    - `"Company" ("press" OR "media") "@domain"` — press pages
    - `site:domain filetype:pdf "@domain"` — press/media kits (richest source;
      a single media kit often lists several real emails)
    """
    queries = []
    if domain:
        queries.extend([
            f'site:{domain} "@{domain}" -noreply -info',
            f'"{company}" "@{domain}" -site:github.com',
            f'"{company}" ("press" OR "media" OR "newsroom") "@{domain}"',
            f'site:{domain} filetype:pdf "@{domain}"',
            f'"{company}" careers email "@{domain}"',
            f'"{company}" hiring manager "@{domain}"',
        ])
    queries.append(f'"{company}" "email us" OR "contact us" OR "reach out at"')

    all_emails = []
    seen = set()
    sem = asyncio.Semaphore(3)

    async def _run_dork(query: str) -> None:
        if len(all_emails) >= 4:
            return  # early exit — enough dork hits already
        async with sem:
            try:
                results = await search.search_multi_engine(query, max_results=5)
            except Exception:
                return
            for r in results:
                body = r.get("body", "") + " " + r.get("title", "")
                href = r.get("href", "")
                emails_found = re.findall(
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                    body,
                )
                for email in emails_found:
                    key = email.lower()
                    if key in seen:
                        continue
                    if _is_placeholder_email(email):
                        continue
                    # Prefer emails on the company's own domain; still allow
                    # gmail/yahoo for small startups where founders use them.
                    if domain and domain not in key and "gmail.com" not in key and "yahoo.com" not in key:
                        continue
                    seen.add(key)
                    all_emails.append({
                        "address": email,
                        "pattern": "google_dork",
                        "confidence": 0.55,
                        "source_url": href,
                    })

    await asyncio.gather(*(_run_dork(q) for q in queries))

    return _dedupe_emails(all_emails)[:5]


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
                        and "github.com" not in email
                        and not _is_placeholder_email(email)):
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

            return _dedupe_emails(emails)
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
    location = job.get("search_location") or job.get("location", "")
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

    # Search queries targeting different sources — all fired CONCURRENTLY
    # (semaphore 3) instead of serially; each query is now ~1 backend round
    # trip thanks to search_multi_engine's early-return.
    search_queries = [
        f"{company} hiring manager {role} site:linkedin.com",
        f"{company} recruiter engineering team",
        f"{company} careers team leadership",
        f"{company} CTO founder engineering",
        f"{company} site:github.com",
    ]
    search_sem = asyncio.Semaphore(3)

    async def _run_query(query: str) -> None:
        async with search_sem:
            try:
                results = await search.search_multi_engine(query, max_results=5)
            except Exception as exc:
                log.warning("contact_search_failed", query=query, error=str(exc))
                return
            for r in results:
                title = r.get("title", "")
                snippet = r.get("body", "") or r.get("snippet", "")
                href = r.get("href") or r.get("link", "")
                if "github.com" in query:
                    all_search_results.append(f"GitHub: {title} — {href}")
                else:
                    all_search_results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {href}")

    await asyncio.gather(*(_run_query(q) for q in search_queries))

    if not all_search_results:
        # No web results — fall back to scraping the job page itself for a
        # contact email before declaring manual lookup needed.
        job_page_emails = await scrape_job_page_for_emails(
            job.get("apply_url", ""), job.get("career_page_url", "")
        )
        email_guesses = rank_email_guesses(
            await email_handoff.enrich_with_mx(_dedupe_emails(job_page_emails))
        )
        await log_and_broadcast_event(
            "progress",
            f"Could not find contacts for {company}. Manual lookup needed."
            + (f" Found {len(email_guesses)} email(s) on the job page." if email_guesses else ""),
            data={"manual_lookup_needed": True, "email_count": len(email_guesses)}
        )
        return {
            "contact_result": {
                "contacts": [],
                "company_domain": "",
                "manual_lookup_needed": True,
                "email_guesses": email_guesses,
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
        result = await call_gemma(messages, fallback_chain="fast", require_keys=["contacts"])
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        contact_result = json.loads(content.strip())
    except Exception as exc:
        errors.append(f"Contact extraction error: {exc}")
        log.error("contact_extraction_error", job_id=job_id, error=str(exc))

    # Normalize LLM output — contacts must be a list of dicts, else treat as none
    raw_contacts = contact_result.get("contacts", [])
    if not isinstance(raw_contacts, list):
        raw_contacts = []
    contacts_clean = [
        c for c in raw_contacts
        if isinstance(c, dict) and c.get("name") and float(c.get("confidence", 0) or 0) >= 0.3
    ]
    contact_result["contacts"] = contacts_clean

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
    # Step 4: Multi-method email finding (all run; results merged & ranked)
    # ------------------------------------------------------------------
    from vellum.tools import email_enrichment

    contacts = contact_result.get("contacts", [])
    email_guesses_all: list[dict] = []

    # Method A: Job posting page itself (most relevant — often has recruiter email)
    job_page_emails = await scrape_job_page_for_emails(
        job.get("apply_url", ""), job.get("career_page_url", "")
    )
    email_guesses_all.extend(job_page_emails)

    # Method B: Company contact/about/team page scraping (expanded page set
    # — contact, privacy, terms, press, media-kit, newsroom — with mailto/JSON-LD/obfuscation decode).
    # Emails on a THIRD-PARTY domain (partner listings like japan-ip-network.com
    # on a client's site) are dropped here — only the company domain and
    # personal providers are outreach targets.
    if domain:
        contact_emails = await scrape_contact_page_emails(domain)
        for item in contact_emails:
            addr = (item.get("address") or "").lower()
            if addr and "@" in addr:
                edomain = addr.split("@")[1]
                if domain not in edomain and "gmail.com" not in edomain and "yahoo.com" not in edomain:
                    continue
            email_guesses_all.append(item)

    # Method C: Keyless LinkedIn — real people names via search + emails from
    # GUEST pages (no login needed): company About section, then each
    # employee's public profile (5-15% publish a personal email). These are
    # the referral/cold-outreach targets.
    linkedin_people_task = asyncio.create_task(email_enrichment.linkedin_company_people(company, role))
    linkedin_url_task = asyncio.create_task(email_enrichment.linkedin_company_url(company))
    linkedin_people = await linkedin_people_task
    contact_result["linkedin_people"] = linkedin_people[:5]
    linkedin_url = await linkedin_url_task
    contact_result["linkedin_company_url"] = linkedin_url
    linkedin_guest_emails = await email_enrichment.linkedin_guest_emails(company, linkedin_url)
    contact_result["linkedin_guest_emails"] = linkedin_guest_emails
    email_guesses_all.extend(linkedin_guest_emails)

    # Method C2: Team-page discovery — companies publish employee LinkedIn
    # profiles on /team /people /about pages. Real names, company-confirmed.
    team_people = []
    if domain:
        team_people = await email_enrichment.scrape_team_linkedin_profiles(domain)
    contact_result["team_people"] = team_people[:10]

    # Merge: team-page people (company-confirmed) first, then search people,
    # then LLM contacts — dedup by LinkedIn URL and name.
    all_people = []
    seen_urls, seen_names = set(), set()
    for person in team_people + linkedin_people + list(contacts):
        purl = (person.get("linkedin_url") or "").lower()
        pname = (person.get("name") or "").strip().lower()
        if purl and purl in seen_urls:
            continue
        if pname and pname in seen_names:
            continue
        seen_urls.add(purl)
        seen_names.add(pname)
        all_people.append(person)

    # Method C3: PEOPLE-FIRST web search — for each known employee, query
    # '"Name" "Company" (<location>)' and harvest published emails directly.
    # The Hunter-style flow: names first, then one targeted query per person
    # (all parallel). Runs concurrently with the LinkedIn profile harvest.
    profile_emails_task = asyncio.create_task(email_enrichment.linkedin_profile_emails(all_people))
    person_emails = await search_person_emails(all_people, company, domain, location)
    contact_result["person_search_emails"] = person_emails
    email_guesses_all.extend(person_emails)
    profile_emails = await profile_emails_task
    contact_result["linkedin_profile_emails"] = profile_emails
    email_guesses_all.extend(profile_emails)

    # Method D: Email permutations — ONLY from a REAL, learned pattern.
    # The pattern is inferred from confirmed personal emails found in the
    # crawl (site/wayback/linkedin), mirroring Hunter's own model: one real
    # 'first.last' address predicts the format >80% of the time. Each
    # discovered employee gets a pattern-informed address. Blind guessing
    # is never done.
    if domain:
        inferred_pattern = email_enrichment.infer_email_pattern(email_guesses_all, domain)
        if inferred_pattern:
            for person in all_people[:5]:
                name_parts = str(person.get("name", "")).split()
                if not name_parts:
                    continue
                perm_emails = email_handoff.generate_email_permutations_with_pattern(
                    name_parts[0], " ".join(name_parts[1:]), domain, inferred_pattern
                )
                if perm_emails:
                    perm_emails[0]["name"] = person.get("name", "")
                    perm_emails[0]["linkedin_url"] = person.get("linkedin_url", "")
                    email_guesses_all.extend(perm_emails)

    # Short-circuit: once ≥2 REAL personal emails are in hand, the slower
    # recovery methods (dorks / GitHub commits / Wayback) rarely add value —
    # skip them. Otherwise run them all in parallel.
    found_personal = [
        e for e in email_guesses_all
        if (e.get("pattern") or "") in FOUND_PATTERNS
        and float(e.get("confidence", 0) or 0) >= 0.6
    ]
    if len(found_personal) < 2:
        # Method E: Search dorking for published emails (incl. PDF press/media kits)
        dork_emails = await google_dork_for_emails(company, domain)
        email_guesses_all.extend(dork_emails)

        # Method F: GitHub commit emails
        gh_emails = await extract_github_emails(company)
        email_guesses_all.extend(gh_emails)

        # Method G: Wayback Machine recovery — deleted contact/press pages often
        # still carry the real emails the live site removed. Free, no key.
        if domain:
            wayback_emails = await email_enrichment.recover_emails_via_wayback(domain)
            email_guesses_all.extend(wayback_emails)

    # NOTE: no generic company-inbox fallbacks (careers@/hr@/info@) are added
    # — this pipeline targets REAL EMPLOYEE emails for referrals/cold
    # outreach, not company contact inboxes. Published role-inboxes found on
    # the site (connect@/admin@/careers@) are dropped from the final list
    # for the same reason.

    # Deduplicate, then MX-check + SMTP-verify the top real candidates
    # (enrich_with_mx internally SMTP-verifies the top MX-valid candidates)
    email_guesses_all = _dedupe_emails(email_guesses_all)
    email_guesses_all = _keep_personal_only(email_guesses_all)

    if email_guesses_all:
        email_guesses_all = await email_handoff.enrich_with_mx(email_guesses_all)

    # Final ranking: real found emails first, permutations next, generic last
    email_guesses_all = rank_email_guesses(email_guesses_all)

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
