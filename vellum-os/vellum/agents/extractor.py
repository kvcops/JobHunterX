"""
Vellum OS — Resume Extractor Agent

PyMuPDF text extraction → LLM structured parsing → CandidateProfile.
The extracted `skills` list is ground truth and never modified.
"""

from __future__ import annotations

import json
import re

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.models import CandidateProfile

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
      "bullets": ["Achievement 1", "Achievement 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree Name",
      "institution": "University Name",
      "start": "YYYY",
      "end": "YYYY"
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
- Match project URLs, GitHub, and Portfolio URLs from the extracted embedded links section when applicable.
- For suggested_role: Analyze the candidate's skills and past work roles, and output the single best target job title/role.
- For relevant_experience: Calculate/summarize the total years and domain experience from their past work and projects (e.g. "2+ Years in Software Engineering").
- For languages: List all natural spoken/written languages mentioned (e.g. English, Telugu, Hindi, French).
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

    Pipeline: PyMuPDF text & embedded link extraction → LLM structured parsing.
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


        profile = CandidateProfile(**data)
        log.info(
            "profile_extracted",
            name=profile.name,
            skills_count=len(profile.skills),
            experience_count=len(profile.experience),
            projects_count=len(profile.projects),
        )
        return profile

    except (json.JSONDecodeError, Exception) as exc:
        log.error("profile_extraction_failed", error=str(exc))
        return CandidateProfile()

