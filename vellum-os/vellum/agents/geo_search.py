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


def _clean_company_name(raw_name: str) -> str:
    """Clean company name by stripping search noise and rejecting aggregator titles."""
    if not raw_name:
        return ""
    name = raw_name.strip()
    # Strip common search result suffixes
    name = re.sub(r"\s*[\-|–|—|\|].*", "", name).strip()
    name = re.sub(r"(?i)\s*(careers?|jobs?|hiring|tech companies|inc\.?|ltd\.?).*", "", name).strip()
    
    # Reject aggregator query titles
    name_lower = name.lower()
    if any(p in name_lower for p in ["ai jobs in", "jobs in", "top 10", "software companies in", "best tech", "hiring in"]):
        return ""
    if len(name) < 3 or len(name) > 50:
        return ""
    return name.title()


INDIAN_CITIES = {
    "hyderabad": ["hyderabad", "secunderabad", "cyberabad", "hitec city", "gachibowli"],
    "bengaluru": ["bengaluru", "bangalore", "whitefield", "electronic city", "bellandur"],
    "mumbai": ["mumbai", "bombay", "thane", "navi mumbai", "powai"],
    "delhi": ["delhi", "ncr", "noida", "gurgaon", "gurugram", "faridabad"],
    "chennai": ["chennai", "madras"],
    "pune": ["pune"],
}


def _matches_location_strict(title: str, jd_text: str, target_location: str) -> bool:
    """Two-tier strict location matching. Reject explicit conflicting cities."""
    if not target_location:
        return True
    target_lower = target_location.lower().strip()
    combined_text = (title + " " + jd_text).lower()

    # Remote check (always allowed)
    if "remote" in combined_text or "pan india" in combined_text or "work from home" in combined_text:
        return True

    target_key = _normalise_city(target_lower)
    target_synonyms = INDIAN_CITIES.get(target_key, [target_key])

    # Check if target city is present
    target_found = any(syn in combined_text for syn in target_synonyms)

    # Check if a conflicting city is explicitly named without target city
    for city_key, synonyms in INDIAN_CITIES.items():
        if city_key == target_key:
            continue
        for syn in synonyms:
            # If explicit conflicting city name in title (e.g. "Manager - BAREILLY" or "Hubballi"), reject if target not mentioned
            if syn in title.lower() and not target_found:
                return False

    if target_found:
        return True

    # If title explicitly names another city or state, reject
    conflicting_other_places = ["bareilly", "hubballi", "aurangabad", "lucknow", "chandigarh", "jaipur", "kochi", "trivandrum"]
    for place in conflicting_other_places:
        if place in title.lower() and not target_found:
            return False

    return target_found  # Strict match required if non-remote



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
            raw_name = title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
            clean_name = _clean_company_name(raw_name)
            if clean_name:
                ddgs_companies.append({
                    "name": clean_name,
                    "website": r.get("href", ""),
                    "source": "ddgs",
                    "confidence": 0.6,
                })
    except Exception as exc:
        errors.append(f"ddgs search error: {exc}")

    # --- Source 3: Unadvertised Social Hiring Posts ---
    try:
        social_posts = await search.search_unadvertised_social_posts(role=role, location=location, max_results=5)
        for post in social_posts:
            if post.get("contact_email"):
                # Save directly as an outreach draft
                draft = {
                    "company": post.get("company", "Tech Company"),
                    "contact_name": "Hiring Manager",
                    "contact_role": "Hiring Lead",
                    "email_guesses": [{"address": post["contact_email"], "pattern": "direct_social", "mx_valid": post.get("is_mx_verified")}],
                    "subject": f"Application for {role} role at {post.get('company', 'your company')}",
                    "body": f"Hi,\n\nI saw your post regarding the {role} position in {location}. Attached is my CV.\n\nBest regards,\n{profile.get('name', 'Candidate')}",
                    "mailto_uri": f"mailto:{post['contact_email']}?subject=Application%20for%20{role}%20Role",
                    "confidence": 0.85,
                    "status": "drafted",
                }
                await db.insert_outreach(draft)
        events.append(AgentEvent(
            agent="geo_search",
            event_type="progress",
            message=f"Social Post Miner: Found {len(social_posts)} direct email hiring posts",
            confidence=0.85,
        ).model_dump(mode="json"))
    except Exception as exc:
        log.warning("social_post_miner_error", error=str(exc))

    # --- Source 4: Curated ATS boards (confidence: 0.8) ---
    city_key = _normalise_city(location)
    curated_urls = CURATED_BOARDS.get(city_key, [])

    # --- Merge and deduplicate ---
    all_companies = []
    seen_names = set()

    for company in osm_companies + ddgs_companies:
        c_name = _clean_company_name(company["name"])
        if not c_name:
            continue
        name_key = c_name.lower()
        if name_key not in seen_names:
            seen_names.add(name_key)
            company["name"] = c_name
            all_companies.append(company)

    events.append(AgentEvent(
        agent="geo_search",
        event_type="progress",
        message=f"Total verified unique companies: {len(all_companies)} + {len(curated_urls)} curated",
    ).model_dump(mode="json"))

    # --- Career page discovery for each company ---
    for company in all_companies[:15]:
        if len(jobs) >= MAX_TOTAL_JOBS:
            break
        try:
            career_results = await search.search_career_pages(company["name"])
            if not career_results:
                continue

            top_result = career_results[0]
            if top_result["score"] < 0.65:
                continue

            page = await scrape.fetch_page(top_result["url"])
            html = page.get("html", "")
            if not html:
                continue

            links = await scrape.extract_apply_links(
                top_result["url"],
                api_key=settings.google_api_key or "",
                html=html,
            )

            for link in links[:6]:
                if len(jobs) >= MAX_TOTAL_JOBS:
                    break
                role_title = (link.get("text") or "").strip()
                if not role_title or link["url"].rstrip("/") == top_result["url"].rstrip("/"):
                    continue

                job_page = await scrape.fetch_page(link["url"])
                job_html = job_page.get("html", "")
                jd_text = await scrape.extract_jd_text(job_html or html)

                if len(jd_text) < 180:
                    continue

                # Strict location check!
                if not _matches_location_strict(role_title, jd_text, location):
                    log.info("location_mismatch_skipped", company=company["name"], title=role_title, location=location)
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
                        message=f"Discovered: {company['name']} - {role_title[:80]}",
                        confidence=top_result["score"],
                    ).model_dump(mode="json"))

        except Exception as exc:
            errors.append(f"Error processing {company['name']}: {exc}")

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
            name_match = re.search(r"greenhouse\.io/(\w+)|lever\.co/(\w+)", board_url)
            company_name = (name_match.group(1) or name_match.group(2)).title() if name_match else "Unknown"

            for link in links[:6]:
                if len(jobs) >= MAX_TOTAL_JOBS:
                    break
                role_title = (link.get("text") or "").strip()
                if not role_title:
                    continue

                job_page = await scrape.fetch_page(link["url"])
                jd_text = await scrape.extract_jd_text(job_page.get("html", ""))

                if len(jd_text) < 180:
                    continue

                # Strict location check!
                if not _matches_location_strict(role_title, jd_text, location):
                    log.info("curated_location_mismatch_skipped", company=company_name, title=role_title, location=location)
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
        message=f"Discovery complete. {len(jobs)} jobs verified and stored.",
    ).model_dump(mode="json"))

    return {
        "discovered_jobs": jobs,
        "events": events,
        "errors": errors,
    }

