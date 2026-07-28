"""
Vellum OS — Search Tool (ddgs 7.x — replaces broken googlesearch-python)

Multi-source search with URL scoring for career-page discovery,
direct ATS job search, and role-priority contact search.
All stdout/stderr from ddgs internal engines is completely silenced.
"""

from __future__ import annotations

import sys
import io
import contextlib
import re
from typing import Optional
from urllib.parse import urlparse

from vellum.config.logging import get_logger

log = get_logger("search")


@contextlib.contextmanager
def silence_stdout_stderr():
    """Intercept and silence raw prints/logs emitted by ddgs or third-party engines."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


# ---------------------------------------------------------------------------
# URL scoring for career-page quality
# ---------------------------------------------------------------------------

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
    "hirect.in", "apna.co", "safalta.com", "freshersworld.com",
    "consultancy", "placement",
}


async def fetch_hasjob_jobs(max_results: int = 15) -> list[dict]:
    """Fetch live tech jobs from Hasjob RSS/Atom feed (hasjob.co)."""
    import httpx
    from bs4 import BeautifulSoup

    url = "https://hasjob.co/feed"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                res = await client.get("https://hasjob.co/")
                if res.status_code != 200:
                    return []
            soup = BeautifulSoup(res.text, "xml" if "xml" in res.headers.get("content-type", "") else "html.parser")
            items = soup.find_all(["item", "entry", "div"], class_=re.compile(r"job|post", re.I)) if not soup.find_all("item") else soup.find_all("item")

            parsed = []
            for item in items[:max_results]:
                title = item.find(["title", "h2", "a"])
                t_str = title.get_text(strip=True) if title else ""
                link = item.find("link")
                href = link.get_text(strip=True) if link and link.string else (link.get("href") if link else "")
                desc = item.find(["description", "summary", "p"])
                d_str = desc.get_text(strip=True) if desc else t_str

                if t_str and len(t_str) > 3:
                    parsed.append({
                        "company": "Indian Tech Startup",
                        "title": t_str,
                        "apply_url": href or "https://hasjob.co/",
                        "career_page_url": "https://hasjob.co/",
                        "location": "India",
                        "jd_text": d_str,
                        "ats_source": "hasjob",
                        "confidence": 0.92,
                    })
            log.info("hasjob_feed_success", count=len(parsed))
            return parsed
    except Exception as exc:
        log.warning("hasjob_feed_failed", error=str(exc)[:100])
        return []


async def search_wellfound_instahyre_jobs(role: str, location: str, max_results: int = 10) -> list[dict]:
    """Search for public search-indexed job pages on Wellfound India & Instahyre."""
    queries = [
        f'"{role}" "{location}" site:wellfound.com/company',
        f'"{role}" "{location}" site:instahyre.com/jobs-at',
    ]
    found = []
    seen_urls = set()

    for q in queries:
        results = await search_multi_engine(q, max_results=5)
        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = r.get("title", "")
            snippet = r.get("body", "")

            # Extract company name from title
            comp = title.split(" - ")[0].split(" | ")[0].replace("Jobs at", "").strip()

            found.append({
                "url": url,
                "title": title,
                "company": comp or "Indian Startup",
                "snippet": snippet,
                "score": 0.85,
                "source": "search_indexed_portals",
            })
            if len(found) >= max_results:
                break
        if len(found) >= max_results:
            break
    log.info("search_indexed_portals_complete", count=len(found))
    return found


async def search_unadvertised_social_posts(
    role: str = "Software Engineer",
    location: str = "Bengaluru",
    max_results: int = 10,
) -> list[dict]:
    """Mine unadvertised social hiring posts for direct email applications."""
    queries = [
        f'site:linkedin.com/posts "hiring" "{role}" "{location}" "send resume to"',
        f'site:linkedin.com/posts "hiring" "{role}" "{location}" "email your CV"',
        f'site:linkedin.com/posts "hiring" "{role}" "{location}" "email me at"',
        f'site:x.com "{role}" "{location}" "hiring" "email"',
    ]

    found_posts = []
    seen_urls = set()

    for q in queries:
        results = await search_multi_engine(q, max_results=5)
        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            body = r.get("body", "")
            title = r.get("title", "")
            combined_text = f"{title} {body}"

            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", combined_text)
            clean_emails = [e for e in emails if not e.endswith(".png") and not e.endswith(".jpg")]

            valid_email = ""
            for email in clean_emails:
                if await verify_email_mx(email):
                    valid_email = email
                    break

            company = title.split(" - ")[0].split(" | ")[0].strip()

            found_posts.append({
                "url": url,
                "title": title,
                "snippet": body[:300],
                "company": company[:60],
                "contact_email": valid_email or (clean_emails[0] if clean_emails else ""),
                "is_mx_verified": bool(valid_email),
                "low_competition": True,
                "source": "social_post_miner",
            })

            if len(found_posts) >= max_results:
                break

        if len(found_posts) >= max_results:
            break

    log.info("social_post_miner_complete", found=len(found_posts))
    return found_posts

CAREER_PATH_PATTERNS = re.compile(
    r"/(careers?|jobs?|openings?|positions?|apply|join-us|work-with-us|vacancies)",
    re.IGNORECASE,
)

NOISE_PATTERNS = re.compile(
    r"/(news|blog|article|press|about|wiki|review)", re.IGNORECASE
)


def score_career_url(url: str, company_name: str = "") -> float:
    """Score a URL for career-page relevance. Higher = better. Range ~0.0–1.0."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.lower()
    score = 0.5

    for ats in ATS_DOMAINS:
        if ats in domain:
            score += 0.3
            break

    if CAREER_PATH_PATTERNS.search(path):
        score += 0.25

    if company_name:
        slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
        if slug and slug in domain:
            score += 0.15

    for penalty in PENALTY_DOMAINS:
        if penalty in domain:
            return 0.0

    if NOISE_PATTERNS.search(path):
        score -= 0.3

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Career-page search
# ---------------------------------------------------------------------------

async def search_career_pages(company_name: str, max_results: int = 8) -> list[dict]:
    """Search for a company's career page using DuckDuckGo."""
    import asyncio
    from ddgs import DDGS

    query = f"{company_name} careers jobs apply"

    def _search():
        with silence_stdout_stderr():
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            except Exception:
                return []

    raw_results = await asyncio.to_thread(_search)
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


async def search_direct_ats_jobs(role: str, location: str, max_results: int = 10) -> list[dict]:
    """Search for direct job listings on known ATS platforms (Greenhouse, Lever, Ashby)."""
    import asyncio
    from ddgs import DDGS

    queries = [
        f'"{role}" "{location}" site:boards.greenhouse.io',
        f'"{role}" "{location}" site:jobs.lever.co',
        f'"{role}" "{location}" site:jobs.ashbyhq.com',
    ]

    def _search(q):
        with silence_stdout_stderr():
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(q, max_results=5))
            except Exception:
                return []

    raw_results = []
    for q in queries:
        res = await asyncio.to_thread(_search, q)
        raw_results.extend(res)
        if len(raw_results) >= max_results:
            break

    parsed = []
    seen_urls = set()
    for r in raw_results:
        url = r.get("href") or r.get("link", "")
        title = r.get("title", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        domain_match = re.search(r"(?:boards\.greenhouse\.io|jobs\.lever\.co|jobs\.ashbyhq\.com)/([^/]+)", url)
        if domain_match:
            slug = domain_match.group(1).replace("-", " ").strip()
            if slug and slug.lower() not in ["jobs", "careers", "apply", "search"]:
                company = slug.title()
            else:
                continue
        else:
            continue

        clean_title = re.sub(r"(?i)\s*(careers?|jobs?|greenhouse|lever|ashby|hiring).*", "", title).strip()
        parsed.append({
            "url": url,
            "title": clean_title or title,
            "company": company,
            "snippet": r.get("body", ""),
            "score": 0.88,
        })
    log.info("direct_ats_search_success", role=role, location=location, count=len(parsed))
    return parsed



# ---------------------------------------------------------------------------
# Contact search (role-priority)
# ---------------------------------------------------------------------------

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
    """Search for contacts at a company, prioritising HMs/EMs over founders."""
    import asyncio
    import json
    from ddgs import DDGS
    from vellum.config.llm_router import call_llm_with_fallback

    contacts = []
    seen_urls = set()

    CONTACT_PARSER_PROMPT = """You are an expert recruitment parser. Extract the clean, real name of the person from the search result.

Company: {company_name}
Target Role Type: {target_role}

Search Result:
- Title: {title}
- Snippet: {snippet}
- URL: {url}

CRITICAL RULES:
1. The name MUST be a real person's name (e.g., "John Doe", "Vamsi Krishna").
2. The name MUST NOT be a job title, location, or generic phrase (e.g. "Engineering Manager", "Hyderabad", "LinkedIn").
3. Make sure the person actually works or worked at {company_name} in a recruiting, engineering manager, or leadership capacity.

Return a JSON object:
{{
  "name": "Person's Name (or empty string if not a real person)",
  "role": "Their exact title (or empty string)",
  "is_valid": true/false
}}
Return valid JSON only. No markdown formatting or commentary."""

    for role in CONTACT_ROLES:
        query = f'{company_name} "{role}" {location} site:linkedin.com/in'

        def _search(q=query):
            with silence_stdout_stderr():
                try:
                    with DDGS() as ddgs:
                        return list(ddgs.text(q, max_results=3))
                except Exception:
                    return []

        results = await asyncio.to_thread(_search)

        for r in results:
            url = r.get("href") or r.get("link", "")
            if not url or url in seen_urls:
                continue
            if "linkedin.com/in/" not in url:
                continue
            seen_urls.add(url)

            title = r.get("title", "")
            snippet = r.get("body", "") or r.get("snippet", "")

            # Use LLM to verify and clean the contact name and role
            messages = [
                {"role": "system", "content": "You are a recruitment parsing assistant."},
                {
                    "role": "user",
                    "content": CONTACT_PARSER_PROMPT.format(
                        company_name=company_name,
                        target_role=role,
                        title=title,
                        snippet=snippet,
                        url=url,
                    )
                }
            ]

            name = ""
            actual_role = role
            is_valid = False
            try:
                res = await call_llm_with_fallback("fast", messages)
                content = res.get("content", "").strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                data = json.loads(content.strip())
                name = data.get("name", "").strip()
                actual_role = data.get("role", "").strip() or role
                is_valid = data.get("is_valid", False)
            except Exception as exc:
                log.debug("llm_contact_parsing_failed", error=str(exc))
                # Fallback to regex if LLM fails
                name_match = re.match(r"^([^–\-|]+)", title)
                name = name_match.group(1).strip() if name_match else ""
                is_valid = len(name) > 2 and "linkedin" not in name.lower()

            if not is_valid or not name:
                continue

            role_idx = CONTACT_ROLES.index(role) if role in CONTACT_ROLES else len(CONTACT_ROLES)
            confidence = max(0.3, 0.8 - (role_idx * 0.06))

            contacts.append({
                "name": name,
                "role": actual_role,
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
        with silence_stdout_stderr():
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            except Exception:
                return []

    results = await asyncio.to_thread(_ddgs)
    if results:
        return results

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
    """Mine unadvertised social hiring posts for direct email applications."""
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

            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", combined_text)
            clean_emails = [e for e in emails if not e.endswith(".png") and not e.endswith(".jpg")]

            valid_email = ""
            for email in clean_emails:
                if await verify_email_mx(email):
                    valid_email = email
                    break

            company = title.split(" - ")[0].split(" | ")[0].strip()

            found_posts.append({
                "url": url,
                "title": title,
                "snippet": body[:300],
                "company": company[:60],
                "contact_email": valid_email or (clean_emails[0] if clean_emails else ""),
                "is_mx_verified": bool(valid_email),
                "low_competition": True,
                "source": "social_post_miner",
            })

            if len(found_posts) >= max_results:
                break

        if len(found_posts) >= max_results:
            break

    log.info("social_post_miner_complete", found=len(found_posts))
    return found_posts
