"""
JobHunterX — Job Discovery Engine (DuckDuckGo + Career Page Scraping)

The core of the new architecture: finds REAL jobs at Indian companies
using free DuckDuckGo search + direct career page scraping.

Why this works:
  - DuckDuckGo search is FREE, no API key, no credits, no limits (with
    reasonable rate limiting).
  - Searches target the actual job postings on company websites, job
    boards, and career pages — NOT aggregator noise.
  - Focused on India: queries are crafted to surface jobs at Indian
    locations for the user's profile.
  - Finds startups and hidden companies that people don't know about.
  - Avoids mass-hiring spam (TCS, Infosys, Wipro, etc.).

Flow:
  1. Build smart search queries from the user's profile (role, skills, location)
  2. Run DuckDuckGo text searches (batched, rate-limited)
  3. Extract job posting URLs from search results
  4. Scrape each URL for job details (title, company, location, JD)
  5. Return structured job dicts for scoring/storage
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.config.logging import get_logger

log = get_logger("job_discovery")

MASS_HIRING_BLACKLIST = {
    "tcs", "infosys", "wipro", "hcl", "cognizant", "tech mahindra",
    "capgemini", "accenture", "mindtree", "mphasis", "ltimindtree",
    "hexaware", "cyient", "persistent", "birlasoft", "zensar",
    "tata consultancy", "l&t infotech", "larsen", "nttdata",
    "virtusa", "ust global", "ust", "epam", "dxc technology",
    "unisys", "atos", "sopra steria", "firstsource",
}

AGGREGATOR_DOMAINS = {
    "linkedin.com", "indeed.com", "indeed.co.in",
    "glassdoor.com", "glassdoor.co.in", "glassdoor.co.uk",
    "naukri.com", "monster.com", "monster.co.in", "monsterindia.com",
    "shine.com", "timesjobs.com", "foundit.in",
    "instahyre.com", "hirist.com", "cutshort.io",
    "ziprecruiter.com", "simplyhired.com", "simplyhired.co.in",
    "jooble.org", "careerjet.co.in", "jobrapido.com", "adzuna.in",
    "google.com/search", "bing.com", "duckduckgo.com",
    "quora.com", "reddit.com", "youtube.com",
    "facebook.com", "twitter.com", "instagram.com",
    "placementindia.com", "freshersworld.com", "iimjobs.com",
    "internshala.com", "apna.co", "hirect.in",
    "workindia.in", "meetro.in", "rozgaar.com",
    "talent.com", "6figr.com", "ambitionbox.com",
    "wellfound.com", "angel.co",
    "boringdude.in", "indiabharti.in",
    "remoterocketship.com", "dailyremote.com", "jobtogether.com", "jobgether.com",
    "startup.jobs", "startupjobs.com", "remoteco.com", "remote.co",
    "weworkremotely.com", "remoteok.com", "remoteok.io", "jobspresso.co",
    "himalayas.app", "flexjobs.com", "workingnomads.co", "workingnomads.com",
    "jobserf.com", "postjobfree.com", "bebee.com", "careerbuilder.com",
    "lensa.com", "jobisite.com", "jobisjob.com", "jora.com", "jobindex.dk",
    "trovit.com", "careerarc.com", "snagajob.com", "jobtarget.com",
}

CAREER_PAGE_PATTERNS = [
    r"/careers", r"/jobs", r"/openings", r"/join-us", r"/work-with-us",
    r"/hiring", r"/vacancies", r"/positions", r"/apply",
    r"boards\.greenhouse\.io", r"jobs\.lever\.co", r"jobs\.ashbyhq\.com",
    r"\.recruitee\.com", r"careers\.smartrecruiters\.com",
    r"\.bamboohr\.com/careers", r"\.freshteam\.com",
    r"\.workable\.com", r"\.breezy\.hr",
    r"angel\.co/company", r"wellfound\.com/company",
]

INDIA_CITIES = [
    "bangalore", "bengaluru", "hyderabad", "mumbai", "pune", "chennai",
    "delhi", "ncr", "noida", "gurugram", "gurgaon", "kolkata",
    "ahmedabad", "kochi", "indore", "jaipur", "chandigarh",
    "thiruvananthapuram", "coimbatore", "visakhapatnam", "vizag",
    "nagpur", "lucknow", "bhopal", "mysore", "mangalore",
]


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    company: str = ""
    is_job_posting: bool = False


def _is_blacklisted_company(name: str) -> bool:
    name_low = name.lower().strip()
    for bl in MASS_HIRING_BLACKLIST:
        if bl in name_low:
            return True
    return False


def _is_aggregator(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        for agg in AGGREGATOR_DOMAINS:
            if agg in domain:
                return True
    except Exception:
        pass
    return False


def _looks_like_job_url(url: str) -> bool:
    url_low = url.lower()
    for pat in CAREER_PAGE_PATTERNS:
        if re.search(pat, url_low):
            return True
    job_keywords = ["/job/", "/role/", "/position/", "/vacancy/",
                    "/opening/", "/career/", "/posting/"]
    for kw in job_keywords:
        if kw in url_low:
            return True
    return False


def _extract_company_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        domain = re.sub(r"^www\.", "", domain)

        # 1. Known ATS board URL patterns (where path contains company name)
        if "greenhouse.io" in domain:
            m = re.search(r"boards\.greenhouse\.io/(\w+)", url)
            return m.group(1).title() if m else ""
        if "lever.co" in domain:
            m = re.search(r"jobs\.lever\.co/(\w[\w-]*)", url)
            return m.group(1).replace("-", " ").title() if m else ""
        if "ashbyhq.com" in domain:
            m = re.search(r"jobs\.ashbyhq\.com/(\w[\w-]*)", url)
            return m.group(1).replace("-", " ").title() if m else ""
        if "workable.com" in domain:
            m = re.search(r"apply\.workable\.com/(\w[\w-]*)", url)
            return m.group(1).replace("-", " ").title() if m else ""

        # 2. Skip aggregator or job board domains — do NOT treat job board domain as company name
        if _is_aggregator(url):
            return ""

        domain_low = domain.lower()
        if any(kw in domain_low for kw in ["job", "career", "hiring", "recruit", "work", "apply", "talent", "search", "board", "portal"]):
            return ""

        # 3. Direct company site domain name (e.g. zimperium.com -> Zimperium, splitero.com -> Splitero)
        parts = domain.split(".")
        if len(parts) >= 2:
            comp = parts[-2].replace("-", " ").title()
            if len(comp) >= 3 and len(comp) < 30:
                return comp
    except Exception:
        pass
    return ""


GARBAGE_COMPANY_WORDS = {
    "вакансии", "ищет", "команду", "кнопка", "откликнуться",
    "careers", "jobs", "hiring", "openings", "apply", "job board", "portal",
    "top 2025", "fresher", "freshers", "overview", "home", "index", "about us",
    "freelancer", "freelance", "contract", "salary", "reviews", "salaries",
    "workfromhome", "remote jobs", "software engineer", "ai engineer", "developer",
}

def _clean_company_name(name: str) -> str:
    if not name:
        return ""
    name_clean = re.sub(r"\s+", " ", name).strip()
    # If contains non-Latin scripts that indicate foreign garbage search results (e.g. Cyrillic)
    if re.search(r"[\u0400-\u04FF]", name_clean):
        return ""
    # Strip common trailing noisy suffixes
    name_clean = re.sub(r"\s*[-|·—].*$", "", name_clean).strip()
    name_clean = re.sub(r"\b(Inc|LLC|Ltd|Pvt|Private|Limited|Corp|Corporation|Co)\.?$", "", name_clean, flags=re.I).strip()
    
    low = name_clean.lower()
    if any(g in low for g in ["hiring at", "fresher jobs", "vacancies", "freelancer"]):
        return ""
    if len(name_clean) < 2 or len(name_clean) > 40:
        return ""
    return name_clean


def _extract_company_from_title(title: str) -> str:
    if not title:
        return ""
    # Reject non-English / Cyrillic titles outright
    if re.search(r"[\u0400-\u04FF]", title):
        return ""

    patterns = [
        r"(?:at|@)\s+([A-Za-z0-9\s&\.\-]{2,35})(?:\s*[-|·—]|$)",
        r"^([A-Za-z0-9\s&\.]{2,30})\s+(?:is hiring|careers|jobs|openings|hiring)",
        r"^([A-Za-z0-9\s&\.]{2,30})\s*[-|·—]\s*(?:Software|AI|Backend|Frontend|Full|Data|Machine|ML|DevOps)",
    ]
    for pat in patterns:
        m = re.search(pat, title, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            candidate = _clean_company_name(candidate)
            if candidate and candidate.lower() not in GARBAGE_COMPANY_WORDS:
                return candidate
    return ""


def build_search_queries(profile: dict, plan: dict) -> list[str]:
    """Build targeted DuckDuckGo search queries for Indian job market.

    Strategy: multiple focused queries instead of one broad one.
    Each query is designed to surface different types of opportunities.
    """
    queries = []

    target_roles = plan.get("target_roles") or []
    if not target_roles:
        role = (profile.get("suggested_role") or "software engineer").lower()
        target_roles = [role]

    locations = plan.get("locations") or []
    if not locations:
        loc = profile.get("location") or "Bangalore"
        locations = [loc]

    skills = (profile.get("skills") or [])[:8]
    years = float(plan.get("years_experience") or 0)
    seniority = plan.get("seniority_max") or "entry"

    exp_terms = []
    if years < 1:
        exp_terms = ["fresher", "entry level", "0-1 years", "freshers", "graduate"]
    elif years < 3:
        exp_terms = ["1-3 years", "junior", "associate"]
    elif years < 5:
        exp_terms = ["3-5 years", "mid level"]
    else:
        exp_terms = [f"{int(years)}+ years", "experienced"]

    india_locations = []
    for loc in locations:
        loc_low = loc.lower().strip()
        if loc_low == "remote":
            india_locations.append("remote")
        elif any(c in loc_low for c in INDIA_CITIES):
            india_locations.append(loc)
        else:
            india_locations.append(loc)

    primary_role = target_roles[0] if target_roles else "software engineer"

    for loc in india_locations[:3]:
        suffix = "India" if loc.lower() != "remote" else ""
        queries.append(f'"{primary_role}" hiring {loc} {suffix} 2026'.strip())

    if len(target_roles) > 1:
        for role in target_roles[1:3]:
            loc = india_locations[0] if india_locations else "India"
            queries.append(f'"{role}" jobs {loc} India')

    if years < 1:
        for loc in india_locations[:2]:
            queries.append(f'"{primary_role}" fresher hiring {loc} 2026')
        queries.append(f'{primary_role} freshers India startup hiring 2026')

    top_skills = skills[:3]
    if top_skills:
        skill_str = " ".join(top_skills)
        loc = india_locations[0] if india_locations else "India"
        queries.append(f'{skill_str} developer jobs {loc} India startup')

    for loc in india_locations[:2]:
        queries.append(f'startup hiring {primary_role} {loc} India careers')

    queries.append(f'{primary_role} India startup careers page hiring 2026')

    if top_skills:
        queries.append(f'{" ".join(top_skills[:2])} hiring India careers apply')

    for loc in india_locations[:2]:
        if exp_terms:
            queries.append(f'{primary_role} {exp_terms[0]} {loc} India hiring')

    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = re.sub(r"\s+", " ", q).strip()
        q_norm = q_clean.lower()
        if q_norm not in seen:
            seen.add(q_norm)
            unique_queries.append(q_clean)

    return unique_queries[:15]


async def search_ddg(query: str, max_results: int = 15) -> list[SearchResult]:
    """Run a single DuckDuckGo search and return parsed results."""

    def _search() -> list[dict]:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=max_results,
                    region="in-en",
                ))
                return results
        except Exception as exc:
            log.warning("ddg_search_failed", query=query[:60], error=str(exc)[:120])
            return []

    raw = await asyncio.to_thread(_search)
    results = []
    for r in raw:
        url = r.get("href") or r.get("url") or ""
        title = r.get("title") or ""
        snippet = r.get("body") or r.get("snippet") or ""

        if not url or _is_aggregator(url):
            continue

        company = _extract_company_from_url(url) or _extract_company_from_title(title)
        if _is_blacklisted_company(company) or _is_blacklisted_company(title):
            continue

        is_job = _looks_like_job_url(url) or any(
            kw in title.lower() for kw in
            ["hiring", "job", "career", "opening", "apply", "position", "vacancy",
             "engineer", "developer", "analyst", "designer", "intern"]
        )

        results.append(SearchResult(
            title=title,
            url=url,
            snippet=snippet,
            company=company,
            is_job_posting=is_job,
        ))

    return results


async def scrape_job_page(url: str) -> dict:
    """Scrape a job posting URL to extract structured data.

    Returns: {title, company, location, jd_text, apply_url}
    """
    from jobhunterx.tools.ats_client import fetch_page

    try:
        html = await fetch_page(url, timeout=10.0)
    except Exception as exc:
        log.debug("scrape_job_page_failed", url=url[:80], error=str(exc)[:100])
        return {}

    if not html or len(html) < 200:
        return {}

    from bs4 import BeautifulSoup

    def _parse(html_content: str, page_url: str) -> dict:
        soup = BeautifulSoup(html_content, "html.parser")
        data = {}

        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title_el = soup.find("h1")
        if title_el:
            data["title"] = title_el.get_text(strip=True)[:200]

        if not data.get("title"):
            og = soup.find("meta", property="og:title")
            if og:
                data["title"] = (og.get("content") or "")[:200]

        if not data.get("title"):
            title_tag = soup.find("title")
            if title_tag:
                data["title"] = title_tag.get_text(strip=True)[:200]

        body_text = soup.get_text(separator=" ", strip=True)
        body_text = re.sub(r"\s+", " ", body_text)[:6000]
        data["jd_text"] = body_text

        loc_markers = []
        for city in INDIA_CITIES:
            if city in body_text.lower():
                loc_markers.append(city.title())
        if "remote" in body_text.lower():
            loc_markers.append("Remote")
        if loc_markers:
            data["location"] = ", ".join(loc_markers[:3])

        company = _extract_company_from_url(page_url)
        og_site = soup.find("meta", property="og:site_name")
        if og_site:
            company = (og_site.get("content") or company or "")[:100]
        data["company"] = company

        ld_json = soup.find("script", type="application/ld+json")
        if ld_json:
            try:
                import json
                ld = json.loads(ld_json.string or "")
                if isinstance(ld, list):
                    ld = next((x for x in ld if x.get("@type") == "JobPosting"), ld[0] if ld else {})
                if isinstance(ld, dict):
                    if ld.get("@type") == "JobPosting":
                        data["title"] = data.get("title") or ld.get("title", "")
                        org = ld.get("hiringOrganization") or {}
                        if isinstance(org, dict):
                            data["company"] = org.get("name") or data.get("company", "")
                        jl = ld.get("jobLocation")
                        if isinstance(jl, dict):
                            addr = jl.get("address") or {}
                            if isinstance(addr, dict):
                                city = addr.get("addressLocality", "")
                                region = addr.get("addressRegion", "")
                                data["location"] = f"{city}, {region}".strip(", ") or data.get("location", "")
                        desc = ld.get("description", "")
                        if desc and len(desc) > len(data.get("jd_text", "")):
                            clean = re.sub(r"<[^>]+>", " ", desc)
                            data["jd_text"] = re.sub(r"\s+", " ", clean)[:6000]
            except Exception:
                pass

        _APPLY_LINK_PATTERNS = [
            "greenhouse.io", "lever.co", "ashbyhq.com", "recruitee.com",
            "smartrecruiters.com", "bamboohr.com", "freshteam.com",
            "workable.com", "breezy.hr", "myworkdayjobs.com",
            "careers.", "jobs.", "/careers/", "/jobs/", "/apply",
        ]
        _APPLY_ANCHOR_TEXTS = [
            "apply now", "apply here", "apply for this job",
            "apply online", "click here to apply", "apply",
            "apply for this position", "apply for this role",
        ]

        best_apply_url = page_url
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            text = (a.get_text(strip=True) or "").lower()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            from urllib.parse import urljoin
            full_href = urljoin(page_url, href)
            href_low = full_href.lower()
            if any(pat in href_low for pat in _APPLY_LINK_PATTERNS):
                if not _is_aggregator(full_href):
                    best_apply_url = full_href
                    break
            if any(t in text for t in _APPLY_ANCHOR_TEXTS):
                if not _is_aggregator(full_href) and full_href != page_url:
                    best_apply_url = full_href
                    break

        data["apply_url"] = best_apply_url
        data["career_page_url"] = best_apply_url if best_apply_url != page_url else page_url
        return data

    return await asyncio.to_thread(_parse, html, url)


async def discover_jobs(
    profile: dict,
    plan: dict,
    max_queries: int = 12,
    results_per_query: int = 12,
    max_scrape: int = 40,
    scrape_concurrency: int = 6,
    inter_query_delay: float = 1.5,
    event_cb=None,
) -> list[dict]:
    """Full discovery pipeline: search → filter → scrape → structure.

    Args:
        profile: candidate profile dict
        plan: search plan from search_planner
        max_queries: how many DDG queries to run
        results_per_query: results per query
        max_scrape: max URLs to scrape for job details
        scrape_concurrency: parallel scrape workers
        inter_query_delay: seconds between DDG queries (rate limit)
        event_cb: async callback for progress events

    Returns: list of job dicts ready for scoring/storage
    """

    async def emit(msg: str):
        if event_cb:
            try:
                await event_cb({
                    "agent": "job_discovery",
                    "event_type": "progress",
                    "message": msg,
                })
            except Exception:
                pass

    queries = build_search_queries(profile, plan)[:max_queries]
    await emit(f"Built {len(queries)} search queries for {plan.get('locations', ['India'])}")

    all_results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for i, query in enumerate(queries):
        await emit(f"[{i+1}/{len(queries)}] Searching: {query[:60]}...")
        results = await search_ddg(query, max_results=results_per_query)
        for r in results:
            norm_url = r.url.rstrip("/").lower()
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                all_results.append(r)
        if i < len(queries) - 1:
            await asyncio.sleep(inter_query_delay)

    log.info("ddg_search_complete", total_queries=len(queries),
             unique_results=len(all_results))
    await emit(f"Found {len(all_results)} unique results from {len(queries)} searches")

    job_results = [r for r in all_results if r.is_job_posting]
    non_job = [r for r in all_results if not r.is_job_posting]

    to_scrape = job_results[:max_scrape]
    remaining = max_scrape - len(to_scrape)
    if remaining > 0:
        to_scrape.extend(non_job[:remaining])

    await emit(f"Scraping {len(to_scrape)} promising URLs for job details...")

    sem = asyncio.Semaphore(scrape_concurrency)

    async def scrape_one(result: SearchResult) -> Optional[dict]:
        async with sem:
            data = await scrape_job_page(result.url)
            if not data or not data.get("jd_text"):
                return None
            data["company"] = data.get("company") or result.company or ""
            data["title"] = data.get("title") or result.title or ""
            data["search_snippet"] = result.snippet
            data["source"] = "ddg_search"
            return data

    scraped = await asyncio.gather(*(scrape_one(r) for r in to_scrape))
    jobs = [j for j in scraped if j is not None]

    valid_jobs = []
    for job in jobs:
        company = job.get("company", "")
        if _is_blacklisted_company(company):
            continue
        if not job.get("title") and not job.get("jd_text"):
            continue
        title = job.get("title") or ""
        jd = job.get("jd_text") or ""
        combined = f"{title} {jd}".lower()
        has_india = any(c in combined for c in INDIA_CITIES) or "india" in combined or "remote" in combined
        if not has_india and not job.get("location"):
            continue
        valid_jobs.append(job)

    log.info("discovery_complete", scraped=len(jobs), valid=len(valid_jobs))
    await emit(f"Discovery complete: {len(valid_jobs)} valid jobs from {len(jobs)} scraped pages")

    return valid_jobs


async def scrape_career_page_jobs(
    companies: list[dict],
    concurrency: int = 5,
    event_cb=None,
) -> list[dict]:
    """Scrape career pages of known companies for direct job listings.

    This complements DuckDuckGo search — for seed companies we visit their
    career pages directly and extract any visible job links.
    """
    from jobhunterx.tools.ats_client import fetch_page
    from bs4 import BeautifulSoup

    async def emit(msg: str):
        if event_cb:
            try:
                await event_cb({
                    "agent": "job_discovery",
                    "event_type": "progress",
                    "message": msg,
                })
            except Exception:
                pass

    sem = asyncio.Semaphore(concurrency)
    all_jobs: list[dict] = []

    async def scrape_company(comp: dict) -> list[dict]:
        async with sem:
            name = comp.get("name", "")
            website = (comp.get("website") or "").rstrip("/")
            careers_url = comp.get("careers_url") or ""

            urls_to_try = []
            if careers_url:
                urls_to_try.append(careers_url)
            if website:
                urls_to_try.append(f"{website}/careers")
                urls_to_try.append(f"{website}/jobs")

            found_jobs = []
            for url in urls_to_try[:2]:
                try:
                    html = await fetch_page(url, timeout=8.0)
                except Exception:
                    continue
                if not html or len(html) < 500:
                    continue

                def _extract(html_text: str, base: str, company_name: str):
                    soup = BeautifulSoup(html_text, "html.parser")
                    links = []
                    seen = set()
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if not href or href.startswith("#") or href.startswith("javascript:"):
                            continue
                        from urllib.parse import urljoin
                        full = urljoin(base, href)
                        if full in seen:
                            continue
                        text = a.get_text(strip=True)[:150]
                        if not text or len(text) < 3:
                            continue
                        if _is_aggregator(full):
                            continue
                        url_low = full.lower()
                        is_job_link = any(kw in url_low for kw in
                            ["/job/", "/jobs/", "/openings/", "/position/",
                             "/apply/", "/career/", "/posting/",
                             "greenhouse.io", "lever.co", "ashbyhq.com"])
                        if not is_job_link:
                            continue
                        seen.add(full)
                        links.append({
                            "title": text,
                            "apply_url": full,
                            "company": company_name,
                            "source": "career_page",
                            "career_page_url": base,
                        })
                    return links[:20]

                page_jobs = await asyncio.to_thread(_extract, html, url, name)
                found_jobs.extend(page_jobs)
                if found_jobs:
                    break

            return found_jobs

    companies_to_scrape = [c for c in companies if not _is_blacklisted_company(c.get("name", ""))]
    results = await asyncio.gather(*(scrape_company(c) for c in companies_to_scrape))

    for company_jobs in results:
        all_jobs.extend(company_jobs)

    if all_jobs:
        await emit(f"Found {len(all_jobs)} job links from {len(companies_to_scrape)} company career pages")

    return all_jobs
