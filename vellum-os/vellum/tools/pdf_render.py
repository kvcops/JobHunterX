"""
Vellum OS — PDF Render Tool (Jinja2 + xhtml2pdf)

Generates single-page ATS-safe resumes using pure Python.
Includes iterative length control to best-effort fit on one page.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from vellum.config.logging import get_logger

log = get_logger("pdf_render")

# Path to the Jinja2 resume template
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# ---------------------------------------------------------------------------
# Shrink profiles — each attempt reduces sizes/counts further
# ---------------------------------------------------------------------------

SHRINK_PROFILES = [
    {   # Attempt 0: Default generous layout
        "font_size_body": "8.8pt",
        "font_size_name": "18pt",
        "font_size_section": "9.2pt",
        "font_size_small": "8pt",
        "font_size_skill": "8.5pt",
        "font_size_bullet": "8.5pt",
        "margin_x": "10mm",
        "margin_y": "6mm",
        "margin_section": "5px",
        "margin_exp": "3px",
        "margin_bullet": "0.5px",
        "line_height": "1.28",
        "max_bullets_per_exp": 99,
        "max_projects": 99,
        "max_education": 99,
        "max_achievements": 99,
    },
    {   # Attempt 1: Slightly tighter
        "font_size_body": "8.2pt",
        "font_size_name": "16pt",
        "font_size_section": "8.8pt",
        "font_size_small": "7.5pt",
        "font_size_skill": "8.0pt",
        "font_size_bullet": "8.0pt",
        "margin_x": "8mm",
        "margin_y": "5mm",
        "margin_section": "4px",
        "margin_exp": "2px",
        "margin_bullet": "0.5px",
        "line_height": "1.24",
        "max_bullets_per_exp": 4,
        "max_projects": 99,
        "max_education": 99,
        "max_achievements": 99,
    },
    {   # Attempt 2: Compact
        "font_size_body": "7.8pt",
        "font_size_name": "14pt",
        "font_size_section": "8.2pt",
        "font_size_small": "7pt",
        "font_size_skill": "7.5pt",
        "font_size_bullet": "7.5pt",
        "margin_x": "7mm",
        "margin_y": "4mm",
        "margin_section": "3px",
        "margin_exp": "2px",
        "margin_bullet": "0.5px",
        "line_height": "1.20",
        "max_bullets_per_exp": 3,
        "max_projects": 99,
        "max_education": 99,
        "max_achievements": 99,
    },
    {   # Attempt 3: Ultra-compact — last resort
        "font_size_body": "7.5pt",
        "font_size_name": "13pt",
        "font_size_section": "7.8pt",
        "font_size_small": "6.8pt",
        "font_size_skill": "7.2pt",
        "font_size_bullet": "7.2pt",
        "margin_x": "6mm",
        "margin_y": "3mm",
        "margin_section": "2px",
        "margin_exp": "1px",
        "margin_bullet": "0.2px",
        "line_height": "1.16",
        "max_bullets_per_exp": 3,
        "max_projects": 99,
        "max_education": 99,
        "max_achievements": 99,
    },
]


def _render_html(
    profile: dict,
    tailored_bullets: dict | None = None,
    tailored_summary: str | None = None,
    categorized_skills: dict[str, list[str]] | None = None,
    shrink_profile: dict | None = None,
) -> str:
    """Render the Jinja2 resume template to HTML string.

    Args:
        profile: CandidateProfile-compatible dict.
        tailored_bullets: Optional dict mapping experience index to new bullets list.
        tailored_summary: Optional tailored executive summary.
        categorized_skills: Optional categorized skills dict.
        shrink_profile: Layout/sizing parameters for iterative shrink.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("resume.html")

    sp = shrink_profile or SHRINK_PROFILES[0]
    max_bullets = sp.get("max_bullets_per_exp", 99)

    # Build experience with optional tailored bullets
    experience = []
    for i, exp in enumerate(profile.get("experience", [])):
        bullets = exp.get("bullets", [])
        if tailored_bullets and i in tailored_bullets:
            bullets = tailored_bullets[i]
        # Trim bullets to shrink limit
        bullets = bullets[:max_bullets]
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
        # Shrink profile layout parameters
        **sp,
    )


def sanitize_html_for_pdf(html: str) -> str:
    """Replace non-ASCII unicode hyphens, quotes, and space characters 
    to prevent square boxes (tofu) in standard PDF Helvetica fonts.
    """
    # Hyphens and dashes
    html = html.replace("\u2011", "-")  # Non-breaking hyphen
    html = html.replace("\u2010", "-")  # Hyphen
    html = html.replace("\u2012", "-")  # Figure dash
    html = html.replace("\u2013", "-")  # En dash
    html = html.replace("\u2014", "-")  # Em dash
    html = html.replace("\u2015", "-")  # Horizontal bar
    html = html.replace("\u2212", "-")  # Minus sign

    # Smart quotes
    html = html.replace("\u201c", '"').replace("\u201d", '"')
    html = html.replace("\u2018", "'").replace("\u2019", "'")

    # Non-breaking spaces
    html = html.replace("\xa0", " ")

    # Special bullets
    html = html.replace("\u2022", "&bull;")

    return html


def _html_to_pdf(html: str) -> tuple[bytes, int]:
    """Convert HTML to PDF bytes using xhtml2pdf.

    Returns (pdf_bytes, page_count).
    """
    from xhtml2pdf import pisa

    # Clean unicode symbols that crash default Helvetica
    html = sanitize_html_for_pdf(html)

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        log.error("xhtml2pdf_error", error_count=pisa_status.err)

    pdf_bytes = buffer.getvalue()
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes))
    return pdf_bytes, max(page_count, 1)


def render_resume_pdf(
    profile: dict,
    tailored_bullets: dict | None = None,
    tailored_summary: str | None = None,
    categorized_skills: dict[str, list[str]] | None = None,
    max_iterations: int = 4,
) -> dict:
    """Render a resume PDF with executive ATS formatting.

    Uses an iterative shrink loop: tries progressively smaller fonts/margins
    until the resume fits on exactly 1 page.

    Returns: {"pdf_bytes": bytes, "page_count": int, "trimmed": bool, "shrink_level": int}
    """
    best_pdf = None
    best_pages = 999
    shrink_level = 0

    for attempt in range(min(max_iterations, len(SHRINK_PROFILES))):
        sp = SHRINK_PROFILES[attempt]
        html = _render_html(
            profile,
            tailored_bullets,
            tailored_summary,
            categorized_skills,
            shrink_profile=sp,
        )
        pdf_bytes, page_count = _html_to_pdf(html)

        log.info(
            "pdf_render_attempt",
            attempt=attempt,
            pages=page_count,
            font=sp["font_size_body"],
            margin=sp["margin_y"],
        )

        if page_count == 1:
            return {
                "pdf_bytes": pdf_bytes,
                "page_count": 1,
                "trimmed": attempt > 0,
                "shrink_level": attempt,
            }

        # Track the best (fewest pages) result so far
        if page_count < best_pages:
            best_pages = page_count
            best_pdf = pdf_bytes
            shrink_level = attempt

    # If we exhausted all shrink profiles and still > 1 page,
    # return the most compact version
    log.warning("pdf_still_multipage", pages=best_pages, shrink_level=shrink_level)
    return {
        "pdf_bytes": best_pdf or pdf_bytes,
        "page_count": best_pages,
        "trimmed": True,
        "shrink_level": shrink_level,
    }
