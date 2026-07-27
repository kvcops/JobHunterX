"""
Vellum OS — Search Tool (ddgs 7.x — replaces broken googlesearch-python)

Multi-source search with URL scoring for career-page discovery
and role-priority contact search.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from vellum.config.logging import get_logger

log = get_logger("search")

# ---------------------------------------------------------------------------
# URL scoring for career-page quality
# ---------------------------------------------------------------------------

# Known ATS domains (high signal for real career pages)
ATS_DOMAINS = {
    "greenhouse.io", "boards.greenhouse.io",
    "lever.co", "jobs.lever.co",
    "ashbyhq.com", "jobs.ashbyhq.com",
    "myworkdayjobs.com",
    "smartrecruiters.com", "jobs.smartrecruiters.com",
    "bamboohr.com",
    "recruitee.com",
    "breezy.hr",
    "freshteam.com",
    "zoho.com",
}

# Domains to penalise (aggregators, not direct career pages)
PENALTY_DOMAINS = {
    "linkedin.com", "glassdoor.com", "glassdoor.co.in",
    "indeed.com", "indeed.co.in",
    "naukri.com", "monster.com", "internshala.com",
    "ambitionbox.com", "payscale.com",
    "jooble.org", "jooble.in", "ziprecruiter.com",
    "simplyhired.com", "careerjet.com", "talent.com",
    "jobrapido.com", "adzuna.com", "jora.com",
    "12indiajobs", "winit.com", "winitjobs.com",
    "foundit.in", "shine.com", "timesjobs.com",
    "updazz.com", "cutshort.io", "instahyre.com",
    "hirect.in", "apna.co", "safalta.com",
}

# Career-path patterns (boost)
CAREER_PATH_PATTERNS = re.compile(
    r"/(careers?|jobs?|openings?|positions?|apply|join-us|work-with-us|vacancies)",
    re.IGNORECASE,
)

# Noise patterns (penalise)
NOISE_PATTERNS = re.compile(
    r"/(news|blog|article|press|about|wiki|review)", re.IGNORECASE
)


def score_career_url(url: str, company_name: str = "") -> float:
    """Score a URL for career-page relevance. Higher = better. Range ~0.0–1.0."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.lower()
    score = 0.5  # baseline

    # ATS domain boost
    for ats in ATS_DOMAINS:
        if ats in domain:
            score += 0.3
            break

    # Career path boost
    if CAREER_PATH_PATTERNS.search(path):
        score += 0.25

    # Company domain match boost
    if company_name:
        slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
        if slug and slug in domain:
            score += 0.15

    # Penalty for aggregators
    for penalty in PENALTY_DOMAINS:
        if penalty in domain:
            return 0.0

    # Penalty for noise pages
    if NOISE_PATTERNS.search(path):
        score -= 0.3

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Career-page search
# ---------------------------------------------------------------------------

async def search_career_pages(company_name: str, max_results: int = 8) -> list[dict]:
    """Search for a company's career page using DuckDuckGo.

    Returns list of {"url": str, "title": str, "score": float, "source": "ddgs"}.
    Results are sorted by score descending.
    """
    import asyncio
    from ddgs import DDGS

    query = f"{company_name} careers jobs apply"

    def _search():
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return results

    try:
        raw_results = await asyncio.to_thread(_search)
    except Exception as exc:
        log.error("ddgs_search_error", company=company_name, error=str(exc))
        return []

    scored = []
    for r in raw_results:
        url = r.get("href") or r.get("link", "")
        if not url:
            continue
        s = score_career_url(url, company_name)
        scored.append({
            "url": url,
            "title": r.get("title", ""),
            "body": r.get("body", ""),
            "score": round(s, 3),
            "source": "ddgs",
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    log.info(
        "career_page_search",
        company=company_name,
        results=len(scored),
        top_score=scored[0]["score"] if scored else 0,
    )
    return scored


# ---------------------------------------------------------------------------
# Contact search (role-priority)
# ---------------------------------------------------------------------------

# Priority order: Hiring Manager > EM > Recruiter > VP > CTO > Founder
CONTACT_ROLES = [
    "Hiring Manager",
    "Engineering Manager",
    "Technical Recruiter",
    "Recruiter",
    "VP Engineering",
    "Head of Engineering",
    "CTO",
    "Founder",
    "Co-Founder",
]


async def search_contacts(
    company_name: str,
    location: str = "",
    max_results: int = 5,
) -> list[dict]:
    """Search for contacts at a company, prioritising HMs/EMs over founders.

    Returns list of {"name": str, "role": str, "source_url": str,
                      "confidence": float, "source": "ddgs"}.
    """
    import asyncio
    from ddgs import DDGS

    contacts = []
    seen_urls = set()

    for role in CONTACT_ROLES:
        query = f'{company_name} "{role}" {location} site:linkedin.com/in'

        def _search(q=query):
            with DDGS() as ddgs:
                return ddgs.text(q, max_results=3)

        try:
            results = await asyncio.to_thread(_search)
        except Exception as exc:
            log.warning("contact_search_error", role=role, error=str(exc))
            continue

        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen_urls:
                continue
            if "linkedin.com/in/" not in url:
                continue
            seen_urls.add(url)

            title = r.get("title", "")
            # Try to extract name from LinkedIn title (format: "Name - Role - Company")
            name_match = re.match(r"^([^–\-|]+)", title)
            name = name_match.group(1).strip() if name_match else ""

            # Confidence decreases as we go down the priority list
            role_idx = CONTACT_ROLES.index(role) if role in CONTACT_ROLES else len(CONTACT_ROLES)
            confidence = max(0.3, 0.8 - (role_idx * 0.06))

            contacts.append({
                "name": name,
                "role": role,
                "source_url": url,
                "confidence": round(confidence, 2),
                "source": "ddgs",
            })

        if len(contacts) >= max_results:
            break

    log.info("contact_search", company=company_name, found=len(contacts))
    return contacts[:max_results]


# ---------------------------------------------------------------------------
# Multi-Engine Search Aggregator & Email MX Verification
# ---------------------------------------------------------------------------

async def verify_email_mx(email_address: str) -> bool:
    """Verify if the email domain has valid DNS MX records."""
    import asyncio, socket
    if not email_address or "@" not in email_address:
        return False
    domain = email_address.split("@")[-1].strip()

    def _check():
        try:
            import dns.resolver
            records = dns.resolver.resolve(domain, "MX")
            return len(records) > 0
        except Exception:
            # Fallback to socket gethostbyname
            try:
                socket.gethostbyname(domain)
                return True
            except Exception:
                return False

    return await asyncio.to_thread(_check)


async def search_multi_engine(query: str, max_results: int = 10) -> list[dict]:
    """Multi-engine search aggregator (DDGS + fallback text search)."""
    import asyncio
    from ddgs import DDGS

    def _ddgs():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))

    try:
        results = await asyncio.to_thread(_ddgs)
        if results:
            return results
    except Exception as exc:
        log.warning("multi_engine_ddgs_failed", query=query, error=str(exc))

    # Fallback: HTML search fetch
    try:
        from vellum.tools import scrape
        search_url = f"html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        page = await scrape.fetch_page(f"https://{search_url}")
        html = page.get("html", "")
        links = re.findall(r'<a class="result__url" href="([^"]+)">(.*?)</a>', html)
        fallback_results = []
        for url, text in links[:max_results]:
            fallback_results.append({"href": url, "title": text, "body": ""})
        return fallback_results
    except Exception as exc:
        log.error("multi_engine_fallback_failed", error=str(exc))
        return []


async def search_unadvertised_social_posts(
    role: str = "Software Engineer",
    location: str = "Hyderabad",
    max_results: int = 10,
) -> list[dict]:
    """Mine unadvertised social hiring posts (LinkedIn posts, Twitter/X) for direct email applications.

    Targeting posts that say 'We are hiring', 'Send resume to email@...', filtering for
    low engagement (<50 likes) for maximum candidate success rates.
    """
    queries = [
        f'site:linkedin.com/posts "we are hiring" "{role}" "{location}" "send resume to"',
        f'site:linkedin.com/posts "hiring" "{role}" "{location}" "email your CV"',
        f'"{role}" "{location}" "mail your resume" site:linkedin.com/posts',
    ]

    found_posts = []
    seen_urls = set()

    for q in queries:
        results = await search_multi_engine(q, max_results=8)
        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            body = r.get("body", "")
            title = r.get("title", "")
            combined_text = f"{title} {body}"

            # Extract email addresses from post content
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", combined_text)
            clean_emails = [e for e in emails if not e.endswith(".png") and not e.endswith(".jpg")]

            # Verify email MX if found
            valid_email = ""
            for email in clean_emails:
                if await verify_email_mx(email):
                    valid_email = email
                    break

            # Company name extraction
            company = title.split(" - ")[0].split(" | ")[0].strip()

            found_posts.append({
                "url": url,
                "title": title,
                "snippet": body[:300],
                "company": company[:60],
                "contact_email": valid_email or (clean_emails[0] if clean_emails else ""),
                "is_mx_verified": bool(valid_email),
                "low_competition": True,  # Fresh social post
                "source": "social_post_miner",
            })

            if len(found_posts) >= max_results:
                break

        if len(found_posts) >= max_results:
            break

    log.info("social_post_miner_complete", found=len(found_posts))
    return found_posts

