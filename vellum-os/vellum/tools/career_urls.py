"""
Vellum OS — Career Page URL Pattern Database

Maps company slugs to known career page URL patterns and ATS detection.
Used by career_scraper.py to systematically discover job listings
without relying on search engines.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from vellum.config.logging import get_logger

log = get_logger("career_urls")


# ---------------------------------------------------------------------------
# ATS Domain Detection Patterns
# ---------------------------------------------------------------------------

ATS_PATTERNS = {
    "greenhouse": {
        "domain_pattern": r"boards\.greenhouse\.io",
        "api_url": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
        "career_url": "https://boards.greenhouse.io/{slug}",
    },
    "lever": {
        "domain_pattern": r"(?:jobs\.)?lever\.co",
        "api_url": "https://api.lever.co/v0/postings/{slug}?mode=json",
        "career_url": "https://jobs.lever.co/{slug}",
        "api_url_eu": "https://api.eu.lever.co/v0/postings/{slug}?mode=json",
    },
    "ashby": {
        "domain_pattern": r"jobs\.ashbyhq\.com",
        "api_url": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
        "career_url": "https://jobs.ashbyhq.com/{slug}",
    },
    "smartrecruiters": {
        "domain_pattern": r"(?:jobs\.)?smartrecruiters\.com",
        "api_url": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        "career_url": "https://jobs.smartrecruiters.com/{slug}",
    },
    "freshteam": {
        "domain_pattern": r"freshteam\.com",
        "api_url": "https://{slug}.freshteam.com/jobs.json",
        "career_url": "https://{slug}.freshteam.com/jobs",
    },
    "workday": {
        "domain_pattern": r"myworkdayjobs\.com",
        "career_url": "https://{slug}.wd1.myworkdayjobs.com",
    },
    "bamboohr": {
        "domain_pattern": r"bamboohr\.com",
        "career_url": "https://{slug}.bamboohr.com/careers",
    },
    "recruitee": {
        "domain_pattern": r"recruitee\.com",
        "career_url": "https://{slug}.recruitee.com",
    },
    "breezy": {
        "domain_pattern": r"breezy\.hr",
        "career_url": "https://breezy.hr/{slug}",
    },
}


# ---------------------------------------------------------------------------
# Career Page URL Patterns (tried in order)
# ---------------------------------------------------------------------------

CAREER_URL_PATTERNS = [
    # Direct company domain patterns
    "https://careers.{slug}.com",
    "https://careers.{slug}.com/jobs",
    "https://careers.{slug}.com/openings",
    "https://careers.{slug}.com/positions",
    "https://careers.{slug}.com/hiring",
    "https://{slug}.com/careers",
    "https://{slug}.com/careers/jobs",
    "https://{slug}.com/jobs",
    "https://{slug}.com/openings",
    "https://{slug}.com/positions",
    "https://{slug}.com/hiring",
    "https://www.{slug}.com/careers",
    "https://www.{slug}.com/jobs",
    # ATS-hosted career pages
    "https://boards.greenhouse.io/{slug}",
    "https://jobs.lever.co/{slug}",
    "https://jobs.ashbyhq.com/{slug}",
    "https://jobs.smartrecruiters.com/{slug}",
    "https://{slug}.freshteam.com/jobs",
]


# ---------------------------------------------------------------------------
# Contact / About Page URL Patterns (for email finding)
# ---------------------------------------------------------------------------

CONTACT_PAGE_PATTERNS = [
    "https://{domain}/contact",
    "https://{domain}/contact-us",
    "https://{domain}/contact/",
    "https://{domain}/contactus",
    "https://{domain}/get-in-touch",
    "https://{domain}/about",
    "https://{domain}/about/team",
    "https://{domain}/about/leadership",
    "https://{domain}/about/us",
    "https://{domain}/team",
    "https://{domain}/people",
    "https://{domain}/our-team",
    "https://{domain}/meet-the-team",
    # .html static variants — common on SMB/Indian company sites
    "https://{domain}/contact.html",
    "https://{domain}/contact-us.html",
    "https://{domain}/about.html",
    "https://{domain}/team.html",
    "https://{domain}/people.html",
    "https://{domain}/about/team.html",
    # Legal pages — statistically email-rich (privacy/legal contacts)
    "https://{domain}/privacy",
    "https://{domain}/privacy-policy",
    "https://{domain}/terms",
    "https://{domain}/terms-of-service",
    "https://{domain}/imprint",
    "https://{domain}/legal",
    "https://{domain}/legal/contact",
    # Press / media kit pages — publish real media-contact emails
    "https://{domain}/press",
    "https://{domain}/press-kit",
    "https://{domain}/media",
    "https://{domain}/media-kit",
    "https://{domain}/newsroom",
    "https://{domain}/news",
    "https://{domain}/press-releases",
    "https://{domain}/resources/press-kit",
]


# ---------------------------------------------------------------------------
# Domains to NEVER scrape (third-party aggregators)
# ---------------------------------------------------------------------------

EXCLUDED_DOMAINS = {
    # Job aggregators
    "linkedin.com", "indeed.com", "glassdoor.com", "glassdoor.co.in",
    "naukri.com", "monster.com", "internshala.com", "ambitionbox.com",
    "jooble.org", "jooble.in", "ziprecruiter.com", "simplyhired.com",
    "careerjet.com", "talent.com", "jobrapido.com", "adzuna.com",
    "jora.com", "foundit.in", "shine.com", "timesjobs.com",
    "cutshort.io", "instahyre.com", "hirect.in", "apna.co",
    "wellfound.com", "12indiajobs.com", "winit.com", "winitjobs.com",
    "updazz.com", "payscale.com", "fresherworld.com",
    # Third-party ATS (we use their APIs, not web scraping)
    "bamboohr.com", "recruitee.com", "breezy.hr", "workable.com",
    "jobvite.com", "icims.com",
    # Staffing agencies
    "randstad.com", "adecco.com", "manpowergroup.com",
    "teamlease.com", "quess.in", "collabera.com",
}


# ---------------------------------------------------------------------------
# URL Quality Scoring
# ---------------------------------------------------------------------------

def is_excluded_domain(url: str) -> bool:
    """Check if a URL belongs to an excluded domain."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return any(excluded in domain for excluded in EXCLUDED_DOMAINS)
    except Exception:
        return False


def detect_ats_from_url(url: str) -> str | None:
    """Detect which ATS a URL belongs to."""
    url_lower = url.lower()
    for ats_name, config in ATS_PATTERNS.items():
        if re.search(config["domain_pattern"], url_lower):
            return ats_name
    return None


def score_career_url(url: str, company_slug: str = "") -> float:
    """Score a URL for career-page relevance. Higher = better. Range ~0.0-1.0."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
    except Exception:
        return 0.0

    score = 0.5

    # Bonus for known ATS domains (direct API access)
    for ats_name, config in ATS_PATTERNS.items():
        if re.search(config["domain_pattern"], domain):
            score += 0.3
            break

    # Bonus for career-related path patterns
    career_patterns = [
        "/careers?", "/jobs?", "/openings", "/positions",
        "/apply", "/join-us", "/work-with-us", "/vacancies",
    ]
    if any(p in path for p in career_patterns):
        score += 0.25

    # Bonus if company slug appears in domain
    if company_slug:
        slug_clean = re.sub(r"[^a-z0-9]", "", company_slug.lower())
        if slug_clean and slug_clean in domain:
            score += 0.15

    # Penalty for excluded domains
    if is_excluded_domain(url):
        return 0.0

    # Penalty for noise patterns
    noise_patterns = ["/news", "/blog", "/article", "/press", "/about", "/wiki", "/review"]
    if any(p in path for p in noise_patterns):
        score -= 0.3

    return max(0.0, min(1.0, score))


def get_ats_api_url(ats_type: str, slug: str) -> str | None:
    """Get the API URL for a given ATS type and company slug."""
    config = ATS_PATTERNS.get(ats_type)
    if not config:
        return None
    api_url = config.get("api_url")
    if api_url:
        return api_url.format(slug=slug)
    return None


def get_career_urls_for_slug(slug: str) -> list[str]:
    """Generate career page URLs to try for a company slug."""
    return [pattern.format(slug=slug) for pattern in CAREER_URL_PATTERNS]


def get_contact_urls_for_domain(domain: str) -> list[str]:
    """Generate contact/about page URLs to try for a company domain."""
    return [pattern.format(domain=domain) for pattern in CONTACT_PAGE_PATTERNS]
