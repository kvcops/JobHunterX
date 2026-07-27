"""
Vellum OS — Resume Extractor Agent

PyMuPDF text extraction → LLM structured parsing → CandidateProfile.
The extracted `skills` list is ground truth and never modified.
"""

from __future__ import annotations

import json

from vellum.config.llm_router import call_llm_with_fallback
from vellum.config.logging import get_logger
from vellum.models import CandidateProfile

log = get_logger("extractor")

EXTRACTION_SYSTEM_PROMPT = """You are a resume parser. Extract structured information from the resume text below.
Return a JSON object with exactly these keys:
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+91-XXXXXXXXXX",
  "location": "City, Country",
  "linkedin": "linkedin.com/in/...",
  "summary": "Professional summary paragraph",
  "skills": ["skill1", "skill2", ...],
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
  ]
}

Rules:
- Extract ONLY what is explicitly written. Do NOT infer or add anything.
- For skills, list every technology, tool, language, and framework mentioned.
- Return valid JSON only. No markdown, no explanation."""


async def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF with sort=True for column-aware reading."""
    import asyncio

    def _extract():
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            text = page.get_text(sort=True)
            pages_text.append(text)
        doc.close()
        return "\n\n".join(pages_text)

    return await asyncio.to_thread(_extract)


async def extract_profile(pdf_bytes: bytes) -> CandidateProfile:
    """Extract a structured CandidateProfile from PDF bytes.

    Pipeline: PyMuPDF text extraction → LLM structured parsing.
    Uses the 'extraction' fallback chain (gemma-4-31b preferred).
    """
    # Step 1: Extract raw text
    raw_text = await extract_text_from_pdf(pdf_bytes)
    if not raw_text.strip():
        log.error("empty_pdf_text")
        return CandidateProfile()

    log.info("pdf_text_extracted", length=len(raw_text))

    # Step 2: LLM structured extraction
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": raw_text[:8000]},  # Limit to 8k chars
    ]

    try:
        result = await call_llm_with_fallback(
            chain_name="extraction",
            messages=messages,
            use_cache=False,  # Each resume is unique
        )
        content = result["content"]

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        profile = CandidateProfile(**data)
        log.info(
            "profile_extracted",
            name=profile.name,
            skills_count=len(profile.skills),
            experience_count=len(profile.experience),
        )
        return profile

    except (json.JSONDecodeError, Exception) as exc:
        log.error("profile_extraction_failed", error=str(exc))
        return CandidateProfile()
