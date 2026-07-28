"""
Vellum OS — India-Native Career Search Agent (Agent A)

Multi-source Indian startup & tech hiring discovery:
  - Channel 0: Direct Startup ATS APIs (Greenhouse, Lever, Ashby, Freshteam, Zoho Recruit)
  - Channel 0.5: Getro-Powered Indian VC Portfolio Boards (Blume, Peak XV)
  - Channel 1: Indian Tech Community Job Feeds (Hasjob RSS)
  - Channel 2: Search-Engine Indexed Indian Startup Portals (Wellfound / Instahyre)
  - Channel 3: Indian Founder Social Hiring Post Miner (LinkedIn / X Email Dorks)
  - Channel 4: Direct High-Precision ATS Search
"""

from __future__ import annotations

import re

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import search, scrape, ats_api
from vellum.models import JobListing, AgentEvent
from vellum.api.ws import manager as ws_manager
from vellum.agents import job_evaluator

log = get_logger("geo_search")

MAX_TOTAL_JOBS = 30


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


def _matches_location_strict(title: str, jd_text: str, target_location: str) -> bool:
    """Strict location matching for Indian tech cities."""
    if not target_location:
        return True
    target_lower = target_location.lower().strip()
    combined_text = (title + " " + jd_text).lower()

    if "remote" in combined_text or "pan india" in combined_text or "work from home" in combined_text:
        return True

    target_key = _normalise_city(target_lower)
    target_synonyms = INDIAN_CITIES.get(target_key, [target_key])
    target_found = any(syn in combined_text for syn in target_synonyms)

    for city_key, synonyms in INDIAN_CITIES.items():
        if city_key == target_key:
            continue
        for syn in synonyms:
            if syn in title.lower() and not target_found:
                return False

    other_cities = ["bareilly", "hubballi", "aurangabad", "lucknow", "chandigarh", "jaipur", "kochi", "trivandrum"]
    for city in other_cities:
        if city in title.lower() and not target_found:
            return False

    return target_found
async def run(state: dict) -> dict:
    """Agent A: Multi-source Indian tech hiring discovery.

    Input state: {"location": str, "profile": dict, "role": str}
    Output: adds to state["discovered_jobs"] and state["events"]
    """
    location = state.get("location", "Bengaluru")
    profile = state.get("profile", {})
    jobs: list[dict] = []
    events: list[dict] = []
    errors: list[str] = []
    role = state.get("role") or "software engineer"

    async def broadcast_progress(percentage: int, message: str):
        event_dict = AgentEvent(
            agent="geo_search",
            event_type="search_progress",
            message=message,
            data={"percentage": percentage}
        ).model_dump(mode="json")
        await ws_manager.broadcast(event_dict)

    await broadcast_progress(5, f"Starting discovery for {role} in {location}...")

    raw_candidates = []

    # --- Channel 0: Direct Startup ATS APIs (Greenhouse, Lever, Ashby, Freshteam, Zoho) ---
    try:
        hub_jobs = await ats_api.fetch_hub_ats_jobs(location=location, role=role, max_jobs=15)
        for h_item in hub_jobs:
            job_loc = h_item.get("location", "")
            jd_text = h_item.get("jd_text", "")
            if not _matches_location_strict(h_item["title"], f"{job_loc} {jd_text}", location):
                continue
            raw_candidates.append({
                "company": h_item["company"],
                "title": h_item["title"][:160],
                "career_page_url": h_item["career_page_url"],
                "apply_url": h_item["apply_url"],
                "jd_text": h_item["jd_text"][:20000],
                "source": f"ats_hub_{h_item['ats_source']}",
                "confidence": h_item["confidence"],
            })
    except Exception as exc:
        log.warning("hub_ats_scanner_error", error=str(exc))

    await broadcast_progress(20, f"Direct ATS Scan complete: Found {len(raw_candidates)} potential jobs.")

    # --- Channel 0.5: Getro VC Portfolio Boards (Blume, Peak XV) ---
    try:
        vc_boards = [
            ("blume.vc", "Blume Ventures"),
            ("peakxv.com", "Peak XV Partners"),
        ]
        vc_count = 0
        for vc_domain, vc_name in vc_boards:
            vc_jobs = await ats_api.fetch_getro_vc_jobs(vc_domain=vc_domain, vc_name=vc_name)
            for v_item in vc_jobs:
                if not _is_relevant_role(v_item["title"], role):
                    continue
                raw_candidates.append({
                    "company": v_item["company"],
                    "title": v_item["title"][:160],
                    "career_page_url": v_item["career_page_url"],
                    "apply_url": v_item["apply_url"],
                    "jd_text": v_item["jd_text"][:20000],
                    "source": f"vc_getro_{vc_domain}",
                    "confidence": v_item["confidence"],
                })
                vc_count += 1
    except Exception as exc:
        log.warning("vc_board_discovery_error", error=str(exc))

    await broadcast_progress(35, f"VC Boards complete: Added {vc_count} potential jobs.")

    # --- Channel 1: Hasjob Tech Feed (hasjob.co) ---
    try:
        hasjob_items = await search.fetch_hasjob_jobs(max_results=8)
        hj_count = 0
        for hj in hasjob_items:
            if not _is_relevant_role(hj["title"], role):
                continue
            raw_candidates.append({
                "company": hj["company"],
                "title": hj["title"][:160],
                "career_page_url": hj["career_page_url"],
                "apply_url": hj["apply_url"],
                "jd_text": hj["jd_text"][:20000],
                "source": "hasjob",
                "confidence": hj["confidence"],
            })
            hj_count += 1
    except Exception as exc:
        log.warning("hasjob_discovery_error", error=str(exc))

    await broadcast_progress(50, f"Hasjob RSS complete: Added {hj_count} potential jobs.")

    # --- Channel 2: Search-Indexed Indian Startup Portals (Wellfound / Instahyre) ---
    try:
        portal_items = await search.search_wellfound_instahyre_jobs(role=role, location=location, max_results=6)
        portal_count = 0
        for p_item in portal_items:
            if not _is_relevant_role(p_item["title"], role):
                continue
            raw_candidates.append({
                "company": p_item["company"],
                "title": p_item["title"][:160],
                "career_page_url": p_item["url"],
                "apply_url": p_item["url"],
                "jd_text": p_item["snippet"][:20000],
                "source": "search_indexed_portals",
                "confidence": p_item["score"],
            })
            portal_count += 1
    except Exception as exc:
        log.warning("portal_discovery_error", error=str(exc))

    await broadcast_progress(65, f"Startup Portals complete: Added {portal_count} potential jobs.")

    # --- Channel 3: Unadvertised Social Hiring Posts (LinkedIn/X Email Posts) ---
    try:
        social_posts = await search.search_unadvertised_social_posts(role=role, location=location, max_results=5)
        for post in social_posts:
            if post.get("contact_email"):
                draft = {
                    "company": post.get("company", "Indian Tech Startup"),
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
    except Exception as exc:
        log.warning("social_post_miner_error", error=str(exc))

    await broadcast_progress(75, f"Founder Social Post Miner complete. Evaluating jobs with Job Evaluator Agent...")

    # --- Phase 1.5: Job Evaluator Filtering Agent ---
    try:
        filtered_candidates = await job_evaluator.filter_jobs(raw_candidates, profile, role)
    except Exception as exc:
        log.error("job_evaluator_error", error=str(exc))
        filtered_candidates = raw_candidates

    # Only process up to MAX_TOTAL_JOBS
    for item in filtered_candidates[:MAX_TOTAL_JOBS]:
        try:
            job = JobListing(
                company=item["company"],
                role=item["title"],
                career_page_url=item["career_page_url"],
                apply_url=item["apply_url"],
                jd_text=item["jd_text"],
                source=item["source"],
                discovery_confidence=item["confidence"],
            )
            job_dict = job.model_dump(mode="json")
            job_id = await db.insert_job(job_dict)
            if job_id:
                job_dict["id"] = job_id
                jobs.append(job_dict)
                
                # Create and append/broadcast discovery event
                event_dict = AgentEvent(
                    agent="geo_search",
                    event_type="discovery",
                    job_id=job_id,
                    message=f"Discovered (Evaluated Fit): {item['company']} - {item['title'][:80]}",
                    confidence=item["confidence"],
                ).model_dump(mode="json")
                events.append(event_dict)
                await ws_manager.broadcast(event_dict)
        except Exception as exc:
            log.warning("job_insertion_failed", company=item.get("company"), error=str(exc))

    await broadcast_progress(80, f"Discovery complete! Found {len(jobs)} relevant, candidate-matched jobs.")

    log.info("geo_search_complete", total_discovered=len(jobs))
    return {
        "discovered_jobs": jobs,
        "events": events,
        "errors": errors,
    }
