"""
JobHunterX — Job Title & Company Name Extraction & Normaliser Utility

Heuristic + Rule-based parser to clean raw web-scraped job titles and companies.
Strips aggregator portal tails (Bayt, Weekday, Indeed, etc.), extracts real company
and role from search result headlines, and eliminates 'Unknown' / generic titles.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Common job aggregator portals that should never be used as hiring company names
PORTAL_DOMAINS = {
    "bayt.com", "bayt", "weekday", "weekdayworks", "hasjob", "greenhouse",
    "lever", "ashby", "ashbyhq", "linkedin", "indeed", "naukri", "monster",
    "jobgether", "instahyre", "aijobs", "hirect", "apna", "wellfound", "angel",
    "glassdoor", "simplyhired", "ziprecruiter", "jobsora", "careerjet",
}

# Common role keywords to distinguish role titles from company names
ROLE_KEYWORDS = {
    "engineer", "developer", "architect", "lead", "manager", "specialist",
    "consultant", "analyst", "scientist", "head", "director", "vp", "cto",
    "intern", "designer", "administrator", "sme", "tester", "qa",
}

# Generic title noise to strip or replace
BAD_TITLE_PATTERNS = [
    r"^attach\s+resume/cv", r"^submit\s+application", r"^apply\s+now",
    r"^job\s+application\s+for\s+", r"^careers?\s+at\s+", r"^hiring\s+",
    r"jobs?\s+opening\s+in\s+", r"jobs?\s+in\s+",
]


def clean_job_title_and_company(
    raw_title: str | None,
    raw_company: str | None,
    snippet: str | None = "",
    apply_url: str | None = "",
) -> tuple[str, str]:
    """Clean and extract verified Job Title and Company Name.

    Returns:
        (company_name, job_role)
    """
    title = (raw_title or "").strip()
    company = (raw_company or "").strip()
    snippet_text = (snippet or "").strip()
    url_str = (apply_url or "").strip()

    # Step 1: Clean raw company if it's a portal, "Unknown", placeholder, or contains a role keyword
    if company.lower() in ("unknown", "n/a", "none", "not specified", "not-specified", "unspecified", "clean company name") or any(p in company.lower() for p in PORTAL_DOMAINS) or any(k in company.lower() for k in ROLE_KEYWORDS):
        company = ""

    # Step 2: Check snippet for explicit "Company Name: X" or "Company: X"
    if not company and snippet_text:
        m = re.search(r"(?:company\s*name|company|client)\b\s*:\s*([A-Za-z0-9\.\&\-\s]+?)(?:\s+(?:industry|location|about|role|job|position|full|part|contract|tech)|[,\.\n]|$)", snippet_text, re.I)
        if m:
            candidate_comp = m.group(1).strip()
            if not _is_city_or_portal(candidate_comp) and not any(k in candidate_comp.lower() for k in ROLE_KEYWORDS):
                company = _sanitize_company_string(candidate_comp)

    # Step 3: Extract from title if title contains "Job Application for <Role> at <Company>"
    m = re.search(r"job\s+application\s+for\s+(.*?)\s+at\s+(.*)", title, re.I)
    if m:
        extracted_role = m.group(1).strip()
        extracted_company = m.group(2).strip()
        comp_parts = [p.strip() for p in re.split(r"\s*[\-\|—–]\s*", extracted_company) if p.strip()]
        valid_parts = [p for p in comp_parts if not _is_city_or_portal(p)]
        if valid_parts and not company:
            company = _sanitize_company_string(valid_parts[0])
        title = extracted_role

    # Step 4: Extract from title if title contains "<Role> at <Company>" or "<Role> in <Company>"
    if not company or _is_city_or_portal(company):
        m = re.search(r"(.*?)\s+at\s+([A-Za-z0-9\s\.\&\-]+)", title, re.I)
        if m:
            candidate_role = m.group(1).strip()
            candidate_comp = m.group(2).strip()
            comp_parts = [p.strip() for p in re.split(r"\s*[\-\|—–]\s*", candidate_comp) if p.strip()]
            valid_parts = [p for p in comp_parts if not _is_city_or_portal(p)]
            if valid_parts:
                company = _sanitize_company_string(valid_parts[0])
                # Clean candidate role if hyphenated
                role_parts = [p.strip() for p in re.split(r"\s*[\-\|—–]\s*", candidate_role) if p.strip()]
                if len(role_parts) >= 2:
                    title = " ".join(role_parts)
                else:
                    title = candidate_role

    # Step 4: Handle hyphen / pipe separated titles (e.g. "Company - Role" or "Role - Company - Portal")
    if (" - " in title or " | " in title or " — " in title) and (not company or _is_city_or_portal(company)):
        parts = [p.strip() for p in re.split(r"\s*[\-\|—–]\s*", title) if p.strip()]
        # Strip trailing portal parts (e.g. "Bayt.com")
        clean_parts = [p for p in parts if not _is_city_or_portal(p)]

        if len(clean_parts) >= 2:
            part0_has_role = any(k in clean_parts[0].lower() for k in ROLE_KEYWORDS)
            part1_has_role = any(k in clean_parts[1].lower() for k in ROLE_KEYWORDS)

            if part0_has_role and not part1_has_role:
                title = clean_parts[0]
                if not company:
                    company = _sanitize_company_string(clean_parts[1])
            elif part1_has_role and not part0_has_role:
                title = clean_parts[1]
                if not company:
                    company = _sanitize_company_string(clean_parts[0])
            elif len(clean_parts) >= 3:
                # e.g. "Smart Working Solutions - AI Engineer - ElevenLabs"
                company = _sanitize_company_string(clean_parts[0])
                title = clean_parts[1]

    # Step 5: Clean title noise (e.g. "Job Application for...", "ATTACH RESUME/CV", portal prefixes)
    for p in PORTAL_DOMAINS:
        title = re.sub(r"(?i)^\s*" + re.escape(p) + r"\b\s*[\-\|—–]\s*", "", title).strip()
        title = re.sub(r"(?i)\s*[\-\|—–]\s*" + re.escape(p) + r"\b\s*$", "", title).strip()

    title_lower = title.lower()
    for bad_pat in BAD_TITLE_PATTERNS:
        title = re.sub(bad_pat, "", title, flags=re.I).strip()

    if not title or title.lower() in ("attach resume/cv", "submit application", "apply now", "careers"):
        # Try extracting role from snippet or URL
        title = _extract_role_from_snippet_or_url(snippet_text, url_str)

    # Step 6: Extract company from URL domain or snippet if still empty
    if not company or _is_city_or_portal(company):
        company = _extract_company_from_url_or_snippet(url_str, snippet_text)

    # Fallback formatting
    company = _sanitize_company_string(company) or "Tech Company"
    title = title.strip() or "Software Engineer"

    return company, title


def _is_city_or_portal(text: str) -> bool:
    """Return True if string is a portal domain or city name."""
    t = text.lower().strip()
    if any(p in t for p in PORTAL_DOMAINS):
        return True
    cities = {
        "hyderabad", "bengaluru", "bangalore", "mumbai", "ncr", "delhi", "gurgaon",
        "noida", "pune", "chennai", "remote", "india", "hitech city", "secunderabad",
    }
    if t in cities:
        return True
    return False


def _sanitize_company_string(raw: str) -> str:
    """Format company name properly."""
    if not raw:
        return ""
    s = raw.strip()
    s = re.sub(r"(?i)\s*\b(careers?|jobs?|hiring|inc\.?|ltd\.?|llc|pvt|corp\.?|portal|board)\b.*", "", s).strip()
    s = re.sub(r"\s*[\-|–|—|\|].*", "", s).strip()
    if len(s) < 2 or len(s) > 40:
        return ""
    return s.title()


def _extract_role_from_snippet_or_url(snippet: str, url: str) -> str:
    """Extract job title from text snippet or URL path."""
    text = snippet[:500]
    m = re.search(r"(senior|junior|lead|principal|staff|head|generative)?\s*(ai|ml|python|full\s*stack|backend|frontend|software|data)\s*(engineer|developer|architect|scientist|lead)", text, re.I)
    if m:
        return m.group(0).title()

    if url:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        for p in path_parts:
            p_clean = p.replace("-", " ").replace("_", " ")
            if any(k in p_clean.lower() for k in ROLE_KEYWORDS):
                return p_clean.title()

    return "Software Engineer"


def _extract_company_from_url_or_snippet(url: str, snippet: str) -> str:
    """Extract hiring company from URL structure or snippet text."""
    if snippet:
        # Check snippet for "Company Name: X" or "hiring at X" or "Client: X"
        m = re.search(r"(?:company\s*name|hiring\s+at|client):\s*([A-Za-z0-9\s\.\&]+)", snippet, re.I)
        if m:
            comp = m.group(1).strip()
            if not _is_city_or_portal(comp):
                return _sanitize_company_string(comp)

        m = re.search(r"at\s+([A-Z][A-Za-z0-9\&]{2,20})\b", snippet)
        if m:
            comp = m.group(1).strip()
            if not _is_city_or_portal(comp):
                return _sanitize_company_string(comp)

    if url:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        # Handle ATS subdomains like globalhealthcareexchangeinc.greenhouse.io
        parts = netloc.split(".")
        if len(parts) >= 3 and parts[-2] in ("greenhouse", "lever", "ashbyhq", "workday"):
            candidate = parts[0]
            if candidate not in ("boards", "jobs"):
                return _sanitize_company_string(candidate.replace("-", " ").replace("_", " "))

        # Handle path like jobs.lever.co/companyname
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts and len(path_parts[0]) > 2 and not _is_city_or_portal(path_parts[0]):
            return _sanitize_company_string(path_parts[0].replace("-", " "))

        # Fallback to domain name if not portal
        domain_name = parts[0]
        if domain_name not in PORTAL_DOMAINS and len(domain_name) > 2:
            return domain_name.title()

    return ""
