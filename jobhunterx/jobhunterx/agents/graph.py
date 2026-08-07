"""
JobHunterX — Orchestration

Board-first architecture:
  1. job_sync engine: companies → ATS boards (free JSON APIs) → jobs → score
  2. Per-job pipeline: validate/tailor resume → browser apply (kept)

No web-search, no contact finding, no cold email. LLM is Gemma only.
"""

from __future__ import annotations

import asyncio
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from jobhunterx.agents import validator_tailor, browser_agent, job_sync
from jobhunterx.config.logging import get_logger
from jobhunterx.config import database as db
from jobhunterx.models import JobPipelineState

log = get_logger("graph")


# ---------------------------------------------------------------------------
# Per-job pipeline: validate/tailor → browser apply
# ---------------------------------------------------------------------------

def _should_apply(state: JobPipelineState) -> str:
    """Route after validation: apply if matched or explicitly forced."""
    if state.get("force_apply", False):
        return "apply"
    validation = state.get("validation", {})
    match_score = validation.get("match_score", 0)
    if match_score >= 0.3:
        return "apply"
    return "skip"


def build_validate_only_pipeline():
    """Validate + tailor resume only (no apply). Used during scoring review."""
    checkpointer = InMemorySaver()
    graph = StateGraph(JobPipelineState)
    graph.add_node("validate_tailor", validator_tailor.run)
    graph.set_entry_point("validate_tailor")
    graph.add_edge("validate_tailor", END)
    return graph.compile(checkpointer=checkpointer)


def build_apply_pipeline():
    """Full per-job pipeline: validate/tailor → browser apply."""
    checkpointer = InMemorySaver()
    graph = StateGraph(JobPipelineState)
    graph.add_node("validate_tailor", validator_tailor.run)
    graph.add_node("browse_apply", browser_agent.run)
    graph.set_entry_point("validate_tailor")
    graph.add_conditional_edges(
        "validate_tailor",
        _should_apply,
        {
            "apply": "browse_apply",
            "skip": END,
        },
    )
    graph.add_edge("browse_apply", END)
    return graph.compile(checkpointer=checkpointer)


# Module-level graph instances
_validate_only_pipeline = None
_apply_pipeline = None
_graph_lock = asyncio.Lock()

# Active pipeline references for HITL resume
_active_pipelines: dict[str, dict] = {}


def get_validate_only_pipeline():
    global _validate_only_pipeline
    if _validate_only_pipeline is None:
        _validate_only_pipeline = build_validate_only_pipeline()
    return _validate_only_pipeline


def get_apply_pipeline():
    global _apply_pipeline
    if _apply_pipeline is None:
        _apply_pipeline = build_apply_pipeline()
    return _apply_pipeline


async def run_job_pipeline(
    job: dict,
    profile: dict,
    run_id: str = "",
    event_callback=None,
    search_location: str = "",
    validate_only: bool = True,
    force_apply: bool = False,
    include_browser: bool = True,
) -> dict:
    """Run the per-job pipeline: tailor resume (+ browser apply when asked)."""
    pipeline = get_validate_only_pipeline() if validate_only else get_apply_pipeline()
    job_id = job.get("id", str(uuid.uuid4()))
    thread_id = f"job-{job_id}"

    # Always refresh the profile from DB to get the latest edits
    fresh_profile = await db.get_latest_profile()
    if fresh_profile:
        profile = fresh_profile

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
        _active_pipelines[job_id] = {"thread_id": thread_id, "config": config}

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
    """Resume an interrupted pipeline. 'done' re-runs the apply flow; 'skip' aborts."""
    from langgraph.types import Command

    pipeline_info = _active_pipelines.get(job_id)
    if not pipeline_info:
        log.warning("no_active_pipeline", job_id=job_id)
        return {"error": "No active pipeline for this job"}

    pipeline = get_apply_pipeline()
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
    auto_apply: bool = False,
) -> dict:
    """Run the multi-agent job discovery & streaming evaluation flow."""
    from jobhunterx.agents import job_search_agents

    summary = await job_search_agents.run_multi_agent_search(
        profile=profile,
        preferred_location=location,
        event_cb=event_callback,
    )
    return {
        "run_id": str(uuid.uuid4()),
        "jobs_discovered": summary.get("jobs_stored", 0),
        "auto_applied": 0,
        "auto_failed": 0,
        "sync": summary,
    }


async def run_single_job_apply(
    job_id: str,
    event_callback=None,
    include_browser: bool = True,
) -> dict:
    """Per-job pipeline when the user clicks Apply on a job card."""
    job = await db.get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    profile = await db.get_latest_profile()
    if not profile:
        return {"error": "No candidate profile found. Upload a resume first."}

    from jobhunterx.api.ws import manager as ws_manager

    async def _event_cb(event: dict):
        await ws_manager.broadcast(event)
        if event_callback:
            await event_callback(event)

    run_id = str(uuid.uuid4())
    result = await run_job_pipeline(
        job, profile, run_id, _event_cb,
        search_location=job.get("search_location", ""),
        validate_only=False,
        include_browser=include_browser,
    )

    # Track application state so the UI never re-suggests an applied job.
    if result.get("errors"):
        await db.update_job(job_id, status="apply_failed")
    else:
        await db.update_job(job_id, status="applied")
    return result