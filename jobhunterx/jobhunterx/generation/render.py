"""Render document content to PDF (Jinja2 with autoescaping → xhtml2pdf)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from jobhunterx.config.logging import get_logger
from jobhunterx.generation import richtext, styles
from jobhunterx.tools.pdf_render import SHRINK_PROFILES, _html_to_pdf

log = get_logger("render")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Extra compaction steps for a one-page resume, applied after font shrinking: fewer bullets and achievements first,
# projects last and one at a time (they are ordered most relevant first, so the least relevant goes).
_TRIM_STEPS = [
    {"max_bullets_per_exp": 3, "max_achievements": 2},
    {"max_bullets_per_exp": 2, "max_achievements": 1},
    {"max_bullets_per_exp": 2, "max_projects": 5, "max_achievements": 1},
    {"max_bullets_per_exp": 2, "max_projects": 4, "max_achievements": 0},
    {"max_bullets_per_exp": 2, "max_projects": 3, "max_achievements": 0},
    {"max_bullets_per_exp": 2, "max_projects": 2, "max_achievements": 0},
    # Beyond here the content really is more than a page: keep cutting the least important parts until it fits —
    # a resume never goes to a second page.
    {"max_bullets_per_exp": 2, "max_projects": 2, "max_achievements": 0, "max_extras": 0, "max_certs": 3},
    {"max_bullets_per_exp": 1, "max_projects": 2, "max_achievements": 0, "max_extras": 0, "max_certs": 2},
    {"max_bullets_per_exp": 1, "max_projects": 1, "max_achievements": 0, "max_extras": 0, "max_certs": 0,
     "max_education": 2, "max_skill_groups": 5},
    {"max_bullets_per_exp": 1, "max_projects": 1, "max_achievements": 0, "max_extras": 0, "max_certs": 0,
     "max_education": 1, "max_skill_groups": 4, "max_experience": 3, "hide_summary": True},
    {"max_bullets_per_exp": 1, "max_projects": 0, "max_achievements": 0, "max_extras": 0, "max_certs": 0,
     "max_education": 1, "max_skill_groups": 3, "max_experience": 2, "hide_summary": True},
]

# Every knob the templates read, at "show everything".
_ALL = {"max_bullets_per_exp": 99, "max_projects": 99, "max_education": 99, "max_achievements": 99, "max_certs": 99,
        "max_extras": 99, "max_skill_groups": 99, "max_experience": 99, "hide_summary": False}
# The knobs that hide content (reported to the app so the editor can show what the page left out).
_LIMITS = tuple(k for k in _ALL if k.startswith("max_")) + ("hide_summary",)

_CV_LAYOUT = {**SHRINK_PROFILES[0], "font_size_body": "9.5pt", "font_size_bullet": "9.3pt", "font_size_name": "20pt",
              "font_size_section": "10.5pt", "margin_x": "16mm", "margin_y": "14mm", "line_height": "1.35",
              "margin_exp": "6px", "margin_bullet": "1.5px"}


@lru_cache(maxsize=1)
def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "j2"]))
    env.filters["cap"] = lambda text, st: str(text).upper() if st.get("caps") else str(text)   # xhtml2pdf ignores text-transform
    env.filters["rich"] = richtext.to_html          # **bold**, *italic*, [label](url) inside any text
    return env


def _num(v: object, default: float) -> float:
    m = re.match(r"\s*([\d.]+)", str(v or ""))
    return float(m.group(1)) if m else default


def _geometry(ctx: dict) -> dict:
    """Frame positions (mm, A4) for the two-column layout, from the step's margins and type sizes."""
    mx, my = _num(ctx.get("margin_x"), 10), _num(ctx.get("margin_y"), 6)
    name_pt, small_pt = _num(ctx.get("font_size_name"), 18), _num(ctx.get("font_size_small"), 8)
    hh = round(name_pt * 0.42 + small_pt * 1.0 + 7, 1)        # name + headline + two contact lines + the rule
    w = 210 - 2 * mx
    sw = round(w * 0.29, 1)
    gap = 5
    top = round(my + hh + 1, 1)
    return {"mx": mx, "my": my, "w": w, "hh": hh, "sw": sw, "main_x": round(mx + sw + gap, 1),
            "mw": round(w - sw - gap, 1), "top": top, "h": round(297 - top - my, 1)}


def _render(template: str, **ctx) -> str:
    ctx = {**_ALL, **ctx}
    return _env().get_template(template).render(g=_geometry(ctx), **ctx)


def _fit_one_page(template: str, content: dict, steps: list[dict], kind: str,
                  style: str = styles.DEFAULT_STYLE) -> tuple[bytes, int, dict]:
    """Try each layout until the document fits on one page; otherwise keep the shortest result.
    Returns (pdf, pages, the content limits the fitting layout applied — empty when nothing was hidden)."""
    best: tuple[bytes, int, dict] | None = None
    for sp in steps:
        sp = {**_ALL, **sp}
        pdf, pages = _html_to_pdf(_render(template, doc=content, s=styles.get(style), **sp))
        limits = {k: sp[k] for k in _LIMITS if sp[k] != _ALL[k]}
        if pages == 1:
            return pdf, 1, limits
        if best is None or pages < best[1]:
            best = (pdf, pages, limits)
    log.warning(f"{kind}_multi_page", pages=best[1] if best else 0)
    return best  # type: ignore[return-value]


def _resume_steps() -> list[dict]:
    return [dict(sp) for sp in SHRINK_PROFILES] + [{**SHRINK_PROFILES[-1], **t} for t in _TRIM_STEPS]


def render_resume_fit(content: dict, style: str = styles.DEFAULT_STYLE) -> tuple[bytes, int, dict]:
    """One page, always: shrink typography first, then hide the lowest-relevance items. The third value says what was
    hidden ({"max_bullets_per_exp": 2, ...}) so the editor can show it."""
    return _fit_one_page("resume.html", content, _resume_steps(), "resume", style)


def render_resume(content: dict, style: str = styles.DEFAULT_STYLE) -> tuple[bytes, int]:
    pdf, pages, _ = render_resume_fit(content, style)
    return pdf, pages


def render_cv(content: dict, style: str = styles.DEFAULT_STYLE) -> tuple[bytes, int]:
    """A CV gets a roomier layout, but is still squeezed onto one page when it can be."""
    roomy = {**_CV_LAYOUT, "margin_section": "10px"}
    steps = [roomy] + [dict(sp) for sp in SHRINK_PROFILES] \
        + [{**SHRINK_PROFILES[-1], **t} for t in _TRIM_STEPS]
    pdf, pages, _ = _fit_one_page("cv.html", content, steps, "cv", style)
    return pdf, pages


def render_cover_letter(content: dict, header: dict, style: str = styles.DEFAULT_STYLE) -> tuple[bytes, int]:
    return _html_to_pdf(_render("cover_letter.html", doc=content, header=header, s=styles.get(style), **{**_ALL, **_CV_LAYOUT}))


def render_document(kind: str, content: dict, header: dict, style: str) -> tuple[bytes, int]:
    """Any document kind in any style (the style id is checked against the table, never used as a path)."""
    if kind == "resume":
        return render_resume(content, style)
    if kind == "cv":
        return render_cv(content, style)
    return render_cover_letter(content, header, style)
