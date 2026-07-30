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
    """Route after validation: apply if matched, skip otherwise."""
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

BATCH_MATCH_SCORING_PROMPT = """You are a top-tier executive talent manager. Compare the candidate profile against multiple job descriptions and assign a match score (0.0-1.0) for each.

CRITICAL MATCHING RULES:
1. Location Match: The candidate targets "{target_location}". Strict onsite in a different city = lower score.
2. Experience Match: Candidate has "{candidate_experience}". Mismatched seniority = low score.
3. Skills Match: Weight overlap between candidate skills and JD requirements heavily.
4. Role Alignment: Job role must align with candidate's target role.
5. CTC: Only penalize if the JD explicitly states compensation below candidate's expected CTC "{expected_ctc}".

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
  {{"job_index": 0, "match_score": 0.75, "matching_skills": ["Python", "FastAPI"], "missing_skills": ["React"], "reasoning": "Strong backend match"}},
  ...
]

Return valid JSON array only. No markdown commentary."""


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
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        scores = json.loads(content.strip())

        if isinstance(scores, list) and len(scores) == len(jobs):
            return scores
        elif isinstance(scores, list) and len(scores) > 0:
            # Pad or truncate to match job count
            while len(scores) < len(jobs):
                scores.append({"match_score": 0.5, "matching_skills": [], "missing_skills": [], "reasoning": "Default"})
            return scores[:len(jobs)]
    except Exception as exc:
        log.warning("batch_score_failed", error=str(exc))

    # Fallback: return default scores
    return [{"match_score": 0.5, "matching_skills": [], "missing_skills": [], "reasoning": "Batch scoring unavailable"} for _ in jobs]


async def run_job_pipeline(
    job: dict,
    profile: dict,
    run_id: str = "",
    event_callback=None,
    search_location: str = "",
    validate_only: bool = True,
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
    """Run the complete flow: discovery → batch scoring → per-job pipelines.

    Batch scores 10 jobs at a time for efficiency.
    Processes jobs concurrently with a semaphore limit.
    """
    run_id = str(uuid.uuid4())
    settings = get_settings()

    # Phase 1: Discovery
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
        return {"run_id": run_id, "jobs_processed": 0}

    # Phase 1.5: Batch match scoring (10 jobs at a time)
    from vellum.api.ws import manager as ws_manager

    if event_callback:
        await event_callback({
            "agent": "graph",
            "event_type": "progress",
            "message": f"Batch scoring {len(discovered_jobs)} jobs (10 at a time)...",
        })

    batch_size = 10
    for i in range(0, len(discovered_jobs), batch_size):
        batch = discovered_jobs[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(discovered_jobs) + batch_size - 1) // batch_size

        log.info("batch_scoring", batch=batch_num, total=total_batches, jobs_in_batch=len(batch))

        try:
            scores = await batch_score_jobs(batch, profile, location)
            for job, score_data in zip(batch, scores):
                match_score = score_data.get("match_score", 0.5) if isinstance(score_data, dict) else 0.5
                job["match_score"] = match_score

                # Persist score to DB immediately
                job_id = job.get("id", "")
                if job_id:
                    validation_json = json.dumps(score_data) if isinstance(score_data, dict) else "{}"
                    try:
                        await db.update_job(
                            job_id,
                            match_score=match_score,
                            validation_json=validation_json,
                        )
                    except Exception:
                        pass

            # Broadcast batch progress
            pct = min(80, int(((i + len(batch)) / len(discovered_jobs)) * 80))
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

    # Phase 2: Per-job pipelines (concurrent, limited)
    semaphore = asyncio.Semaphore(settings.max_job_pipelines)
    completed_jobs = 0
    total_jobs = len(discovered_jobs)

    async def process_job(job_dict):
        nonlocal completed_jobs
        async with semaphore:
            res = await run_job_pipeline(
                job_dict, profile, run_id, event_callback,
                search_location=location,
            )
            completed_jobs += 1
            percentage = 80 + int((completed_jobs / total_jobs) * 20)
            
            # Broadcast search progress to UI
            await ws_manager.broadcast({
                "agent": "graph",
                "event_type": "search_progress",
                "message": f"Processed job {completed_jobs}/{total_jobs}: {job_dict.get('company')} - {job_dict.get('role', '')[:40]}",
                "data": {"percentage": percentage, "processed": completed_jobs, "total": total_jobs}
            })
            return res

    tasks = [process_job(job) for job in discovered_jobs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if isinstance(r, dict) and not r.get("errors"))
    error_count = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("errors")))

    if event_callback:
        await event_callback({
            "agent": "graph",
            "event_type": "complete",
            "message": f"Search complete. {len(discovered_jobs)} discovered, {success_count} processed, {error_count} errors.",
        })

    return {
        "run_id": run_id,
        "jobs_discovered": len(discovered_jobs),
        "jobs_processed": success_count,
        "jobs_errored": error_count,
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
