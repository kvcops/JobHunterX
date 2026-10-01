"""
JobHunterX — PDF primitives (xhtml2pdf) and resume layout shrink profiles.

Document templates and rendering live in jobhunterx/generation/render.py.
"""

from __future__ import annotations

import io
import re

from jobhunterx.config.logging import get_logger

log = get_logger("pdf_render")


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
