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


def _render_html(profile: dict, tailored_bullets: dict | None = None) -> str:
    """Render the Jinja2 resume template to HTML string.

    Args:
        profile: CandidateProfile-compatible dict.
        tailored_bullets: Optional dict mapping experience index to new bullets list.
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
        summary=profile.get("summary", ""),
        experience=experience,
        skills_flat=skills_flat,
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

    # Count pages by looking for /Type /Page in the raw PDF
    # (Simple heuristic — xhtml2pdf doesn't expose page count directly)
    import re
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes))
    return pdf_bytes, max(page_count, 1)


def render_resume_pdf(
    profile: dict,
    tailored_bullets: dict | None = None,
    max_iterations: int = 5,
) -> dict:
    """Render a resume PDF with iterative single-page fitting.

    Strategy:
    1. Render full content → check page count.
    2. If > 1 page: trim bullets starting from last experience entry.
    3. Re-render until 1 page or max iterations reached.

    Returns: {"pdf_bytes": bytes, "page_count": int, "trimmed": bool}
    """
    html = _render_html(profile, tailored_bullets)
    pdf_bytes, page_count = _html_to_pdf(html)

    if page_count <= 1:
        log.info("pdf_rendered", pages=1, trimmed=False)
        return {"pdf_bytes": pdf_bytes, "page_count": 1, "trimmed": False}

    # --- Iterative trimming ---
    log.info("pdf_overflow", pages=page_count, starting_trim=True)

    experience = profile.get("experience", [])
    # Work with copies so we don't mutate original
    working_bullets: dict[int, list[str]] = {}
    for i, exp in enumerate(experience):
        bullets = list(exp.get("bullets", []))
        if tailored_bullets and i in tailored_bullets:
            bullets = list(tailored_bullets[i])
        working_bullets[i] = bullets

    trimmed = False
    for iteration in range(max_iterations):
        # Find the experience entry with the most bullets and trim one
        max_idx = -1
        max_count = 0
        for idx, bullets in working_bullets.items():
            if len(bullets) > max_count:
                max_count = len(bullets)
                max_idx = idx

        if max_idx < 0 or max_count <= 1:
            break  # Nothing left to trim

        # Remove the shortest (most generic) bullet
        bullets = working_bullets[max_idx]
        shortest_idx = min(range(len(bullets)), key=lambda j: len(bullets[j]))
        bullets.pop(shortest_idx)
        trimmed = True

        html = _render_html(profile, working_bullets)
        pdf_bytes, page_count = _html_to_pdf(html)

        if page_count <= 1:
            log.info("pdf_trimmed_to_fit", iterations=iteration + 1)
            return {"pdf_bytes": pdf_bytes, "page_count": 1, "trimmed": True}

    # Still overflowing — return best effort
    log.warning("pdf_still_overflow", pages=page_count, after_iterations=max_iterations)
    return {"pdf_bytes": pdf_bytes, "page_count": page_count, "trimmed": trimmed}
