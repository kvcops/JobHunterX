"""
Resume extraction: PDF → CandidateProfile.

PyMuPDF reads text and embedded links; the LLM maps it onto the
CandidateProfile schema (validated by pydantic, one repair attempt). The
resume text is fenced as untrusted data. Extracted URLs are only accepted if
they appear in the PDF text or link annotations.
"""

from __future__ import annotations

import asyncio
import re

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.intelligence.llm_structured import call_structured, fence

log = get_logger("extractor")

VERSION = "profile-extract-v1"

_SYSTEM = """You convert a resume into a structured candidate profile.
Extract ONLY what is written in the resume. Never invent or infer employers, dates, skills, metrics or links.
- experience: every job/internship with all of its bullets verbatim (light whitespace cleanup only);
  employment_type is "internship" for internships/trainee roles, otherwise "full_time", "part_time", "contract" or "freelance" if stated, else "".
- education: every degree/diploma/school with grade and details if present.
- projects: every project with its technologies and link if present.
- skills: every technology, tool, language, framework and method named anywhere in the resume, as written.
- certifications, achievements, competitions, languages (spoken languages) as lists.
- suggested_role: the single job title that best describes the candidate today.
- relevant_experience: a short phrase describing their experience as stated (e.g. "1.5 years in ML engineering").
- Leave qa_memory and preferences empty."""


async def extract_text_and_links_from_pdf(pdf_bytes: bytes) -> tuple[str, list[str]]:
    def _extract():
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            texts, links = [], []
            for page in doc:
                texts.append(page.get_text(sort=True))
                for link in page.get_links():
                    uri = link.get("uri")
                    if uri and uri not in links:
                        links.append(uri)
            return "\n\n".join(texts), links
        finally:
            doc.close()

    return await asyncio.to_thread(_extract)


def _keep_known_urls(profile: CandidateProfile, text: str, links: list[str]) -> CandidateProfile:
    allowed = " ".join(links) + " " + text

    def ok(url: str) -> str:
        url = (url or "").strip()
        if not url:
            return ""
        core = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
        return url if core and core.lower() in allowed.lower() else ""

    profile.linkedin, profile.github, profile.portfolio = ok(profile.linkedin), ok(profile.github), ok(profile.portfolio)
    for p in profile.projects:
        p.url = ok(p.url)
    return profile


async def extract_profile(pdf_bytes: bytes) -> tuple[CandidateProfile, dict]:
    """Return (profile, extraction_info) — info: {status: ok|partial|failed, warnings: [...]}."""
    text, links = await extract_text_and_links_from_pdf(pdf_bytes)
    if not text.strip():
        return CandidateProfile(), {"status": "failed", "warnings": ["No text found in the PDF (is it a scanned image?)."]}
    user = "Resume text:\n" + fence(text, 30000) + ("\n\nEmbedded links:\n" + fence("\n".join(links), 3000) if links else "")
    profile, model = await call_structured(task="profile_extract", version=VERSION, model=CandidateProfile,
                                           system=_SYSTEM, user=user, chain="extraction", max_tokens=8192,
                                           cache_parts=(text, "|".join(links)))
    if profile is None:
        return CandidateProfile(), {"status": "failed",
                                    "warnings": ["The AI could not read this resume right now. Please try again or fill in your profile manually."]}
    profile = _keep_known_urls(profile, text, links)
    warnings = []
    if not profile.experience and not profile.projects:
        warnings.append("No experience or projects were found — please check your profile.")
    if not profile.skills:
        warnings.append("No skills were found — please add them.")
    log.info("profile_extracted", model=model, skills=len(profile.skills), experience=len(profile.experience))
    return profile, {"status": "partial" if warnings else "ok", "warnings": warnings}
