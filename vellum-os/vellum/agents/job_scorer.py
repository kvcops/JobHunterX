"""
Vellum OS — Job Scorer

Scores scraped jobs against the candidate profile to build the review queue.

Two-stage design (budget-first — every LLM call costs tokens):
  1. Deterministic keyword pre-filter (skills overlap + role + location)
     — zero tokens, robust first-pass ranking.
  2. Gemma batch scoring of the top candidates: 10 jobs per call, JSON out.

When the Gemma daily budget (15k RPD) is exhausted the keyword score still
stands, so the system degrades gracefully instead of dying.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from vellum.config import gemma as g
from vellum.config.logging import get_logger

log = get_logger("job_scorer")

KEYWORD_SCORE = "keyword_score"
FINAL_SCORE = "match_score"

_SCORE_SYSTEM = """You are a ruthless job-match screener for an Indian software candidate.
Score each job ONLY on how well it matches the candidate's skills, years of experience, and location preference.
Use the FULL 0-1 range: 0 = no match, 0.2-0.4 = weak, 0.5-0.7 = good, 0.8-1.0 = excellent.
Do NOT inflate scores. Be strict and honest. Return only JSON.

Output format (exactly):
{"scores":[{"i":0,"score":0.0,"why":"one short reason"}]}"""


def _keyword_score(job: dict, profile: dict) -> float:
    """Cheap deterministic relevance: skill overlap + role + location hints.

    Returns 0-1. Never uses the LLM.
    """
    role_low = (job.get("role") or "").lower()
    loc_low = (job.get("location") or "").lower()
    jd_low = (job.get("jd_text") or "")[:4000].lower()

    skills = profile.get("skills") or []
    if isinstance(skills, list):
        skills = [s.lower() for s in skills if isinstance(s, str)]
    else:
        skills = [s.lower() for s in str(skills).split(",")]

    score = 0.0
    # Skill overlap (heaviest signal)
    hits = sum(1 for s in skills if s and s in jd_low)
    overlap = min(1.0, hits / max(1, min(len(skills), 8)))
    score += 0.55 * overlap

    # Role match
    target_role = (profile.get("suggested_role") or "").lower()
    if target_role:
        target_words = [w for w in re.split(r"[^a-z0-9+.#]+", target_role) if len(w) > 3]
        if any(w in role_low for w in target_words):
            score += 0.20
        else:
            score += 0.05

    # Location preference soft-boost
    target_loc = (profile.get("location") or "")
    if target_loc:
        city = re.split(r"[,\s]+", target_loc.lower())[0]
        if city and (city in loc_low or "remote" in loc_low):
            score += 0.10

    # Freshest jobs slightly preferred (posted_at present)
    if job.get("posted_at"):
        score += 0.05

    return round(min(1.0, score), 3)


def _llm_eligible(jobs: list[dict], profile: dict) -> list[int]:
    """Idxs of jobs that pass the keyword prefilter (cheap, no tokens)."""
    idxs = []
    for i, job in enumerate(jobs):
        ks = _keyword_score(job, profile)
        if ks >= 0.35:  # only worth spending LLM tokens on plausible matches
            idxs.append(i)
    return idxs


async def score_batch(jobs: list[dict], profile: dict, max_llm_jobs: int = 20) -> list[dict]:
    """Score a list of job dicts in place: adds match_score to each dict.

    Returns the same list (dictionaries mutated) with 'keyword_score' and
    'match_score' set. match_score = Gemma score when available, else the
    keyword score (budget-exhausted path).
    """
    for job in jobs:
        job["keyword_score"] = _keyword_score(job, profile)
        job[FINAL_SCORE] = min(job["keyword_score"], 1.0)

    eligible = _llm_eligible(jobs, profile)
    if not eligible:
        return jobs

    # Batch into groups of 10, only the eligible ones
    eligible.sort(key=lambda i: jobs[i]["keyword_score"], reverse=True)
    eligible = eligible[: max_llm_jobs]

    colours = (
        f"Candidate target role: {profile.get('suggested_role') or 'Software Engineer'}\n"
        f"Candidate skills: {', '.join((profile.get('skills') or [])[:25])}\n"
        f"Target location: {profile.get('location') or 'India'}\n"
        f"Years experience: {profile.get('relevant_experience') or '0'}\n\n"
        "Jobs:\n"
    )
    batch_limit = 10
    for start in range(0, len(eligible), batch_limit):
        group = eligible[start:start + batch_limit]
        lines = []
        for jid, idx in enumerate(group):
            job = jobs[idx]
            jd = re.sub(r"\s+", " ", job.get("jd_text") or "")[:1000]
            lines.append(
                f"[{jid}] title={job.get('role','')} | location={job.get('location','')} "
                f"| dept={job.get('department','')} | posted={job.get('posted_at','')}\njd: {jd}"
            )
        user_prompt = colours + "\n".join(lines) + "\n\nReturn ONLY the JSON object."

        if await g.gemma_available():
            try:
                raw = await g.call_gemma(
                    system=_SCORE_SYSTEM,
                    user=user_prompt,
                    max_tokens=1100,
                    temperature=0.1,
                )
                scores = _parse_scores(raw)
                if scores:
                    for entry in scores:
                        i = entry.get("i")
                        s = entry.get("score")
                        if i is not None and s is not None and 0 <= i < len(group):
                            jobs[group[i]][FINAL_SCORE] = round(max(0.0, min(1.0, float(s))), 3)
                    log.info("gemma_batch_scored", count=len(group), scores=len(scores))
                    continue
            except RuntimeError as exc:
                if "budget_exhausted" in str(exc):
                    log.warning("gemma_budget_exhausted_scoring_skipped")
                    break  # stop using budget, keep keyword scores
            except Exception as exc:
                log.warning("gemma_batch_failed", error=str(exc)[:150])
        # Fallback: keep keyword scores for this group.

    return jobs


def _parse_scores(content: str) -> list[dict]:
    """Extract the scores array from raw/JSON/fence-wrapped LLM output."""
    text = content or ""
    text = re.sub(r"\x60{3}", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    entries = data.get("scores") or data.get("score") or []
    return entries if isinstance(entries, list) else []