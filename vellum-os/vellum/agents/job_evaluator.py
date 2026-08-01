"""
Vellum OS — Job Evaluator Agent (Agent E)

Validates discovered jobs against candidate profile and experience level 
before they are written to the database or processed.
"""

from __future__ import annotations

import json
import asyncio
import re
from typing import Any

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.utils.json_helper import parse_llm_json

log = get_logger("job_evaluator")

# ---------------------------------------------------------------------------
# Experience extraction helpers
# ---------------------------------------------------------------------------

_LEVEL_MAP = {
    "intern": 0,
    "junior": 1,
    "mid-level": 3,
    "senior": 5,
    "lead": 7,
    "principal": 10,
}


def extract_experience_from_jd(jd_text: str) -> float | None:
    """Parse a minimum experience requirement (in years) from JD text.

    Patterns handled:
      - "X-Y years" or "X to Y years" → returns X
      - "X+ years" → returns X
      - "minimum X years" → returns X
      - Level keywords (intern/junior/mid-level/senior/lead/principal)
    """
    if not jd_text:
        return None

    text = jd_text.lower()

    # "X-Y years" or "X to Y years"
    m = re.search(r"(\d+)[\s]*[-–to]+\s*(\d+)\s*years?", text)
    if m:
        return float(m.group(1))

    # "X+ years"
    m = re.search(r"(\d+)\+?\s*years?", text)
    if m:
        return float(m.group(1))

    # "minimum X years"
    m = re.search(r"minimum\s+(\d+)\s*years?", text)
    if m:
        return float(m.group(1))

    # Level keywords
    for level, years in _LEVEL_MAP.items():
        if re.search(rf"\b{level}\b", text):
            return float(years)

    return None


def is_experience_match(required_exp: float | None, user_experience: float) -> bool:
    """Return True if the user has enough experience for the role.

    Permissive when required_exp is unknown.
    """
    if required_exp is None:
        return True
    return required_exp <= user_experience


def _heuristic_match_score(job: dict, profile: dict, target_role: str) -> float:
    """Compute a fast 0-1 match score from skill overlap + role alignment.

    This guarantees every job has a sensible match score even before the
    slower LLM validation runs, so the UI never shows a flat 0%.
    """
    title = (job.get("title") or job.get("role") or "").lower()
    jd = (job.get("jd_text") or "").lower()[:4000]
    haystack = f"{title} {jd}"

    profile_skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    if not profile_skills:
        return 0.5

    matched = sum(1 for s in profile_skills if s and len(s) > 2 and s in haystack)
    skill_ratio = matched / len(profile_skills) if profile_skills else 0

    # Role token overlap — weighted more heavily now
    role_tokens = [t.lower() for t in (target_role or "").split() if len(t) > 2]
    role_hits = sum(1 for t in role_tokens if t in haystack)
    role_ratio = (role_hits / len(role_tokens)) if role_tokens else 0.5

    # Experience match bonus/penalty
    exp_bonus = 0.0
    qa_memory = profile.get("qa_memory", {})
    if isinstance(qa_memory, dict):
        yoe = qa_memory.get("years_of_experience", "")
    else:
        yoe = getattr(qa_memory, "years_of_experience", "") or ""
    if yoe:
        try:
            user_yoe = float(re.search(r"(\d+)", str(yoe)).group(1))
            jd_exp = extract_experience_from_jd(job.get("jd_text", ""))
            if jd_exp is not None:
                if user_yoe >= jd_exp:
                    exp_bonus = 0.05  # Good match
                elif user_yoe >= jd_exp * 0.7:
                    exp_bonus = 0.0  # Close enough
                else:
                    exp_bonus = -0.1  # Underqualified
        except (AttributeError, ValueError):
            pass

    # Weighted blend: role alignment now worth 35% (was 20%), skills 45%
    score = 0.30 + 0.45 * skill_ratio + 0.25 * role_ratio + exp_bonus
    return max(0.10, min(0.95, round(score, 2)))

BATCH_EVALUATION_PROMPT = """You are an expert AI Job Recruiter. Evaluate a batch of job listings against a candidate profile to determine which jobs are a good fit.

Candidate Profile:
- Name: {name}
- Target Role: {target_role}
- Experience Level: {experience_level}
- Key Skills: {skills}
- Expected CTC: {expected_ctc}

Job Listings:
{jobs_block}

CRITICAL RULES:
1. Role Alignment: Job title/role must align with candidate's target role or tech background ({target_role}). Reject sales, marketing, non-tech roles.
2. Experience Match: Do not approve senior/staff/principal roles for junior candidates or intern roles for experienced candidates.
3. Quality Check: Reject generic directory listings or corrupted text.
4. Salary/CTC Match: If a job listing explicitly mentions a salary, compensation range, or budget, check it against the candidate's expected CTC ({expected_ctc}). If the listing's compensation is significantly below the candidate's expected CTC, reject it (evaluating as false). If the listing does not mention any compensation details, do NOT reject or penalize it.

Return a JSON array of booleans corresponding to each job in order, e.g.:
[true, false, true, true]

Return valid JSON array only. No commentary."""


async def evaluate_batch_jobs(jobs: list[dict], profile: dict, target_role: str) -> list[bool]:
    """Evaluate a batch of up to 5 jobs in a single LLM call."""
    if not jobs:
        return []

    name = profile.get("name", "Candidate")
    skills = ", ".join(profile.get("skills", [])[:15])
    exp_level = profile.get("relevant_experience", "N/A")
    qa_memory = profile.get("qa_memory", {})
    expected_ctc = qa_memory.get("expected_ctc") or qa_memory.get("expected_salary") or "Not specified"

    jobs_lines = []
    for idx, job in enumerate(jobs):
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        snippet = job.get("jd_text", "")[:400].replace("\n", " ")
        jobs_lines.append(f"Job [{idx+1}]: {company} — {title} | Snippet: {snippet}")

    jobs_block = "\n".join(jobs_lines)

    messages = [
        {"role": "system", "content": "You are a professional recruiting evaluator."},
        {
            "role": "user",
            "content": BATCH_EVALUATION_PROMPT.format(
                name=name,
                target_role=target_role,
                experience_level=exp_level,
                skills=skills,
                jobs_block=jobs_block,
                expected_ctc=expected_ctc,
            ),
        },
    ]

    try:
        res = await call_llm_with_fallback("fast", messages)
        results = parse_llm_json(res.get("content", ""), default=[])

        if isinstance(results, list) and len(results) == len(jobs):
            return [bool(r) for r in results]
        elif isinstance(results, dict) and "results" in results:
            return [bool(r) for r in results["results"][:len(jobs)]]
    except Exception as exc:
        log.warning("batch_evaluation_failed", error=str(exc))

    # Fallback to True for all if LLM batch fails
    return [True] * len(jobs)


async def filter_jobs(jobs: list[dict], profile: dict, target_role: str) -> list[dict]:
    """Filter a list of discovered jobs using heuristic pre-filtering and batch LLM evaluation."""
    if not jobs:
        return []

    log.info("filtering_discovered_jobs", count=len(jobs), target_role=target_role)

    # Step 1: Heuristic pre-filtering + match-score assignment.
    # Compute a fast skill-overlap match score for every job so the UI never
    # shows a flat 0%, and drop obviously irrelevant roles.
    target_role_lower = target_role.lower()
    role_tokens = [t for t in target_role_lower.split() if len(t) > 2]

    # Extract user experience from profile
    user_experience = None
    
    # First try qa_memory.years_of_experience (most reliable numeric field)
    qa_memory = profile.get("qa_memory", {})
    if isinstance(qa_memory, dict):
        yoe = qa_memory.get("years_of_experience", "")
    else:
        yoe = getattr(qa_memory, "years_of_experience", "") or ""
    if yoe:
        try:
            match = re.search(r"(\d+)", str(yoe))
            if match:
                user_experience = float(match.group(1))
        except (AttributeError, ValueError):
            pass
    
    # Fallback: extract from relevant_experience text (e.g. "3+ Years in AI/ML")
    if user_experience is None:
        exp_str = profile.get("relevant_experience", "")
        if exp_str:
            try:
                match = re.search(r"(\d+)", str(exp_str))
                if match:
                    user_experience = float(match.group(1))
            except (AttributeError, ValueError):
                pass
    
    # Fallback: calculate from experience entries
    if user_experience is None:
        experience_entries = profile.get("experience", [])
        if experience_entries:
            # Count unique companies as a rough experience proxy
            companies = set()
            for exp in experience_entries:
                if isinstance(exp, dict):
                    c = exp.get("company", "")
                else:
                    c = getattr(exp, "company", "")
                if c:
                    companies.add(c.lower().strip())
            if companies:
                user_experience = max(1.0, float(len(companies)))

    heuristic_passed = []
    for job in jobs:
        title = job.get("title", "").lower()
        # Non-tech roles rejection (unless title matches target role tokens)
        if any(bad in title for bad in ["sales", "marketing", "telecaller", "customer care", "accountant", "receptionist", "driver"]):
            if not any(token in title for token in role_tokens):
                continue

        # Experience matching
        jd_text = job.get("jd_text", "")
        required_exp = extract_experience_from_jd(jd_text)
        job["experience_required"] = required_exp
        if user_experience is not None:
            matched = is_experience_match(required_exp, user_experience)
            job["experience_matched"] = matched
            if not matched:
                continue  # Skip jobs requiring more experience

        # Assign / persist a heuristic match score immediately.
        score = _heuristic_match_score(job, profile, target_role)
        job["match_score"] = score
        try:
            jid = job.get("id") or job.get("career_page_url")
            if jid:
                await db.update_job(jid, match_score=score)
        except Exception:
            pass
        heuristic_passed.append(job)

    if not heuristic_passed:
        return jobs[:10]  # Fallback to raw if heuristic filtered everything

    # Step 2: Batch LLM evaluation (5 jobs per batch)
    batch_size = 5
    filtered_jobs = []

    for i in range(0, len(heuristic_passed), batch_size):
        batch = heuristic_passed[i : i + batch_size]
        eval_results = await evaluate_batch_jobs(batch, profile, target_role)
        for job, is_fit in zip(batch, eval_results):
            if is_fit:
                filtered_jobs.append(job)
        await asyncio.sleep(1.0)  # Gentle delay between batches

    log.info("filtering_complete", original_count=len(jobs), filtered_count=len(filtered_jobs))

    # Step 3: Sort by match score (best first) for profile-relevant ordering
    filtered_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return filtered_jobs if filtered_jobs else heuristic_passed[:15]

