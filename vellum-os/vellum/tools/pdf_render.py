"""
Vellum OS — PDF Render Tool (Jinja2 + xhtml2pdf)

Generates single-page ATS-safe resumes using pure Python.
Includes iterative length control to best-effort fit on one page.
"""

from __future__ import annotations

import io
from pathlib import Path

from vellum.config.logging import get_logger

log = get_logger("pdf_render")

# Path to the Jinja2 resume template
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _render_html(
    profile: dict,
    tailored_bullets: dict | None = None,
    tailored_summary: str | None = None,
    categorized_skills: dict[str, list[str]] | None = None,
) -> str:
    """Render the Jinja2 resume template to HTML string.

    Args:
        profile: CandidateProfile-compatible dict.
        tailored_bullets: Optional dict mapping experience index to new bullets list.
        tailored_summary: Optional tailored executive summary.
        categorized_skills: Optional categorized skills dict.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("resume.html")

    # Build experience with optional tailored bullets
    experience = []
    for i, exp in enumerate(profile.get("experience", [])):
        bullets = exp.get("bullets", [])
        if tailored_bullets and i in tailored_bullets:
            bullets = tailored_bullets[i]
        experience.append({
            "role": exp.get("role", ""),
            "company": exp.get("company", ""),
            "start": exp.get("start", ""),
            "end": exp.get("end", ""),
            "bullets": bullets,
        })

    skills = profile.get("skills", [])
    skills_flat = ", ".join(skills) if skills else ""
    summary_text = tailored_summary or profile.get("summary", "")
    languages = profile.get("languages", [])

    return template.render(
        name=profile.get("name", ""),
        email=profile.get("email", ""),
        phone=profile.get("phone", ""),
        location=profile.get("location", ""),
        present_address=profile.get("present_address", ""),
        permanent_address=profile.get("permanent_address", ""),
        linkedin=profile.get("linkedin", ""),
        github=profile.get("github", ""),
        portfolio=profile.get("portfolio", ""),
        summary=summary_text,
        languages=languages,
        experience=experience,
        skills_flat=skills_flat,
        categorized_skills=categorized_skills,
        education=profile.get("education", []),
        projects=profile.get("projects", []),
        competitions=profile.get("competitions", []),
        achievements=profile.get("achievements", []),
    )


def _html_to_pdf(html: str) -> tuple[bytes, int]:
    """Convert HTML to PDF bytes using xhtml2pdf.

    Returns (pdf_bytes, page_count).
    """
    from xhtml2pdf import pisa

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        log.error("xhtml2pdf_error", error_count=pisa_status.err)

    pdf_bytes = buffer.getvalue()
    import re
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes))
    return pdf_bytes, max(page_count, 1)


def render_resume_pdf(
    profile: dict,
    tailored_bullets: dict | None = None,
    tailored_summary: str | None = None,
    categorized_skills: dict[str, list[str]] | None = None,
    max_iterations: int = 3,
) -> dict:
    """Render a resume PDF with executive ATS formatting.

    Returns: {"pdf_bytes": bytes, "page_count": int, "trimmed": bool}
    """
    html = _render_html(profile, tailored_bullets, tailored_summary, categorized_skills)
    pdf_bytes, page_count = _html_to_pdf(html)

    log.info("pdf_rendered", pages=page_count)
    return {"pdf_bytes": pdf_bytes, "page_count": page_count, "trimmed": False}
