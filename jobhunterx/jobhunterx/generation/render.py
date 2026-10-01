"""Render document content to PDF (Jinja2 with autoescaping → xhtml2pdf)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from jobhunterx.config.logging import get_logger
from jobhunterx.tools.pdf_render import SHRINK_PROFILES, _html_to_pdf

log = get_logger("render")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Extra compaction steps for a one-page resume, applied after font shrinking:
# fewer bullets per role and fewer projects (lowest-relevance items are last).
_TRIM_STEPS = [
    {"max_bullets_per_exp": 3, "max_projects": 2, "max_achievements": 2},
    {"max_bullets_per_exp": 2, "max_projects": 2, "max_achievements": 1},
    {"max_bullets_per_exp": 2, "max_projects": 1, "max_achievements": 0},
]

_CV_LAYOUT = {**SHRINK_PROFILES[0], "font_size_body": "9.5pt", "font_size_bullet": "9.3pt", "font_size_name": "20pt",
              "font_size_section": "10.5pt", "margin_x": "16mm", "margin_y": "14mm", "line_height": "1.35",
              "margin_exp": "6px", "margin_bullet": "1.5px"}


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)),
                       autoescape=select_autoescape(["html", "j2"]))


def _render(template: str, **ctx) -> str:
    return _env().get_template(template).render(**ctx)


def _fit_one_page(template: str, content: dict, steps: list[dict], kind: str) -> tuple[bytes, int]:
    """Try each layout until the document fits on one page; otherwise keep the shortest result."""
    best: tuple[bytes, int] | None = None
    for sp in steps:
        pdf, pages = _html_to_pdf(_render(template, doc=content, **sp))
        if pages == 1:
            return pdf, 1
        if best is None or pages < best[1]:
            best = (pdf, pages)
    log.warning(f"{kind}_multi_page", pages=best[1] if best else 0)
    return best  # type: ignore[return-value]


def render_resume(content: dict) -> tuple[bytes, int]:
    """One page: shrink typography first, then trim lowest-relevance items."""
    steps = [dict(sp) for sp in SHRINK_PROFILES] + [{**SHRINK_PROFILES[-1], **t} for t in _TRIM_STEPS]
    return _fit_one_page("resume.html", content, steps, "resume")


def render_cv(content: dict) -> tuple[bytes, int]:
    """A CV gets a roomier layout, but is still squeezed onto one page when it can be."""
    roomy = {**_CV_LAYOUT, "margin_section": "10px"}
    steps = [roomy] + [dict(sp) for sp in SHRINK_PROFILES] \
        + [{**SHRINK_PROFILES[-1], **t} for t in _TRIM_STEPS]
    return _fit_one_page("cv.html", content, steps, "cv")


def render_cover_letter(content: dict, header: dict) -> tuple[bytes, int]:
    return _html_to_pdf(_render("cover_letter.html", doc=content, header=header, **_CV_LAYOUT))
