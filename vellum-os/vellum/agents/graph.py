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
# Graph 2b: Full Apply Pipeline (user-triggered, automatic mode)
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


def build_prep_pipeline():
    """Build the per-job PREP pipeline (manual mode Apply button).

    Sequence: validate/tailor → contact search → email draft → STOP.

    In manual mode the user reviews contacts + the drafted outreach email
    before submitting anything themselves — the browser apply step is NOT
    run. Browser auto-submit only happens in automatic mode.
    """
    checkpointer = InMemorySaver()

    graph = StateGraph(JobPipelineState)

    graph.add_node("validate_tailor", validator_tailor.run)
    graph.add_node("find_contacts", contact_finder.run)
    graph.add_node("draft_email", email_drafter.run)

    graph.set_entry_point("validate_tailor")
    graph.add_conditional_edges(
        "validate_tailor",
        _should_apply,
        {
            "apply": "find_contacts",
            "skip": END,
        },
    )
    graph.add_edge("find_contacts", "draft_email")
    graph.add_edge("draft_email", END)

    return graph.compile(checkpointer=checkpointer)


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
_prep_pipeline = None
_validate_only_pipeline = None
_graph_lock = asyncio.Lock()

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


def get_prep_pipeline():
    global _prep_pipeline
    if _prep_pipeline is None:
        _prep_pipeline = build_prep_pipeline()
    return _prep_pipeline


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


def _fallback_score_single_job(job: dict, profile: dict, location: str = "", target_role: str = "") -> dict:
    """Intelligently score a job deterministically if LLM batch scoring fails or returns empty."""
    co = job.get("company", "")
    ro = job.get("role") or job.get("title", "")
    jd_text = (job.get("jd_text") or "").lower()

    cand_skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    # Use user-specified target role, fall back to suggested_role
    cand_role = (target_role or profile.get("suggested_role") or "Software Engineer").lower()
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


async def batch_score_jobs(jobs: list[dict], profile: dict, location: str = "", target_role: str = "") -> list[dict]:
    """Score up to 10 jobs in a single LLM call for efficiency.
    
    Returns list of dicts with match_score, matching_skills, missing_skills, reasoning.
    """
    from vellum.config.llm_router import call_llm_with_fallback
    
    if not jobs:
        return []

    name = profile.get("name", "Candidate")
    # Use the user-specified target role, falling back to suggested_role only if not provided
    effective_role = target_role or profile.get("suggested_role", "Software Engineer")
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
                target_role=effective_role,
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
                    final_scores.append(_fallback_score_single_job(job, profile, location, effective_role))
            return final_scores
    except Exception as exc:
        log.warning("batch_score_failed", error=str(exc))

    # Fallback: compute intelligent deterministic scores for each job
    return [_fallback_score_single_job(j, profile, location, effective_role) for j in jobs]


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
    """Run the per-job pipeline.

    Args:
        job: Job dict from database.
        profile: CandidateProfile dict.
        run_id: Unique run identifier.
        event_callback: Async callable for streaming events.
        search_location: The location the user searched for (for matching).
        validate_only: If True (default), only validate/tailor. If False,
                       run the apply pipeline.
        force_apply: If True, bypass match threshold and apply directly.
        include_browser: When False (manual mode), the pipeline stops after
                         contact search + email draft — no browser submit.

    Returns pipeline result dict.
    """
    if validate_only:
        pipeline = get_validate_only_pipeline()
    elif include_browser:
        pipeline = get_job_pipeline()
    else:
        pipeline = get_prep_pipeline()
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
    auto_apply: bool = False,
) -> dict:
    """Run the complete discovery flow: discover → verify → LLM validate → display.

    Uses Gemma 4 for deep job validation with experience-first filtering.
    Enforces company diversity and minimum relevance threshold.
    Loops discovery until enough quality jobs are found.

    When auto_apply=True (automatic pipeline mode), matched jobs are also
    pushed through the full apply pipeline (contact search → email → browser).
    """
    run_id = str(uuid.uuid4())
    from vellum.api.ws import manager as ws_manager
    from vellum.agents.job_llm_validator import validate_and_filter_jobs, MIN_RELEVANCE_SCORE

    effective_role = role or profile.get("suggested_role", "Software Engineer")
    all_discovered: list[dict] = []
    final_validated: list[dict] = []
    seen_urls: set[str] = set()
    company_count: dict[str, int] = {}  # Track diversity across rounds
    discovery_round = 0
    MAX_ROUNDS = 8  # Discovery attempts to reach the requested job count
    APPLY_SEMAPHORE = 3  # Max concurrent auto-applications

    while len(final_validated) < limit and discovery_round < MAX_ROUNDS:
        discovery_round += 1
        round_limit = min(limit * 2, 150)  # Discover extra to account for filtering

        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "progress",
                "message": f"Discovery round {discovery_round}: searching for {effective_role} in {location}...",
            })

        log.info("discovery_round", round=discovery_round, target=limit, found_so_far=len(final_validated))

        # Phase 1: Discovery
        try:
            raw_jobs = await run_discovery(location, profile, role, round_limit, event_callback)
        except Exception as exc:
            log.error("discovery_error", round=discovery_round, error=str(exc))
            break

        # Deduplicate against previously seen URLs
        new_jobs = []
        for job in raw_jobs:
            url = job.get("apply_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                new_jobs.append(job)

        if not new_jobs:
            if event_callback:
                await event_callback({
                    "agent": "graph",
                    "event_type": "progress",
                    "message": f"Round {discovery_round}: no new jobs found. Expanding search...",
                })
            # Try web search with broader terms for next round
            continue

        all_discovered.extend(new_jobs)

        # Phase 2: Jobs from geo_search are already URL-verified and stored in DB.
        # No second filter_active_jobs call needed — it would kill valid jobs.
        verified_jobs = new_jobs

        if not verified_jobs:
            continue

        # Phase 3: LLM Validation with Gemma 4
        # Pass existing company_count to enforce diversity across rounds
        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "progress",
                "message": f"Running LLM validation on {len(verified_jobs)} verified jobs...",
            })

        validation_result = await validate_and_filter_jobs(
            jobs=verified_jobs,
            profile=profile,
            target_role=effective_role,
            target_count=limit,
            location=location,
            event_callback=event_callback,
        )

        round_validated = validation_result.get("validated", [])
        round_low_score = validation_result.get("low_score", [])

        # Store ALL jobs in DB — validated get "matched", low_score get "discovered"
        for job in round_validated:
            company_key = (job.get("company") or "").lower().strip()
            current = company_count.get(company_key, 0)
            if current < 2 and len(final_validated) < limit:
                company_count[company_key] = current + 1
                job["status"] = "matched"
                final_validated.append(job)
            else:
                job["status"] = "discovered"

        for job in round_low_score:
            job["status"] = "discovered"  # Low score jobs go to "Low Score" filter

        # Persist ALL jobs to DB in one pass (both validated and low score)
        all_round_jobs = round_validated + round_low_score
        for job in all_round_jobs:
            job_id = job.get("id", "")
            if job_id:
                try:
                    await db.update_job(
                        job_id,
                        company=job.get("company", ""),
                        role=job.get("role", ""),
                        match_score=job.get("match_score", 0),
                        validation_json=job.get("validation_json", ""),
                        status=job.get("status", "discovered"),
                    )
                except Exception:
                    pass

        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "progress",
                "message": f"Round {discovery_round}: {len(round_validated)} validated, {len(round_low_score)} low score. Total: {len(final_validated)}/{limit}.",
            })

    # Final sort by match score
    final_validated.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    final_validated = final_validated[:limit]

    # Automatic mode: push matched jobs through the full apply pipeline
    auto_applied = 0
    auto_failed = 0
    if auto_apply and final_validated:
        if event_callback:
            await event_callback({
                "agent": "graph",
                "event_type": "progress",
                "message": f"Automatic mode: applying to {len(final_validated)} matched jobs...",
            })
        semaphore = asyncio.Semaphore(APPLY_SEMAPHORE)

        async def _auto_apply_one(job: dict) -> None:
            nonlocal auto_applied, auto_failed
            async with semaphore:
                try:
                    result = await run_job_pipeline(
                        job,
                        profile,
                        run_id,
                        event_callback,
                        search_location=location,
                        validate_only=False,  # Full pipeline: apply + outreach
                    )
                    if result.get("errors"):
                        auto_failed += 1
                    else:
                        browser_status = result.get("browser_result", {}).get("status")
                        if browser_status == "applied":
                            auto_applied += 1
                        else:
                            auto_failed += 1
                except Exception as exc:
                    log.warning("auto_apply_failed", job_id=job.get("id"), error=str(exc))
                    auto_failed += 1

        await asyncio.gather(*[_auto_apply_one(job) for job in final_validated])

    # Broadcast completion
    if event_callback:
        msg = (
            f"Discovery complete! {len(final_validated)} relevant jobs found "
            f"across {len(company_count)} companies. "
            f"All jobs scored above {MIN_RELEVANCE_SCORE}% relevance. "
            f"Review in Applications tab."
        )
        if auto_apply:
            msg += f" {auto_applied} applications launched (automatic mode)."
        await event_callback({
            "agent": "graph",
            "event_type": "complete",
            "message": msg,
        })

    log.info(
        "full_search_complete",
        total_discovered=len(all_discovered),
        final_validated=len(final_validated),
        unique_companies=len(company_count),
        rounds=discovery_round,
        auto_applied=auto_applied,
        auto_failed=auto_failed,
    )

    return {
        "run_id": run_id,
        "jobs_discovered": len(final_validated),
        "auto_applied": auto_applied,
        "auto_failed": auto_failed,
    }


async def run_single_job_apply(
    job_id: str,
    event_callback=None,
    include_browser: bool = True,
) -> dict:
    """Run the per-job pipeline independently for a single job.

    Used when the user clicks 'Apply' on an individual job card.
    Fetches the job and latest profile from DB.
    include_browser=False (manual mode): stops after contacts + email draft.
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
        validate_only=False,
        include_browser=include_browser,
    )
    return result
