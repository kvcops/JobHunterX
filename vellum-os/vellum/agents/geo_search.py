"""
Vellum OS — India-Native Career Search Agent (Agent A)

Multi-source Indian startup & tech hiring discovery:
  - Primary: Web search via DuckDuckGo (free, no API key)
  - Secondary: Public ATS APIs (Greenhouse, Lever, Ashby)
  - Tertiary: VC Portfolio boards (Getro-powered)

All discovery is direct and structured. No paid APIs.
"""

from __future__ import annotations

import asyncio
import re

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import ats_api, web_search_scraper
from vellum.models import JobListing, AgentEvent
from vellum.api.ws import manager as ws_manager
from vellum.utils.job_cleaner import clean_job_title_and_company

log = get_logger("geo_search")

MAX_TOTAL_JOBS = 80


def _effective_max_jobs(limit: int) -> int:
    """Scale the hard cap with the requested limit so big targets can be met.

    Rounds up to the next multiple of the requested limit (min 80, max 600).
    """
    target = max(int(limit), 10)
    return max(80, min(600, target * 2))


def _normalise_city(location: str) -> str:
    """Normalise city name for Indian tech hub lookup."""
    city = location.lower().strip()
    aliases = {
        "bangalore": "bengaluru",
        "bombay": "mumbai",
        "madras": "chennai",
        "calcutta": "kolkata",
        "gurgaon": "ncr",
        "gurugram": "ncr",
        "noida": "ncr",
        "delhi": "ncr",
    }
    return aliases.get(city, city)


# Quality filters
JD_KEYWORDS = [
    "experience", "skill", "responsibilit", "qualification",
    "requirement", "role", "position", "job", "work",
    "team", "develop", "manage", "lead", "design", "build",
    "engineer", "analyst", "specialist", "coordinator",
    "salary", "benefit", "location", "report", "degree",
]

NON_JOB_TITLE_PATTERNS = [
    r"^jobs?\s+(in|at|by|near)", r"^all\s+jobs",
    r"^(remote|executive|startup|it|tech)\s+jobs",
    r"job\s+(search|categories?|alerts?)",
    r"(by\s+location|by\s+city|by\s+department)",
    r"^browse\s+", r"^view\s+all",
    r"^(contract|temp|career|careers|search|accommodations|terms|protect|fraudulent|login|home|privacy)",
]

IRRELEVANT_ROLE_TERMS = [
    "native speaker", "native tamil", "native polish", "native taiwanese",
    "native spanish", "translator", "transcriber", "data entry",
    "call center", "telecaller", "customer service representative",
    "ai trainer", "annotation specialist", "evaluator", "rater",
    "unpaid", "campus drive", "stipend", "trainee",
]


def _clean_company_name(raw_name: str) -> str:
    """Clean company name by stripping search noise."""
    if not raw_name:
        return ""
    name = raw_name.strip()
    if re.match(r"^\d+[\d,]*\+?", name):
        return ""

    raw_lower = name.lower()
    blacklisted_terms = [
        "choosing", "how to", "find a", "top startups", "top 10", "top 20",
        "software companies", "tech companies", "ai jobs", "jobs in",
        "native speaker", "work from home", "remote jobs", "urgent:",
        "directory", "portal", "platform", "comparison", "tips",
    ]
    if any(term in raw_lower for term in blacklisted_terms):
        return ""

    name = re.sub(r"\s*[\-|–|—|\|].*", "", name).strip()
    name = re.sub(r"(?i)\s*(careers?|jobs?|hiring|tech companies|inc\.?|ltd\.?|llc|pvt).*", "", name).strip()

    words = name.split()
    if len(words) > 4 or len(name) < 2 or len(name) > 36:
        return ""

    return name.title()


def _is_relevant_role(role_title: str, target_role: str = "") -> bool:
    """Check if job title is relevant to the target role.

    Now actively checks role overlap instead of only rejecting obviously wrong titles.
    """
    title_lower = role_title.lower().strip()
    if not title_lower:
        return False
    if re.match(r"^\d+[\d,]*\+?\s+", title_lower):
        return False
    for term in IRRELEVANT_ROLE_TERMS:
        if term in title_lower and (not target_role or term not in target_role.lower()):
            return False
    for pat in NON_JOB_TITLE_PATTERNS:
        if re.search(pat, title_lower):
            return False

    # Active role relevance check: at least one meaningful token from target_role
    # must appear in the job title. This prevents "Data Analyst" from passing
    # when the user searches for "Software Engineer".
    if target_role:
        target_tokens = [t.lower() for t in target_role.split() if len(t) > 2]
        if target_tokens:
            title_tokens = set(title_lower.split())
            # Require at least one target token in title, OR a strong synonym match
            ROLE_SYNONYMS = {
                "engineer": {"developer", "sde", "swe", " programmer", "coder"},
                "developer": {"engineer", "sde", "swe", "programmer"},
                "software": {"full stack", "fullstack", "backend", "frontend", "front-end", "back-end"},
                "frontend": {"front-end", "ui ", "react", "vue", "angular"},
                "backend": {"back-end", "server-side", "api ", "rest"},
                "full stack": {"fullstack", "full-stack", "software engineer", "web developer"},
                "data scientist": {"ml engineer", "machine learning", "ai engineer", "data analyst"},
                "machine learning": {"ml engineer", "ai engineer", "data scientist"},
                "ai": {"ml", "machine learning", "artificial intelligence", "deep learning"},
                "devops": {"sre", "platform engineer", "infrastructure", "cloud engineer"},
                "product manager": {"product owner", "pm ", "program manager"},
                "analyst": {"data analyst", "business analyst", "analytics"},
            }
            expanded_target = set(target_tokens)
            for token in target_tokens:
                for syn_key, syn_vals in ROLE_SYNONYMS.items():
                    if token in syn_key or syn_key in token:
                        expanded_target.update(syn_vals)

            if not any(t in title_lower for t in expanded_target if len(t) > 2):
                return False

    return True


INDIAN_CITIES = {
    "hyderabad": ["hyderabad", "secunderabad", "cyberabad", "hitec city", "gachibowli"],
    "bengaluru": ["bengaluru", "bangalore", "whitefield", "electronic city", "bellandur", "koramangala", "hsr layout"],
    "mumbai": ["mumbai", "bombay", "thane", "navi mumbai", "powai"],
    "ncr": ["delhi", "ncr", "noida", "gurgaon", "gurugram", "faridabad"],
    "chennai": ["chennai", "madras"],
    "pune": ["pune"],
    "visakhapatnam": ["visakhapatnam", "vizag"],
}


# Foreign country / region tokens.
FOREIGN_LOCATION_TOKENS = [
    "usa", "u.s.", "u.s.a", "united states", "us-", "san francisco", "new york",
    "seattle", "austin", "boston", "chicago", "mountain view", "palo alto",
    "redmond", "atlanta", "denver", "remote - us", "remote-us", "remote (us)",
    "canada", "toronto", "vancouver", "montreal",
    "uk", "u.k.", "united kingdom", "london", "england", "remote - uk",
    "ireland", "dublin",
    "germany", "berlin", "munich", "netherlands", "amsterdam", "france", "paris",
    "spain", "barcelona", "madrid", "portugal", "lisbon", "italy", "milan",
    "sweden", "stockholm", "norway", "oslo", "denmark", "copenhagen", "finland",
    "poland", "warsaw", "remote - europe", "remote-emea",
    "israel", "tel aviv", "tel-aviv",
    "australia", "sydney", "melbourne", "new zealand", "auckland",
    "singapore", "japan", "tokyo", "china", "beijing", "shanghai", "hong kong",
    "south korea", "seoul", "taiwan", "vietnam", "hanoi", "philippines", "manila",
    "indonesia", "jakarta", "malaysia", "kuala lumpur", "thailand", "bangkok",
    "brazil", "sao paulo", "mexico", "mexico city", "argentina", "buenos aires",
    "south africa", "johannesburg", "cape town", "remote - apac",
    "dubai", "uae", "saudi arabia", "riyadh", "qatar", "doha",
]


def _matches_location_strict(title: str, jd_text: str, target_location: str) -> bool:
    """Strict location matching that rejects foreign-based jobs."""
    if not target_location:
        return True
    target_lower = target_location.lower().strip()
    loc_line = (title + " " + jd_text[:300]).lower()

    for tok in FOREIGN_LOCATION_TOKENS:
        if tok in loc_line:
            return False

    if any(t in loc_line for t in ["worldwide", "anywhere", "global", "work from anywhere"]):
        return True

    if "remote" in loc_line or "work from home" in loc_line or "pan india" in loc_line:
        return True

    if "india" in loc_line:
        return True

    target_key = _normalise_city(target_lower)
    target_synonyms = INDIAN_CITIES.get(target_key, [target_key])
    if any(syn in loc_line for syn in target_synonyms):
        return True

    if not jd_text or len(jd_text) < 15:
        return True

    return False


async def discover_jobs_from_catalog(location: str, role: str, limit: int = 50) -> list[dict]:
    """Directly query public ATS APIs for companies in the local TECH_HUB_STARTUPS catalog."""
    from vellum.tools.ats_api import TECH_HUB_STARTUPS, fetch_greenhouse_jobs, fetch_lever_jobs, fetch_ashby_jobs
    
    loc_key = _normalise_city(location)
    companies = TECH_HUB_STARTUPS.get(loc_key, [])
    if not companies:
        # Fallback to general pool of tech startups if location not in catalog
        companies = TECH_HUB_STARTUPS.get("bengaluru", [])[:40] + TECH_HUB_STARTUPS.get("hyderabad", [])[:40]
        
    semaphore = asyncio.Semaphore(15)
    discovered = []
    seen_urls = set()
    company_job_count = {}
    MAX_PER_COMPANY = 3  # Cap jobs per company to avoid single-company dominance
    
    async def _check_company(company_slug: str):
        async with semaphore:
            if company_job_count.get(company_slug, 0) >= MAX_PER_COMPANY:
                return

            # Check Greenhouse
            try:
                gh_jobs = await fetch_greenhouse_jobs(company_slug)
                for job in gh_jobs:
                    if company_job_count.get(company_slug, 0) >= MAX_PER_COMPANY:
                        break
                    url = job.get("apply_url", "")
                    if url and url in seen_urls:
                        continue
                    if _is_relevant_role(job["title"], role) and _matches_location_strict(job["title"], job.get("jd_text", ""), location):
                        if url:
                            seen_urls.add(url)
                        discovered.append(job)
                        company_job_count[company_slug] = company_job_count.get(company_slug, 0) + 1
            except Exception:
                pass
                
            # Check Lever
            try:
                lever_jobs = await fetch_lever_jobs(company_slug)
                for job in lever_jobs:
                    if company_job_count.get(company_slug, 0) >= MAX_PER_COMPANY:
                        break
                    url = job.get("apply_url", "")
                    if url and url in seen_urls:
                        continue
                    if _is_relevant_role(job["title"], role) and _matches_location_strict(job["title"], job.get("jd_text", ""), location):
                        if url:
                            seen_urls.add(url)
                        discovered.append(job)
                        company_job_count[company_slug] = company_job_count.get(company_slug, 0) + 1
            except Exception:
                pass
                
            # Check Ashby
            try:
                ashby_jobs = await fetch_ashby_jobs(company_slug)
                for job in ashby_jobs:
                    if company_job_count.get(company_slug, 0) >= MAX_PER_COMPANY:
                        break
                    url = job.get("apply_url", "")
                    if url and url in seen_urls:
                        continue
                    if _is_relevant_role(job["title"], role) and _matches_location_strict(job["title"], job.get("jd_text", ""), location):
                        if url:
                            seen_urls.add(url)
                        discovered.append(job)
                        company_job_count[company_slug] = company_job_count.get(company_slug, 0) + 1
            except Exception:
                pass

    tasks = [_check_company(c) for c in companies]
    await asyncio.gather(*tasks)
    
    standardized = []
    for item in discovered:
        standardized.append({
            "company": item["company"],
            "title": item["title"][:160],
            "career_page_url": item.get("career_page_url", ""),
            "apply_url": item.get("apply_url", ""),
            "jd_text": item.get("jd_text", "")[:20000],
            "source": item.get("ats_source", "ats_catalog"),
            "confidence": 0.95,
        })
        
    return standardized


async def run(state: dict) -> dict:
    """Agent A: Multi-source Indian tech hiring discovery.
    
    Uses web search (DuckDuckGo) for job discovery.
    Falls back to ATS API hub and VC portfolio boards.
    
    Input state: {"location": str, "profile": dict, "role": str, "limit": int}
    Output: adds to state["discovered_jobs"] and state["events"]
    """
    location = state.get("location", "Bengaluru")
    profile = state.get("profile", {})
    limit = state.get("limit") or MAX_TOTAL_JOBS
    hard_cap = _effective_max_jobs(limit)
    role = state.get("role") or "software engineer"
    company = state.get("company", "")  # Optional: focus on specific company
    jobs: list[dict] = []
    events: list[dict] = []
    errors: list[str] = []

    async def broadcast_progress(percentage: int, message: str):
        event_dict = AgentEvent(
            agent="geo_search",
            event_type="search_progress",
            message=message,
            data={"percentage": percentage}
        ).model_dump(mode="json")
        await ws_manager.broadcast(event_dict)

    await broadcast_progress(5, f"Starting discovery for {role} in {location}...")

    # Global deduplication across all sources
    seen_urls = set()

    # --- Phase 1: ATS Catalog Search ---
    try:
        await broadcast_progress(10, f"Querying direct ATS endpoints for local {location} startups...")
        catalog_jobs = await discover_jobs_from_catalog(location, role, limit)
        for job in catalog_jobs:
            if len(jobs) >= limit:
                break
            url = job.get("apply_url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            jobs.append(job)
        await broadcast_progress(40, f"Catalog query complete: Found {len(jobs)} direct startup jobs.")
    except Exception as exc:
        log.warning("catalog_discovery_error", error=str(exc))

    # --- Phase 2: Web Search (DuckDuckGo + Bing fallback) ---
    if len(jobs) < hard_cap:
        try:
            search_limit = min(hard_cap - len(jobs), 50)  # Respect rate limits
            await broadcast_progress(45, f"Searching web for additional {role} jobs...")
            web_jobs = await web_search_scraper.search_and_enrich(
                role=role,
                location=location,
                company=company,
                max_results=search_limit,
                enrich_top=min(25, search_limit),  # Enrich with full page details
                skills=profile.get("skills", []),
            )
            
            # Process and filter jobs
            for job in web_jobs:
                if len(jobs) >= hard_cap:
                    break
                
                title = job.get("title", "")
                if not title:
                    continue
                
                # Filter by role relevance
                if not _is_relevant_role(title, role):
                    continue
                
                # Deduplicate by URL
                url = job.get("apply_url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                
                # Lenient pre-verification check: reject only if clearly matching a foreign location
                loc_line = (title + " " + job.get("snippet", "")).lower()
                if any(tok in loc_line for tok in FOREIGN_LOCATION_TOKENS):
                    continue
                # Clean company & title
                company_name, clean_title = clean_job_title_and_company(
                    raw_title=title,
                    raw_company=job.get("company", ""),
                    snippet=job.get("snippet", ""),
                    apply_url=job.get("apply_url", ""),
                )
    
                jobs.append({
                    "company": company_name,
                    "title": clean_title[:160],
                    "career_page_url": job.get("apply_url", ""),
                    "apply_url": job.get("apply_url", ""),
                    "jd_text": job.get("jd_text") or job.get("snippet", "") or "",
                    "source": job.get("source", "web_search"),
                    "confidence": 0.85,
                })
            
            await broadcast_progress(75, f"Web search complete. Total found so far: {len(jobs)}.")
        except Exception as exc:
            log.warning("web_search_error", error=str(exc))
            errors.append(f"Web search error: {str(exc)[:200]}")

    # --- Secondary: VC Portfolio Boards (Getro) ---
    if len(jobs) < hard_cap:
        try:
            vc_boards = [
                ("blume.vc", "Blume Ventures"),
                ("peakxv.com", "Peak XV Partners"),
            ]
            for vc_domain, vc_name in vc_boards:
                vc_jobs = await ats_api.fetch_getro_vc_jobs(vc_domain=vc_domain, vc_name=vc_name)
                for v_item in vc_jobs:
                    if len(jobs) >= hard_cap:
                        break
                    if not _is_relevant_role(v_item["title"], role):
                        continue
                    if not _matches_location_strict(v_item["title"], v_item.get("jd_text", ""), location):
                        continue
                    url = v_item.get("apply_url", "")
                    if url and url in seen_urls:
                        continue
                    if url:
                        seen_urls.add(url)
                    jobs.append({
                        "company": v_item["company"],
                        "title": v_item["title"][:160],
                        "career_page_url": v_item["career_page_url"],
                        "apply_url": v_item["apply_url"],
                        "jd_text": v_item["jd_text"][:20000],
                        "source": f"vc_getro_{vc_domain}",
                        "confidence": v_item["confidence"],
                    })
        except Exception as exc:
            log.warning("vc_board_discovery_error", error=str(exc))

    # --- Tertiary: Direct career-page scraping of local startup catalog ---
    if len(jobs) < hard_cap:
        try:
            await broadcast_progress(80, f"Directly scanning career pages of {location} startups for more roles...")
            from vellum.agents.career_scraper import run as career_scrape_run
            career_result = await career_scrape_run({
                "location": location,
                "profile": profile,
                "role": role,
                "limit": min(hard_cap - len(jobs), 60),
            })
            for c_job in career_result.get("discovered_jobs", []):
                if len(jobs) >= hard_cap:
                    break
                url = c_job.get("apply_url") or c_job.get("career_page_url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                if not _is_relevant_role(c_job.get("title") or c_job.get("role", ""), role):
                    continue
                if not _matches_location_strict(
                    c_job.get("title") or c_job.get("role", ""),
                    c_job.get("jd_text", ""),
                    location,
                ):
                    continue
                jobs.append({
                    "company": c_job.get("company", ""),
                    "title": (c_job.get("title") or c_job.get("role", ""))[:160],
                    "career_page_url": c_job.get("career_page_url", ""),
                    "apply_url": c_job.get("apply_url", ""),
                    "jd_text": c_job.get("jd_text", "")[:20000],
                    "source": c_job.get("source", "career_page_scrape"),
                    "confidence": c_job.get("confidence", 0.8),
                })
        except Exception as exc:
            log.warning("career_page_discovery_error", error=str(exc))

    await broadcast_progress(85, f"Verifying HTTP status and active posting pages for {len(jobs)} jobs...")
    from vellum.tools.url_verifier import filter_active_jobs
    jobs = await filter_active_jobs(jobs)

    # Apply strict location filtering on verified jobs using full description
    jobs = [
        j for j in jobs
        if _matches_location_strict(j.get("title", ""), j.get("jd_text", ""), location)
    ]

    await broadcast_progress(90, f"Total verified active jobs in {location}: {len(jobs)}.")

    # Store jobs in database — NO WebSocket events here.
    # Jobs only appear in UI AFTER LLM validation in graph.py.
    stored_count = 0
    for item in jobs[:limit]:
        try:
            job = JobListing(
                company=item["company"],
                role=item["title"],
                career_page_url=item.get("career_page_url", ""),
                apply_url=item.get("apply_url", ""),
                jd_text=item.get("jd_text", ""),
                source=item.get("source", "geo_search"),
                discovery_confidence=item.get("confidence", 0.9),
            )
            job_dict = job.model_dump(mode="json")
            job_id = await db.insert_job(job_dict)
            if job_id:
                job_dict["id"] = job_id
                item["id"] = job_id
                stored_count += 1
        except Exception as exc:
            log.warning("job_insertion_failed", company=item.get("company"), error=str(exc))

    await broadcast_progress(100, f"Discovery complete! Found {len(jobs)} relevant jobs.")

    log.info("geo_search_complete", total_discovered=len(jobs))
    return {
        "discovered_jobs": jobs,
        "events": events,
        "errors": errors,
    }
