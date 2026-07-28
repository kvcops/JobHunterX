"""
Vellum OS — Public ATS API Adapters

Fetches structured job postings directly from public, unauthenticated
ATS APIs (Greenhouse, Lever, Ashby) using company board slugs.
"""

from __future__ import annotations

import re
import httpx
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("ats_api")

# HTTP Client Timeout & User-Agent Header
TIMEOUT = 10.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


async def fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Greenhouse Job Board API.

    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug_clean}/jobs?content=true"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            data = res.json()
            raw_jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                apply_url = j.get("absolute_url", "")
                location = j.get("location", {}).get("name", "")
                content = j.get("content", "")  # HTML content

                # Extract plain text from HTML content
                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(content, "html.parser").get_text(separator="\n", strip=True) if content else title

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://boards.greenhouse.io/{slug_clean}",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "greenhouse",
                    "confidence": 0.95,
                })
            log.info("greenhouse_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("greenhouse_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_lever_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Lever Postings API.

    Endpoint: GET https://api.lever.co/v0/postings/{slug}?mode=json
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://api.lever.co/v0/postings/{slug_clean}?mode=json"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            raw_jobs = res.json()
            if not isinstance(raw_jobs, list):
                return []

            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("text", "").strip()
                apply_url = j.get("hostedUrl", "") or j.get("applyUrl", "")
                categories = j.get("categories", {})
                location = categories.get("location", "")
                description = j.get("descriptionPlain", "") or j.get("description", "")

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://jobs.lever.co/{slug_clean}",
                    "location": location,
                    "jd_text": description,
                    "ats_source": "lever",
                    "confidence": 0.95,
                })
            log.info("lever_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("lever_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_ashby_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Ashby Job Board API.

    Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{slug}
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug_clean}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            data = res.json()
            raw_jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                job_id = j.get("id", "")
                apply_url = f"https://jobs.ashbyhq.com/{slug_clean}/{job_id}" if job_id else f"https://jobs.ashbyhq.com/{slug_clean}"
                location = j.get("locationName", "") or j.get("location", "")
                description = j.get("descriptionHtml", "") or title

                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://jobs.ashbyhq.com/{slug_clean}",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "ashby",
                    "confidence": 0.95,
                })
            log.info("ashby_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("ashby_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_freshteam_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Freshteam ATS (Freshworks). Endpoint: https://{slug}.freshteam.com/jobs.json"""
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://{slug_clean}.freshteam.com/jobs.json"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            content_type = res.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                # Returned HTML instead of JSON (typical for parked/inactive domains)
                return []
            raw_jobs = res.json()
            if not isinstance(raw_jobs, list):
                return []
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                apply_url = j.get("url", "") or f"https://{slug_clean}.freshteam.com/jobs/{j.get('id', '')}"
                location = j.get("location", {}).get("city", "") if isinstance(j.get("location"), dict) else str(j.get("location", ""))
                description = j.get("description", "") or title
                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True) if description else title
                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://{slug_clean}.freshteam.com/jobs",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "freshteam",
                    "confidence": 0.95,
                })
            log.info("freshteam_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.debug("freshteam_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_zoho_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Zoho Recruit ATS (in/com)."""
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    urls = [
        f"https://{slug_clean}.zohorecruit.in/careers",
        f"https://{slug_clean}.zohorecruit.com/careers",
    ]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            for url in urls:
                res = await client.get(url)
                if res.status_code == 200 and ("zoho" in res.text.lower() or "job" in res.text.lower()):
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(res.text, "html.parser")
                    jobs = []
                    for card in soup.find_all(["div", "tr", "li"], class_=re.compile(r"job|career|posting", re.I)):
                        title_el = card.find(["a", "h2", "h3", "h4"])
                        if title_el:
                            t_text = title_el.get_text(strip=True)
                            href = title_el.get("href", "")
                            if t_text and len(t_text) > 3:
                                jobs.append({
                                    "company": slug_clean.title(),
                                    "title": t_text,
                                    "apply_url": href if href.startswith("http") else f"{url}/{href.lstrip('/')}",
                                    "career_page_url": url,
                                    "location": "India",
                                    "jd_text": t_text,
                                    "ats_source": "zohorecruit",
                                    "confidence": 0.90,
                                })
                    if jobs:
                        log.info("zoho_api_success", company=slug_clean, count=len(jobs))
                        return jobs
            return []
    except Exception as exc:
        log.debug("zoho_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_getro_vc_jobs(vc_domain: str = "blume.vc", vc_name: str = "Blume Ventures") -> list[dict]:
    """Extract structured portfolio company jobs from Getro-powered VC job boards (Next.js __NEXT_DATA__)."""
    url = f"https://{vc_domain}/jobs" if not vc_domain.startswith("http") else vc_domain
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if not script or not script.string:
                return []
            import json
            data = json.loads(script.string)
            page_props = data.get("props", {}).get("pageProps", {})
            jobs_list = page_props.get("jobs", []) or page_props.get("initialJobs", [])
            parsed_jobs = []
            for j in jobs_list:
                company_obj = j.get("company", {}) or {}
                comp_name = company_obj.get("name", "VC Portfolio Startup")
                title = j.get("title", "") or j.get("name", "")
                apply_url = j.get("url", "") or j.get("applyUrl", "") or url
                location = j.get("location", "") or company_obj.get("location", "India")
                description = j.get("description", "") or title
                if title:
                    parsed_jobs.append({
                        "company": comp_name,
                        "title": title,
                        "apply_url": apply_url,
                        "career_page_url": url,
                        "location": str(location),
                        "jd_text": str(description)[:5000],
                        "ats_source": f"vc_getro_{vc_domain}",
                        "confidence": 0.92,
                    })
            log.info("getro_vc_jobs_success", vc=vc_name, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("getro_vc_jobs_failed", vc=vc_name, error=str(exc)[:100])
        return []


# Comprehensive catalog of mid-size tech companies, product startups, and AI labs across Indian hubs
TECH_HUB_STARTUPS = {
    "hyderabad": [
        "darwinbox", "highradius", "koreai", "zenoti", "cohesity", "thoughtspot",
        "rubrik", "nutanix", "tanla", "yellowai", "gramener", "skan", "gushwork",
        "haptik", "scalereal", "plotline", "superops", "squadstack", "segwise",
        "opentext", "epam-systems", "deshaw", "arcesium", "factset", "mathworks",
        "synopsys", "cadence", "amd", "qualcomm", "nvidia", "micron", "virtusa", "cyient",
    ],
    "bengaluru": [
        "swiggy", "razorpay", "cred", "meesho", "zepto", "groww", "postman",
        "browserstack", "juspay", "chargebee", "freshworks", "hasura", "clevertap",
        "dream11", "zomato", "blinkit", "ola", "slice", "navi", "cars24",
        "lenskart", "paytm", "policybazaar", "shadowfax", "porter", "spinny",
        "kuku-fm", "pocket-fm", "atlan", "lambdatest", "sprinto", "invideo",
        "dhiwise", "truefoundry", "devtron", "middleware", "portkey", "unfoldai",
    ],
    "mumbai": [
        "dream11", "games24x7", "mpl", "fractal-analytics", "nykaa", "clevertap",
        "haptik", "bookmyshow", "upgrad", "pharmeasy", "eruditus",
    ],
    "ncr": [
        "zomato", "blinkit", "urbancompany", "cars24", "spinny", "paytm",
        "policybazaar", "mobikwik", "lenskart", "mamaearth", "cardekho", "lendingkart",
    ],
    "pune": [
        "mindtickle", "druva", "pubmatic", "furlenco", "scalereal", "persistent",
    ],
}

# Universal Indian/Global Tech Startups pool
UNIVERSAL_STARTUPS = [
    "hasura", "plivo", "postman", "browserstack", "juspay", "chargebee",
    "freshworks", "clevertap", "atlan", "lambdatest", "sprinto", "invideo",
    "dhiwise", "truefoundry", "devtron", "middleware", "portkey", "unfoldai",
    "scalereal", "plotline", "superops", "segwise", "skan", "gushwork",
]


async def fetch_jobs_for_ats_company(company_name: str, company_slug: str = "") -> list[dict]:
    """Try fetching jobs for a company across Greenhouse, Lever, Ashby, Freshteam, Zoho Recruit APIs."""
    base_raw = company_slug or company_name
    slug_candidates = [
        re.sub(r"[^a-zA-Z0-9_\-]", "", base_raw.lower().strip()),
        re.sub(r"[^a-zA-Z0-9]", "", base_raw.lower().strip()),
        re.sub(r"\s+", "-", base_raw.lower().strip()),
    ]
    seen_slugs = set()

    for slug in slug_candidates:
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Try Greenhouse
        gh_jobs = await fetch_greenhouse_jobs(slug)
        if gh_jobs:
            return gh_jobs

        # Try Lever
        lever_jobs = await fetch_lever_jobs(slug)
        if lever_jobs:
            return lever_jobs

        # Try Ashby
        ashby_jobs = await fetch_ashby_jobs(slug)
        if ashby_jobs:
            return ashby_jobs

        # Try Freshteam
        ft_jobs = await fetch_freshteam_jobs(slug)
        if ft_jobs:
            return ft_jobs

        # Try Zoho Recruit
        zoho_jobs = await fetch_zoho_jobs(slug)
        if zoho_jobs:
            return zoho_jobs

    return []


async def fetch_hub_ats_jobs(location: str, role: str, max_jobs: int = 25) -> list[dict]:
    """Concurrently probe 30+ startup ATS boards for a target tech hub and role.

    Bypasses fragile web search engines, returning structured JSON instantly.
    """
    import asyncio

    city_key = location.lower().strip()
    # Normalize city key
    if "bangalore" in city_key or "bengaluru" in city_key:
        city_key = "bengaluru"
    elif "hyderabad" in city_key or "secunderabad" in city_key:
        city_key = "hyderabad"
    elif "mumbai" in city_key or "bombay" in city_key:
        city_key = "mumbai"
    elif "delhi" in city_key or "noida" in city_key or "gurgaon" in city_key or "gurugram" in city_key:
        city_key = "ncr"
    elif "pune" in city_key:
        city_key = "pune"

    target_slugs = list(TECH_HUB_STARTUPS.get(city_key, []))
    # Add universal startups pool
    for s in UNIVERSAL_STARTUPS:
        if s not in target_slugs:
            target_slugs.append(s)

    log.info("direct_ats_hub_scan_started", city=city_key, slug_count=len(target_slugs), role=role)

    # Gather jobs concurrently
    tasks = [fetch_jobs_for_ats_company(slug, slug) for slug in target_slugs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    role_terms = [t.strip().lower() for t in role.split() if len(t.strip()) > 2]

    for res in results:
        if isinstance(res, list):
            for job in res:
                title = job.get("title", "").lower()
                jd = job.get("jd_text", "").lower()
                loc = job.get("location", "").lower()

                # Basic relevance check: role term in title or JD
                matches_role = any(term in title for term in role_terms) or ("engineer" in title or "developer" in title or "ai" in title or "ml" in title or "data" in title)
                if not matches_role:
                    continue

                # Basic location check: city name, remote, or india
                matches_loc = not location or city_key in loc or "remote" in loc or "india" in loc or "remote" in title

                if matches_loc:
                    all_jobs.append(job)
                    if len(all_jobs) >= max_jobs:
                        break

        if len(all_jobs) >= max_jobs:
            break

    log.info("direct_ats_hub_scan_complete", city=city_key, jobs_found=len(all_jobs))
    return all_jobs

