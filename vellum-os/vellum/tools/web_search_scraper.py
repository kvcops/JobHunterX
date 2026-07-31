"""
Vellum OS — Web Search Job Scraper (v2)

Best practices implementation:
- Multi-source: DuckDuckGo + Greenhouse/Lever public APIs
- Rate limiting with jitter and exponential backoff
- User-agent rotation
- Proper deduplication
"""

from __future__ import annotations

import asyncio
import random
import re
import json
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from vellum.config.logging import get_logger

log = get_logger("web_search_scraper")

# HTTP timeout
TIMEOUT = 15.0

# Base headers
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# Domains to skip (aggregators, directories, spam sites)
SKIP_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "naukri.com",
    "monster.com", "internshala.com", "ambitionbox.com", "jooble.org",
    "ziprecruiter.com", "simplyhired.com", "careerjet.com", "talent.com",
    "adzuna.com", "jora.com", "foundit.in", "shine.com", "timesjobs.com",
    "cutshort.io", "instahyre.com", "hirect.in", "apna.co",
    "wellfound.com", "fresherworld.com", "payscale.com", "jobsora.com",
    "placementindia.com", "beincareer.com", "onjob.io", "himalayas.app",
    "jobspipe.dev", "jobgether.com", "bebee.com", "click.in", "workindia.in",
    "fresherslive.com", "unstop.com", "glassdoor.co.in", "indeed.co.in",
    "jooble.in", "grabjobs.co", "careerjet.in", "leverageedu.com",
    "indgovtjobs.in", "sarkariresult.com", "freejobalert.com", "naukrirecruiter",
    "monsterindia.com", "rekrute.com", "updazz.com", "jobrapido.com",
    "safalta.com", "winitjobs.com", "adzuna.in", "jora.co.in", "glassdoor.sg",
    "indeed.sg", "linkedin.sg", "hasjob.co",
}


# ---------------------------------------------------------------------------
# Rate Limiter with Jitter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Adaptive rate limiter with exponential backoff and jitter."""
    
    def __init__(
        self,
        requests_per_minute: int = 15,
        min_delay: float = 2.0,
        max_delay: float = 10.0,
    ):
        self.rpm = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_times: list[float] = []
        self.consecutive_failures = 0
    
    async def wait(self):
        """Wait if needed to respect rate limits."""
        now = time.time()
        
        # Clean old request times
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we're at the limit
        if len(self.request_times) >= self.rpm:
            wait_time = 60 - (now - self.request_times[0]) + 1
            if wait_time > 0:
                log.info("rate_limit_wait", seconds=round(wait_time, 1))
                await asyncio.sleep(wait_time)
        
        # Human-like random delay with jitter
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
    
    def record_success(self):
        """Record a successful request."""
        self.request_times.append(time.time())
        self.consecutive_failures = 0
    
    def record_failure(self) -> float:
        """Record a failure and return backoff time."""
        self.consecutive_failures += 1
        backoff = min(
            self.max_delay * (2 ** self.consecutive_failures) + random.uniform(0, 2),
            300  # Max 5 minutes
        )
        return backoff


# ---------------------------------------------------------------------------
# DuckDuckGo Search
# ---------------------------------------------------------------------------

def _build_search_queries(role: str, location: str, company: str = "", skills: list[str] | None = None) -> list[str]:
    """Build targeted search queries for job discovery."""
    queries = []
    
    clean_role = role.replace('"', '').strip()
    
    # Primary: specific role + location (with and without quotes)
    queries.append(f'{clean_role} jobs {location}')
    queries.append(f'"{clean_role}" jobs {location}')
    queries.append(f'"{clean_role}" hiring {location} apply now')
    
    # With company name if provided
    if company:
        queries.append(f'"{company}" {clean_role} jobs {location}')
        queries.append(f'"{company}" careers hiring {location}')
    
    # Skill-based queries: use top 3 most specific skills for targeted search
    if skills:
        # Pick skills that are specific enough (len > 3, not generic terms)
        specific_skills = [s for s in skills if len(s) > 3 and s.lower() not in {
            "communication", "leadership", "teamwork", "problem solving",
            " analytical", "management", "agile", "sql",
        }][:3]
        for skill in specific_skills:
            queries.append(f'"{skill}" "{clean_role}" jobs {location}')
    
    # ATS-specific queries (queried separately for better engine response and no quote restrictions)
    queries.append(f'{clean_role} {location} site:greenhouse.io')
    queries.append(f'{clean_role} {location} site:lever.co')
    queries.append(f'{clean_role} {location} site:ashbyhq.com')
    
    # Indian job boards
    queries.append(f'{clean_role} {location} site:hasjob.co')
    
    return queries


def _get_random_headers() -> dict:
    """Get headers with random user-agent."""
    headers = dict(BASE_HEADERS)
    headers["User-Agent"] = random.choice(USER_AGENTS)
    return headers


def _is_valid_job_url(url: str) -> bool:
    """Check if URL looks like a real job listing page."""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
    except Exception:
        return False
    
    # Skip aggregator domains
    for skip in SKIP_DOMAINS:
        if skip in domain:
            return False
    
    # Skip social media, news, blogs
    skip_patterns = [
        "twitter.com", "facebook.com", "instagram.com", "youtube.com",
        "reddit.com", "medium.com", "substack.com",
        "/blog/", "/news/", "/article/", "/press/",
    ]
    for pattern in skip_patterns:
        if pattern in domain or pattern in path:
            return False
    
    # Good signs: job-related paths or ATS domains
    good_patterns = [
        "/jobs", "/job", "/careers", "/positions",
        "/openings", "/apply", "/posting",
        "greenhouse.io", "lever.co", "ashbyhq.com",
        "myworkdayjobs.com", "smartrecruiters.com",
    ]
    for pattern in good_patterns:
        if pattern in path or pattern in domain:
            return True
    
    return False


def _extract_job_from_search_result(result: dict) -> dict | None:
    """Extract job info from a search result."""
    title = result.get("title", "").strip()
    body = result.get("body", "").strip()
    url = result.get("href", "") or result.get("link", "")
    
    if not title or not url:
        return None
    
    # Skip if title looks like navigation
    skip_titles = [
        "jobs in", "all jobs", "view all", "browse", "search",
        "sign in", "log in", "register", "subscribe",
    ]
    title_lower = title.lower()
    if any(skip in title_lower for skip in skip_titles):
        return None
    
    # Extract company from title
    company = ""
    if " - " in title:
        parts = title.split(" - ")
        company = parts[-1].strip()
    elif " | " in title:
        parts = title.split(" | ")
        company = parts[-1].strip()
    
    # Clean company name
    company = re.sub(r"\s*(careers?|jobs?|hiring|inc\.?|ltd\.?|llc|pvt).*", "", company, flags=re.I).strip()
    if len(company) > 60 or len(company) < 2:
        company = ""
    
    return {
        "title": title,
        "company": company,
        "apply_url": url,
        "snippet": body[:500],
        "source": "web_search",
    }


async def _search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Search DuckDuckGo via ddgs library."""
    from ddgs import DDGS
    
    def _do_search():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    
    try:
        return await asyncio.to_thread(_do_search)
    except Exception as exc:
        log.warning("ddgs_search_failed", error=str(exc)[:100])
        return []


async def filter_shady_and_aggregator_jobs_with_llm(results: list[dict], role: str, location: str) -> list[dict]:
    """Use LLM to classify and filter out shady sites, third-party aggregators, and spam directories.
    
    Returns only high-quality direct career/job posting pages matching the target role and location.
    """
    from vellum.config.llm_router import call_llm_with_fallback
    from vellum.utils.json_helper import parse_llm_json
    
    if not results:
        return []
        
    prompt = f"""You are an elite job discovery assistant. Your goal is to review a list of web search results and select ONLY the high-quality, authentic, direct application pages (like Greenhouse, Lever, Ashby, Workday, or a company's direct career section).
    
    CRITICAL CLASSIFICATION RULES:
    1. **Direct Application only**: Keep ONLY URLs that lead to direct application forms or official company job postings.
    2. **Exclude Shady/Aggregators**: Strict reject for third-party directories, generic job aggregators, spam lists, blogs, walk-in summaries, or forums (e.g. PlacementIndia, BeInCareer, OnJob, Jobspipe, Jobgether, etc. - even if not explicitly in standard lists).
    3. **Role & Location Check**: The target role is "{role}" and location is "{location}". Discard anything that doesn't align.
    
    List of results to classify:
    """
    
    items = []
    for idx, r in enumerate(results):
        items.append(f"[{idx}] Title: {r.get('title')}\nURL: {r.get('apply_url')}\nSnippet: {r.get('snippet')}\n")
        
    prompt += "\n".join(items)
    prompt += """
    Return a JSON array of objects representing the index and classification:
    [
      {{
        "index": 0,
        "is_direct_job_page": true/false,
        "company_name": "Name of the actual hiring company",
        "reason": "Why this is classified as direct or rejected as aggregator/shady"
      }}
    ]
    Return valid JSON array only. No markdown formatting or explanation outside JSON."""
    
    messages = [
        {"role": "system", "content": "You are a professional recruiting coordinator."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        res = await call_llm_with_fallback("fast", messages)
        classifications = parse_llm_json(res.get("content", ""), default=[])
        
        filtered = []
        if isinstance(classifications, list):
            class_map = {{item.get("index"): item for item in classifications if isinstance(item, dict) and "index" in item}}
            for idx, r in enumerate(results):
                info = class_map.get(idx)
                if info and info.get("is_direct_job_page") is True:
                    if info.get("company_name") and info["company_name"].lower() not in {"unknown", "not specified", "n/a", "company", "hiring company"}:
                        r["company"] = info["company_name"]
                    filtered.append(r)
        return filtered
    except Exception as exc:
        log.warning("llm_filtering_failed", error=str(exc))
        return results


async def search_jobs_via_web(
    role: str,
    location: str,
    company: str = "",
    max_results: int = 30,
    rate_limiter: RateLimiter | None = None,
    skills: list[str] | None = None,
) -> list[dict]:
    """Search for jobs using DuckDuckGo web search."""
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    
    queries = _build_search_queries(role, location, company, skills=skills)
    all_jobs = []
    seen_urls = set()
    
    for query in queries:
        if len(all_jobs) >= max_results:
            break
        
        await rate_limiter.wait()
        results = await _search_duckduckgo(query, max_results=10)
        
        for r in results:
            if len(all_jobs) >= max_results:
                break
            
            url = r.get("href", "")
            if not url or url in seen_urls:
                continue
            
            if not _is_valid_job_url(url):
                continue
            
            seen_urls.add(url)
            job = _extract_job_from_search_result(r)
            if job:
                all_jobs.append(job)
        
        rate_limiter.record_success()
    
    # Filter out shady/aggregator jobs using LLM
    all_jobs = await filter_shady_and_aggregator_jobs_with_llm(all_jobs, role, location)
    
    log.info("web_search_complete", query=f"{role} in {location}", found=len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Greenhouse/Lever Public APIs (Free, No Key)
# ---------------------------------------------------------------------------

async def fetch_greenhouse_jobs(
    company_slug: str,
    rate_limiter: RateLimiter | None = None,
) -> list[dict]:
    """Fetch jobs from Greenhouse public API (no key needed)."""
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    
    try:
        await rate_limiter.wait()
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=_get_random_headers()) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            
            data = res.json()
            jobs = []
            
            for j in data.get("jobs", []):
                title = j.get("title", "").strip()
                if not title:
                    continue
                
                # Extract location
                location = j.get("location", {}).get("name", "")
                
                # Extract description text
                content = j.get("content", "")
                if content:
                    from bs4 import BeautifulSoup as BS
                    jd_text = BS(content, "html.parser").get_text(separator="\n", strip=True)
                else:
                    jd_text = ""
                
                jobs.append({
                    "title": title,
                    "company": company_slug.replace("-", " ").title(),
                    "apply_url": j.get("absolute_url", ""),
                    "location": location,
                    "snippet": jd_text[:500],
                    "source": "greenhouse_api",
                })
            
            rate_limiter.record_success()
            log.info("greenhouse_api_success", company=company_slug, count=len(jobs))
            return jobs[:20]
    
    except Exception as exc:
        log.warning("greenhouse_api_failed", company=company_slug, error=str(exc)[:100])
        return []


async def fetch_lever_jobs(
    company_slug: str,
    rate_limiter: RateLimiter | None = None,
) -> list[dict]:
    """Fetch jobs from Lever public API (no key needed)."""
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    
    try:
        await rate_limiter.wait()
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=_get_random_headers()) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            
            data = res.json()
            if not isinstance(data, list):
                return []
            
            jobs = []
            for j in data:
                title = j.get("text", "").strip()
                if not title:
                    continue
                
                categories = j.get("categories", {})
                location = categories.get("location", "")
                description = j.get("descriptionPlain", "") or j.get("description", "")
                
                jobs.append({
                    "title": title,
                    "company": company_slug.replace("-", " ").title(),
                    "apply_url": j.get("hostedUrl", ""),
                    "location": location,
                    "snippet": description[:500] if description else "",
                    "source": "lever_api",
                })
            
            rate_limiter.record_success()
            log.info("lever_api_success", company=company_slug, count=len(jobs))
            return jobs[:20]
    
    except Exception as exc:
        log.warning("lever_api_failed", company=company_slug, error=str(exc)[:100])
        return []


# ---------------------------------------------------------------------------
# Page Enrichment
# ---------------------------------------------------------------------------

def _extract_jobs_from_page(html: str, base_url: str) -> list[dict]:
    """Extract job listings from a career page."""
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []
    
    jobs = []
    seen_titles = set()
    
    # Method 1: JSON-LD JobPosting
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "JobPosting":
                    title = item.get("title", "").strip()
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        org = item.get("hiringOrganization", {})
                        jobs.append({
                            "title": title,
                            "company": org.get("name", ""),
                            "apply_url": item.get("url", ""),
                            "snippet": _clean_html(item.get("description", ""))[:500],
                            "source": "jsonld",
                        })
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Method 2: Links to ATS or job pages
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        
        if not href or not text or len(text) < 5:
            continue
        
        full_url = urljoin(base_url, href)
        
        # Check if it's a job link
        is_job_link = False
        url_lower = full_url.lower()
        
        for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "myworkdayjobs.com"]:
            if ats in url_lower:
                is_job_link = True
                break
        
        if re.search(r"/jobs?/\d+|/positions?/\d+|/openings?/\d+", url_lower):
            is_job_link = True
        
        if is_job_link and text not in seen_titles:
            skip_words = ["view all", "see all", "browse", "search", "back", "home"]
            if not any(w in text.lower() for w in skip_words):
                seen_titles.add(text)
                jobs.append({
                    "title": text[:200],
                    "company": "",
                    "apply_url": full_url,
                    "location": "",
                    "snippet": "",
                    "source": "page_link",
                })
    
    return jobs[:20]


def _clean_html(html: str) -> str:
    """Strip HTML tags from text."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", "", html)


async def enrich_job_from_page(job: dict) -> dict:
    """Fetch the job page and extract more details."""
    url = job.get("apply_url", "")
    if not url:
        return job
    
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers=_get_random_headers(),
        ) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return job
            
            page_jobs = _extract_jobs_from_page(res.text, url)
            
            if page_jobs:
                first = page_jobs[0]
                job["title"] = first.get("title") or job["title"]
                job["company"] = first.get("company") or job.get("company", "")
                job["location"] = first.get("location", "")
                job["snippet"] = first.get("snippet", "") or job.get("snippet", "")
                job["source"] = f"enriched_{first.get('source', 'page')}"
            else:
                # Fallback: if no structured sub-jobs extracted, extract clean text of the page itself
                soup = BeautifulSoup(res.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                page_text = soup.get_text(separator=" ", strip=True)
                if len(page_text) > 100:
                    job["snippet"] = page_text[:20000]
                    job["source"] = "enriched_direct_page"
            
            return job
    
    except Exception:
        return job


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def search_and_enrich(
    role: str,
    location: str,
    company: str = "",
    max_results: int = 30,
    enrich_top: int = 10,
    skills: list[str] | None = None,
) -> list[dict]:
    """Search for jobs using multiple sources and enrich top results.
    
    Sources (in order):
    1. Greenhouse/Lever public APIs (if company specified)
    2. DuckDuckGo web search
    
    Args:
        role: Job title/role
        location: City/location
        company: Optional company name to focus on
        max_results: Total results to fetch (25-50)
        enrich_top: How many top results to fetch full details for
        skills: Optional list of candidate skills for targeted search
    
    Returns:
        List of enriched job dicts
    """
    rate_limiter = RateLimiter(requests_per_minute=12, min_delay=2.0, max_delay=8.0)
    all_jobs = []
    seen_urls = set()
    
    # Source 1: Greenhouse/Lever APIs if company specified
    if company:
        # Try common slug variations
        slug_variations = [
            company.lower().replace(" ", "-"),
            company.lower().replace(" ", ""),
        ]
        
        for slug in slug_variations:
            if len(all_jobs) >= max_results // 2:
                break
            
            # Try Greenhouse
            gh_jobs = await fetch_greenhouse_jobs(slug, rate_limiter)
            for job in gh_jobs:
                url = job.get("apply_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_jobs.append(job)
            
            # Try Lever
            if len(all_jobs) < max_results // 2:
                lever_jobs = await fetch_lever_jobs(slug, rate_limiter)
                for job in lever_jobs:
                    url = job.get("apply_url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_jobs.append(job)
    
    # Source 2: DuckDuckGo web search
    if len(all_jobs) < max_results:
        web_jobs = await search_jobs_via_web(
            role, location, company,
            max_results=max_results - len(all_jobs),
            rate_limiter=rate_limiter,
            skills=skills,
        )
        for job in web_jobs:
            url = job.get("apply_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(job)
    
    # Enrich top results
    enriched = []
    for i, job in enumerate(all_jobs[:max_results]):
        if i < enrich_top:
            enriched_job = await enrich_job_from_page(job)
            enriched.append(enriched_job)
            await asyncio.sleep(random.uniform(1.0, 3.0))
        else:
            enriched.append(job)
    
    log.info(
        "search_complete",
        role=role,
        location=location,
        total=len(enriched),
        sources="greenhouse+lever+ddgs" if company else "ddgs",
    )
    
    return enriched
