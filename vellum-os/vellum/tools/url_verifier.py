"""
Vellum OS — Active Job URL & Page Verification Module

Verifies that a discovered job URL:
1. Responds with HTTP 200 OK (no 404, 410, 403, 500, or timeouts).
2. Does NOT redirect to a generic homepage, login page, or search index.
3. Is NOT closed, filled, expired, or no longer accepting applications.
4. Contains authentic Job Description content (minimum length & key JD terms).
"""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from vellum.config.logging import get_logger

log = get_logger("url_verifier")

# HTTP Request Timeout
VERIFY_TIMEOUT = 10.0

# User Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# Strings that indicate a job is closed / expired / non-existent
CLOSED_JOB_PATTERNS = [
    r"no\s+longer\s+available",
    r"position\s+has\s+been\s+filled",
    r"job\s+posting\s+has\s+expired",
    r"this\s+role\s+is\s+(closed|filled)",
    r"no\s+longer\s+accepting\s+applications",
    r"404\s*-\s*not\s+found",
    r"page\s+not\s+found",
    r"job\s+not\s+found",
    r"this\s+posting\s+is\s+unlisted",
    r"search\s+for\s+other\s+jobs",
    r"this\s+job\s+is\s+closed",
    r"job\s+has\s+been\s+removed",
]

# Required JD keywords (at least one must be in text/body if page has text)
MIN_JD_KEYWORDS = [
    "experience", "skills", "responsibilities", "requirements",
    "role", "qualifications", "engineer", "developer", "manager",
    "lead", "description", "apply", "location", "team", "work",
]


async def verify_job_url(url: str, min_text_len: int = 100) -> tuple[bool, str, str]:
    """Verify if a job URL is active, reachable, and contains an active job posting.

    Returns:
        (is_active: bool, reason: str, page_text: str)
    """
    if not url or not url.startswith(("http://", "https://")):
        return False, "Invalid URL format", ""

    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    if path_lower.endswith((".md", ".txt", ".csv", ".json", ".xml", ".rss")):
        return False, "URL points to static index/markdown file, not a job page", ""

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT, follow_redirects=True, headers=headers) as client:
            res = await client.get(url)

            # Check status code
            if res.status_code != 200:
                return False, f"HTTP {res.status_code}", ""

            # Check if redirected to root domain or generic search page
            final_url = str(res.url)
            parsed_final = urlparse(final_url)
            path = parsed_final.path.lower().rstrip("/")

            if not path or path in ("", "/jobs", "/careers", "/search", "/login", "/home"):
                return False, "Redirected to root or generic page", ""

            # Parse page HTML
            html = res.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            page_text = soup.get_text(separator=" ", strip=True)
            text_lower = page_text.lower()

            # Check for closed / expired patterns
            for pat in CLOSED_JOB_PATTERNS:
                if re.search(pat, text_lower):
                    return False, f"Posting expired/closed ('{pat}')", ""

            # Check minimum text length & JD keywords
            if len(page_text) < min_text_len:
                return False, f"Insufficient text content ({len(page_text)} chars)", ""

            has_jd_kw = any(kw in text_lower for kw in MIN_JD_KEYWORDS)
            if not has_jd_kw:
                return False, "Page lacks standard job description keywords", ""

            return True, "Active", page_text[:20000]

    except httpx.TimeoutException:
        return False, "Request timeout (unreachable)", ""
    except Exception as exc:
        return False, f"Connection error: {str(exc)[:100]}", ""


async def filter_active_jobs(jobs: list[dict], max_concurrency: int = 8) -> list[dict]:
    """Filter a batch of job listings, returning ONLY active, reachable postings.
    
    Runs HTTP verification in parallel batches.
    """
    if not jobs:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _check(job: dict) -> dict | None:
        async with semaphore:
            url = job.get("apply_url") or job.get("career_page_url") or ""
            is_active, reason, text = await verify_job_url(url)
            if is_active:
                if text and not job.get("jd_text"):
                    job["jd_text"] = text
                return job
            else:
                log.info("job_link_rejected", company=job.get("company"), title=job.get("title"), url=url, reason=reason)
                return None

    results = await asyncio.gather(*[_check(j) for j in jobs])
    active_jobs = [j for j in results if j is not None]

    log.info("job_verification_complete", total_checked=len(jobs), total_active=len(active_jobs))
    return active_jobs
