"""
Vellum OS — LangGraph Orchestration

Two-tier architecture:
  1. Discovery Graph: runs once to populate job queue
  2. Per-Job Pipeline: independent pipeline per job for validation/apply/outreach

Uses InMemorySaver for HITL checkpointing, interrupt() + Command for pause/resume.
"""

from __future__ import annotations

import asyncio
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from vellum.agents import geo_search, validator_tailor, browser_agent, deep_research
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
# Graph 2: Per-Job Pipeline
# ---------------------------------------------------------------------------

def _should_apply(state: JobPipelineState) -> str:
    """Route after validation: apply if matched, skip otherwise."""
    validation = state.get("validation", {})
    match_score = validation.get("match_score", 0)
    if match_score >= 0.3:
        return "apply"
    return "skip"


def build_job_pipeline():
    """Build the per-job validation → apply + outreach pipeline.

    Uses InMemorySaver for HITL checkpointing.
    """
    checkpointer = InMemorySaver()

    graph = StateGraph(JobPipelineState)

    # Nodes
    graph.add_node("validate_tailor", validator_tailor.run)
    graph.add_node("browse_apply", browser_agent.run)
    graph.add_node("research_outreach", deep_research.run)

    # Entry
    graph.set_entry_point("validate_tailor")

    # Conditional: after validation, either apply+outreach or skip
    graph.add_conditional_edges(
        "validate_tailor",
        _should_apply,
        {
            "apply": "browse_apply",
            "skip": END,
        },
    )

    # After browser agent, run outreach in parallel concept
    # (LangGraph handles this as sequential but both get the validated state)
    graph.add_edge("browse_apply", "research_outreach")
    graph.add_edge("research_outreach", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Job Queue Manager
# ---------------------------------------------------------------------------

# Module-level graph instances
_discovery_graph = None
_job_pipeline = None

# Active pipeline references for HITL resume
_active_pipelines: dict[str, dict] = {}


def get_discovery_graph():
    global _discovery_graph
    if _discovery_graph is None:
        _discovery_graph = build_discovery_graph()
    return _discovery_graph


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


async def run_job_pipeline(
    job: dict,
    profile: dict,
    run_id: str = "",
    event_callback=None,
    search_location: str = "",
) -> dict:
    """Run the per-job pipeline (validate → apply → outreach).

    Args:
        job: Job dict from database.
        profile: CandidateProfile dict.
        run_id: Unique run identifier.
        event_callback: Async callable for streaming events.
        search_location: The location the user searched for (for matching).

    Returns pipeline result dict.
    """
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
    """Run the complete flow: discovery → per-job pipelines.

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

    # Phase 2: Per-job pipelines (concurrent, limited)
    semaphore = asyncio.Semaphore(settings.max_job_pipelines)
    completed_jobs = 0
    total_jobs = len(discovered_jobs)

    from vellum.api.ws import manager as ws_manager

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
                "message": f"Processed job {completed_jobs}/{total_jobs}: {job_dict.get('company')} - {job_dict.get('role')[:40]}",
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
    )
    return result
