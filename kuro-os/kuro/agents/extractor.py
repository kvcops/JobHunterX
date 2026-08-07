"""
Kuro OS ΓÇö Resume Extractor Agent

PyMuPDF text extraction ΓåÆ LLM structured parsing ΓåÆ CandidateProfile.
The extracted `skills` list is ground truth and never modified.
"""

from __future__ import annotations

import json
import re

from kuro.config.llm_router import call_llm_with_fallback
from kuro.config.logging import get_logger
from kuro.models import CandidateProfile

log = get_logger("extractor")

EXTRACTION_SYSTEM_PROMPT = """You are an expert resume parser. Extract structured information from the resume text and extracted links below.
Based on the candidate's skills and experience, also analyze their profile and suggest the most suitable job role or title (e.g. "Software Engineer", "Frontend Developer", "Data Scientist", "DevOps Engineer").

Return a JSON object with exactly these keys:
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+91-XXXXXXXXXX",
  "location": "City, Country",
  "present_address": "Full Present / Current Address",
  "permanent_address": "Full Permanent Address",
  "linkedin": "https://linkedin.com/in/...",
  "github": "https://github.com/...",
  "portfolio": "https://...",
  "summary": "Professional summary paragraph",
  "suggested_role": "Suggested job title that fits best",
  "relevant_experience": "Summarized total experience e.g. '3+ Years in AI/ML & Full Stack Development' or 'Fresh Graduate / Entry Level'",
  "languages": ["English", "Hindi", "Telugu"],
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "role": "Job Title",
      "company": "Company Name",
      "start": "Mon YYYY",
      "end": "Mon YYYY or Present",
      "bullets": ["Detailed achievement/contribution 1", "Detailed achievement/contribution 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree / Diploma Name",
      "institution": "University / College / School Name",
      "start": "YYYY",
      "end": "YYYY",
      "grade": "CGPA e.g. 8.9/10 or Percentage e.g. 92%",
      "details": "Major, Specialization, or Key Coursework"
    }
  ],
  "projects": [
    {
      "title": "Project Title",
      "description": "Short description of project",
      "url": "Project Link or Repo URL if present",
      "technologies": ["tech1", "tech2"]
    }
  ],
  "competitions": ["Competition or Hackathon 1", "Award 2"],
  "achievements": ["Key Achievement 1", "Certification 2"]
}

Rules:
- Extract ONLY what is explicitly written or present in the embedded links. Do NOT fabricate or hallucinate.
- Extract ALL education qualifications mentioned (Degrees, Diplomas, High School, Certifications) without missing any. Include CGPA/grades and details/coursework if mentioned.
- Extract ALL work experience and internship positions. Include ALL bullets/contributions/achievements listed for each role without dropping or summarizing them into single lines.
- Match project URLs, GitHub, and Portfolio URLs from the extracted embedded links section when applicable.
- For projects: Carefully identify all projects (personal, academic, professional, or open-source) listed in the resume. For each project, extract: the exact name/title as "title", a concise description as "description", the url as "url", and technologies used as a list.
- For suggested_role: Analyze the candidate's skills and past work roles, and output the single best target job title/role.
- For relevant_experience: Calculate/summarize the total years and domain experience from their past work and projects.
- For languages: List all natural spoken/written languages mentioned.
- For skills: List every technology, tool, programming language, and framework mentioned.
- Return valid JSON only. No markdown, no explanation."""


def _parse_json_object(content: str) -> dict:
    """Extract one complete JSON object from Gemma/Gemini text output."""
    text = content or ""
    text = text.replace("<|channel|>thought", "").replace("<|channel|>", "")
    text = re.sub(r"\x60{3}(?:json)?", "", text, flags=re.I)
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and ("name" in value or "skills" in value or "experience" in value):
            return value
    raise json.JSONDecodeError("No complete profile JSON object found", text, 0)


async def extract_text_and_links_from_pdf(pdf_bytes: bytes) -> tuple[str, list[str]]:
    """Extract raw text and embedded hyperlinked URIs from PDF bytes using PyMuPDF."""
    import asyncio

    def _extract():
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        extracted_links = []
        for page in doc:
            text = page.get_text(sort=True)
            pages_text.append(text)
            links = page.get_links()
            for link in links:
                uri = link.get("uri")
                if uri and uri not in extracted_links:
                    extracted_links.append(uri)
        doc.close()
        
        full_text = "\n\n".join(pages_text)
        if extracted_links:
            full_text += "\n\n--- Extracted Embedded Hyperlinks in PDF ---\n" + "\n".join(extracted_links)
        return full_text, extracted_links

    return await asyncio.to_thread(_extract)


async def extract_profile(pdf_bytes: bytes) -> CandidateProfile:
    """Extract a structured CandidateProfile from PDF bytes.

    Pipeline: PyMuPDF text & embedded link extraction ΓåÆ LLM structured parsing.
    Uses the 'extraction' fallback chain (gemma-4-31b preferred).
    """
    # Step 1: Extract raw text and embedded links
    raw_text, links = await extract_text_and_links_from_pdf(pdf_bytes)
    if not raw_text.strip():
        log.error("empty_pdf_text")
        return CandidateProfile()

    log.info("pdf_text_extracted", length=len(raw_text), links_count=len(links))

    # Step 2: LLM structured extraction
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": raw_text[:30000]},  # Up to 30k chars
    ]

    try:
        result = await call_llm_with_fallback(
            chain_name="extraction",
            messages=messages,
            use_cache=False,
            max_tokens=8192,
        )
        try:
            data = _parse_json_object(result["content"])
        except json.JSONDecodeError:
            log.warning("profile_json_retry", model=result.get("model", "unknown"))
            retry_messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT + "\nOutput only one complete JSON object. No reasoning, markdown, or commentary."},
                {"role": "user", "content": raw_text[:30000]},
            ]
            retry = await call_llm_with_fallback(
                chain_name="fast",
                messages=retry_messages,
                use_cache=False,
                max_tokens=8192,
            )
            data = _parse_json_object(retry["content"])

        # Defensive key normalization for projects to ensure Pydantic parsing succeeds without dropping data
        if isinstance(data, dict):
            if "projects" in data and isinstance(data["projects"], list):
                normalized_projects = []
                for proj in data["projects"]:
                    if isinstance(proj, dict):
                        title = proj.get("title") or proj.get("name") or proj.get("project_name") or ""
                        url = proj.get("url") or proj.get("link") or proj.get("github_url") or proj.get("project_url") or ""
                        desc = proj.get("description") or proj.get("details") or proj.get("body") or proj.get("summary") or ""
                        tech = proj.get("technologies") or proj.get("tech") or proj.get("tools") or proj.get("tech_stack") or []
                        if isinstance(tech, str):
                            tech = [t.strip() for t in tech.split(",") if t.strip()]
                        normalized_projects.append({
                            "title": title,
                            "url": url,
                            "description": desc,
                            "technologies": tech
                        })
                data["projects"] = normalized_projects

            # Defensive key normalization for education
            if "education" in data and isinstance(data["education"], list):
                normalized_edu = []
                for edu in data["education"]:
                    if isinstance(edu, dict):
                        degree = edu.get("degree") or edu.get("qualification") or edu.get("course") or ""
                        institution = edu.get("institution") or edu.get("university") or edu.get("school") or edu.get("college") or ""
                        start = edu.get("start") or edu.get("start_date") or ""
                        end = edu.get("end") or edu.get("end_date") or edu.get("year") or edu.get("years") or ""
                        grade = edu.get("grade") or edu.get("cgpa") or edu.get("marks") or edu.get("score") or edu.get("percentage") or ""
                        details = edu.get("details") or edu.get("description") or edu.get("major") or edu.get("field_of_study") or edu.get("coursework") or ""
                        normalized_edu.append({
                            "degree": str(degree),
                            "institution": str(institution),
                            "start": str(start),
                            "end": str(end),
                            "grade": str(grade),
                            "details": str(details)
                        })
                data["education"] = normalized_edu

            # Defensive key normalization for experience
            if "experience" in data and isinstance(data["experience"], list):
                normalized_exp = []
                for exp in data["experience"]:
                    if isinstance(exp, dict):
                        role = exp.get("role") or exp.get("title") or exp.get("position") or ""
                        company = exp.get("company") or exp.get("organization") or exp.get("employer") or ""
                        start = exp.get("start") or exp.get("start_date") or ""
                        end = exp.get("end") or exp.get("end_date") or ""
                        bullets_raw = exp.get("bullets") or exp.get("contributions") or exp.get("responsibilities") or exp.get("achievements") or exp.get("highlights") or exp.get("description") or []
                        if isinstance(bullets_raw, str):
                            bullets = [b.strip("-*ΓÇó ").strip() for b in bullets_raw.split("\n") if b.strip()]
                        elif isinstance(bullets_raw, list):
                            bullets = [str(b).strip("-*ΓÇó ").strip() for b in bullets_raw if str(b).strip()]
                        else:
                            bullets = []
                        normalized_exp.append({
                            "role": str(role),
                            "company": str(company),
                            "start": str(start),
                            "end": str(end),
                            "bullets": bullets
                        })
                data["experience"] = normalized_exp

        profile = CandidateProfile(**data)
        log.info(
            "profile_extracted",
            name=profile.name,
            skills_count=len(profile.skills),
            experience_count=len(profile.experience),
            projects_count=len(profile.projects),
        )
        return profile

    except Exception as exc:
        log.error("profile_extraction_failed", error=str(exc), exc_type=type(exc).__name__)
        return CandidateProfile()

