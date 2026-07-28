"""
Vellum OS — Validator & Tailor Agent (Agent C)

Per-job pipeline: freshness check → JD validation → Google XYZ bullet tailoring → PDF.
Generates high-impact ATS resumes adhering strictly to candidate ground truth.
"""

from __future__ import annotations

import json
import re

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.tools import scrape, pdf_render
from vellum.models import AgentEvent

log = get_logger("validator_tailor")

# ---------------------------------------------------------------------------
# Prompts — High-Impact ATS & Google XYZ Formula
# ---------------------------------------------------------------------------

VALIDATION_PROMPT = """You are a top-tier executive talent manager. Compare the candidate profile against the target job description.
Return a JSON object with this exact structure:
{{
  "match_score": 0.0-1.0,
  "matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "reasoning": "Detailed 2-sentence breakdown of alignment"
}}

Candidate Profile:
{profile_summary}

Job Description:
{jd_text}

Return valid JSON only. No markdown commentary."""

SUMMARY_TAILORING_PROMPT = """You are a world-class executive resume writer. Craft a high-impact, 2-3 sentence Professional Executive Summary for the candidate, tailored specifically to the target Job Description.

CRITICAL ATS & TRUTHFULNESS RULES:
1. Highlight the candidate's real technical background, core skills, and alignment with the target role ({target_role}).
2. Naturally integrate key requirements and domain keywords from the Target Job Description.
3. STRICT TRUTHFULNESS: Do NOT invent fake experience, unearned titles, or fake metric numbers not backed by candidate's profile.
4. Write in active, powerful third-person tone (no "I", "my", or "our").

Candidate Details:
Name: {name}
Target Role: {target_role}
Key Skills: {skills_list}
Original Summary: {original_summary}

Target Job Description:
{jd_text}

Return a JSON object:
{{
  "tailored_summary": "High-impact 2-3 sentence summary..."
}}
Return valid JSON only. No markdown."""

BULLET_TAILORING_PROMPT = """You are an elite ATS Resume Optimization Specialist using the Google XYZ Formula (Accomplished [X] as measured by [Y] by doing [Z]).
Transform the candidate's raw work experience bullet points into deeply detailed, high-impact, technical bullet points tailored to the target Job Description.

CRITICAL ATS & IMPACT RULES:
1. Use Google XYZ Formula: Start with a strong action verb, specify technical tools/methods [Z], state the outcome or engineering result [X/Y].
2. Keywords Integration: Seamlessly embed relevant technical terms and requirements from the Job Description that align with candidate's ground-truth skills ({skills_list}).
3. Technical Depth & Context: Do NOT make bullets artificially short or generic. Write rich, impactful 20-35 word bullet points.
4. STRICT TRUTHFULNESS: You MUST NOT invent fake companies, fake projects, or fake tools outside the candidate's real skill list. Preserve any real metrics from original bullets.
5. Order Preservation: Return a JSON array of strings — transformed bullets matching the exact count of original bullets.

Role: {role_title} at {company_name}
Original Bullets:
{original_bullets}

Target Job Description:
{jd_text}

Return a JSON array of strings only. Valid JSON, no markdown."""


def _categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    """Categorize candidate skills into logical ATS skill groups."""
    categories: dict[str, list[str]] = {
        "Languages": [],
        "Frameworks & AI": [],
        "Cloud & DevOps": [],
        "Databases & Tools": [],
        "Core Competencies": [],
    }
    
    lang_keywords = {"python", "javascript", "typescript", "c++", "c#", "java", "rust", "go", "sql", "html", "css", "bash", "r", "php", "ruby"}
    framework_keywords = {"react", "next.js", "vue", "angular", "node.js", "express", "fastapi", "django", "flask", "pytorch", "tensorflow", "langchain", "llama", "gemma", "gemini", "scikit-learn", "tailwind", "redux"}
    cloud_keywords = {"aws", "gcp", "azure", "docker", "kubernetes", "ci/cd", "github actions", "terraform", "ansible", "linux", "nginx"}
    db_keywords = {"postgresql", "mysql", "mongodb", "redis", "elasticsearch", "pinecone", "weaviate", "qdrant", "chroma", "sqlite", "git", "postman", "jira"}

    for skill in skills:
        s_lower = skill.lower().strip()
        if not s_lower:
            continue
        if any(k in s_lower for k in lang_keywords):
            categories["Languages"].append(skill)
        elif any(k in s_lower for k in framework_keywords):
            categories["Frameworks & AI"].append(skill)
        elif any(k in s_lower for k in cloud_keywords):
            categories["Cloud & DevOps"].append(skill)
        elif any(k in s_lower for k in db_keywords):
            categories["Databases & Tools"].append(skill)
        else:
            categories["Core Competencies"].append(skill)

    # Filter out empty categories
    return {k: v for k, v in categories.items() if v}


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
    target_role = job.get("role") or profile.get("suggested_role") or "Software Engineer"
    events: list[dict] = []
    errors: list[str] = []

    from vellum.api.ws import manager as ws_manager

    async def log_and_broadcast_event(event_type: str, message: str, confidence: float = 0.0, data: dict = None):
        evt = AgentEvent(
            agent="validator_tailor",
            event_type=event_type,
            job_id=job_id,
            message=message,
            confidence=confidence,
            data=data
        ).model_dump(mode="json")
        events.append(evt)
        await ws_manager.broadcast(evt)

    await log_and_broadcast_event(
        "progress",
        f"Validating: {job.get('company', '')} — {job.get('role', '')}"
    )

    # ------------------------------------------------------------------
    # Step 1: Freshness check (best-effort)
    # ------------------------------------------------------------------
    freshness = {"is_fresh": None, "confidence": 0.0, "evidence": "unknown", "detected_date": None}
    jd_text = job.get("jd_text", "")

    if not jd_text and job.get("apply_url"):
        page = await scrape.fetch_page(job["apply_url"])
        html = page.get("html", "")
        headers = page.get("headers", {})
        if html:
            jd_text = await scrape.extract_jd_text(html)
            freshness = await scrape.extract_job_freshness(html, headers)
    elif jd_text:
        if job.get("career_page_url"):
            page = await scrape.fetch_page(job["career_page_url"])
            freshness = await scrape.extract_job_freshness(
                page.get("html", ""), page.get("headers", {})
            )

    freshness_json = json.dumps(freshness)
    await db.update_job(job_id, freshness_json=freshness_json, jd_text=jd_text)

    if freshness.get("is_fresh") is False and freshness.get("confidence", 0) >= 0.7:
        await db.update_job(job_id, status="skipped")
        await log_and_broadcast_event(
            "progress",
            f"Skipped — confirmed stale ({freshness.get('evidence')})",
            confidence=freshness.get("confidence")
        )
        return {"freshness": freshness, "events": events, "errors": errors}

    if not jd_text:
        await db.update_job(job_id, status="skipped")
        await log_and_broadcast_event(
            "progress",
            "Skipped — no JD text extracted"
        )
        return {"freshness": freshness, "events": events, "errors": errors}

    # ------------------------------------------------------------------
    # Step 2: Validation (match score)
    # ------------------------------------------------------------------
    await db.update_job(job_id, status="validating")

    # Generate full rich candidate profile context memory
    exp_details = []
    for exp in profile.get("experience", []):
        bullets_str = "\n  * ".join(exp.get("bullets", []))
        exp_details.append(
            f"- {exp.get('role')} at {exp.get('company')} ({exp.get('start')} - {exp.get('end')}):\n  * {bullets_str}"
        )
    edu_details = []
    for edu in profile.get("education", []):
        edu_details.append(
            f"- {edu.get('degree')} from {edu.get('institution')} ({edu.get('start')} - {edu.get('end')})"
        )

    profile_summary = f"""Name: {profile.get('name', '')}
Email: {profile.get('email', '')}
Phone: {profile.get('phone', '')}
Location: {profile.get('location', '')}
Present Address: {profile.get('present_address', '')}
Permanent Address: {profile.get('permanent_address', '')}
Suggested Role: {profile.get('suggested_role', '')}
Relevant Experience Level: {profile.get('relevant_experience', '')}
Languages: {', '.join(profile.get('languages', [])) if isinstance(profile.get('languages'), list) else profile.get('languages', '')}
Skills: {', '.join(profile.get('skills', []))}
Professional Summary: {profile.get('summary', '')}

Detailed Work Experience:
{chr(10).join(exp_details)}

Education:
{chr(10).join(edu_details)}"""

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

    await log_and_broadcast_event(
        "progress",
        f"Match score: {validation.get('match_score', 0):.0%}",
        confidence=validation.get("confidence"),
        data=validation
    )

    if validation.get("match_score", 0) < 0.3:
        await db.update_job(job_id, status="skipped")
        await log_and_broadcast_event(
            "progress",
            "Skipped — low match score"
        )
        return {"freshness": freshness, "validation": validation, "events": events, "errors": errors}

    # ------------------------------------------------------------------
    # Step 3: High-Impact Tailoring (Summary + Google XYZ Bullets)
    # ------------------------------------------------------------------
    await db.update_job(job_id, status="matched")

    # A) Tailored Executive Summary
    tailored_summary = profile.get("summary", "")
    try:
        sum_messages = [
            {"role": "system", "content": "You are a professional resume strategist."},
            {
                "role": "user",
                "content": SUMMARY_TAILORING_PROMPT.format(
                    name=profile.get("name", "Candidate"),
                    target_role=target_role,
                    skills_list=", ".join(profile.get("skills", [])),
                    original_summary=profile.get("summary", ""),
                    jd_text=jd_text[:2500],
                ),
            },
        ]
        sum_res = await call_llm_with_fallback("tailoring", sum_messages)
        sum_content = sum_res["content"]
        if "```json" in sum_content:
            sum_content = sum_content.split("```json")[1].split("```")[0]
        elif "```" in sum_content:
            sum_content = sum_content.split("```")[1].split("```")[0]
        sum_data = json.loads(sum_content.strip())
        if isinstance(sum_data, dict) and sum_data.get("tailored_summary"):
            tailored_summary = sum_data["tailored_summary"]
    except Exception as exc:
        log.warning("summary_tailor_failed", error=str(exc))

    # B) Tailored Experience Bullets (Google XYZ Formula)
    tailored_bullets: dict[int, list[str]] = {}
    for i, exp in enumerate(profile.get("experience", [])):
        original_bullets = exp.get("bullets", [])
        if not original_bullets:
            continue

        tailor_messages = [
            {"role": "system", "content": "You are an elite ATS Resume Optimization Specialist."},
            {
                "role": "user",
                "content": BULLET_TAILORING_PROMPT.format(
                    role_title=exp.get("role", "Engineer"),
                    company_name=exp.get("company", "Company"),
                    skills_list=", ".join(profile.get("skills", [])),
                    original_bullets=json.dumps(original_bullets),
                    jd_text=jd_text[:2500],
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
                valid_bullets = [b for b in new_bullets if isinstance(b, str) and len(b) > 10]
                tailored_bullets[i] = valid_bullets[:len(original_bullets)]

        except Exception as exc:
            errors.append(f"Tailoring error for exp {i}: {exc}")
            log.error("tailoring_error", job_id=job_id, exp_idx=i, error=str(exc))

    # Categorize skills for resume template
    categorized_skills = _categorize_skills(profile.get("skills", []))

    # ------------------------------------------------------------------
    # Step 4: PDF generation (high-impact template)
    # ------------------------------------------------------------------
    pdf_result = pdf_render.render_resume_pdf(
        profile,
        tailored_bullets=tailored_bullets,
        tailored_summary=tailored_summary,
        categorized_skills=categorized_skills,
    )
    pdf_bytes = pdf_result["pdf_bytes"]

    await db.update_job(job_id, tailored_pdf=pdf_bytes, status="matched")

    await log_and_broadcast_event(
        "complete",
        f"High-impact tailored ATS resume ready ({pdf_result['page_count']} page)"
    )

    return {
        "freshness": freshness,
        "validation": validation,
        "tailored_pdf": pdf_bytes,
        "events": events,
        "errors": errors,
    }

