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
    "aijobs.net", "aijobs.dev",
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


_DIRECT_JOB_URL_PATTERNS = [
    r"linkedin\.com/jobs/(?:view|collections)",
    r"indeed\.(?:com|co\.in)/(?:viewjob|job)",
    r"foundit\.in/job",
    r"naukri\.com/job-listings",
    r"hirist\.(?:com|tech)/j/",
    r"cutshort\.io/job",
    r"wellfound\.com/jobs",
    r"boards\.greenhouse\.io",
    r"jobs\.lever\.co",
    r"jobs\.ashbyhq\.com",
    r"apply\.workable\.com",
    r"careers\.smartrecruiters\.com",
    r"jobs\.smartrecruiters\.com",
    r"\.bamboohr\.com/careers",
    r"\.freshteam\.com/jobs",
    r"\.breezy\.hr/p/",
    r"myworkdayjobs\.com",
]


def _is_direct_job_url(url: str) -> bool:
    url_low = url.lower()
    for pat in _DIRECT_JOB_URL_PATTERNS:
        if re.search(pat, url_low):
            return True
    return False


def _is_aggregator(url: str) -> bool:
    if _is_direct_job_url(url):
        return False
    try:
        url_low = url.lower()
        domain = urlparse(url).netloc.lower()
        for agg in AGGREGATOR_DOMAINS:
            if agg in domain or agg in url_low:
                return True
    except Exception:
        pass
    return False


def _looks_like_job_url(url: str) -> bool:
    if _is_direct_job_url(url):
        return True
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
    target_loc_name = india_locations[0] if india_locations else "India"
    loc_str = "India remote" if target_loc_name.lower() == "remote" else f'"{target_loc_name}" India'

    for loc in india_locations[:3]:
        suf = "India" if loc.lower() != "remote" else "India remote"
        queries.append(f'"{primary_role}" hiring "{loc}" {suf}'.strip())

    if len(target_roles) > 1:
        for role in target_roles[1:3]:
            queries.append(f'"{role}" jobs {loc_str}')

    if years < 1:
        for loc in india_locations[:2]:
            queries.append(f'"{primary_role}" fresher hiring "{loc}" India')
        queries.append(f'"{primary_role}" freshers {loc_str} startup hiring')

    top_skills = skills[:3]
    if top_skills:
        skill_str = " ".join(top_skills)
        queries.append(f'{skill_str} developer jobs {loc_str} startup')

    for loc in india_locations[:2]:
        queries.append(f'startup hiring "{primary_role}" "{loc}" India careers')

    queries.append(f'"{primary_role}" {loc_str} startup careers page hiring')

    if top_skills:
        queries.append(f'{" ".join(top_skills[:2])} hiring {loc_str} careers apply')

    for loc in india_locations[:2]:
        if exp_terms:
            queries.append(f'"{primary_role}" {exp_terms[0]} "{loc}" India hiring')

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


async def search_via_router(
    query: str,
    context,
    config: dict | None = None,
) -> list[SearchResult]:
    """Run a single query through the sequential search router.

    Router priority: TinyFish (0 credits) -> Tavily (1 credit) -> Exa ($0.007)
    -> DDGS (0 credits), halted early by the context-aware Quality Gate.
    Results are normalized with the same aggregator/blacklist filters as
    search_ddg(). Returns [] if the router yields nothing usable.
    """
    from jobhunterx.tools.search_router import route_search_queries

    cfg = config or {}
    if not cfg.get("MAX_SEARCH_QUERIES_PER_RUN"):
        cfg = {**cfg, "MAX_SEARCH_QUERIES_PER_RUN": 1}
    try:
        items = await route_search_queries([query], context=context, config=cfg)
    except Exception as exc:
        log.warning("router_search_failed", query=query[:60], error=str(exc)[:120])
        return []

    results = []
    for it in items:
        url = (it.url or "").strip()
        title = it.title or ""
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
            snippet=it.snippet or "",
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

        # 1. Parse structured JSON-LD JobPosting FIRST (before decomposing script tags!)
        for ld_json in soup.find_all("script", type="application/ld+json"):
            try:
                if not ld_json.string:
                    continue
                import json
                ld = json.loads(ld_json.string)
                if isinstance(ld, list):
                    ld = next((x for x in ld if isinstance(x, dict) and x.get("@type") == "JobPosting"), ld[0] if ld else {})
                if isinstance(ld, dict) and ld.get("@type") == "JobPosting":
                    if ld.get("title"):
                        data["title"] = str(ld["title"])[:200]
                    org = ld.get("hiringOrganization") or {}
                    if isinstance(org, dict) and org.get("name"):
                        data["company"] = str(org["name"])[:100]
                    jl = ld.get("jobLocation")
                    if isinstance(jl, list):
                        jl = jl[0] if jl else {}
                    if isinstance(jl, dict):
                        addr = jl.get("address") or {}
                        if isinstance(addr, dict):
                            city = addr.get("addressLocality", "")
                            region = addr.get("addressRegion", "")
                            country = addr.get("addressCountry", "")
                            if isinstance(country, dict):
                                country = country.get("name") or country.get("addressCountry") or ""
                            parts = [p for p in (city, region, country) if p]
                            if parts:
                                data["location"] = ", ".join(parts)[:150]
                    elif isinstance(jl, str) and jl.strip():
                        data["location"] = jl.strip()[:150]
                    
                    desc = ld.get("description", "")
                    if desc and len(desc) > 100:
                        clean = re.sub(r"<[^>]+>", " ", desc)
                        data["jd_text"] = re.sub(r"\s+", " ", clean)[:6000]
            except Exception:
                pass

        # 2. Extract OpenGraph and Meta tags
        og_site = soup.find("meta", property="og:site_name")
        if og_site and not data.get("company"):
            data["company"] = (og_site.get("content") or "")[:100]

        if not data.get("company"):
            data["company"] = _extract_company_from_url(page_url)

        if not data.get("title"):
            h1 = soup.find("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)[:200]

        if not data.get("title"):
            og_title = soup.find("meta", property="og:title")
            if og_title:
                data["title"] = (og_title.get("content") or "")[:200]

        if not data.get("title"):
            title_tag = soup.find("title")
            if title_tag:
                data["title"] = title_tag.get_text(strip=True)[:200]

        # 3. Specific location element extraction if JSON-LD location was not found
        if not data.get("location"):
            meta_loc = soup.find("meta", attrs={"name": re.compile(r"job:location|location", re.I)})
            if meta_loc and meta_loc.get("content"):
                data["location"] = meta_loc.get("content").strip()[:150]

        if not data.get("location"):
            loc_el = soup.find(class_=re.compile(r"location|job-location|posting-category", re.I))
            if loc_el:
                loc_txt = loc_el.get_text(separator=" ", strip=True)
                if loc_txt and len(loc_txt) < 100:
                    data["location"] = loc_txt

        # Specific portal extractors (LinkedIn, Indeed, FoundIt, Naukri, Instahyre)
        low_url = page_url.lower()
        if "linkedin.com" in low_url:
            comp_el = soup.find(class_=re.compile(r"topcard__flavor|top-card-layout__first-sub-row|company-name", re.I))
            if comp_el and not data.get("company"):
                data["company"] = comp_el.get_text(strip=True)[:100]
            loc_el = soup.find(class_=re.compile(r"topcard__flavor--bullet|top-card-layout__second-sub-row|location", re.I))
            if loc_el and not data.get("location"):
                data["location"] = loc_el.get_text(strip=True)[:100]
            desc_el = soup.find(class_=re.compile(r"description__text|show-more-less-html", re.I))
            if desc_el:
                clean_desc = re.sub(r"\s+", " ", desc_el.get_text(separator=" ", strip=True))
                if len(clean_desc) > 100:
                    data["jd_text"] = clean_desc[:6000]

        elif "indeed." in low_url:
            comp_el = soup.find(attrs={"data-testid": "inlineHeader-companyName"}) or soup.find(class_=re.compile(r"companyName", re.I))
            if comp_el and not data.get("company"):
                data["company"] = comp_el.get_text(strip=True)[:100]
            loc_el = soup.find(attrs={"data-testid": "inlineHeader-companyLocation"}) or soup.find(class_=re.compile(r"companyLocation", re.I))
            if loc_el and not data.get("location"):
                data["location"] = loc_el.get_text(strip=True)[:100]

        elif "foundit.in" in low_url:
            comp_el = soup.find(class_=re.compile(r"company-name|employer-name", re.I))
            if comp_el and not data.get("company"):
                data["company"] = comp_el.get_text(strip=True)[:100]
            loc_el = soup.find(class_=re.compile(r"location|job-location", re.I))
            if loc_el and not data.get("location"):
                data["location"] = loc_el.get_text(strip=True)[:100]

        elif "naukri.com" in low_url:
            comp_el = soup.find(class_=re.compile(r"jd-header-comp-name|comp-name", re.I))
            if comp_el and not data.get("company"):
                data["company"] = comp_el.get_text(strip=True)[:100]
            loc_el = soup.find(class_=re.compile(r"location|loc", re.I))
            if loc_el and not data.get("location"):
                data["location"] = loc_el.get_text(strip=True)[:100]

        # 4. Clean noise elements for body text extraction
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "svg", "iframe"]):
            tag.decompose()

        if not data.get("jd_text"):
            body_text = soup.get_text(separator=" ", strip=True)
            body_text = re.sub(r"\s+", " ", body_text)[:6000]
            data["jd_text"] = body_text
        else:
            body_text = data["jd_text"]

        # 5. Fallback location extraction if still unknown
        if not data.get("location"):
            loc_markers = []
            for city in INDIA_CITIES:
                if city in body_text.lower():
                    loc_markers.append(city.title())
            if "remote" in body_text.lower():
                loc_markers.append("Remote")
            if loc_markers:
                data["location"] = ", ".join(loc_markers[:3])
            else:
                body_low = body_text.lower()
                foreign_found = []
                for f_marker in ("russia", "moscow", "saint petersburg", "united states", "usa", "san francisco", "new york", "uk", "london", "berlin", "canada", "toronto"):
                    if f_marker in body_low:
                        foreign_found.append(f_marker.title())
                if foreign_found:
                    data["location"] = ", ".join(foreign_found[:2])

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
    """Full discovery pipeline: SearchRouter -> QualityGate -> FetchPipeline -> Structure."""
    from jobhunterx.config.settings import get_settings
    from jobhunterx.tools.quality_gate import SearchContext
    from jobhunterx.tools.search_router import route_search_queries
    from jobhunterx.tools.fetch_pipeline import execute_fetch_pipeline

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

    s = get_settings()
    target_roles = plan.get("target_roles") or [profile.get("suggested_role") or "Software Engineer"]
    locations = plan.get("locations") or [profile.get("location") or "Hyderabad"]

    context = SearchContext(
        target_role=target_roles[0],
        target_location=locations[0],
        experience_level=float(plan.get("years_experience") or 0),
        remote_preference=profile.get("work_type", "hybrid"),
        freshness_requirement="recent",
    )

    cfg = {
        "SEARCH_ROUTER_MODE": s.search_router_mode,
        "PRIMARY_SEARCH_PROVIDER": s.primary_search_provider,
        "STRICT_ZERO_SPEND_PROTECTION": s.strict_zero_spend_protection,
        "QUALITY_SCORE_THRESHOLD": s.quality_score_threshold,
        "TINYFISH_API_KEY": s.tinyfish_api_key,
        "TAVILY_API_KEY": s.tavily_api_key,
        "EXA_API_KEY": s.exa_api_key,
        "BRAVE_API_KEY": s.brave_api_key,
        "BRAVE_ENABLED": s.brave_enabled,
    }

    queries = build_search_queries(profile, plan)[:max_queries]
    await emit(f"Built {len(queries)} search queries for {locations}")

    if getattr(s, "enable_web_search_apis", True):
        serp_items = await route_search_queries(queries, context=context, config=cfg)
        await emit(f"Discovered {len(serp_items)} search results across providers")
        urls_to_fetch = [item.url for item in serp_items]
    else:
        await emit("Web Search APIs disabled in settings. Using direct scraper fallback...")
        urls_to_fetch = []

    if not urls_to_fetch:
        # Fallback to direct DDG search if disabled or no provider results
        for q in queries[:4]:
            ddg_res = await search_ddg(q, max_results=10)
            urls_to_fetch.extend([r.url for r in ddg_res])

    await emit(f"Fetching job details for {len(urls_to_fetch[:max_scrape])} candidate URLs...")
    extracted_jobs = await execute_fetch_pipeline(urls_to_fetch, max_fetch=max_scrape, config=cfg)

    valid_jobs = []
    for job in extracted_jobs:
        company = job.get("company", "")
        if _is_blacklisted_company(company):
            continue
        if not job.get("title") and not job.get("jd_text"):
            continue
        valid_jobs.append(job)

    log.info("discover_jobs_complete", valid_jobs_count=len(valid_jobs))
    await emit(f"Extracted {len(valid_jobs)} valid job postings")
    return valid_jobs

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
