"""
Vellum OS — Career Page Scraper Agent

Systematically discovers job listings by directly querying company career pages
and public ATS APIs. Replaces unreliable DuckDuckGo-based search with
deterministic, structured data extraction.
"""

from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from pathlib import Path

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import ats_api, career_urls, scrape
from vellum.models import JobListing, AgentEvent
from vellum.api.ws import manager as ws_manager

log = get_logger("career_scraper")

MAX_JOBS_PER_COMPANY = 20
MAX_TOTAL_JOBS = 80

# Verified URL data cache
_VERIFIED_URLS_CACHE: dict | None = None


def _load_verified_urls() -> dict:
    """Load verified career URLs from company_career_urls.json.
    
    Returns a dict mapping company_slug -> {
        "careers_url": str | None,
        "verified_url": str | None,
        "has_jobs": bool,
        "ats_platform": str | None,
        "sample_jobs": list[str],
    }
    """
    global _VERIFIED_URLS_CACHE
    if _VERIFIED_URLS_CACHE is not None:
        return _VERIFIED_URLS_CACHE

    # Look for the file in multiple locations
    search_paths = [
        Path(__file__).parent.parent.parent / "company_career_urls.json",
        Path(__file__).parent.parent.parent.parent / "company_career_urls.json",
    ]

    for path in search_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                companies = data.get("hyderabad", {})
                _VERIFIED_URLS_CACHE = {}
                confirmed_count = 0
                ats_count = 0
                for slug, info in companies.items():
                    entry = {
                        "careers_url": info.get("careers_url"),
                        "verified_url": info.get("verified_url"),
                        "has_jobs": info.get("has_jobs", False),
                        "ats_platform": info.get("ats_platform"),
                        "sample_jobs": info.get("sample_jobs", []),
                    }
                    _VERIFIED_URLS_CACHE[slug] = entry
                    if entry["has_jobs"]:
                        confirmed_count += 1
                    if entry["ats_platform"]:
                        ats_count += 1
                log.info("verified_urls_loaded",
                    count=len(_VERIFIED_URLS_CACHE),
                    confirmed_with_jobs=confirmed_count,
                    ats_detected=ats_count,
                    path=str(path))
                return _VERIFIED_URLS_CACHE
            except Exception as exc:
                log.warning("verified_urls_load_failed", path=str(path), error=str(exc)[:100])

    log.warning("verified_urls_not_found")
    _VERIFIED_URLS_CACHE = {}
    return _VERIFIED_URLS_CACHE


def get_verified_info(company_slug: str) -> dict | None:
    """Get verified URL info for a company, if available."""
    cache = _load_verified_urls()
    return cache.get(company_slug)


def parse_experience_from_jd(jd_text: str) -> float | None:
    """Extract required years of experience from JD text.
    
    Returns the minimum required experience in years, or None if not found.
    """
    if not jd_text:
        return None
    
    text = jd_text.lower()[:3000]  # Only check first 3000 chars
    
    # Pattern 1: "X-Y years" or "X to Y years"
    patterns = [
        r'(\d+)[\s\-]+(?:to|[-])\s*(\d+)\s*(?:\+\s*)?years?',
        r'(\d+)\s*(?:\+\s*)?years?\s*(?:of\s+)?(?:experience|exp)',
        r'minimum\s*(?:of\s*)?(\d+)\s*years?',
        r'at\s*least\s*(\d+)\s*years?',
        r'require.*?(\d+)\s*years?',
        r'(\d+)\s*years?\s*(?:of\s+)?(?:relevant\s+)?(?:experience|exp)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                # Range like "3-5 years" — take the minimum
                return float(groups[0])
            elif len(groups) == 1:
                return float(groups[0])
    
    # Pattern 2: Level indicators
    level_map = {
        "intern": 0, "trainee": 0, "fresher": 0,
        "junior": 1, "mid-level": 3, "mid level": 3,
        "senior": 5, "lead": 7, "principal": 10,
        "staff": 10, "director": 12, "vp": 15, "cto": 15,
    }
    
    for level, years in level_map.items():
        if level in text:
            return float(years)
    
    return None


def matches_role_keywords(title: str, role_keywords: str) -> bool:
    """Check if a job title matches the target role keywords."""
    if not role_keywords:
        return True
    
    title_lower = title.lower()
    role_tokens = [t.lower().strip() for t in role_keywords.split() if len(t.strip()) > 2]
    
    if not role_tokens:
        return True
    
    # At least one role token must appear in the title
    return any(token in title_lower for token in role_tokens)


def is_job_fresh(job: dict, max_age_days: int = 30) -> bool:
    """Check if a job posting is still fresh based on dates."""
    # Check validThrough from JSON-LD
    valid_through = job.get("valid_through")
    if valid_through:
        try:
            vt = datetime.fromisoformat(valid_through.replace("Z", "+00:00"))
            if vt < datetime.now(timezone.utc):
                return False  # Expired
        except (ValueError, TypeError):
            pass
    
    # Check datePosted
    date_posted = job.get("date_posted")
    if date_posted:
        try:
            posted = datetime.fromisoformat(date_posted.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - posted).days
            if age_days > max_age_days:
                return False  # Too old
        except (ValueError, TypeError):
            pass
    
    return True


async def extract_jsonld_jobs(html: str, company_slug: str) -> list[dict]:
    """Extract JobPosting structured data from HTML via JSON-LD."""
    if not html:
        return []
    
    jobs = []
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
                
                for item in items:
                    if item.get("@type") == "JobPosting":
                        # Extract location
                        location = ""
                        job_loc = item.get("jobLocation", {})
                        if isinstance(job_loc, dict):
                            addr = job_loc.get("address", {})
                            if isinstance(addr, dict):
                                parts = [
                                    addr.get("addressLocality", ""),
                                    addr.get("addressRegion", ""),
                                    addr.get("addressCountry", ""),
                                ]
                                location = ", ".join(p for p in parts if p)
                        
                        # Extract salary
                        salary_info = None
                        base_salary = item.get("baseSalary")
                        if isinstance(base_salary, dict):
                            value = base_salary.get("value", {})
                            salary_info = {
                                "currency": base_salary.get("currency", ""),
                                "min": value.get("minValue"),
                                "max": value.get("maxValue"),
                                "unit": value.get("unitText", ""),
                            }
                        
                        # Extract description (strip HTML tags)
                        desc_html = item.get("description", "")
                        if desc_html:
                            from bs4 import BeautifulSoup as BS
                            desc_text = BS(desc_html, "html.parser").get_text(separator="\n", strip=True)
                        else:
                            desc_text = ""
                        
                        jobs.append({
                            "company": item.get("hiringOrganization", {}).get("name", company_slug.title()),
                            "title": item.get("title", ""),
                            "location": location,
                            "description": desc_text,
                            "date_posted": item.get("datePosted"),
                            "valid_through": item.get("validThrough"),
                            "employment_type": item.get("employmentType"),
                            "salary": salary_info,
                            "direct_apply": item.get("directApply", False),
                            "source": "jsonld",
                        })
            except (json.JSONDecodeError, TypeError):
                continue
    except ImportError:
        pass
    
    return jobs


async def extract_job_links_from_html(html: str, base_url: str, company_slug: str) -> list[dict]:
    """Extract job application links from career page HTML."""
    if not html:
        return []
    
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        soup = BeautifulSoup(html, "html.parser")
        links = []
        seen_urls = set()
        
        # Known ATS selectors
        selectors = [
            'a[href*="boards.greenhouse.io"]',
            'a[href*="jobs.lever.co"]',
            'a[href*="jobs.ashbyhq.com"]',
            'a[href*="apply.workable.com"]',
            'a[href*="/apply"]',
            'a[href*="/jobs/"]',
            'a[href*="/careers/"]',
            'a[href*="/openings/"]',
            'a[href*="/positions/"]',
        ]
        
        for selector in selectors:
            for a_tag in soup.select(selector):
                href = a_tag.get("href", "").strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                
                full_url = urljoin(base_url, href)
                if full_url in seen_urls:
                    continue
                
                link_text = a_tag.get_text(strip=True)[:200]
                
                # Skip non-job links
                if not link_text or len(link_text) < 4:
                    continue
                if any(skip in link_text.lower() for skip in [
                    "view all", "all jobs", "browse", "search", "categories",
                    "hiring journey", "benefits", "culture", "values",
                ]):
                    continue
                
                seen_urls.add(full_url)
                links.append({
                    "url": full_url,
                    "text": link_text,
                    "source": "html_link",
                })
        
        return links
    except ImportError:
        return []


async def try_ats_apis(company_slug: str, role_keywords: str, location: str) -> list[dict]:
    """Try ATS API adapters for a company slug.
    
    If we have verified ATS platform data, try that platform first.
    Otherwise, try all known ATS platforms.
    """
    verified = get_verified_info(company_slug)
    detected_ats = verified.get("ats_platform") if verified else None

    # If we know the ATS platform, try it first (and only it)
    if detected_ats:
        try:
            if detected_ats == "greenhouse":
                return await ats_api.fetch_greenhouse_jobs(company_slug)
            elif detected_ats == "lever":
                return await ats_api.fetch_lever_jobs(company_slug)
            elif detected_ats == "ashby":
                return await ats_api.fetch_ashby_jobs(company_slug)
            elif detected_ats == "freshteam":
                return await ats_api.fetch_freshteam_jobs(company_slug)
        except Exception:
            pass

    # Fallback: try all ATS APIs
    all_jobs = []

    # Try Greenhouse
    try:
        gh_jobs = await ats_api.fetch_greenhouse_jobs(company_slug)
        all_jobs.extend(gh_jobs)
    except Exception:
        pass

    if all_jobs:
        return all_jobs

    # Try Lever
    try:
        lever_jobs = await ats_api.fetch_lever_jobs(company_slug)
        all_jobs.extend(lever_jobs)
    except Exception:
        pass

    if all_jobs:
        return all_jobs

    # Try Ashby
    try:
        ashby_jobs = await ats_api.fetch_ashby_jobs(company_slug)
        all_jobs.extend(ashby_jobs)
    except Exception:
        pass

    if all_jobs:
        return all_jobs

    # Try Freshteam
    try:
        ft_jobs = await ats_api.fetch_freshteam_jobs(company_slug)
        all_jobs.extend(ft_jobs)
    except Exception:
        pass

    return all_jobs


async def try_career_pages(company_slug: str, role_keywords: str, location: str) -> list[dict]:
    """Try career page URLs to find job listings.
    
    ONLY tries verified URLs from company_career_urls.json.
    Does NOT generate URL patterns (they almost never work).
    """
    verified = get_verified_info(company_slug)

    # Only try URLs if we have verified data
    if not verified:
        return []

    urls_to_try = []

    # If verified_url has jobs, use it directly (highest confidence)
    if verified.get("has_jobs") and verified.get("verified_url"):
        urls_to_try.append(("verified", verified["verified_url"]))
    # If verified_url exists but no jobs confirmed, still try it
    elif verified.get("verified_url"):
        urls_to_try.append(("verified", verified["verified_url"]))
    # Fall back to original careers URL
    elif verified.get("careers_url"):
        urls_to_try.append(("original", verified["careers_url"]))

    for source, url in urls_to_try:
        try:
            page = await scrape.fetch_page(url)
            if page.get("error") or not page.get("html"):
                continue

            html = page["html"]

            # Try JSON-LD extraction first
            jsonld_jobs = await extract_jsonld_jobs(html, company_slug)
            if jsonld_jobs:
                for job in jsonld_jobs:
                    job["career_page_url"] = url
                    job["source"] = f"career_page_{source}"
                return jsonld_jobs

            # Try HTML link extraction
            links = await extract_job_links_from_html(html, url, company_slug)
            if links:
                jobs = []
                for link in links[:MAX_JOBS_PER_COMPANY]:
                    jobs.append({
                        "company": company_slug.title(),
                        "title": link["text"],
                        "apply_url": link["url"],
                        "career_page_url": url,
                        "jd_text": "",
                        "source": f"career_page_{source}",
                    })
                return jobs
        except Exception:
            continue

    return []


async def scrape_single_company(
    company_slug: str,
    role_keywords: str,
    location: str,
    user_experience: float | None,
) -> list[dict]:
    """Scrape jobs from a single company's career page or ATS API.
    
    Strategy based on verification data:
    1. If has_jobs=True: Use verified URL directly (confirmed real jobs)
    2. If ats_platform detected: Try that ATS API (Greenhouse, Lever, etc.)
    3. Otherwise: Skip (marketing pages with no accessible jobs)
    """
    verified = get_verified_info(company_slug)

    # Skip companies with no useful data
    if not verified:
        return []

    has_confirmed_jobs = verified.get("has_jobs") and verified.get("verified_url")
    has_ats = verified.get("ats_platform")

    # If no confirmed jobs and no ATS, skip this company
    if not has_confirmed_jobs and not has_ats:
        return []

    jobs = []

    # Step 1: If confirmed jobs, try career page first
    if has_confirmed_jobs:
        jobs = await try_career_pages(company_slug, role_keywords, location)
        if jobs:
            log.info("verified_url_success", company=company_slug, count=len(jobs))
            # If we got jobs from career page, also try ATS as backup
            ats_jobs = await try_ats_apis(company_slug, role_keywords, location)
            if ats_jobs:
                # Merge ATS jobs (avoid duplicates by URL)
                seen_urls = {j.get("apply_url", "") for j in jobs}
                for ats_job in ats_jobs:
                    if ats_job.get("apply_url", "") not in seen_urls:
                        jobs.append(ats_job)
                        seen_urls.add(ats_job.get("apply_url", ""))
        else:
            # Career page didn't work, try ATS
            jobs = await try_ats_apis(company_slug, role_keywords, location)
    else:
        # Only ATS available
        jobs = await try_ats_apis(company_slug, role_keywords, location)

    if not jobs:
        return []

    # Step 2: Filter jobs
    filtered = []
    for job in jobs:
        title = job.get("title", "")

        # Filter by role keywords
        if not matches_role_keywords(title, role_keywords):
            continue

        # Filter by experience
        jd_text = job.get("jd_text", "") or job.get("description", "")
        if user_experience is not None and jd_text:
            required_exp = parse_experience_from_jd(jd_text)
            if required_exp is not None and required_exp > user_experience:
                continue

        # Filter by freshness
        if not is_job_fresh(job):
            continue

        # Normalize the job dict
        normalized = {
            "company": job.get("company", company_slug.title()),
            "title": title[:160],
            "career_page_url": job.get("career_page_url", ""),
            "apply_url": job.get("apply_url", ""),
            "jd_text": jd_text[:20000],
            "source": job.get("source", "ats_api"),
            "confidence": job.get("confidence", 0.95),
            "location": job.get("location", ""),
            "experience_required": parse_experience_from_jd(jd_text),
            "date_posted": job.get("date_posted"),
            "valid_through": job.get("valid_through"),
        }

        if not normalized["apply_url"]:
            normalized["apply_url"] = normalized["career_page_url"]

        filtered.append(normalized)

    return filtered[:MAX_JOBS_PER_COMPANY]


async def run(state: dict) -> dict:
    """Career Scraper: Systematic career page discovery.
    
    Input state: {"location": str, "profile": dict, "role": str, "limit": int}
    Output: adds to state["discovered_jobs"] and state["events"]
    """
    location = state.get("location", "Bengaluru")
    profile = state.get("profile", {})
    role = state.get("role") or "software engineer"
    limit = state.get("limit") or MAX_TOTAL_JOBS
    
    from vellum.tools.ats_api import TECH_HUB_STARTUPS
    from vellum.agents import job_evaluator
    
    # Get company list for this location
    location_key = location.lower().strip()
    aliases = {
        "bangalore": "bengaluru", "bombay": "mumbai",
        "gurgaon": "ncr", "gurugram": "ncr", "noida": "ncr", "delhi": "ncr",
    }
    location_key = aliases.get(location_key, location_key)
    company_list = TECH_HUB_STARTUPS.get(location_key, [])
    
    if not company_list:
        log.warning("no_companies_for_location", location=location)
        return {"discovered_jobs": [], "events": [], "errors": [f"No companies found for {location}"]}
    
    # Extract user experience
    user_experience = None
    exp_str = profile.get("relevant_experience", "")
    if exp_str:
        try:
            user_experience = float(re.search(r"(\d+)", str(exp_str)).group(1))
        except (AttributeError, ValueError):
            pass
    
    events = []
    all_jobs = []
    
    # Broadcast start
    await ws_manager.broadcast({
        "agent": "career_scraper",
        "event_type": "search_progress",
        "message": f"Scanning {len(company_list)} companies in {location}...",
        "data": {"percentage": 0, "total_companies": len(company_list)},
    })
    
    # Scrape each company
    for idx, company_slug in enumerate(company_list):
        if len(all_jobs) >= limit:
            break
        
        try:
            company_jobs = await scrape_single_company(
                company_slug, role, location, user_experience
            )
            all_jobs.extend(company_jobs)
            
            if company_jobs:
                log.info("company_jobs_found",
                    company=company_slug, count=len(company_jobs))
        except Exception as exc:
            log.warning("company_scrape_error",
                company=company_slug, error=str(exc)[:100])
        
        # Progress update every 10 companies
        if (idx + 1) % 10 == 0 or idx == len(company_list) - 1:
            pct = int(((idx + 1) / len(company_list)) * 70)
            await ws_manager.broadcast({
                "agent": "career_scraper",
                "event_type": "search_progress",
                "message": f"Scanned {idx + 1}/{len(company_list)} companies. Found {len(all_jobs)} jobs so far.",
                "data": {"percentage": pct, "scanned": idx + 1, "total": len(company_list), "jobs_found": len(all_jobs)},
            })
        
        # Small delay between companies to be respectful
        import asyncio
        await asyncio.sleep(0.5)
    
    # Deduplicate by apply_url
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get("apply_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            unique_jobs.append(job)
    
    all_jobs = unique_jobs[:limit]
    
    # Batch LLM scoring
    await ws_manager.broadcast({
        "agent": "career_scraper",
        "event_type": "search_progress",
        "message": f"Scoring {len(all_jobs)} jobs for relevance...",
        "data": {"percentage": 75},
    })
    
    try:
        filtered_jobs = await job_evaluator.filter_jobs(all_jobs, profile, role)
    except Exception as exc:
        log.error("job_evaluator_error", error=str(exc))
        filtered_jobs = all_jobs
    
    # Store in DB and collect results
    stored_jobs = []
    for job in filtered_jobs:
        try:
            listing = JobListing(
                company=job["company"],
                role=job["title"],
                career_page_url=job.get("career_page_url", ""),
                apply_url=job.get("apply_url", ""),
                jd_text=job.get("jd_text", ""),
                source=job.get("source", "career_scraper"),
                discovery_confidence=job.get("confidence", 0.9),
            )
            job_dict = listing.model_dump(mode="json")
            job_id = await db.insert_job(job_dict)
            if job_id:
                job_dict["id"] = job_id
                job_dict["match_score"] = job.get("match_score", 0.5)
                stored_jobs.append(job_dict)
                
                event_dict = AgentEvent(
                    agent="career_scraper",
                    event_type="discovery",
                    job_id=job_id,
                    message=f"Discovered: {job['company']} — {job['title'][:80]}",
                    confidence=job.get("confidence", 0.9),
                ).model_dump(mode="json")
                events.append(event_dict)
                await ws_manager.broadcast(event_dict)
        except Exception as exc:
            log.warning("job_insertion_failed", company=job.get("company"), error=str(exc))
    
    await ws_manager.broadcast({
        "agent": "career_scraper",
        "event_type": "search_progress",
        "message": f"Discovery complete! Found {len(stored_jobs)} relevant jobs.",
        "data": {"percentage": 100},
    })
    
    log.info("career_scraping_complete", total_discovered=len(stored_jobs))
    return {
        "discovered_jobs": stored_jobs,
        "events": events,
        "errors": [],
    }
