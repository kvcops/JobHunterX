"""
Vellum OS — India-Native Career Search Agent (Agent A)

Multi-source Indian startup & tech hiring discovery:
  - Primary: Web search via DuckDuckGo (free, no API key)
  - Secondary: Public ATS APIs (Greenhouse, Lever, Ashby)
  - Tertiary: VC Portfolio boards (Getro-powered)

All discovery is direct and structured. No paid APIs.
"""

from __future__ import annotations

import re

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import ats_api, web_search_scraper
from vellum.models import JobListing, AgentEvent
from vellum.api.ws import manager as ws_manager

log = get_logger("geo_search")

MAX_TOTAL_JOBS = 80


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
    """Check if job title is relevant."""
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

    for city_synonyms in INDIAN_CITIES.values():
        if any(syn in title.lower() for syn in city_synonyms):
            return True

    return False


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

    await broadcast_progress(5, f"Searching for {role} jobs in {location}...")

    # --- Primary: Web Search (DuckDuckGo) ---
    try:
        search_limit = min(limit, 50)  # Respect rate limits
        web_jobs = await web_search_scraper.search_and_enrich(
            role=role,
            location=location,
            company=company,
            max_results=search_limit,
            enrich_top=15,  # Enrich top 15 with full page details
        )
        
        # Process and filter jobs
        for job in web_jobs:
            if len(jobs) >= limit:
                break
            
            title = job.get("title", "")
            if not title:
                continue
            
            # Filter by role relevance
            if not _is_relevant_role(title, role):
                continue
            
            # Filter by location
            if not _matches_location_strict(title, job.get("snippet", ""), location):
                continue
            
            # Clean company name
            company_name = _clean_company_name(job.get("company", ""))
            if not company_name:
                # Try to extract from title
                company_name = _clean_company_name(title.split(" - ")[-1] if " - " in title else "")
            
            jobs.append({
                "company": company_name or "Unknown",
                "title": title[:160],
                "career_page_url": job.get("apply_url", ""),
                "apply_url": job.get("apply_url", ""),
                "jd_text": job.get("snippet", "")[:20000],
                "source": job.get("source", "web_search"),
                "confidence": 0.85,
            })
        
        await broadcast_progress(60, f"Web search complete: Found {len(jobs)} relevant jobs.")
    
    except Exception as exc:
        log.warning("web_search_error", error=str(exc))
        errors.append(f"Web search error: {str(exc)[:200]}")

    # --- Secondary: VC Portfolio Boards (Getro) ---
    if len(jobs) < limit:
        try:
            vc_boards = [
                ("blume.vc", "Blume Ventures"),
                ("peakxv.com", "Peak XV Partners"),
            ]
            for vc_domain, vc_name in vc_boards:
                vc_jobs = await ats_api.fetch_getro_vc_jobs(vc_domain=vc_domain, vc_name=vc_name)
                for v_item in vc_jobs:
                    if len(jobs) >= limit:
                        break
                    if not _is_relevant_role(v_item["title"], role):
                        continue
                    if not _matches_location_strict(v_item["title"], v_item.get("jd_text", ""), location):
                        continue
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

    await broadcast_progress(90, f"Total discovered: {len(jobs)} jobs.")

    # Store jobs in database
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
                
                event_dict = AgentEvent(
                    agent="geo_search",
                    event_type="discovery",
                    job_id=job_id,
                    message=f"Discovered: {item['company']} — {item['title'][:80]}",
                    confidence=item.get("confidence", 0.9),
                ).model_dump(mode="json")
                events.append(event_dict)
                await ws_manager.broadcast(event_dict)
        except Exception as exc:
            log.warning("job_insertion_failed", company=item.get("company"), error=str(exc))

    await broadcast_progress(100, f"Discovery complete! Found {len(jobs)} relevant jobs.")

    log.info("geo_search_complete", total_discovered=len(jobs))
    return {
        "discovered_jobs": jobs,
        "events": events,
        "errors": errors,
    }
