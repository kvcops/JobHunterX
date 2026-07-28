"""
Vellum OS — Scraping Tool (3-tier: BS4 → trafilatura → ScrapeGraphAI)

Deterministic HTML parsing first, LLM fallback only when necessary.
Also includes best-effort freshness detection with confidence scoring.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from vellum.config.logging import get_logger

log = get_logger("scrape")

# Link texts that are clearly navigation/section headers, not job postings
NON_JOB_LINK_TEXTS = {
    "hiring journey", "using ai", "work environment", "benefits",
    "working here", "career areas", "search for jobs", "job search",
    "job categories", "categories", "remote jobs", "executive jobs",
    "jobs by location", "jobs by city", "department", "teams",
    "life at", "culture", "values", "diversity", "apply now",
    "view all jobs", "all jobs", "featured jobs", "recommended jobs",
    "relevance", "date posted", " العربية", "english", "hindi",
    "job alerts", "create alert", "save search", "recent searches",
    "startup jobs", "frontend developer jobs", "ios development jobs",
    "android developer jobs", "it jobs", "technology jobs",
    "product jobs", "design jobs", "marketing jobs", "sales jobs",
    "engineering jobs", "data science jobs",
}

# Known bad aggregator domains — their "job links" are category pages
BAD_AGGREGATOR_DOMAINS = {
    "12indiajobs", "12jobsindia", "winit", "jooble",
    "careerjet", "jobrapido", "adzuna", "jora", "talent",
}


def _is_non_job_link(url: str, text: str) -> bool:
    """Check if a link is navigation/category, not an actual job posting."""
    text_lower = text.lower().strip()

    # Empty or very short text
    if not text_lower or len(text_lower) < 4:
        return True

    # Known non-job phrases
    if text_lower in NON_JOB_LINK_TEXTS:
        return True
    for prefix in ("jobs in", "jobs at", "all jobs", "view all", "browse "):
        if text_lower.startswith(prefix):
            return True
    for suffix in (" jobs", " careers", " openings"):
        if text_lower.endswith(suffix) and len(text_lower) < 30:
            return True

    # URL patterns that are clearly category/navigation pages
    url_lower = url.lower()
    category_patterns = [
        "/category/", "/department/", "/team/", "/location/",
        "/language/", "/remote/", "/country/", "/city/",
    ]
    for pat in category_patterns:
        if pat in url_lower:
            return True

    # Bad aggregator domains
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    for bad in BAD_AGGREGATOR_DOMAINS:
        if bad in domain:
            return True

    return False


# ---------------------------------------------------------------------------
# Known ATS CSS selectors for deterministic link extraction (Tier 1)
# ---------------------------------------------------------------------------

ATS_SELECTORS = {
    "greenhouse": [
        'a[href*="boards.greenhouse.io"]',
        'a[href*="greenhouse.io/embed/job"]',
        'div.opening a',
    ],
    "lever": [
        'a[href*="jobs.lever.co"]',
        'a.posting-title',
        'div.posting a[href*="/apply"]',
    ],
    "ashby": [
        'a[href*="jobs.ashbyhq.com"]',
        'a[href*="/apply"]',
    ],
    "workday": [
        'a[href*="myworkdayjobs.com"]',
        'a[href*="workday.com"]',
    ],
    "generic": [
        'a[href*="/apply"]',
        'a[href*="/jobs/"]',
        'a[href*="/careers/"]',
        'a[href*="/openings/"]',
        'a[href*="/positions/"]',
    ],
}

# ---------------------------------------------------------------------------
# Tier 1: Deterministic HTML parsing (BS4 + CSS selectors + regex)
# ---------------------------------------------------------------------------

async def extract_apply_links_deterministic(html: str, base_url: str = "") -> list[dict]:
    """Extract job application links using BeautifulSoup + known ATS selectors.

    Returns list of {"url": str, "text": str, "method": "deterministic",
                      "confidence": 0.9, "ats_type": str}.
    """
    if not html or not html.strip():
        return []

    import asyncio
    from urllib.parse import urljoin

    def _parse():
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen_urls = set()

        # Try each ATS pattern
        for ats_type, selectors in ATS_SELECTORS.items():
            for selector in selectors:
                try:
                    for a_tag in soup.select(selector):
                        href = a_tag.get("href", "").strip()
                        if not href or href.startswith("#") or href.startswith("javascript:"):
                            continue
                        full_url = urljoin(base_url, href) if base_url else href
                        if full_url in seen_urls:
                            continue
                        link_text = a_tag.get_text(strip=True)[:100]
                        if _is_non_job_link(full_url, link_text):
                            continue
                        seen_urls.add(full_url)
                        links.append({
                            "url": full_url,
                            "text": link_text,
                            "method": "deterministic",
                            "confidence": 0.9,
                            "ats_type": ats_type,
                        })
                except Exception:
                    continue

        return links

    return await asyncio.to_thread(_parse)


# ---------------------------------------------------------------------------
# Tier 2: curl_cffi + httpx fallback + trafilatura for JD text extraction
# ---------------------------------------------------------------------------

async def fetch_page(url: str) -> dict:
    """Fetch a page using curl_cffi with Chrome TLS fingerprint and httpx fallback.

    Returns {"html": str, "status": int, "headers": dict} or {"error": str}.
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"error": "Invalid URL", "html": "", "status": 0, "headers": {}}

    import asyncio

    def _fetch():
        # Tier 1: curl_cffi Chrome impersonation
        try:
            from curl_cffi import requests as cffi_requests
            resp = cffi_requests.get(
                url,
                impersonate="chrome",
                timeout=12,
                allow_redirects=True,
            )
            if resp.status_code == 200 and resp.text:
                return {
                    "html": resp.text,
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                }
        except Exception as exc:
            log.warning("curl_cffi_failed", url=url, error=str(exc)[:100])

        # Tier 2: Standard httpx fallback
        try:
            import httpx
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                res = client.get(url)
                return {
                    "html": res.text,
                    "status": res.status_code,
                    "headers": dict(res.headers),
                }
        except Exception as exc:
            log.warning("httpx_fallback_failed", url=url, error=str(exc)[:100])
            return {"error": str(exc), "html": "", "status": 0, "headers": {}}

    try:
        result = await asyncio.to_thread(_fetch)
        if result.get("status") == 200:
            log.info("page_fetched", url=url, status=result["status"])
        return result
    except Exception as exc:
        log.warning("page_fetch_error", url=url, error=str(exc)[:100])
        return {"error": str(exc), "html": "", "status": 0, "headers": {}}


async def extract_jd_text(html: str) -> str:
    """Extract clean job description text from HTML using trafilatura.

    Returns clean text string.
    """
    if not html or not html.strip():
        return ""

    import asyncio
    import trafilatura

    def _extract():
        text = trafilatura.extract(html, include_comments=False)
        return text or ""

    try:
        return await asyncio.to_thread(_extract)
    except Exception as exc:
        log.warning("trafilatura_error", error=str(exc)[:100])
        return ""


# ---------------------------------------------------------------------------
# Tier 3: ScrapeGraphAI LLM fallback (expensive, last resort)
# ---------------------------------------------------------------------------

async def extract_apply_links_llm(url: str, api_key: str) -> list[dict]:
    """Extract job links using ScrapeGraphAI with Gemini. Last resort.

    Returns list of {"url": str, "text": str, "method": "llm",
                      "confidence": 0.7}.
    """
    import asyncio

    def _scrape():
        try:
            from scrapegraphai.graphs import SmartScraperGraph

            graph_config = {
                "llm": {
                    "api_key": api_key,
                    "model": "gemini-pro",
                },
                "verbose": False,
                "headless": True,
            }

            scraper = SmartScraperGraph(
                prompt="Find all job application links on this page. Return a list of objects with 'url' and 'title' keys.",
                source=url,
                config=graph_config,
            )
            result = scraper.run()
            if isinstance(result, list):
                return [
                    {
                        "url": item.get("url", ""),
                        "text": item.get("title", ""),
                        "method": "llm",
                        "confidence": 0.7,
                    }
                    for item in result
                    if item.get("url")
                ]
            return []
        except Exception as exc:
            log.error("scrapegraphai_error", url=url, error=str(exc))
            return []

    return await asyncio.to_thread(_scrape)


# ---------------------------------------------------------------------------
# Combined extraction pipeline
# ---------------------------------------------------------------------------

async def extract_apply_links(
    url: str, api_key: str = "", html: str = ""
) -> list[dict]:
    """Three-tier extraction: deterministic → trafilatura → LLM fallback.

    Args:
        url: Career page URL.
        api_key: Google API key for ScrapeGraphAI fallback.
        html: Pre-fetched HTML (optional; will fetch if empty).

    Returns list of link dicts, sorted by confidence.
    """
    # Fetch HTML if not provided
    if not html:
        result = await fetch_page(url)
        html = result.get("html", "")
        if not html:
            return []

    # Tier 1: Deterministic
    links = await extract_apply_links_deterministic(html, base_url=url)
    if links:
        log.info("tier1_deterministic_success", url=url, count=len(links))
        return links

    # Do not invoke the legacy ScrapeGraphAI fallback here. It hard-codes
    # gemini-pro, adds a LangChain provider dependency, and can turn an
    # aggregator page into fake job links. Job links must be deterministic.
    log.info("deterministic_job_links_not_found", url=url)
    return []


# ---------------------------------------------------------------------------
# Freshness detection (best-effort with confidence)
# ---------------------------------------------------------------------------

def _parse_date_from_text(text: str) -> Optional[datetime]:
    """Try to parse a date from various formats found in text."""
    patterns = [
        # ISO-like: 2026-07-15
        r"(\d{4}-\d{2}-\d{2})",
        # US: July 15, 2026 or Jul 15, 2026
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})",
        # UK: 15 July 2026
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})",
        # dd/mm/yyyy or mm/dd/yyyy
        r"(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            for fmt in [
                "%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%b %d, %Y",
                "%b %d %Y", "%d %B %Y", "%d %b %Y", "%m/%d/%Y", "%d/%m/%Y",
            ]:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


async def extract_job_freshness(
    html: str, headers: dict | None = None
) -> dict:
    """Best-effort freshness detection with confidence scoring.

    Checks (in order):
    1. HTTP Last-Modified header → confidence 0.9
    2. <meta> date tags → confidence 0.85
    3. JSON-LD datePosted → confidence 0.8
    4. Regex dates in text → confidence 0.4
    5. No date found → confidence 0.0

    Returns FreshnessResult dict.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)

    headers = headers or {}

    # Check 1: HTTP Last-Modified
    last_mod = headers.get("Last-Modified") or headers.get("last-modified")
    if last_mod:
        try:
            dt = parsedate_to_datetime(last_mod)
            return {
                "is_fresh": dt >= cutoff,
                "confidence": 0.9,
                "evidence": "HTTP Last-Modified",
                "detected_date": dt.isoformat(),
            }
        except Exception:
            pass

    # Check 2: Meta tags
    meta_patterns = [
        r'<meta\s+property="article:published_time"\s+content="([^"]+)"',
        r'<meta\s+name="date"\s+content="([^"]+)"',
        r'<meta\s+property="og:updated_time"\s+content="([^"]+)"',
    ]
    for pat in meta_patterns:
        match = re.search(pat, html, re.IGNORECASE)
        if match:
            try:
                dt = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
                return {
                    "is_fresh": dt >= cutoff,
                    "confidence": 0.85,
                    "evidence": "meta tag",
                    "detected_date": dt.isoformat(),
                }
            except Exception:
                continue

    # Check 3: JSON-LD datePosted (common in ATS)
    jsonld_match = re.search(r'"datePosted"\s*:\s*"([^"]+)"', html)
    if jsonld_match:
        try:
            dt = datetime.fromisoformat(jsonld_match.group(1).replace("Z", "+00:00"))
            return {
                "is_fresh": dt >= cutoff,
                "confidence": 0.8,
                "evidence": "JSON-LD datePosted",
                "detected_date": dt.isoformat(),
            }
        except Exception:
            pass

    # Check 4: Regex in visible text (low confidence)
    import asyncio
    text = await extract_jd_text(html)
    dt = _parse_date_from_text(text)
    if dt:
        return {
            "is_fresh": dt >= cutoff,
            "confidence": 0.4,
            "evidence": "regex date in text",
            "detected_date": dt.isoformat(),
        }

    # Check 5: No date found
    return {
        "is_fresh": None,
        "confidence": 0.0,
        "evidence": "unknown",
        "detected_date": None,
    }
