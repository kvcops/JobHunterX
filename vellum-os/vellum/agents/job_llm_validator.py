"""
Vellum OS — LLM-Powered Job Validator (Agent F)

Two-stage intelligent job validation:
  Stage 1: Quick experience pre-filter (regex, zero LLM cost)
  Stage 2: Gemma 4 LLM deep validation via google GenAI library directly
    (NOT litellm — litellm returns 503s for Gemma)

Enforces company diversity and minimum relevance threshold.
Loops discovery until enough quality jobs are found.

Rate limits (Gemini API for Gemma):
  - 30 requests per minute
  - 16,000 tokens per minute
  - 14,400 requests per day
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from typing import Any, Optional

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.utils.json_helper import parse_llm_json
from vellum.config.settings import get_settings

log = get_logger("job_llm_validator")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MIN_RELEVANCE_SCORE = 65       # Minimum LLM score to keep a job (0-100)
MAX_PER_COMPANY = 2            # Max jobs from same company for diversity
BATCH_SIZE = 3                 # Jobs per LLM call (keep small for quality)

# Gemma model via Gemini API (direct google library, NOT litellm)
GEMMA_MODEL = "gemma-4-26b-a4b-it"
GEMMA_THINKING_LEVEL = "minimal"  # "none" or "minimal" — keep it fast

# Rate limiting
GEMINI_RPM = 30                # 30 requests per minute
GEMINI_MIN_DELAY = 60.0 / GEMINI_RPM  # 2.0 seconds between calls

# ---------------------------------------------------------------------------
# Stage 1: Quick Experience Pre-Filter (no LLM)
# ---------------------------------------------------------------------------

def extract_required_experience(jd_text: str) -> float | None:
    """Extract minimum years of experience required from JD text."""
    if not jd_text:
        return None

    text = jd_text.lower()

    m = re.search(r"(\d+)[\s]*[-–to]+\s*(\d+)\s*years?", text)
    if m:
        return float(m.group(1))

    m = re.search(r"(\d+)\+?\s*years?", text)
    if m:
        return float(m.group(1))

    m = re.search(r"(?:minimum|at\s+least)\s+(\d+)\s*years?", text)
    if m:
        return float(m.group(1))

    level_map = {
        "intern": 0, "fresher": 0,
        "junior": 1, "associate": 1,
        "mid-level": 3, "mid level": 3,
        "senior": 5, "sr": 5,
        "lead": 7, "principal": 10, "staff": 8,
    }
    for level, years in level_map.items():
        if re.search(rf"\b{level}\b", text):
            return float(years)

    return None


def get_user_years_of_experience(profile: dict) -> float | None:
    """Extract user's years of experience from profile."""
    qa_memory = profile.get("qa_memory", {})
    if isinstance(qa_memory, dict):
        yoe = qa_memory.get("years_of_experience", "")
    else:
        yoe = getattr(qa_memory, "years_of_experience", "") or ""

    if yoe:
        m = re.search(r"(\d+)", str(yoe))
        if m:
            return float(m.group(1))

    exp_str = profile.get("relevant_experience", "")
    if exp_str:
        m = re.search(r"(\d+)", str(exp_str))
        if m:
            return float(m.group(1))

    experience_entries = profile.get("experience", [])
    if experience_entries:
        companies = set()
        for exp in experience_entries:
            if isinstance(exp, dict):
                c = exp.get("company", "")
            else:
                c = getattr(exp, "company", "")
            if c:
                companies.add(c.lower().strip())
        if companies:
            return max(1.0, float(len(companies)))

    return None


def experience_passes(user_exp: float | None, required_exp: float | None) -> bool:
    if user_exp is None or required_exp is None:
        return True
    return user_exp >= max(0, required_exp - 1.0)


# ---------------------------------------------------------------------------
# Stage 2: Gemma via google library (direct, NOT litellm)
# ---------------------------------------------------------------------------

_gemini_client: Any = None
_gemini_last_call: float = 0.0
_gemini_call_count: int = 0
_gemini_token_count: int = 0
_gemini_reset_time: float = 0.0
_gemini_lock = threading.Lock()


def _get_gemini_client():
    """Lazily create gemini client using the app's API key."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        settings = get_settings()
        _gemini_client = genai.Client(api_key=settings.google_api_key)
    return _gemini_client


def _enforce_gemini_rate_limit() -> None:
    """Enforce 30 RPM rate limit for Gemini/Gemma calls."""
    global _gemini_last_call, _gemini_call_count, _gemini_token_count, _gemini_reset_time

    with _gemini_lock:
        now = time.monotonic()

        # Reset counters every 60 seconds
        if now - _gemini_reset_time >= 60.0:
            _gemini_call_count = 0
            _gemini_token_count = 0
            _gemini_reset_time = now

        # Enforce minimum delay between calls (2 seconds for 30 RPM)
        elapsed = now - _gemini_last_call
        if elapsed < GEMINI_MIN_DELAY:
            time.sleep(GEMINI_MIN_DELAY - elapsed)

        _gemini_last_call = time.monotonic()
        _gemini_call_count += 1


async def llm_validate_single_job(
    job: dict,
    profile: dict,
    target_role: str,
    user_exp: float | None,
) -> dict:
    """Validate a single job using Gemma 4 via google GenAI library directly.

    Uses Gemma model through the official google library — NOT litellm.
    Litellm returns 503 errors for Gemma models; using the library directly
    bypasses that issue entirely.
    """
    title = job.get("title") or job.get("role", "Unknown")
    company = job.get("company", "Unknown")
    jd_text = (job.get("jd_text") or "")[:4000]
    location = job.get("search_location") or job.get("location", "")

    name = profile.get("name", "Candidate")
    skills = ", ".join(profile.get("skills", [])[:20])
    summary = (profile.get("summary") or "")[:300]

    prompt = VALIDATION_PROMPT.format(
        name=name,
        target_role=target_role,
        skills=skills,
        experience=str(user_exp) if user_exp else "Not specified",
        summary=summary,
        company=company,
        title=title,
        location=location,
        jd_text=jd_text,
    )

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    # Run the blocking google library call in a thread to not block the event loop
    result = await loop.run_in_executor(
        None,
        _call_gemma_sync,
        prompt,
    )

    if result and "relevance_score" in result:
        return result

    log.warning("gemma_validation_failed", company=company, title=title)

    return {
        "experience_ok": True,
        "experience_required": "Unknown",
        "experience_verdict": "Gemma validation failed",
        "skills_needed": [],
        "skills_matched": [],
        "skills_missing": [],
        "relevance_score": 30,
        "clean_title": title,
        "clean_company": company,
        "one_line_summary": "Validation failed — manual review recommended",
    }


def _call_gemma_sync(prompt: str) -> dict:
    """Synchronous call to Gemma via google GenAI library."""
    _enforce_gemini_rate_limit()

    client = _get_gemini_client()

    response = client.models.generate_content(
        model=GEMMA_MODEL,
        contents=prompt,
        config={
            "thinkingConfig": {
                "thinkingLevel": GEMMA_THINKING_LEVEL,
            },
        },
    )

    text = response.text if hasattr(response, "text") else str(response)
    return parse_llm_json(text, default={})


def _messages_to_prompt(messages: list[dict]) -> str:
    """Flatten chat messages into a single prompt for Gemma (not a chat API)."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role.upper()}: {content}")
    return "\n\n".join(parts)


async def call_gemma(
    messages: list[dict],
    fallback_chain: str = "fast",
    require_keys: Optional[list[str]] = None,
) -> dict:
    """Call Gemma 4 (gemma-4-26b-a4b-it) via the google GenAI library.

    Gemma is NOT routed through litellm (litellm returns 503 for Gemma
    models), so we use the official google library directly with its own
    rate limiter. Returns the same shape as call_llm_with_fallback
    ({"content", "model", ...}) so callers are interchangeable.

    Falls back to the standard router chain when Gemma errors, rate-limits
    hard, or returns output missing required keys.
    """
    from vellum.config.llm_router import call_llm_with_fallback

    prompt = _messages_to_prompt(messages)

    try:
        parsed = await asyncio.get_event_loop().run_in_executor(None, _call_gemma_sync, prompt)
        if isinstance(parsed, dict) and parsed:
            if require_keys and not all(k in parsed for k in require_keys):
                log.warning(
                    "gemma_missing_keys",
                    missing=[k for k in require_keys if k not in parsed],
                    fallback_chain=fallback_chain,
                )
            else:
                log.info("gemma_call", model=GEMMA_MODEL, prompt_chars=len(prompt))
                return {
                    "content": json.dumps(parsed, ensure_ascii=False),
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "model": GEMMA_MODEL,
                    "latency_ms": 0,
                    "cache_hit": False,
                }
    except Exception as exc:
        log.warning("gemma_call_failed", error=str(exc)[:200], fallback_chain=fallback_chain)

    return await call_llm_with_fallback(fallback_chain, messages)


# ---------------------------------------------------------------------------
# Validation Prompt
# ---------------------------------------------------------------------------

VALIDATION_PROMPT = """You are an expert technical recruiter. Analyze this job posting against the candidate profile and give a precise relevance assessment.

CANDIDATE PROFILE:
Name: {name}
Target Role: {target_role}
Skills: {skills}
Experience: {experience} years
Summary: {summary}

JOB POSTING:
Company: {company}
Title: {title}
Location: {location}
Job Description:
{jd_text}

ANALYSIS RULES:
1. EXPERIENCE CHECK: Compare candidate's {experience} years against the job's requirement. If the job requires significantly more experience (e.g. job needs 8+ years and candidate has 2), set score very low (below 30).
2. SKILL MATCH: Extract the key skills/technologies from the JD. Compare with candidate skills. Count exact and close matches.
3. ROLE ALIGNMENT: Does this job title/role align with the candidate's target role of "{target_role}"?
4. RELEVANCE SCORE (0-100): Weighted: experience fit (30%), skill overlap (40%), role alignment (20%), location fit (10%).

Return EXACTLY this JSON:
{{
  "experience_ok": true,
  "experience_required": "5+ years",
  "experience_verdict": "Candidate has X years, job needs Y years — [match/mismatch/close]",
  "skills_needed": ["Python", "FastAPI", "PostgreSQL"],
  "skills_matched": ["Python", "PostgreSQL"],
  "skills_missing": ["FastAPI"],
  "relevance_score": 75,
  "clean_title": "Senior Software Engineer",
  "clean_company": "CompanyName",
  "one_line_summary": "Backend role requiring Python and 5+ years experience"
}}

Return valid JSON only. No commentary."""


# ---------------------------------------------------------------------------
# Main Validation Pipeline
# ---------------------------------------------------------------------------

async def validate_and_filter_jobs(
    jobs: list[dict],
    profile: dict,
    target_role: str,
    target_count: int,
    location: str,
    event_callback=None,
) -> dict:
    """Validate ALL jobs using LLM and return categorized results.

    Every job gets a score. Jobs are categorized as:
      - "validated": score >= threshold, passes diversity check
      - "low_score": score below threshold or experience mismatch

    Returns dict with keys:
      - "validated": list of quality jobs for main tab
      - "low_score": list of rejected jobs for "Low Score" tab
      - "stats": summary statistics
    """
    user_exp = get_user_years_of_experience(profile)
    company_count: dict[str, int] = {}
    validated_jobs: list[dict] = []
    low_score_jobs: list[dict] = []
    total_processed = 0

    async def broadcast(msg: str, pct: int = 0):
        if event_callback:
            await event_callback({
                "agent": "job_validator",
                "event_type": "validation_progress",
                "message": msg,
                "data": {"percentage": pct},
            })

    await broadcast(f"Starting Gemma 4 validation for {len(jobs)} jobs...", 0)

    # Stage 1: Quick experience pre-filter
    exp_passed = []
    for job in jobs:
        jd_text = job.get("jd_text", "")
        required_exp = extract_required_experience(jd_text)
        job["_required_exp"] = required_exp

        if not experience_passes(user_exp, required_exp):
            score = 15
            job["match_score"] = round(score / 100.0, 2)
            job["validation_status"] = "low_score"
            job["one_line_summary"] = f"Experience mismatch: needs {required_exp or '?'} years"
            job["skills_needed"] = []
            job["skills_matched"] = []
            job["skills_missing"] = []
            job["experience_verdict"] = f"Requires {required_exp or '?'} years — candidate has {user_exp or '?'}"
            job["validation_json"] = json.dumps({"relevance_score": score, "experience_ok": False})
            low_score_jobs.append(job)
            continue

        exp_passed.append(job)

    await broadcast(
        f"Experience filter: {len(exp_passed)}/{len(jobs)} passed "
        f"({len(low_score_jobs)} skipped for experience mismatch)",
        20
    )

    # Stage 1.5: URL Active status and Location alignment pre-validation
    await broadcast(
        f"Pre-validating {len(exp_passed)} jobs for active URL and location target...",
        30
    )
    
    from vellum.tools.url_verifier import verify_job_url, verify_job_text_local
    from vellum.agents.geo_search import _matches_location_strict
    
    verified_located = []
    
    # Scale URL checking concurrency with CPU count
    import os
    cpu_count = os.cpu_count() or 4
    concurrency_limit = min(32, max(8, cpu_count * 2))
    sem = asyncio.Semaphore(concurrency_limit)
    
    async def verify_and_check_location(job: dict) -> tuple[dict, str | None]:
        async with sem:
            url = job.get("apply_url") or job.get("career_page_url") or ""
            if not url:
                return job, "No valid job application or career URL"
                
            # If the job description is already present and valid, skip HTTP fetch
            jd_text = job.get("jd_text", "")
            if jd_text and len(jd_text) >= 100:
                is_active, reason = verify_job_text_local(jd_text)
                page_text = jd_text
            else:
                is_active, reason, page_text = await verify_job_url(url)
                
            if not is_active:
                return job, f"Job has expired or is closed: {reason}"
                
            # If verify_job_url extracted the text and the job doesn't have it, enrich it
            if page_text and not job.get("jd_text"):
                job["jd_text"] = page_text
                
            # Check if location aligns strictly
            if not _matches_location_strict(
                job.get("title") or job.get("role") or "",
                job.get("jd_text") or "",
                location
            ):
                return job, f"Location mismatch: job is not in or remote-eligible for {location}"
                
            return job, None

    # Run pre-verification in parallel
    pv_tasks = [verify_and_check_location(j) for j in exp_passed]
    pv_results = await asyncio.gather(*pv_tasks)
    
    for job, reject_reason in pv_results:
        if reject_reason:
            score = 15
            job["match_score"] = round(score / 100.0, 2)
            job["validation_status"] = "low_score"
            job["one_line_summary"] = reject_reason
            job["skills_needed"] = []
            job["skills_matched"] = []
            job["skills_missing"] = []
            job["experience_verdict"] = reject_reason
            job["validation_json"] = json.dumps({"relevance_score": score, "experience_ok": False, "reason": reject_reason})
            low_score_jobs.append(job)
        else:
            verified_located.append(job)
            
    await broadcast(
        f"Pre-validation complete: {len(verified_located)}/{len(exp_passed)} jobs active and located in {location} "
        f"({len(exp_passed) - len(verified_located)} jobs skipped/expired)",
        40
    )

    # Stage 2: Gemma LLM validation in small batches
    for i in range(0, len(verified_located), BATCH_SIZE):
        batch = verified_located[i:i + BATCH_SIZE]
        total_processed += len(batch)

        tasks = [
            llm_validate_single_job(job, profile, target_role, user_exp)
            for job in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for job, result in zip(batch, results):
            if isinstance(result, Exception):
                score = 25
                job["match_score"] = round(score / 100.0, 2)
                job["validation_status"] = "low_score"
                job["one_line_summary"] = "Gemma validation error"
                job["skills_needed"] = []
                job["skills_matched"] = []
                job["skills_missing"] = []
                job["experience_verdict"] = "Validation error"
                job["validation_json"] = json.dumps({"relevance_score": score})
                low_score_jobs.append(job)
                continue

            score = result.get("relevance_score", 0)
            clean_company = result.get("clean_company") or job.get("company", "Unknown")

            job["company"] = clean_company
            job["role"] = result.get("clean_title") or job.get("title", "")
            job["title"] = job["role"]
            job["match_score"] = round(score / 100.0, 2)
            job["skills_needed"] = result.get("skills_needed", [])
            job["skills_matched"] = result.get("skills_matched", [])
            job["skills_missing"] = result.get("skills_missing", [])
            job["experience_verdict"] = result.get("experience_verdict", "")
            job["one_line_summary"] = result.get("one_line_summary", "")
            job["validation_json"] = json.dumps(result)

            if score < MIN_RELEVANCE_SCORE:
                job["validation_status"] = "low_score"
                low_score_jobs.append(job)
                continue

            current_count = company_count.get(clean_company.lower().strip(), 0)
            if current_count >= MAX_PER_COMPANY:
                job["validation_status"] = "low_score"
                job["one_line_summary"] = f"Duplicate from {clean_company} (max 2 per company)"
                low_score_jobs.append(job)
                continue

            company_count[clean_company.lower().strip()] = current_count + 1
            job["validation_status"] = "validated"
            validated_jobs.append(job)

        pct = min(80, int(40 + (total_processed / max(1, len(verified_located))) * 40))
        await broadcast(
            f"Gemma validated {total_processed}/{len(verified_located)} jobs — "
            f"{len(validated_jobs)} quality, {len(low_score_jobs)} low score",
            pct
        )

        # Rate limit: 2 second delay between batches (30 RPM = 1 call every 2s)
        if i + BATCH_SIZE < len(verified_located):
            await asyncio.sleep(GEMINI_MIN_DELAY)

    validated_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    low_score_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)

    await broadcast(
        f"Done: {len(validated_jobs)} validated, {len(low_score_jobs)} low score "
        f"across {len(company_count)} companies",
        90
    )

    log.info(
        "validation_complete",
        total_input=len(jobs),
        validated=len(validated_jobs),
        low_score=len(low_score_jobs),
        unique_companies=len(company_count),
    )

    return {
        "validated": validated_jobs,
        "low_score": low_score_jobs,
        "stats": {
            "total": len(jobs),
            "validated": len(validated_jobs),
            "low_score": len(low_score_jobs),
            "companies": len(company_count),
        },
    }