"""
JobHunterX — Job Validator Agent (Company Name & Job Quality Verification)

Validates discovered search results to ensure:
  1. The entry is a real, legitimate tech job posting (not a blog post, Russian spam, or aggregator page).
  2. The company name is a clean, genuine organization name (not a web heading, SEO text, or title fragment).
  3. The job role is a concise professional title (e.g., 'AI Engineer', 'Backend Developer').
"""

from __future__ import annotations

import json
import re
from typing import Any

from jobhunterx.config.llm_router import call_llm_with_fallback
from jobhunterx.config.logging import get_logger
from jobhunterx.utils.json_helper import parse_llm_json

log = get_logger("job_validator_agent")

_VALIDATE_JOB_PROMPT = """You are a strict job posting quality auditor and data normalization agent.
Review the discovered job posting details below and clean up the Company Name and Job Title.

DISCOVERED ITEM:
Raw Company: "{company}"
Raw Role/Title: "{role}"
URL: "{url}"
Description Snippet: "{jd_snippet}"

RULES:
1. **is_valid_job**: Set to true ONLY if this is a real tech/software job vacancy posting. Set to false if it's foreign non-English spam, a news article, random blog post, or non-job webpage.
2. **clean_company**: Extract the EXACT, clean official name of the hiring company or startup (e.g., "Monterail", "Zimperium", "Tensorops", "Startupfellows").
   - DO NOT include generic words like "Fresher Jobs", "Freelancer", "Hiring", "Careers", "AI Engineer in team...", or foreign language text like "Вакансия |".
   - If the company name is missing or corrupted, extract the real company name from the description snippet or URL domain.
3. **clean_role**: Provide a clean, standardized job title (e.g., "AI Engineer", "LLM Engineer", "Software Engineer"). Strip website titles, company names, and location suffixes from the title.

Return ONLY a JSON object with this exact structure:
{{
  "is_valid_job": true,
  "clean_company": "Clean Company Name",
  "clean_role": "Clean Job Title",
  "reject_reason": ""
}}
Return valid JSON only."""


KNOWN_AGGREGATOR_NAMES = {
    "startup jobs", "remote rocketship", "dailyremote", "jobtogether", "jobgether",
    "remoteco", "remote.co", "remote ok", "weworkremotely", "jobspresso", "himalayas",
    "flexjobs", "workingnomads", "jobserf", "postjobfree", "bebee", "careerbuilder",
    "lensa", "jobisite", "jobisjob", "jora", "jobindex", "trovit", "careerarc",
    "snagajob", "jobtarget", "indeed", "glassdoor", "naukri", "monster", "simplyhired",
    "ziprecruiter", "jooble", "adzuna", "talent", "hirect", "internshala", "apna", "workindia",
}


def _extract_real_company_from_text(text: str) -> str:
    """Try to extract a genuine hiring company name from text snippet or job title."""
    if not text:
        return ""
    
    # Patterns like "at Sharebite", "@ Tensorops", "by Zimperium", "Job Application for AI Engineer at Sharebite"
    patterns = [
        r"(?:at|@|for|join)\s+([A-Z][A-Za-z0-9\s&\.]{2,25})\b",
        r"([A-Z][A-Za-z0-9]{2,25})\s+is\s+(?:hiring|looking|building|seeking)",
        r"(?:at|@)\s+([A-Za-z0-9\.\-]{3,20})\s+Back to jobs",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            candidate = m.group(1).strip()
            # Clean common trailing punctuation or filler
            candidate = re.sub(r"\s*[-|·—].*$", "", candidate).strip()
            low = candidate.lower()
            if candidate and low not in KNOWN_AGGREGATOR_NAMES and len(candidate) >= 3 and len(candidate) <= 30:
                if not any(g in low for g in ["fresher", "jobs", "hiring", "careers", "remote", "engineer", "developer"]):
                    return candidate.title()
    return ""


def sanitize_company_name_heuristically(raw_company: str, raw_title: str, url: str) -> str:
    """Fast deterministic sanitizer for company names."""
    if not raw_company:
        return ""
    
    # 1. Reject foreign script noise (e.g. Cyrillic)
    if re.search(r"[\u0400-\u04FF]", raw_company):
        return ""
    
    # 2. Clean common delimiters (e.g. "Monterail · workingengineering.eu" -> "Monterail")
    company = re.split(r"\s*[-|·—@]\s*", raw_company)[0].strip()
    company = re.sub(r"\s*\|.*$", "", company).strip()
    company = re.sub(r"\s*\(.*\)$", "", company).strip()
    
    # 3. Strip legal suffixes
    company = re.sub(r"\b(Inc|LLC|Ltd|Pvt|Private|Limited|Corp|Corporation|Co)\.?$", "", company, flags=re.I).strip()
    
    low = company.lower()
    # 4. Check if the extracted company name is an aggregator or job board name
    if low in KNOWN_AGGREGATOR_NAMES or any(agg in low for agg in ["remote rocketship", "dailyremote", "startup jobs", "jobtogether", "jobgether"]):
        # Try extracting the real company from title (e.g. "AI Engineer at Sharebite" -> "Sharebite")
        real_co = _extract_real_company_from_text(raw_title)
        if real_co:
            return real_co
        return "" # Mark as empty so validator rejects or requires LLM parse
    
    # 5. If it still looks like a sentence or job title, discard
    words = company.split()
    if len(words) > 4:
        return ""
    
    garbage_keywords = [
        "fresher", "vacancies", "hiring", "careers", "jobs", "overview", "reviews",
        "freelancer", "freelance", "salary", "contract", "remote", "engineer", "developer"
    ]
    if any(k in low for k in garbage_keywords) and len(words) > 2:
        return ""

    return company.title()


def sanitize_role_title_heuristically(raw_title: str, company_name: str) -> str:
    """Fast deterministic sanitizer for job titles."""
    if not raw_title:
        return "Software Engineer"
    
    title = raw_title.strip()
    # Strip Russian/Cyrillic noise if present
    title = re.sub(r"[\u0400-\u04FF].*", "", title).strip()
    
    # Remove company name if embedded in title
    if company_name and len(company_name) > 2:
        pattern = re.escape(company_name)
        title = re.sub(pattern, "", title, flags=re.I).strip()
    
    # Strip common prefixes/suffixes like "at Monterail", "Apply directly", "- Bangalore, India"
    title = re.sub(r"\s*[-|·—].*$", "", title).strip()
    title = re.sub(r"\s+(?:at|@)\s+.*$", "", title, flags=re.I).strip()
    title = re.sub(r"(?:Hiring|Careers|Jobs|Openings|Apply).*$", "", title, flags=re.I).strip()
    title = re.sub(r"\s{2,}", " ", title).strip(" ,.-|")

    if not title or len(title) < 3:
        return "Software Engineer"
    return title.title()


async def validate_and_clean_job(job: dict) -> dict:
    """Validate a single job dict and clean company name and role.
    
    Returns dict with keys: is_valid_job (bool), clean_company (str), clean_role (str)
    """
    raw_company = job.get("company", "")
    raw_role = job.get("role") or job.get("title", "")
    url = job.get("apply_url") or job.get("career_page_url", "")
    jd_snippet = (job.get("jd_text") or "")[:800]

    # Reject foreign script noise or Russian language text in company, role, or description
    combined_sample = f"{raw_company} {raw_role} {jd_snippet}".lower()
    if re.search(r"[\u0400-\u04FF]", combined_sample) or any(k in combined_sample for k in ("вакансии", "откликнуться", "команду", "разработчик")):
        log.info("rejected_foreign_garbage_job", company=raw_company, role=raw_role)
        return {
            "is_valid_job": False,
            "clean_company": "",
            "clean_role": "",
            "reject_reason": "Foreign non-English script/language noise detected"
        }

    # Quick heuristic pass first
    h_company = sanitize_company_name_heuristically(raw_company, raw_role, url)

    # Try extracting real company from JD text if company is still missing or dirty
    if not h_company:
        h_company = _extract_real_company_from_text(raw_role) or _extract_real_company_from_text(jd_snippet)

    h_role = sanitize_role_title_heuristically(raw_role, h_company or raw_company)

    # If company is an aggregator name and we couldn't find a real company, reject!
    if not h_company or h_company.lower() in KNOWN_AGGREGATOR_NAMES:
        log.info("rejected_aggregator_job", company=raw_company, role=raw_role, url=url)
        return {
            "is_valid_job": False,
            "clean_company": "",
            "clean_role": "",
            "reject_reason": "Job is from an aggregator listing page without a distinct company name"
        }

    # If heuristics yielded a clean company name and title, return fast without extra LLM call
    if h_company and h_role and len(h_company) < 30:
        return {
            "is_valid_job": True,
            "clean_company": h_company,
            "clean_role": h_role,
            "reject_reason": ""
        }

    # Otherwise, fall back to LLM to parse dirty company/role structure
    try:
        messages = [
            {"role": "system", "content": "You are a job data normalization specialist."},
            {
                "role": "user",
                "content": _VALIDATE_JOB_PROMPT.format(
                    company=raw_company,
                    role=raw_role,
                    url=url,
                    jd_snippet=jd_snippet,
                ),
            },
        ]
        result = await call_llm_with_fallback("extraction", messages)
        data = parse_llm_json(result.get("content", ""))

        if isinstance(data, dict):
            is_valid = bool(data.get("is_valid_job", True))
            c_company = (data.get("clean_company") or h_company or raw_company).strip()
            c_role = (data.get("clean_role") or h_role or raw_role).strip()

            # Reject if LLM returned an aggregator name as company
            if c_company.lower() in KNOWN_AGGREGATOR_NAMES:
                return {
                    "is_valid_job": False,
                    "clean_company": "",
                    "clean_role": "",
                    "reject_reason": "Aggregator domain detected by LLM"
                }

            return {
                "is_valid_job": is_valid,
                "clean_company": c_company,
                "clean_role": c_role,
                "reject_reason": data.get("reject_reason", ""),
            }
    except Exception as exc:
        log.warning("job_validator_llm_failed", error=str(exc))

    return {
        "is_valid_job": bool(h_company and h_company.lower() not in KNOWN_AGGREGATOR_NAMES),
        "clean_company": h_company,
        "clean_role": h_role,
        "reject_reason": "",
    }
