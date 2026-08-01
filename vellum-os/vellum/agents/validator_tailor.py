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
from vellum.utils.json_helper import parse_llm_json

log = get_logger("validator_tailor")

# ---------------------------------------------------------------------------
# Prompts — High-Impact ATS & Google XYZ Formula
# ---------------------------------------------------------------------------

VALIDATION_PROMPT = """You are a top-tier executive talent manager. Compare the candidate profile against the target job description.

CRITICAL MATCHING RULES (enforce strictly):
1. **Company & Role**: Extract the exact clean Company Name and Job Title / Role from the JD.
2. **Location Match**: The candidate targets "{target_location}". If the job is strictly onsite/hybrid in a DIFFERENT city (not remote-eligible), set match_score below 0.25.
3. **Experience Match**: Candidate experience is "{candidate_experience}". Extract required experience from JD and compare strictly. If candidate exp varies significantly from JD required exp, detail the exact variance.
4. **Skills Match**: Evaluate overlap between candidate skills and JD requirements. List matching skills and missing required skills explicitly.
5. **Salary/CTC Match**: Expected CTC is "{expected_ctc}". Only penalize if JD explicitly specifies a salary below expected CTC.

Return a valid JSON object only with this exact structure:
{{
  "company_name": "Clean Company Name",
  "job_role": "Clean Job Title",
  "match_score": 0.0-1.0,
  "matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "required_experience": "e.g. 5+ years",
  "candidate_experience": "{candidate_experience}",
  "experience_variance": "Candidate: X yrs vs Required: Y yrs (Gap: Z yrs)",
  "location_match": true,
  "experience_match": true,
  "reasoning": "Detailed 2-sentence explanation of alignment and where candidate vs job requirements vary."
}}

Candidate Profile:
{profile_summary}

Job Description:
{jd_text}

Return valid JSON object only. Do NOT include unescaped quotes or line breaks inside string values."""

SUMMARY_TAILORING_PROMPT = """You are a world-class executive resume writer. Craft a high-impact, 2-3 sentence Professional Executive Summary for the candidate, tailored specifically to the target Job Description.

CRITICAL ATS & TRUTHFULNESS RULES:
1. Highlight the candidate's real technical background, core skills, and alignment with the target role ({target_role}).
2. Naturally integrate key requirements and domain keywords from the Target Job Description.
3. STRICT TRUTHFULNESS: Do NOT invent fake experience, unearned titles, or fake metric numbers not backed by candidate's profile.
4. ABSOLUTELY DO NOT add any technologies, tools, frameworks, or programming languages that are NOT in the candidate's skill list below. If the JD mentions a skill the candidate doesn't have, DO NOT add it.
5. Write in active, powerful third-person tone (no "I", "my", or "our").
6. ABSOLUTELY FORBIDDEN: Do NOT include candidate's Current CTC, Expected CTC, or any salary/compensation details in the professional executive summary.

Candidate Details:
Name: {name}
Target Role: {target_role}
Key Skills (ONLY use these): {skills_list}
Original Summary: {original_summary}

Target Job Description:
{jd_text}

Return a JSON object:
{{
  "tailored_summary": "High-impact 2-3 sentence summary..."
}}
Return valid JSON only. No markdown."""

BULLET_TAILORING_PROMPT = """You are an elite ATS Resume Optimization Specialist. Rewrite the candidate's raw work experience bullet points into high-impact, technical bullet points tailored to the target Job Description.

CRITICAL ATS & IMPACT RULES:
1. Action-led bullets: Start with a strong action verb (Built, Designed, Led, Optimized, Automated, Architected, etc.), specify the technical tools/methods used, and describe the engineering outcome.
2. Keywords Integration: Seamlessly embed relevant technical terms from the Job Description ONLY IF they exist in the candidate's real skill list ({skills_list}). DO NOT invent or add technologies the candidate doesn't know.
3. Technical Depth & Context: Do NOT make bullets artificially short or generic. Write rich, impactful 20-35 word bullet points.
4. STRICT TRUTHFULNESS — NO FABRICATED METRICS: You MUST NOT invent numbers, percentages, counts, revenue, users, or time savings. Never write "X%", "Y%", "increased X", "reduced Y by Z", "X+ users", or any placeholder letters as metrics. If the original bullet contains a REAL metric, preserve it exactly. If it has no metric, describe the work and impact qualitatively ("delivered", "enabled", "streamlined") without making up quantities.
5. ABSOLUTELY FORBIDDEN: Adding any technology, framework, tool, or programming language not explicitly in the candidate's skill list above. If the JD mentions React but candidate doesn't know React, do NOT mention React.
6. Order Preservation: Return a JSON array of strings — transformed bullets matching the exact count of original bullets.
7. ABSOLUTELY FORBIDDEN: Do NOT include candidate's Current CTC, Expected CTC, or any salary/compensation details in any of the bullet points.
8. FORBIDDEN OUTPUT: Never output the literal tokens "[X]", "[Y]", "[Z]", "X%", "Y%", "by doing Z", "measured by Y", "Accomplished X". Every bullet must read as a truthful, complete sentence with zero placeholder characters.

Role: {role_title} at {company_name}
Original Bullets:
{original_bullets}

Candidate's REAL Skill List (ONLY use these): {skills_list}

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


def _sanitize_tailored_text(text: str, allowed_skills: list[str]) -> str:
    """Post-tailoring sanitizer: check for hallucinated technologies.

    This is a best-effort filter. It scans the text for common technology
    names that do NOT appear in the candidate's real skill list and replaces
    them with a safer generic term.
    """
    if not allowed_skills:
        return text

    # Build set of known candidate skills (lowercased for matching)
    known_lower = {s.lower().strip() for s in allowed_skills if s}

    # Common technology names that might be hallucinated
    # We only flag multi-character tech names that are unambiguous
    common_techs = [
        "React", "Angular", "Vue.js", "Vue", "Svelte", "Next.js", "Nuxt",
        "Django", "Flask", "FastAPI", "Spring", "Express", "Rails",
        "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
        "AWS", "GCP", "Azure", "Docker", "Kubernetes",
        "MongoDB", "PostgreSQL", "MySQL", "Redis", "Elasticsearch",
        "GraphQL", "gRPC", "Kafka", "RabbitMQ", "Terraform",
        "TypeScript", "Rust", "Go", "Kotlin", "Swift", "Scala",
        "Node.js", "Ruby", "PHP", "C#", "C++",
    ]

    sanitized = text
    for tech in common_techs:
        tech_lower = tech.lower()
        # Check if this tech is in the candidate's skills
        is_known = any(tech_lower in sk for sk in known_lower)
        if is_known:
            continue
        # If not known but appears in text, log a warning but don't break
        # the text — just log for observability
        if tech.lower() in sanitized.lower():
            log.warning("hallucinated_tech_detected", tech=tech, text_snippet=sanitized[:100])

    return sanitized


_PLACEHOLDER_METRIC_RE = re.compile(
    r"(?i)(\[[XYZ]\])|"
    r"(\b[XYZ][%]\b)|"
    r"(measured by [XYZ])|"
    r"(by doing [XYZ])|"
    r"(Accomplished [XYZ])|"
    r"(increased [XYZ][%]?)|"
    r"(reduced [XYZ][%]? by [XYZ][%]?)|"
    r"(improved [XYZ][%]?)"
)


def _sanitize_metric_placeholders(text: str) -> str:
    """Strip Google-XYZ placeholder artifacts that some LLMs emit as
    literal 'X%' / '[Y]' tokens instead of real metrics."""
    cleaned = _PLACEHOLDER_METRIC_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).replace(" .", ".").strip(" ,;")
    return cleaned


def _has_placeholder_artifact(text: str) -> bool:
    """True if a bullet still contains literal XYZ placeholder tokens."""
    return bool(
        re.search(r"\[[XYZ]\]", text, re.I)
        or re.search(r"(?<![A-Za-z])[XYZ](?=%|\b)", text)
    )


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

    async def _broadcast_job_status(status: str):
        evt = AgentEvent(
            agent="validator_tailor",
            event_type="job_status_changed",
            job_id=job_id,
            data={"status": status},
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
        await _broadcast_job_status("skipped")
        await log_and_broadcast_event(
            "progress",
            f"Skipped — confirmed stale ({freshness.get('evidence')})",
            confidence=freshness.get("confidence")
        )
        return {"freshness": freshness, "events": events, "errors": errors}

    if not jd_text:
        await db.update_job(job_id, status="skipped")
        await _broadcast_job_status("skipped")
        await log_and_broadcast_event(
            "progress",
            "Skipped — no JD text extracted"
        )
        return {"freshness": freshness, "events": events, "errors": errors}

    # ------------------------------------------------------------------
    # Step 2: Validation (match score) with location + experience rules
    # ------------------------------------------------------------------
    await db.update_job(job_id, status="validating")
    await _broadcast_job_status("validating")

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

    # Determine target location from job's search context or profile
    target_location = job.get("search_location", "") or profile.get("location", "")
    candidate_experience = profile.get("relevant_experience", "N/A")

    qa_memory = profile.get("qa_memory", {})
    current_ctc = qa_memory.get("current_ctc") or "Not specified"
    expected_ctc = qa_memory.get("expected_ctc") or qa_memory.get("expected_salary") or "Not specified"

    profile_summary = f"""Name: {profile.get('name', '')}
Email: {profile.get('email', '')}
Phone: {profile.get('phone', '')}
Location: {profile.get('location', '')}
Present Address: {profile.get('present_address', '')}
Permanent Address: {profile.get('permanent_address', '')}
Suggested Role: {profile.get('suggested_role', '')}
Relevant Experience Level: {candidate_experience}
Languages: {', '.join(profile.get('languages', [])) if isinstance(profile.get('languages'), list) else profile.get('languages', '')}
Skills: {', '.join(profile.get('skills', []))}
Professional Summary: {profile.get('summary', '')}
Current CTC: {current_ctc}
Expected CTC: {expected_ctc}

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
                target_location=target_location,
                candidate_experience=candidate_experience,
                current_ctc=current_ctc,
                expected_ctc=expected_ctc,
            ),
        },
    ]

    validation = {"match_score": 0.0, "matching_skills": [], "missing_skills": [], "reasoning": "", "confidence": 0.0}

    try:
        result = await call_llm_with_fallback("reasoning", validation_messages)
        parsed = parse_llm_json(result.get("content", ""))
        if isinstance(parsed, dict):
            validation = parsed
        validation["confidence"] = min(1.0, validation.get("match_score", 0.0) + 0.2)
    except Exception as exc:
        errors.append(f"Validation error: {exc}")
        log.error("validation_error", job_id=job_id, error=str(exc))

    update_fields = {
        "validation_json": json.dumps(validation),
        "match_score": validation.get("match_score", 0.0),
    }
    invalid_companies = {"clean company name", "not specified", "unknown", "n/a", "tech company", "hiring company", "company name", "none"}
    extracted_co = validation.get("company_name", "").strip()
    if extracted_co and extracted_co.lower() not in invalid_companies and len(extracted_co) > 1:
        update_fields["company"] = extracted_co
        
    invalid_roles = {"clean job title", "not specified", "unknown", "n/a", "job title", "software engineer", "role", "none"}
    extracted_role = validation.get("job_role", "").strip()
    if extracted_role and extracted_role.lower() not in invalid_roles and len(extracted_role) > 1:
        update_fields["role"] = extracted_role

    await db.update_job(job_id, **update_fields)

    await log_and_broadcast_event(
        "progress",
        f"Match score: {validation.get('match_score', 0):.0%}",
        confidence=validation.get("confidence"),
        data=validation
    )

    is_force_apply = state.get("force_apply", False)
    if validation.get("match_score", 0) < 0.3 and not is_force_apply:
        await db.update_job(job_id, status="skipped")
        await _broadcast_job_status("skipped")
        await log_and_broadcast_event(
            "progress",
            "Skipped — low match score"
        )
        return {"freshness": freshness, "validation": validation, "events": events, "errors": errors}

    job_status = "matched" if validation.get("match_score", 0) >= 0.3 else "force_applied"

    # ------------------------------------------------------------------
    # Step 3: High-Impact Tailoring (Summary + Google XYZ Bullets)
    # ------------------------------------------------------------------
    await db.update_job(job_id, status=job_status)
    await _broadcast_job_status(job_status)

    candidate_skills = profile.get("skills", [])
    skills_list_str = ", ".join(candidate_skills)

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
                    skills_list=skills_list_str,
                    original_summary=profile.get("summary", ""),
                    jd_text=jd_text[:2500],
                ),
            },
        ]
        sum_res = await call_llm_with_fallback("tailoring", sum_messages)
        sum_data = parse_llm_json(sum_res.get("content", ""))
        if isinstance(sum_data, dict) and sum_data.get("tailored_summary"):
            tailored_summary = sum_data["tailored_summary"]
            # Sanitize
            tailored_summary = _sanitize_tailored_text(tailored_summary, candidate_skills)
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
                    skills_list=skills_list_str,
                    original_bullets=json.dumps(original_bullets),
                    jd_text=jd_text[:2500],
                ),
            },
        ]

        try:
            result = await call_llm_with_fallback("tailoring", tailor_messages)
            new_bullets = parse_llm_json(result.get("content", ""))

            if isinstance(new_bullets, list):
                valid_bullets = []
                for b in new_bullets:
                    if isinstance(b, str) and len(b) > 10:
                        # Sanitize each bullet: strip hallucinated tech names
                        b = _sanitize_tailored_text(b, candidate_skills)
                        # Strip XYZ placeholder-metric artifacts
                        b = _sanitize_metric_placeholders(b)
                        # Hard safety: drop bullets that still contain placeholders
                        if _has_placeholder_artifact(b):
                            log.warning(
                                "bullet_placeholder_dropped",
                                job_id=job_id,
                                bullet=b[:80],
                            )
                            continue
                        valid_bullets.append(b)
                tailored_bullets[i] = valid_bullets[:len(original_bullets)]

        except Exception as exc:
            errors.append(f"Tailoring error for exp {i}: {exc}")
            log.error("tailoring_error", job_id=job_id, exp_idx=i, error=str(exc))

    # Categorize skills for resume template
    categorized_skills = _categorize_skills(profile.get("skills", []))

    # ------------------------------------------------------------------
    # Step 4: PDF generation (high-impact template with shrink loop)
    # ------------------------------------------------------------------
    pdf_result = pdf_render.render_resume_pdf(
        profile,
        tailored_bullets=tailored_bullets,
        tailored_summary=tailored_summary,
        categorized_skills=categorized_skills,
    )
    pdf_bytes = pdf_result["pdf_bytes"]

    await db.update_job(job_id, tailored_pdf=pdf_bytes, status=job_status)

    shrink_info = f" (shrink level {pdf_result.get('shrink_level', 0)})" if pdf_result.get("trimmed") else ""
    await log_and_broadcast_event(
        "complete",
        f"High-impact tailored ATS resume ready ({pdf_result['page_count']} page{shrink_info})"
    )

    return {
        "freshness": freshness,
        "validation": validation,
        "tailored_pdf": pdf_bytes,
        "events": events,
        "errors": errors,
    }
