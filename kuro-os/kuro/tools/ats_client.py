"""
Kuro OS — ATS Client (free, unauthenticated JSON job feeds)

The backbone of the board-first architecture. Every major ATS publishes a
public JSON API for all open jobs — no API key, no scraping, no blocking.
For each company we probe its careers page for ATS markers, resolve the
board token, then pull structured jobs.

Supported ATS feeds (all verified / widely used):
  - Greenhouse   boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
  - Ashby        api.ashbyhq.com/posting-api/job-board/{token}
  - Lever        api.lever.co/v0/postings/{token}?mode=json
  - Recruitee    {token}.recruitee.com/api/offers
  - SmartRecruiters  api.smartrecruiters.com/v1/companies/{token}/postings
  - BambooHR     {token}.bamboohr.com/careers/jobs (JSON endpoint)
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

from kuro.config.logging import get_logger

log = get_logger("ats_client")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


@dataclass
class Company:
    """A company we track for job discovery."""
    name: str
    website: str = ""
    careers_url: str = ""
    hub: str = ""          # Indian tech hub (Bengaluru, NCR, Mumbai, Pune, Hyderabad, Remote)
    ats: str = ""          # detected: greenhouse|ashby|lever|recruitee|smartrecruiters|bamboohr|none
    ats_token: str = ""
    notes: str = ""


@dataclass
class Job:
    company: str
    role: str
    location: str
    department: str
    jd_text: str
    apply_url: str
    career_page_url: str
    posted_at: str
    source: str
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ATS marker detection
# ---------------------------------------------------------------------------

def detect_ats_from_html(html: str, careers_url: str = "") -> tuple[str, str]:
    """Return (ats_type, board_token) detected in careers-page HTML.

    Order matters: Ashby boards usually also contain Greenhouse-era regex
    noise, so check the most specific markers first.
    """
    text = html or ""
    low = text.lower()

    # Ashby — api.ashbyhq.com/posting-api/job-board/<token>
    m = re.search(r"api\.ashbyhq\.com/posting-api/job-board/([a-z0-9\-]+)", low)
    if m:
        return "ashby", m.group(1)
    m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9\-]+)", low)
    if m:
        return "ashby", m.group(1)

    # Greenhouse
    m = re.search(r"boards[-.]greenhouse\.io/([a-z0-9\-]+)", low)
    if m:
        return "greenhouse", m.group(1)
    m = re.search(r"greenhouse\.io/embed/job_board\?for=([a-z0-9\-]+)", low)
    if m:
        return "greenhouse", m.group(1)

    # Lever
    m = re.search(r"jobs\.lever\.co/([a-z0-9\-]+)", low)
    if m:
        return "lever", m.group(1)
    m = re.search(r"api\.lever\.co/v0/postings/([a-z0-9\-]+)", low)
    if m:
        return "lever", m.group(1)

    # Recruitee
    m = re.search(r"([a-z0-9\-]+)\.recruitee\.com", low)
    if m:
        return "recruitee", m.group(1)

    # SmartRecruiters
    m = re.search(r"careers\.smartrecruiters\.com/([a-z0-9\-]+)", low)
    if m:
        return "smartrecruiters", m.group(1)
    m = re.search(r"api\.smartrecruiters\.com/v1/companies/([a-z0-9\-]+)", low)
    if m:
        return "smartrecruiters", m.group(1)

    # BambooHR
    m = re.search(r"([a-z0-9\-]+)\.bamboohr\.com/careers", low)
    if m:
        return "bamboohr", m.group(1)

    # Freshteam
    if "freshteam" in low:
        return "freshteam", ""

    # Workday (no public JSON) — record but do not support fetching
    if "myworkdayjobs.com" in low or "workday" in low:
        return "workday", ""

    return "none", ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def _fetch_json(url: str, timeout: float = 15.0) -> Optional[dict | list]:
    """Fetch JSON with curl_cffi (Chrome TLS) then httpx fallback."""
    import json

    def _fetch() -> Optional[dict | list]:
        try:
            from curl_cffi import requests as cffi
            resp = cffi.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
            if resp.status_code == 200 and resp.text:
                return json.loads(resp.text)
        except Exception as exc:
            log.debug("ats_curl_failed", url=url, error=str(exc)[:100])
        try:
            import httpx
            with httpx.Client(timeout=timeout, follow_redirects=True,
                              headers={"User-Agent": _UA}) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            log.debug("ats_httpx_failed", url=url, error=str(exc)[:100])
        return None

    try:
        return await asyncio.to_thread(_fetch)
    except Exception:
        return None


async def fetch_page(url: str, timeout: float = 8.0) -> str:
    """Fetch raw HTML for ATS probing."""
    try:
        from curl_cffi import requests as cffi
        resp = cffi.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text or ""
    except Exception:
        pass
    try:
        import httpx
        with httpx.Client(timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": _UA}) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text or ""
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Per-ATS fetchers — each returns list[Job]
# ---------------------------------------------------------------------------

def _clean_html(html: str) -> str:
    """Strip tags, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _greenhouse(token: str, company: str, careers_url: str, max_pages: int = 5) -> list[Job]:
    per_page = 100
    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        url = (f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
               f"?content=true&per_page={per_page}&page={page}")
        data = await _fetch_json(url)
        if not data or not isinstance(data, dict):
            return jobs
        chunk = data.get("jobs") or []
        for item in chunk:
            jd = _clean_html(item.get("content", ""))
            loc = item.get("location") or {}
            loc_name = loc.get("name", "") if isinstance(loc, dict) else str(loc or "")
            jobs.append(Job(
                company=company,
                role=item.get("title", ""),
                location=loc_name,
                department="",
                jd_text=jd,
                apply_url=item.get("absolute_url", ""),
                career_page_url=careers_url,
                posted_at=item.get("updated_at", ""),
                source=f"greenhouse:{token}",
            ))
        if len(chunk) < per_page:
            break
    return jobs


async def _ashby(token: str, company: str, careers_url: str) -> list[Job]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    data = await _fetch_json(url)
    jobs = []
    if not data or not isinstance(data, dict):
        return jobs
    for item in data.get("jobs", []):
        jd = _clean_html(item.get("descriptionHtml", ""))
        loc = item.get("location") or ""
        if isinstance(loc, dict):
            loc = loc.get("name", "")
        jobs.append(Job(
            company=company,
            role=item.get("title", ""),
            location=str(loc or ""),
            department=item.get("department", ""),
            jd_text=jd,
            apply_url=item.get("applyUrl", ""),
            career_page_url=careers_url,
            posted_at=item.get("publishedAt", ""),
            source=f"ashby:{token}",
        ))
    return jobs


async def _lever(token: str, company: str, careers_url: str) -> list[Job]:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    data = await _fetch_json(url)
    jobs = []
    if not data or not isinstance(data, list):
        return jobs
    for item in data:
        jd = item.get("descriptionPlain", "") or _clean_html(item.get("description", ""))
        categories = item.get("categories") or {}
        jobs.append(Job(
            company=company,
            role=item.get("text", ""),
            location=item.get("categories", {}).get("location", "") if isinstance(categories, dict) else "",
            department=item.get("categories", {}).get("team", "") if isinstance(categories, dict) else "",
            jd_text=jd,
            apply_url=item.get("hostedUrl", ""),
            career_page_url=careers_url,
            posted_at=item.get("createdAt", ""),
            source=f"lever:{token}",
        ))
    return jobs


async def _recruitee(token: str, company: str, careers_url: str) -> list[Job]:
    url = f"https://{token}.recruitee.com/api/offers"
    data = await _fetch_json(url)
    jobs = []
    if not data or not isinstance(data, dict):
        return jobs
    for item in data.get("offers", []):
        jd = _clean_html(item.get("description", ""))
        jobs.append(Job(
            company=company,
            role=item.get("title", ""),
            location=item.get("location", ""),
            department="",
            jd_text=jd,
            apply_url=item.get("careers_url", ""),
            career_page_url=careers_url,
            posted_at=item.get("published_at", ""),
            source=f"recruitee:{token}",
        ))
    return jobs


async def _smartrecruiters(token: str, company: str, careers_url: str, limit: int = 100) -> list[Job]:
    jobs: list[Job] = []
    offset = 0
    while True:
        url = (f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
               f"?limit={limit}&offset={offset}")
        data = await _fetch_json(url)
        if not data or not isinstance(data, dict):
            break
        chunk = data.get("content") or []
        for item in chunk:
            loc = item.get("location") or {}
            jd = item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
            jobs.append(Job(
                company=company,
                role=item.get("name", ""),
                location=f"{loc.get('city', '')}, {loc.get('country', '')}".strip(", "),
                department="",
                jd_text=_clean_html(jd),
                apply_url=item.get("ref", ""),
                career_page_url=careers_url,
                posted_at=item.get("releasedDate", ""),
                source=f"smartrecruiters:{token}",
            ))
        total = data.get("totalFound", 0) or 0
        offset += len(chunk)
        if offset >= total or not chunk:
            break
    return jobs


async def _bamboohr(token: str, company: str, careers_url: str) -> list[Job]:
    url = f"https://{token}.bamboohr.com/careers/jobs?source=bamboo"
    data = await _fetch_json(url)
    jobs = []
    if not data or not isinstance(data, list):
        return jobs
    for item in data:
        jd = _clean_html(item.get("jobDescription", ""))
        jobs.append(Job(
            company=company,
            role=item.get("jobOpeningName", ""),
            location=item.get("location", ""),
            department=item.get("departmentLabel", ""),
            jd_text=jd,
            apply_url=item.get("externalPath", ""),
            career_page_url=careers_url,
            posted_at="",
            source=f"bamboohr:{token}",
        ))
    return jobs


_ATS_FETCHERS = {
    "greenhouse": _greenhouse,
    "ashby": _ashby,
    "lever": _lever,
    "recruitee": _recruitee,
    "smartrecruiters": _smartrecruiters,
    "bamboohr": _bamboohr,
}


async def probe_company(company: Company) -> Company:
    """Probe a company's careers page for an ATS board. Mutates and returns it.

    Tries, in order: explicit careers_url → website + /careers → website.
    The candidate URLs are fetched IN PARALLEL — dead sites otherwise burn
    the full timeout serially (up to 3 × per-URL timeout per company), which
    is why syncs used to swim through never-probed backlogs.
    """
    candidates: list[str] = []
    if company.careers_url:
        candidates.append(company.careers_url)
    if company.website:
        base = company.website.rstrip("/")
        candidates.append(base + "/careers")
        candidates.append(base)
        candidates.append(base + "/careers.html")
    if not candidates:
        company.ats = "none"
        return company

    sem = asyncio.Semaphore(len(candidates))

    async def fetch_one(url: str) -> tuple[str, str]:
        async with sem:
            try:
                html = await fetch_page(url)
            except Exception:
                return url, ""
            if not html:
                return url, ""
            return url, html

    pages = await asyncio.gather(*(fetch_one(u) for u in candidates))
    for url, html in pages:
        if not html:
            continue
        ats, token = detect_ats_from_html(html, url)
        if ats != "none":
            company.ats = ats
            company.ats_token = token
            if not company.careers_url:
                company.careers_url = url
            log.info("ats_detected", company=company.name, ats=ats, token=token)
            return company
    company.ats = "none"
    return company


async def fetch_jobs(company: Company) -> list[Job]:
    """Fetch open jobs for a company using its detected ATS board.

    Returns [] when the company has no detectable ATS or the fetch fails.
    """
    if company.ats == "none" or not company.ats_token:
        return []
    fetcher = _ATS_FETCHERS.get(company.ats)
    if not fetcher:
        return []
    try:
        jobs = await fetcher(company.ats_token, company.name, company.careers_url)
        log.info("ats_jobs_fetched", company=company.name, ats=company.ats, count=len(jobs))
        return jobs
    except Exception as exc:
        log.warning("ats_fetch_failed", company=company.name, ats=company.ats, error=str(exc)[:150])
        return []