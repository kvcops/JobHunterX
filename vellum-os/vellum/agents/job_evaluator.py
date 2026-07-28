"""
Vellum OS — Job Evaluator Agent (Agent E)

Validates discovered jobs against candidate profile and experience level 
before they are written to the database or processed.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger

log = get_logger("job_evaluator")

BATCH_EVALUATION_PROMPT = """You are an expert AI Job Recruiter. Evaluate a batch of job listings against a candidate profile to determine which jobs are a good fit.

Candidate Profile:
- Name: {name}
- Target Role: {target_role}
- Experience Level: {experience_level}
- Key Skills: {skills}

Job Listings:
{jobs_block}

CRITICAL RULES:
1. Role Alignment: Job title/role must align with candidate's target role or tech background ({target_role}). Reject sales, marketing, non-tech roles.
2. Experience Match: Do not approve senior/staff/principal roles for junior candidates or intern roles for experienced candidates.
3. Quality Check: Reject generic directory listings or corrupted text.

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
            ),
        },
    ]

    try:
        res = await call_llm_with_fallback("fast", messages)
        content = res.get("content", "").strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        results = json.loads(content.strip())
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

    # Step 1: Fast Heuristic Pre-Filtering
    target_role_lower = target_role.lower()
    role_tokens = [t for t in target_role_lower.split() if len(t) > 2]
    
    heuristic_passed = []
    for job in jobs:
        title = job.get("title", "").lower()
        # Non-tech roles rejection
        if any(bad in title for bad in ["sales", "marketing", "telecaller", "customer care", "accountant", "receptionist", "driver"]):
            if not any(token in title for token in role_tokens):
                continue
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
    return filtered_jobs if filtered_jobs else heuristic_passed[:15]

