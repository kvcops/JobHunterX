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
            score -= 0.6
            break

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
