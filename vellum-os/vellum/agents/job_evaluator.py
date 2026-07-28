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

EVALUATION_PROMPT = """You are an expert AI Job Recruiter. Evaluate if the following job listing is a good fit for the candidate based on target role, experience level, and skills.

Candidate Profile:
- Name: {name}
- Target Role: {target_role}
- Total Experience Level: {experience_level}
- Key Skills: {skills}
- Work Experience Summary: {experience_summary}

Job Listing:
- Company: {company}
- Title: {title}
- Location: {location}
- Excerpt/JD: {jd_excerpt}

CRITICAL RULES:
1. Strict Role Alignment: The job title/role must match the candidate's target role or engineering background. For example, if candidate is a Software Engineer, do not approve Sales, Marketing, HR, or non-technical roles.
2. Experience Level Check: Do not approve roles that are significantly above or below the candidate's level (e.g. do not approve senior/lead/staff/principal roles if candidate is junior, and do not approve junior/intern roles if candidate is senior).
3. Reality Check: Make sure the job description snippet looks like a real, specific job listing and not a generic list of jobs or page error.

Return a JSON object with this exact structure:
{{
  "is_fit": true/false,
  "reason": "1-sentence explanation of fit or misfit"
}}
Return valid JSON only. No markdown formatting or commentary."""


async def evaluate_single_job(job: dict, profile: dict, target_role: str) -> bool:
    """Evaluate a single job against the candidate profile using LLM.
    
    Returns True if the job matches the candidate, False otherwise.
    """
    company = job.get("company", "Unknown Company")
    title = job.get("title", "Unknown Role")
    location = job.get("location", "Unknown Location")
    jd_excerpt = job.get("jd_text", "")[:1500]

    # Format candidate details
    name = profile.get("name", "Candidate")
    skills = ", ".join(profile.get("skills", []))
    exp_level = profile.get("relevant_experience", "N/A")
    exp_summary = "; ".join(
        f"{e.get('role')} at {e.get('company')} ({e.get('start')} - {e.get('end')})"
        for e in profile.get("experience", [])
    )

    messages = [
        {"role": "system", "content": "You are a professional recruiting evaluator."},
        {
            "role": "user",
            "content": EVALUATION_PROMPT.format(
                name=name,
                target_role=target_role,
                experience_level=exp_level,
                skills=skills,
                experience_summary=exp_summary,
                company=company,
                title=title,
                location=location,
                jd_excerpt=jd_excerpt,
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
        
        data = json.loads(content.strip())
        is_fit = data.get("is_fit", False)
        reason = data.get("reason", "")
        
        log.info("job_evaluated", company=company, title=title, is_fit=is_fit, reason=reason)
        return is_fit
    except Exception as exc:
        log.warning("job_evaluation_failed", company=company, title=title, error=str(exc))
        # Default to True on failure so we don't miss job opportunities due to transient errors
        return True


async def filter_jobs(jobs: list[dict], profile: dict, target_role: str) -> list[dict]:
    """Filter a list of discovered jobs concurrently using a semaphore."""
    if not jobs:
        return []

    log.info("filtering_discovered_jobs", count=len(jobs), target_role=target_role)
    
    # Process up to 5 jobs in parallel to avoid hitting rate limits
    semaphore = asyncio.Semaphore(5)

    async def sem_eval(job):
        async with semaphore:
            is_fit = await evaluate_single_job(job, profile, target_role)
            return job if is_fit else None

    tasks = [sem_eval(job) for job in jobs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    filtered = [r for r in results if r is not None and not isinstance(r, Exception)]
    log.info("filtering_complete", original_count=len(jobs), filtered_count=len(filtered))
    return filtered
