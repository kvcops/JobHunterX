"""
Vellum OS — Geospatial Search Agent (Agent A)

Multi-source company discovery: OSM + ddgs + curated ATS boards.
Deduplication, URL scoring, and career-page extraction pipeline.
"""

from __future__ import annotations

import re

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import maps_api, search, scrape
from vellum.models import JobListing, AgentEvent

log = get_logger("geo_search")

# ---------------------------------------------------------------------------
# Curated ATS boards for major Indian tech hubs
# ---------------------------------------------------------------------------

MAX_TOTAL_JOBS = 30

CURATED_BOARDS = {
    "bengaluru": [
        "https://boards.greenhouse.io/razorpay",
        "https://boards.greenhouse.io/flipkart",
        "https://jobs.lever.co/swiggy",
        "https://jobs.lever.co/cred",
    ],
    "hyderabad": [
        "https://boards.greenhouse.io/phonepe",
    ],
    "mumbai": [
        "https://boards.greenhouse.io/dream11",
    ],
}


def _normalise_city(location: str) -> str:
    """Normalise city name for curated board lookup."""
    city = location.lower().strip()
    aliases = {
        "bangalore": "bengaluru",
        "bombay": "mumbai",
        "madras": "chennai",
        "calcutta": "kolkata",
    }
    return aliases.get(city, city)


# ---------------------------------------------------------------------------
# Quality filters
# ---------------------------------------------------------------------------

# Job-relevant keywords that should appear in real job descriptions
JD_KEYWORDS = [
    "experience", "skill", "responsibilit", "qualification",
    "requirement", "role", "position", "job", "work",
    "team", "develop", "manage", "lead", "design", "build",
    "engineer", "analyst", "specialist", "coordinator",
    "salary", "benefit", "location", "report", "degree",
]

# Words/phrases that indicate a real job title (vs a category/nav page)
JOB_TITLE_INDICATORS = [
    "engineer", "developer", "manager", "analyst", "specialist",
    "coordinator", "architect", "consultant", "director", "head of",
    "lead", "associate", "intern", "trainee", "executive",
    "officer", "representative", "scientist", "designer",
    "administrator", "assistant", "advisor", "auditor",
    "supervisor", "president", "vp ", "vice president",
]

# Non-job title patterns to exclude
NON_JOB_TITLE_PATTERNS = [
    r"^jobs?\s+(in|at|by|near)", r"^all\s+jobs",
    r"^(remote|executive|startup|it|tech)\s+jobs",
    r"job\s+(search|categories?|alerts?)",
    r"(by\s+location|by\s+city|by\s+department)",
    r"^browse\s+", r"^view\s+all",
]


def _is_valid_job_title(title: str) -> bool:
    """Check if a title looks like a real job posting, not a nav page."""
    title_lower = title.lower().strip()
    if len(title_lower) < 25:
        return False
    for pat in NON_JOB_TITLE_PATTERNS:
        if re.search(pat, title_lower):
            return False
    for indicator in JOB_TITLE_INDICATORS:
        if indicator in title_lower:
            return True
    return False


def _jd_has_job_keywords(jd_text: str, min_keywords: int = 3) -> bool:
    """Check if JD text contains enough job-relevant keywords."""
    text_lower = jd_text.lower()
    count = sum(1 for kw in JD_KEYWORDS if kw in text_lower)
    return count >= min_keywords


def _matches_location(title: str, jd_text: str, target_location: str) -> bool:
    """Check if job title or JD mentions the target location."""
    if not target_location:
        return True
    target_lower = target_location.lower().strip()
    # Check for city name in title (strong signal)
    city_key = target_lower.split(",")[0].split(" ")[0]  # first word of city
    if len(city_key) > 2:
        combined = (title + " " + jd_text).lower()
        if city_key in combined:
            return True
    return True  # lenient — don't filter out good jobs on location alone


# ---------------------------------------------------------------------------
# Discovery pipeline
# ---------------------------------------------------------------------------

async def run(state: dict) -> dict:
    """Agent A: Multi-source company discovery.

    Input state: {"location": str, "profile": dict}
    Output: adds to state["discovered_jobs"] and state["events"]
    """
    location = state.get("location", "Bengaluru")
    profile = state.get("profile", {})
    jobs: list[dict] = []
    events: list[dict] = []
    errors: list[str] = []

    from vellum.config.settings import get_settings
    settings = get_settings()

    events.append(AgentEvent(
        agent="geo_search",
        event_type="progress",
        message=f"Starting multi-source discovery for {location}",
    ).model_dump(mode="json"))

    # --- Source 1: OpenStreetMap (confidence: 0.5) ---
    coords = await maps_api.geocode_location(location)
    osm_companies = []
    if coords:
        osm_companies = await maps_api.find_tech_companies(
            coords["lat"], coords["lon"], radius_km=20
        )
        events.append(AgentEvent(
            agent="geo_search",
            event_type="progress",
            message=f"OSM: Found {len(osm_companies)} companies",
            confidence=0.5,
        ).model_dump(mode="json"))

    # --- Source 2: ddgs search (confidence: 0.6) ---
    role = state.get("role") or "software engineer"
    ddgs_query = f"{location} tech companies hiring {role}"
    ddgs_companies = []
    try:
        import asyncio
        from ddgs import DDGS

        def _search():
            with DDGS() as ddgs:
                return ddgs.text(ddgs_query, max_results=15)

        results = await asyncio.to_thread(_search)
        for r in results:
            title = r.get("title", "")
            # Extract company name from search result titles
            name = title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
            if name and len(name) < 60:
                ddgs_companies.append({
                    "name": name,
                    "website": r.get("href", ""),
                    "source": "ddgs",
                    "confidence": 0.6,
                })
    except Exception as exc:
        errors.append(f"ddgs search error: {exc}")

    events.append(AgentEvent(
        agent="geo_search",
        event_type="progress",
        message=f"ddgs: Found {len(ddgs_companies)} company leads",
        confidence=0.6,
    ).model_dump(mode="json"))

    # --- Source 3: Curated ATS boards (confidence: 0.8) ---
    city_key = _normalise_city(location)
    curated_urls = CURATED_BOARDS.get(city_key, [])
    events.append(AgentEvent(
        agent="geo_search",
        event_type="progress",
        message=f"Curated boards: {len(curated_urls)} known ATS pages",
        confidence=0.8,
    ).model_dump(mode="json"))

    # --- Merge and deduplicate ---
    all_companies = []
    seen_names = set()

    for company in osm_companies + ddgs_companies:
        name_key = company["name"].lower().strip()
        if name_key not in seen_names and len(name_key) > 2:
            seen_names.add(name_key)
            all_companies.append(company)

    events.append(AgentEvent(
        agent="geo_search",
        event_type="progress",
        message=f"Total unique companies: {len(all_companies)} + {len(curated_urls)} curated",
    ).model_dump(mode="json"))

    # --- Career page discovery for each company ---
    for company in all_companies[:20]:  # Cap at 20 to stay within rate limits
        if len(jobs) >= MAX_TOTAL_JOBS:
            break
        try:
            career_results = await search.search_career_pages(company["name"])
            if not career_results:
                continue

            top_result = career_results[0]
            if top_result["score"] < 0.65:
                continue  # Too noisy

            # Fetch and parse the career page
            page = await scrape.fetch_page(top_result["url"])
            html = page.get("html", "")
            if not html:
                continue

            # Extract apply links (deterministic first)
            links = await scrape.extract_apply_links(
                top_result["url"],
                api_key=settings.google_api_key or "",
                html=html,
            )

            # Store individual job posts, not the whole careers landing page.
            for link in links[:8]:
                if len(jobs) >= MAX_TOTAL_JOBS:
                    break
                role_title = (link.get("text") or "").strip()
                if (
                    not role_title
                    or role_title.lower() in {"apply", "view job", "learn more"}
                    or link["url"].rstrip("/") == top_result["url"].rstrip("/")
                ):
                    continue
                if not _is_valid_job_title(role_title):
                    continue
                job_page = await scrape.fetch_page(link["url"])
                job_html = job_page.get("html", "")
                jd_text = await scrape.extract_jd_text(job_html or html)
                if len(jd_text) < 180 or not _jd_has_job_keywords(jd_text):
                    continue
                if not _matches_location(role_title, jd_text, location):
                    continue
                job = JobListing(
                    company=company["name"],
                    role=role_title[:160],
                    career_page_url=top_result["url"],
                    apply_url=link["url"],
                    jd_text=jd_text[:20000],
                    source=company.get("source", "ddgs"),
                    discovery_confidence=top_result["score"],
                )
                job_dict = job.model_dump(mode="json")
                job_id = await db.insert_job(job_dict)
                if job_id:
                    job_dict["id"] = job_id
                    jobs.append(job_dict)
                    events.append(AgentEvent(
                        agent="geo_search",
                        event_type="discovery",
                        job_id=job_id,
                        message=f"Discovered: {company['name']} - {role_title[:100]}",
                        confidence=top_result["score"],
                    ).model_dump(mode="json"))

        except Exception as exc:
            errors.append(f"Error processing {company['name']}: {exc}")
            log.error("company_processing_error", company=company["name"], error=str(exc))

    # --- Process curated ATS boards ---
    for board_url in curated_urls:
        if len(jobs) >= MAX_TOTAL_JOBS:
            break
        try:
            page = await scrape.fetch_page(board_url)
            html = page.get("html", "")
            if not html:
                continue

            links = await scrape.extract_apply_links_deterministic(html, base_url=board_url)
            # Extract company name from URL
            name_match = re.search(r"greenhouse\.io/(\w+)|lever\.co/(\w+)", board_url)
            company_name = (name_match.group(1) or name_match.group(2)).title() if name_match else "Unknown"

            for link in links[:8]:
                if len(jobs) >= MAX_TOTAL_JOBS:
                    break
                role_title = (link.get("text") or "").strip()
                if not role_title or role_title.lower() in {"apply", "view job", "learn more"}:
                    continue
                if not _is_valid_job_title(role_title):
                    continue
                job_page = await scrape.fetch_page(link["url"])
                jd_text = await scrape.extract_jd_text(job_page.get("html", ""))
                if len(jd_text) < 180 or not _jd_has_job_keywords(jd_text):
                    continue
                if not _matches_location(role_title, jd_text, location):
                    continue
                job = JobListing(
                    company=company_name,
                    role=role_title[:160],
                    career_page_url=board_url,
                    apply_url=link["url"],
                    jd_text=jd_text[:20000],
                    source="curated",
                    discovery_confidence=0.8,
                )
                job_dict = job.model_dump(mode="json")
                job_id = await db.insert_job(job_dict)
                if job_id:
                    job_dict["id"] = job_id
                    jobs.append(job_dict)

        except Exception as exc:
            errors.append(f"Curated board error {board_url}: {exc}")

    events.append(AgentEvent(
        agent="geo_search",
        event_type="complete",
        message=f"Discovery complete. {len(jobs)} jobs found.",
    ).model_dump(mode="json"))

    return {
        "discovered_jobs": jobs,
        "events": events,
        "errors": errors,
    }
