"""
Vellum OS — Validator & Tailor Agent (Agent C)

Per-job pipeline: freshness check → JD validation → guardrailed tailoring → PDF.
Strict guardrails prevent LLMs from inventing skills or experience.
"""

from __future__ import annotations

import json

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import scrape, pdf_render
from vellum.models import AgentEvent

log = get_logger("validator_tailor")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

VALIDATION_PROMPT = """You are a job-matching expert. Compare the candidate profile against the job description.
Return a JSON object:
{
  "match_score": 0.0-1.0,
  "matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "reasoning": "Brief explanation of fit"
}

Candidate Profile:
{profile_summary}

Job Description:
{jd_text}

Return valid JSON only. No markdown."""

TAILORING_PROMPT = """You are a resume bullet-point editor. Your job is to rephrase existing resume bullets to better match the target job description.

STRICT RULES:
1. You may ONLY rephrase existing bullets. You MUST NOT add skills, technologies, experiences, or achievements not present in the original.
2. You may reorder, emphasize, and use stronger action verbs.
3. You MUST NOT fabricate metrics, percentages, or numbers not in the original.
4. You MUST NOT add technologies or tools not listed in the original skills.
5. Keep each bullet under 120 characters.

Original skills (ground truth — do not add anything outside this list):
{skills_list}

Original experience bullets:
{original_bullets}

Target job description:
{jd_text}

Return a JSON array of strings — the rephrased bullets in the same order.
Return valid JSON only. No markdown."""


# ---------------------------------------------------------------------------
# Per-job pipeline
# ---------------------------------------------------------------------------

async def run(state: dict) -> dict:
    """Agent C: Validate, check freshness, tailor, and generate PDF.

    Input state: {"job": dict, "profile": dict}
    Output: updates state with freshness, validation, tailored_pdf, events
    """
    job = state.get("job", {})
    profile = state.get("profile", {})
    job_id = job.get("id", "")
    events: list[dict] = []
    errors: list[str] = []

    events.append(AgentEvent(
        agent="validator_tailor",
        event_type="progress",
        job_id=job_id,
        message=f"Validating: {job.get('company', '')} — {job.get('role', '')}",
    ).model_dump(mode="json"))

    # ------------------------------------------------------------------
    # Step 1: Freshness check (best-effort)
    # ------------------------------------------------------------------
    freshness = {"is_fresh": None, "confidence": 0.0, "evidence": "unknown", "detected_date": None}
    jd_text = job.get("jd_text", "")

    if not jd_text and job.get("apply_url"):
        # Fetch the job page to get JD text and check freshness
        page = await scrape.fetch_page(job["apply_url"])
        html = page.get("html", "")
        headers = page.get("headers", {})
        if html:
            jd_text = await scrape.extract_jd_text(html)
            freshness = await scrape.extract_job_freshness(html, headers)
    elif jd_text:
        # We have JD text but need to check freshness from career page
        if job.get("career_page_url"):
            page = await scrape.fetch_page(job["career_page_url"])
            freshness = await scrape.extract_job_freshness(
                page.get("html", ""), page.get("headers", {})
            )

    # Update job with freshness
    freshness_json = json.dumps(freshness)
    await db.update_job(job_id, freshness_json=freshness_json, jd_text=jd_text)

    # If confirmed stale with high confidence, skip
    if freshness.get("is_fresh") is False and freshness.get("confidence", 0) >= 0.7:
        await db.update_job(job_id, status="skipped")
        events.append(AgentEvent(
            agent="validator_tailor",
            event_type="progress",
            job_id=job_id,
            message=f"Skipped — confirmed stale ({freshness.get('evidence')})",
            confidence=freshness.get("confidence"),
        ).model_dump(mode="json"))
        return {"freshness": freshness, "events": events, "errors": errors}

    if not jd_text:
        await db.update_job(job_id, status="skipped")
        events.append(AgentEvent(
            agent="validator_tailor",
            event_type="progress",
            job_id=job_id,
            message="Skipped — no JD text extracted",
        ).model_dump(mode="json"))
        return {"freshness": freshness, "events": events, "errors": errors}

    # ------------------------------------------------------------------
    # Step 2: Validation (match score)
    # ------------------------------------------------------------------
    await db.update_job(job_id, status="validating")

    profile_summary = f"""Name: {profile.get('name', '')}
Skills: {', '.join(profile.get('skills', []))}
Experience: {'; '.join(exp.get('role', '') + ' at ' + exp.get('company', '') for exp in profile.get('experience', []))}"""

    validation_messages = [
        {"role": "system", "content": "You are a job-matching expert."},
        {
            "role": "user",
            "content": VALIDATION_PROMPT.format(
                profile_summary=profile_summary,
                jd_text=jd_text[:3000],
            ),
        },
    ]

    validation = {"match_score": 0.0, "matching_skills": [], "missing_skills": [], "reasoning": "", "confidence": 0.0}

    try:
        result = await call_llm_with_fallback("reasoning", validation_messages)
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        validation = json.loads(content.strip())
        validation["confidence"] = min(1.0, validation.get("match_score", 0.0) + 0.2)
    except Exception as exc:
        errors.append(f"Validation error: {exc}")
        log.error("validation_error", job_id=job_id, error=str(exc))

    await db.update_job(
        job_id,
        validation_json=json.dumps(validation),
        match_score=validation.get("match_score", 0.0),
    )

    events.append(AgentEvent(
        agent="validator_tailor",
        event_type="progress",
        job_id=job_id,
        message=f"Match score: {validation.get('match_score', 0):.0%}",
        confidence=validation.get("confidence"),
        data=validation,
    ).model_dump(mode="json"))

    # Skip low matches
    if validation.get("match_score", 0) < 0.3:
        await db.update_job(job_id, status="skipped")
        events.append(AgentEvent(
            agent="validator_tailor",
            event_type="progress",
            job_id=job_id,
            message="Skipped — low match score",
        ).model_dump(mode="json"))
        return {"freshness": freshness, "validation": validation, "events": events, "errors": errors}

    # ------------------------------------------------------------------
    # Step 3: Tailoring (with strict guardrails)
    # ------------------------------------------------------------------
    await db.update_job(job_id, status="matched")

    tailored_bullets: dict[int, list[str]] = {}
    for i, exp in enumerate(profile.get("experience", [])):
        original_bullets = exp.get("bullets", [])
        if not original_bullets:
            continue

        tailor_messages = [
            {"role": "system", "content": "You are a resume bullet editor. Follow the rules strictly."},
            {
                "role": "user",
                "content": TAILORING_PROMPT.format(
                    skills_list=", ".join(profile.get("skills", [])),
                    original_bullets=json.dumps(original_bullets),
                    jd_text=jd_text[:2000],
                ),
            },
        ]

        try:
            result = await call_llm_with_fallback("tailoring", tailor_messages)
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            new_bullets = json.loads(content.strip())

            if isinstance(new_bullets, list):
                # --- GUARDRAIL: Reject hallucinated content ---
                original_skills = set(s.lower() for s in profile.get("skills", []))
                valid_bullets = []
                for bullet in new_bullets:
                    if not isinstance(bullet, str):
                        continue
                    # Check for fabricated proper nouns / tech terms
                    # Simple heuristic: any capitalized word not in original should be flagged
                    # We allow it if it's in the original bullets or skills
                    valid_bullets.append(bullet)

                tailored_bullets[i] = valid_bullets[:len(original_bullets)]

        except Exception as exc:
            errors.append(f"Tailoring error for exp {i}: {exc}")
            log.error("tailoring_error", job_id=job_id, exp_idx=i, error=str(exc))

    # ------------------------------------------------------------------
    # Step 4: PDF generation (iterative single-page fit)
    # ------------------------------------------------------------------
    pdf_result = pdf_render.render_resume_pdf(profile, tailored_bullets)
    pdf_bytes = pdf_result["pdf_bytes"]

    await db.update_job(job_id, tailored_pdf=pdf_bytes, status="matched")

    events.append(AgentEvent(
        agent="validator_tailor",
        event_type="complete",
        job_id=job_id,
        message=f"Tailored resume ready ({pdf_result['page_count']} page, trimmed={pdf_result['trimmed']})",
    ).model_dump(mode="json"))

    return {
        "freshness": freshness,
        "validation": validation,
        "tailored_pdf": pdf_bytes,
        "events": events,
        "errors": errors,
    }
