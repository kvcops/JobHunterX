"""
Vellum OS — LangGraph Orchestration

Two-tier architecture:
  1. Discovery Graph: runs once to populate job queue
  2. Per-Job Pipeline: independent pipeline per job for validation/apply/outreach

Uses InMemorySaver for HITL checkpointing, interrupt() + Command for pause/resume.

Pipeline modes:
  - Automatic: runs end-to-end without user intervention
  - Manual: pauses after match score for user to click Apply per job

Batch scoring: scores 10 jobs at a time via a single LLM call for efficiency.
"""

from __future__ import annotations

import asyncio
import json
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from vellum.agents import geo_search, validator_tailor, browser_agent, contact_finder, email_drafter
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.config.settings import get_settings
from vellum.models import DiscoveryState, JobPipelineState
from vellum.utils.json_helper import parse_llm_json

log = get_logger("graph")

# ---------------------------------------------------------------------------
# Graph 1: Discovery
# ---------------------------------------------------------------------------

def build_discovery_graph():
    """Build the company/job discovery graph."""
    graph = StateGraph(DiscoveryState)
    graph.add_node("search", geo_search.run)
    graph.set_entry_point("search")
    graph.add_edge("search", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# Graph 2a: Validate-Only Pipeline (used during search)
# ---------------------------------------------------------------------------

def build_validate_only_pipeline():
    """Build a validate-only pipeline for search results.

    During search, jobs are discovered and validated/tailored but NOT
    auto-applied.  The user must explicitly click Apply from the UI.
    """
    checkpointer = InMemorySaver()
    graph = StateGraph(JobPipelineState)

    graph.add_node("validate_tailor", validator_tailor.run)
    graph.set_entry_point("validate_tailor")
    graph.add_edge("validate_tailor", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Graph 2b: Full Apply Pipeline (user-triggered)
# Pipeline: resume/CV generation → contact search → cold email → browser apply
# ---------------------------------------------------------------------------

def _should_apply(state: JobPipelineState) -> str:
    """Route after validation: apply if matched or if user explicitly requested apply."""
    if state.get("force_apply", False):
        return "apply"
    validation = state.get("validation", {})
    match_score = validation.get("match_score", 0)
    if match_score >= 0.3:
        return "apply"
    return "skip"


def build_job_pipeline():
    """Build the full per-job pipeline.

    Sequence: validate/tailor → contact search → email draft → browser apply
    Only used when the user explicitly clicks Apply on a job card.
    Uses InMemorySaver for HITL checkpointing.
    """
    checkpointer = InMemorySaver()

    graph = StateGraph(JobPipelineState)

    # Nodes
    graph.add_node("validate_tailor", validator_tailor.run)
    graph.add_node("find_contacts", contact_finder.run)
    graph.add_node("draft_email", email_drafter.run)
    graph.add_node("browse_apply", browser_agent.run)

    # Entry
    graph.set_entry_point("validate_tailor")

    # Conditional: after validation, either proceed or skip
    graph.add_conditional_edges(
        "validate_tailor",
        _should_apply,
        {
            "apply": "find_contacts",
            "skip": END,
        },
    )

    # Sequence: resume → contact search → cold email → browser apply
    graph.add_edge("find_contacts", "draft_email")
    graph.add_edge("draft_email", "browse_apply")
    graph.add_edge("browse_apply", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Job Queue Manager
# ---------------------------------------------------------------------------

# Module-level graph instances
_discovery_graph = None
_job_pipeline = None
_validate_only_pipeline = None

# Active pipeline references for HITL resume
_active_pipelines: dict[str, dict] = {}


def get_discovery_graph():
    global _discovery_graph
    if _discovery_graph is None:
        _discovery_graph = build_discovery_graph()
    return _discovery_graph


def get_validate_only_pipeline():
    global _validate_only_pipeline
    if _validate_only_pipeline is None:
        _validate_only_pipeline = build_validate_only_pipeline()
    return _validate_only_pipeline


def get_job_pipeline():
    global _job_pipeline
    if _job_pipeline is None:
        _job_pipeline = build_job_pipeline()
    return _job_pipeline


async def run_discovery(location: str, profile: dict, role: str | None = None, limit: int = 50, event_callback=None) -> list[dict]:
    """Run the discovery graph and return discovered jobs.

    Args:
        location: City name.
        profile: CandidateProfile dict.
        role: Job role / title.
        limit: Max companies/jobs limit.
        event_callback: Async callable for streaming events.

    Returns list of discovered job dicts.
    """
    graph = get_discovery_graph()

    initial_state: DiscoveryState = {
        "location": location,
        "profile": profile,
        "role": role or "software engineer",
        "limit": limit,
        "discovered_jobs": [],
        "errors": [],
        "events": [],
    }

    result = await graph.ainvoke(initial_state)

    # Stream events if callback provided
    if event_callback:
        for event in result.get("events", []):
            await event_callback(event)

    return result.get("discovered_jobs", [])


# ---------------------------------------------------------------------------
# Batch Match Scoring — score 10 jobs at a time
# ---------------------------------------------------------------------------

BATCH_MATCH_SCORING_PROMPT = """You are a top-tier executive talent manager. Compare the candidate profile against multiple job descriptions, extract the clean Company Name and clean Job Role, and assign a match score (0.0-1.0) for each.

CRITICAL MATCHING & EXTRACTION RULES:
1. **Company Extraction**: Extract the real hiring company name (e.g. "GHX", "IQEQ", "ElevenLabs", "CreateAxis Solutions", "Incepteo", "Yuno"). Do NOT use job portals like "Bayt.com", "Weekday", "Greenhouse", "Lever", or "Unknown".
2. **Job Role Extraction**: Extract the clean specific job title (e.g. "Senior AI Engineer", "Digital & AI Solutions Engineer"). Do NOT use page headers like "ATTACH RESUME/CV" or full sentences.
3. **Location Match**: The candidate targets "{target_location}". Strict onsite in a different city = lower score.
4. **Experience Match**: Candidate has "{candidate_experience}". Mismatched seniority = low score.
5. **Skills Match**: Weight overlap between candidate skills and JD requirements heavily.

Candidate Profile:
Name: {name}
Target Role: {target_role}
Skills: {skills}
Experience Level: {candidate_experience}
Summary: {summary}

Jobs to score:
{jobs_block}

Return a JSON array of objects, one per job in order:
[
  {{
    "job_index": 0,
    "company_name": "Clean Company Name",
    "job_role": "Clean Job Title",
    "match_score": 0.75,
    "matching_skills": ["Python", "FastAPI"],
    "missing_skills": ["React"],
    "required_experience": "e.g. 5+ years",
    "experience_variance": "Candidate: X yrs vs Required: Y yrs",
    "reasoning": "Strong backend match"
  }}
]

Return valid JSON array only. Do NOT include unescaped quotes or line breaks inside string values."""


def _fallback_score_single_job(job: dict, profile: dict, location: str = "") -> dict:
    """Intelligently score a job deterministically if LLM batch scoring fails or returns empty."""
    co = job.get("company", "")
    ro = job.get("role") or job.get("title", "")
    jd_text = (job.get("jd_text") or "").lower()

    cand_skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    cand_role = (profile.get("suggested_role") or "Software Engineer").lower()
    cand_exp = profile.get("relevant_experience", "N/A")

    # 1. Skill Overlap
    matching = []
    missing = []
    for sk in cand_skills:
        if len(sk) > 1 and sk in jd_text:
            matching.append(sk.title())
        elif len(sk) > 1:
            missing.append(sk.title())

    match_ratio = len(matching) / max(1, len(cand_skills))

    # 2. Role Title Relevance
    role_match = 0.5
    if any(term in ro.lower() for term in cand_role.split() if len(term) > 2):
        role_match = 0.9

    # 3. Calculated Score (Range 0.25 to 0.95)
    calc_score = round(min(0.95, max(0.25, (match_ratio * 0.55) + (role_match * 0.35) + 0.1)), 2)

    return {
        "company_name": co or "Tech Company",
        "job_role": ro or "Software Engineer",
        "match_score": calc_score,
        "matching_skills": matching[:8],
        "missing_skills": missing[:5],
        "required_experience": "Extracted from JD",
        "experience_variance": f"Candidate: {cand_exp} vs Job Requirements",
        "reasoning": f"Calculated fit score of {int(calc_score*100)}% based on {len(matching)} matching technical skills ({', '.join(matching[:3]) or 'Core competencies'})."
    }


async def batch_score_jobs(jobs: list[dict], profile: dict, location: str = "") -> list[dict]:
    """Score up to 10 jobs in a single LLM call for efficiency.
    
    Returns list of dicts with match_score, matching_skills, missing_skills, reasoning.
    """
    from vellum.config.llm_router import call_llm_with_fallback
    
    if not jobs:
        return []

    name = profile.get("name", "Candidate")
    target_role = profile.get("suggested_role", "Software Engineer")
    skills = ", ".join(profile.get("skills", [])[:20])
    candidate_experience = profile.get("relevant_experience", "N/A")
    summary = profile.get("summary", "")[:300]
    qa_memory = profile.get("qa_memory", {})
    expected_ctc = qa_memory.get("expected_ctc") or qa_memory.get("expected_salary") or "Not specified"
    target_location = location or profile.get("location", "")

    # Build jobs block
    jobs_lines = []
    for idx, job in enumerate(jobs):
        company = job.get("company", "Unknown")
        role = job.get("role", "Unknown")
        jd_snippet = (job.get("jd_text") or "")[:500].replace("\n", " ")
        jobs_lines.append(f"[Job {idx}] {company} — {role}\nJD: {jd_snippet}\n")

    jobs_block = "\n".join(jobs_lines)

    messages = [
        {"role": "system", "content": "You are a job-matching expert."},
        {
            "role": "user",
            "content": BATCH_MATCH_SCORING_PROMPT.format(
                name=name,
                target_role=target_role,
                skills=skills,
                candidate_experience=candidate_experience,
                summary=summary,
                expected_ctc=expected_ctc,
                target_location=target_location,
                jobs_block=jobs_block[:8000],  # Cap tokens
            ),
        },
    ]

    try:
        result = await call_llm_with_fallback("reasoning", messages)
        scores = parse_llm_json(result.get("content", ""), default=[])

        if isinstance(scores, list) and len(scores) > 0:
            final_scores = []
            for idx, job in enumerate(jobs):
                if idx < len(scores) and isinstance(scores[idx], dict) and scores[idx].get("match_score") is not None:
                    final_scores.append(scores[idx])
                else:
                    final_scores.append(_fallback_score_single_job(job, profile, location))
            return final_scores
    except Exception as exc:
        log.warning("batch_score_failed", error=str(exc))

    # Fallback: compute intelligent deterministic scores for each job
    return [_fallback_score_single_job(j, profile, location) for j in jobs]


async def run_job_pipeline(
    job: dict,
    profile: dict,
    run_id: str = "",
    event_callback=None,
    search_location: str = "",
    validate_only: bool = True,
    force_apply: bool = False,
) -> dict:
    """Run the per-job pipeline.

    Args:
        job: Job dict from database.
        profile: CandidateProfile dict.
        run_id: Unique run identifier.
        event_callback: Async callable for streaming events.
        search_location: The location the user searched for (for matching).
        validate_only: If True (default), only validate/tailor. If False,
                       run full pipeline (validate → apply → outreach).
        force_apply: If True, bypass match threshold and apply directly.

    Returns pipeline result dict.
    """
    if validate_only:
        pipeline = get_validate_only_pipeline()
    else:
        pipeline = get_job_pipeline()
    job_id = job.get("id", str(uuid.uuid4()))
    thread_id = f"job-{job_id}"

    # Always refresh the profile from DB to get the latest edits
    fresh_profile = await db.get_latest_profile()
    if fresh_profile:
        profile = fresh_profile

    # Tag job with search location for validator matching
    if search_location:
        job["search_location"] = search_location

    initial_state: JobPipelineState = {
        "job": job,
        "profile": profile,
        "force_apply": force_apply or (not validate_only),
        "errors": [],
        "events": [],
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await pipeline.ainvoke(initial_state, config=config)

        # Store pipeline reference for HITL resume
        _active_pipelines[job_id] = {
            "thread_id": thread_id,
            "config": config,
        }

        # Stream events
        if event_callback:
            for event in result.get("events", []):
                await event_callback(event)

        return result

    except Exception as exc:
        log.error("job_pipeline_error", job_id=job_id, error=str(exc))
        await db.update_job(job_id, status="failed")
        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "error",
                "job_id": job_id,
                "message": f"Pipeline error: {str(exc)[:200]}",
            })
        return {"errors": [str(exc)]}


async def resume_job_pipeline(job_id: str, action: str = "done") -> dict:
    """Resume a HITL-interrupted job pipeline.

    Args:
        job_id: The job ID to resume.
        action: "done" (user completed manual step) or "skip".
    """
    from langgraph.types import Command

    pipeline_info = _active_pipelines.get(job_id)
    if not pipeline_info:
        log.warning("no_active_pipeline", job_id=job_id)
        return {"error": "No active pipeline for this job"}

    pipeline = get_job_pipeline()
    config = pipeline_info["config"]

    try:
        result = await pipeline.ainvoke(
            Command(resume={"action": action}),
            config=config,
        )
        return result
    except Exception as exc:
        log.error("resume_error", job_id=job_id, error=str(exc))
        return {"error": str(exc)}


async def run_full_search(
    location: str,
    profile: dict,
    role: str | None = None,
    limit: int = 50,
    event_callback=None,
) -> dict:
    """Run the complete discovery flow: scrape → filter → score → display.

    This ONLY discovers and scores jobs. It does NOT run per-job pipelines
    (validate/apply/outreach). Those run only when the user clicks Apply.
    
    Batch scores 10 jobs at a time for efficiency.
    """
    run_id = str(uuid.uuid4())

    # Phase 1: Discovery (career pages + ATS APIs)
    log.info("starting_discovery", location=location, role=role, limit=limit, run_id=run_id)
    if event_callback:
        await event_callback({
            "agent": "graph",
            "event_type": "progress",
            "message": f"Starting discovery for {location} (role: {role or 'software engineer'}, limit: {limit})...",
        })

    discovered_jobs = await run_discovery(location, profile, role, limit, event_callback)
    log.info("discovery_complete", job_count=len(discovered_jobs), run_id=run_id)

    if not discovered_jobs:
        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "complete",
                "message": "No jobs discovered.",
            })
        return {"run_id": run_id, "jobs_discovered": 0}

    # Phase 2: Verify active URLs & Batch match scoring (10 jobs at a time)
    from vellum.api.ws import manager as ws_manager
    from vellum.tools.url_verifier import filter_active_jobs

    discovered_jobs = await filter_active_jobs(discovered_jobs)
    if not discovered_jobs:
        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "complete",
                "message": "No active jobs verified.",
            })
        return {"run_id": run_id, "jobs_discovered": 0}

    if event_callback:
        await event_callback({
            "agent": "graph",
            "event_type": "progress",
            "message": f"Batch scoring {len(discovered_jobs)} verified active jobs...",
        })

    batch_size = 10
    for i in range(0, len(discovered_jobs), batch_size):
        batch = discovered_jobs[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(discovered_jobs) + batch_size - 1) // batch_size

        log.info("batch_scoring", batch=batch_num, total=total_batches, jobs_in_batch=len(batch))

        try:
            scores = await batch_score_jobs(batch, profile, location)
            from vellum.utils.job_cleaner import clean_job_title_and_company

            for job, score_data in zip(batch, scores):
                if not isinstance(score_data, dict):
                    score_data = {}
                match_score = score_data.get("match_score", 0.5)
                job["match_score"] = match_score

                # Extract & clean company & role
                raw_co = score_data.get("company_name") or job.get("company", "")
                raw_ro = score_data.get("job_role") or job.get("title") or job.get("role", "")
                clean_co, clean_ro = clean_job_title_and_company(
                    raw_title=raw_ro,
                    raw_company=raw_co,
                    snippet=job.get("jd_text", ""),
                    apply_url=job.get("apply_url", ""),
                )

                job["company"] = clean_co
                job["role"] = clean_ro
                job["title"] = clean_ro

                # Persist score + cleaned company & role to DB immediately
                job_id = job.get("id", "")
                if job_id:
                    validation_json = json.dumps(score_data)
                    try:
                        await db.update_job(
                            job_id,
                            company=clean_co,
                            role=clean_ro,
                            match_score=match_score,
                            validation_json=validation_json,
                        )
                    except Exception:
                        pass

            # Broadcast batch progress
            pct = min(90, int(((i + len(batch)) / len(discovered_jobs)) * 90))
            await ws_manager.broadcast({
                "agent": "graph",
                "event_type": "search_progress",
                "message": f"Batch scored {min(i + batch_size, len(discovered_jobs))}/{len(discovered_jobs)} jobs",
                "data": {"percentage": pct, "processed": min(i + batch_size, len(discovered_jobs)), "total": len(discovered_jobs)}
            })
        except Exception as exc:
            log.error("batch_scoring_error", batch=batch_num, error=str(exc))

        # Small delay between batches
        if i + batch_size < len(discovered_jobs):
            await asyncio.sleep(1.0)

    # Phase 3: Done — jobs are in DB, user reviews in Applications tab
    # Per-job pipelines (validate/apply/outreach) only run when user clicks Apply
    if event_callback:
        await event_callback({
            "agent": "graph",
            "event_type": "complete",
            "message": f"Discovery complete! {len(discovered_jobs)} jobs found and scored. Review in Applications tab and click Apply to proceed.",
        })

    return {
        "run_id": run_id,
        "jobs_discovered": len(discovered_jobs),
    }


async def run_single_job_apply(
    job_id: str,
    event_callback=None,
) -> dict:
    """Run the per-job pipeline independently for a single job.

    Used when the user clicks 'Apply' on an individual job card.
    Fetches the job and latest profile from DB.
    """
    job = await db.get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    profile = await db.get_latest_profile()
    if not profile:
        return {"error": "No candidate profile found. Upload a resume first."}

    from vellum.api.ws import manager as ws_manager

    async def _event_cb(event: dict):
        await ws_manager.broadcast(event)
        if event_callback:
            await event_callback(event)

    run_id = str(uuid.uuid4())
    result = await run_job_pipeline(
        job, profile, run_id, _event_cb,
        search_location=job.get("search_location", ""),
        validate_only=False,  # Full pipeline: validate → contact search → email → apply
    )
    return result
