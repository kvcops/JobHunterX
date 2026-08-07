"""
Kuro OS — Multi-Agent Job Discovery & Evaluation Engine

Coordinated 3-agent pipeline:
  1. Agent 1: Query Strategist (Gemma LLM)
     Uses candidate profile to generate rich, dynamic, non-repetitive search queries
     targeting Indian tech hubs, startups, and high-paying product companies.
  2. Agent 2: Web Scout (DuckDuckGo + Scraper)
     Executes searches, filters aggregators & mass-hirers, checks against seen_job_urls,
     scrapes real job details, stores in DB, and STREAMS `job_found` events to the UI in real-time.
  3. Agent 3: Job Evaluator (Gemma LLM + Scorer)
     Evaluates jobs multi-dimensionally (skills, role fit, experience, location),
     updates DB, and STREAMS `job_scored` events so cards update live in the UI.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from kuro.agents import eligibility, search_planner
from kuro.config import database as db
from kuro.config import gemma as g
from kuro.config.logging import get_logger
from kuro.tools import job_discovery

log = get_logger("job_search_agents")

EventCallback = Callable[[dict], Awaitable[None]]

_QUERY_GEN_SYSTEM = """You are an expert technical talent recruiter and search strategist specialized in the INDIAN tech market.
Generate 15 to 20 highly effective, distinct web search queries to find open job postings for a candidate.

Guidelines:
- Target Indian locations (Bengaluru, Hyderabad, Mumbai, Pune, Gurgaon, Noida, Chennai, Remote, etc.)
- Focus on startups, product companies, SaaS, fintech, and high-growth engineering teams.
- STRICTLY avoid mass-hiring IT service companies (TCS, Infosys, Wipro, Cognizant, Accenture, HCL, LTI).
- Build queries focusing on:
  1. Direct job role + location + 'hiring'/'careers'/'apply'
  2. Skill-specific developer roles in India
  3. Indian startup job postings on Greenhouse, Lever, Ashby, or company career sites
  4. Fresher / junior or mid-level specific queries based on candidate experience
- Output ONLY a JSON array of query strings: ["query 1", "query 2", ...]"""


# ---------------------------------------------------------------------------
# Agent 1: Query Strategist
# ---------------------------------------------------------------------------

async def generate_search_queries(profile: dict, plan: dict) -> list[str]:
    """Agent 1: Gemma-powered query strategist."""
    target_roles = plan.get("target_roles") or [profile.get("suggested_role") or "Software Engineer"]
    skills = (profile.get("skills") or [])[:10]
    locations = plan.get("locations") or [profile.get("location") or "Bengaluru"]
    exp_years = float(plan.get("years_experience") or 0)

    user_prompt = (
        f"Candidate Target Roles: {', '.join(target_roles)}\n"
        f"Top Skills: {', '.join(skills)}\n"
        f"Preferred Locations: {', '.join(locations)}\n"
        f"Years Experience: {exp_years}\n\n"
        "Generate 15-20 diverse search queries for DuckDuckGo. Return ONLY a JSON array of strings."
    )

    queries: list[str] = []
    if await g.gemma_available():
        try:
            raw = await g.call_gemma(
                system=_QUERY_GEN_SYSTEM,
                user=user_prompt,
                max_tokens=800,
                temperature=0.3,
            )
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list) and len(parsed) >= 5:
                    queries = [str(q).strip() for q in parsed if isinstance(q, str) and len(q.strip()) > 5]
                    log.info("agent_query_strategist_success", count=len(queries))
        except Exception as exc:
            log.warning("agent_query_strategist_llm_failed", error=str(exc)[:120])

    if not queries:
        # Fallback query generation logic
        queries = job_discovery.build_search_queries(profile, plan)

    return queries[:20]


# ---------------------------------------------------------------------------
# Agent 3: Job Evaluator (Gemma Multi-Dimensional Scorer)
# ---------------------------------------------------------------------------

_EVALUATE_JOB_SYSTEM = """You are a senior engineering manager evaluating job postings for a software candidate in India.
Score the job from 0.0 to 1.0 based on:
1. Skill Overlap (0.4 weight): How well the candidate's skills match the JD requirements.
2. Role & Responsibility Match (0.3 weight): Is this the right technical domain and seniority level?
3. Location Compatibility (0.2 weight): Is it in the candidate's target city or Remote?
4. Experience Level Fit (0.1 weight): Does the required experience match candidate's background?

Rules:
- Be realistic and strict. 0.0 - 0.45 = Low Score / Unmatched, 0.60 - 1.0 = Matched.
- Return ONLY JSON: {"match_score": 0.85, "reason": "Short 1-sentence breakdown of why this matches"}"""


async def evaluate_single_job(job: dict, profile: dict, plan: dict) -> dict:
    """Agent 3: Evaluate a single job using Gemma or keyword fallbacks."""
    skills = ", ".join((profile.get("skills") or [])[:20])
    target_role = profile.get("suggested_role") or "Software Engineer"
    loc = profile.get("location") or "Bengaluru"
    exp = profile.get("relevant_experience") or "0"

    jd = (job.get("jd_text") or "")[:2000]
    title = job.get("role") or job.get("title") or ""
    company = job.get("company") or ""

    score = 0.0
    reason = "Keyword evaluation"

    if await g.gemma_available():
        try:
            user_prompt = (
                f"CANDIDATE:\n"
                f"- Target Role: {target_role}\n"
                f"- Skills: {skills}\n"
                f"- Location: {loc}\n"
                f"- Experience: {exp}\n\n"
                f"JOB POSTING:\n"
                f"- Title: {title}\n"
                f"- Company: {company}\n"
                f"- Location: {job.get('location', 'India')}\n"
                f"- Description snippet: {jd}\n\n"
                "Evaluate and return JSON with 'match_score' and 'reason'."
            )

            raw = await g.call_gemma(
                system=_EVALUATE_JOB_SYSTEM,
                user=user_prompt,
                max_tokens=300,
                temperature=0.1,
            )
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                s = data.get("match_score")
                r = data.get("reason")
                if s is not None:
                    score = round(max(0.0, min(1.0, float(s))), 3)
                    reason = str(r or "Matched via Gemma AI evaluation")[:200]
                    return {"match_score": score, "reason": reason}
        except Exception as exc:
            log.warning("gemma_single_eval_failed", error=str(exc)[:100])

    # Fallback deterministic evaluation
    from kuro.agents.job_scorer import _keyword_score
    score = _keyword_score(job, profile)
    reason = f"Keyword skill match ({int(score * 100)}%)"
    return {"match_score": score, "reason": reason}


# ---------------------------------------------------------------------------
# Multi-Agent Search Orchestrator
# ---------------------------------------------------------------------------

async def run_multi_agent_search(
    profile: dict,
    preferred_location: Optional[str] = None,
    event_cb: Optional[EventCallback] = None,
) -> dict:
    """Execute the complete multi-agent job discovery & streaming evaluation workflow."""

    async def emit(etype: str, message: str, data: dict | None = None):
        if event_cb:
            try:
                await event_cb({
                    "agent": "multi_agent_search",
                    "event_type": etype,
                    "message": message,
                    "data": data or {},
                })
            except Exception:
                pass

    summary = {
        "queries_run": 0,
        "results_found": 0,
        "jobs_scraped": 0,
        "jobs_stored": 0,
        "jobs_skipped_seen": 0,
        "jobs_rejected_gate": 0,
    }

    # 1. Build search plan
    await emit("progress", "Agent 1 (Planner): Analyzing candidate profile & building search strategy...", {})
    plan = await search_planner.build_search_plan(profile)
    if preferred_location and preferred_location.strip():
        loc = preferred_location.strip().title()
        plan["locations"] = [loc] + [l for l in (plan.get("locations") or []) if l.lower() != loc.lower()]

    # 2. Agent 1: Generate Queries
    await emit("progress", "Agent 1 (Query Strategist): Generating targeted search queries...", {})
    queries = await generate_search_queries(profile, plan)
    summary["queries_run"] = len(queries)
    await emit("progress", f"Generated {len(queries)} intelligent search queries for {plan.get('locations', ['India'])}.", {})

    # Load seen URL hashes to prevent re-discovering cleared jobs
    seen_hashes = await db.get_seen_url_hashes()

    # 3. Agent 2 & Agent 3 Pipeline: Search -> Scrape -> Stream Job -> Batch Score -> Stream Score
    scrape_sem = asyncio.Semaphore(5)
    seen_urls_in_run: set[str] = set()
    newly_discovered_jobs: list[dict] = []

    from kuro.agents.job_scorer import _keyword_score, score_batch

    for idx, query in enumerate(queries):
        await emit("progress", f"[{idx + 1}/{len(queries)}] Web Scout searching: '{query[:50]}'...", {})
        results = await job_discovery.search_ddg(query, max_results=12)
        summary["results_found"] += len(results)

        for res in results:
            url = res.url.strip()
            url_low = url.rstrip("/").lower()
            url_hash = hashlib.sha256(url_low.encode()).hexdigest()

            if url_hash in seen_hashes or url_low in seen_urls_in_run:
                summary["jobs_skipped_seen"] += 1
                continue

            seen_urls_in_run.add(url_low)
            seen_hashes.add(url_hash)

            # Scrape job page
            async with scrape_sem:
                job_data = await job_discovery.scrape_job_page(url)

            if not job_data or not job_data.get("jd_text"):
                continue

            company = job_data.get("company") or res.company or ""
            role = job_data.get("title") or res.title or ""
            if not company or not role:
                continue

            raw_job = {
                "company": company,
                "role": role,
                "location": job_data.get("location") or "",
                "jd_text": job_data.get("jd_text") or "",
                "apply_url": job_data.get("apply_url") or url,
                "career_page_url": job_data.get("career_page_url") or url,
                "source": "multi_agent_ddg",
            }

            # Check Eligibility Gate
            passed, rejected = eligibility.filter_jobs([raw_job], plan)
            if not passed:
                summary["jobs_rejected_gate"] += 1
                continue

            valid_job = passed[0]
            summary["jobs_scraped"] += 1

            # Instant initial keyword score
            initial_score = _keyword_score(valid_job, profile)
            valid_job["match_score"] = initial_score
            valid_job["score_reason"] = f"Keyword skill match ({int(initial_score * 100)}%)"

            # Store in DB immediately
            job_id = await db.insert_job({
                "company": valid_job["company"],
                "role": valid_job["role"],
                "career_page_url": valid_job["career_page_url"],
                "apply_url": valid_job["apply_url"],
                "jd_text": valid_job["jd_text"],
                "source": valid_job["source"],
                "status": "discovered",
            })
            valid_job["id"] = job_id
            await db.update_job(
                job_id,
                match_score=initial_score,
                validation_json=json.dumps({"score_reason": valid_job["score_reason"], "match_score": initial_score}),
            )
            summary["jobs_stored"] += 1
            newly_discovered_jobs.append(valid_job)

            # STREAM `job_found` event immediately to UI!
            await emit("job_found", f"Discovered job: {valid_job['role']} at {valid_job['company']}", {
                "job": valid_job
            })

        await asyncio.sleep(1.0)  # DDG rate limiting

    # 4. Agent 3: Batch Gemma Scoring (1 LLM call per 10 jobs — 90% fewer API calls!)
    if newly_discovered_jobs:
        await emit("progress", f"Agent 3 (Evaluator): Batch evaluating {len(newly_discovered_jobs)} discovered jobs with Gemma AI...", {})
        scored_jobs = await score_batch(newly_discovered_jobs, profile, max_llm_jobs=50)

        for job in scored_jobs:
            jid = job.get("id")
            ms = job.get("match_score", 0.0)
            reason = job.get("score_reason", "Gemma AI evaluated")
            if jid:
                await db.update_job(
                    jid,
                    match_score=ms,
                    validation_json=json.dumps({"score_reason": reason, "match_score": ms}),
                )
                await emit("job_scored", f"Evaluated ({int(ms * 100)}%): {job.get('role')} at {job.get('company')}", {
                    "job_id": jid,
                    "match_score": ms,
                    "reason": reason,
                    "job": job,
                })

    await emit("complete", f"Discovery finished! Discovered & evaluated {summary['jobs_stored']} new jobs.", summary)
    return summary
