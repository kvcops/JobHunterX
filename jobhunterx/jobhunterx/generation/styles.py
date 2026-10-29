"""
Visual styles for resumes, CVs and cover letters.

Every style is ATS-safe by construction: one column, real selectable text in a built-in font, standard section titles, no
icons, no images, no text on dark backgrounds, no layout tricks. They differ only in type, colour, header alignment and
heading treatment, and the content never changes, so switching style cannot alter a single fact.

The same ids drive the PDF templates (xhtml2pdf: tables + simple CSS) and the live preview in the app
(`.paper[data-style=…]` in web/styles.css), which switches instantly with no server call. `get()` accepts only ids from this
table, so a style id from a request can never reach a template path.
"""

from __future__ import annotations

from typing import Any

DEFAULT_STYLE = "classic"

# font: Helvetica | Times-Roman (the PDF's built-in fonts: nothing to ship, no glyph surprises)
# rule / rule_w: the line under each section title · hdr: the line under the header block (None = no line)
# caps: section titles in capitals · align: header alignment
STYLES: dict[str, dict[str, Any]] = {
    "classic": {"label": "Classic", "description": "The original: black headings with a thin rule, name left, contact right.",
                "font": "Helvetica", "name": "#111827", "ink": "#111827", "text": "#1f2937", "muted": "#4b5563", "accent": "#111827",
                "link": "#1d4ed8", "rule": "#111827", "rule_w": "1px", "hdr": None, "hdr_w": "0", "caps": False, "align": "left"},
    "professional": {"label": "Professional", "description": "Navy name and capitals, centred header with a fine rule.",
                     "font": "Helvetica", "name": "#1e3a5f", "ink": "#111827", "text": "#1f2937", "muted": "#4b5563", "accent": "#1e3a5f",
                     "link": "#1e3a5f", "rule": "#1e3a5f", "rule_w": "1px", "hdr": "#1e3a5f", "hdr_w": "1.5px", "caps": True, "align": "center"},
    "harvard": {"label": "Harvard", "description": "Serif, all black, centred. The traditional academic and finance format.",
                "font": "Times-Roman", "name": "#000000", "ink": "#000000", "text": "#111111", "muted": "#333333", "accent": "#000000",
                "link": "#000000", "rule": "#000000", "rule_w": "0.75px", "hdr": None, "hdr_w": "0", "caps": True, "align": "center"},
    "modern": {"label": "Modern", "description": "Left-aligned with one blue accent under the header and each title.",
               "font": "Helvetica", "name": "#0f172a", "ink": "#0f172a", "text": "#1e293b", "muted": "#475569", "accent": "#0369a1",
               "link": "#0369a1", "rule": "#0369a1", "rule_w": "1.5px", "hdr": "#0369a1", "hdr_w": "2px", "caps": True, "align": "left"},
    "slate": {"label": "Slate", "description": "Quiet greys: slate capitals over a hairline. Calm and compact.",
              "font": "Helvetica", "name": "#0f172a", "ink": "#0f172a", "text": "#1f2937", "muted": "#475569", "accent": "#475569",
              "link": "#334155", "rule": "#cbd5e1", "rule_w": "1px", "hdr": None, "hdr_w": "0", "caps": True, "align": "left"},
}

# Earlier ids (documents saved before the redesign) land on the closest current style.
LEGACY = {"elegant": "harvard", "minimal": "slate", "bold": "professional", "emerald": "modern", "ats": "classic"}


def normalize(style_id: str | None) -> str:
    sid = LEGACY.get(style_id or "", style_id)
    return sid if isinstance(sid, str) and sid in STYLES else DEFAULT_STYLE


def get(style_id: str | None) -> dict[str, Any]:
    """The style for an id; anything unknown (or hostile) falls back to the default."""
    sid = normalize(style_id)
    return {"id": sid, **STYLES[sid]}


def valid(style_id: object) -> bool:
    return isinstance(style_id, str) and style_id in STYLES


def listing() -> list[dict[str, Any]]:
    """For the UI: id, label, description and what is needed to draw a swatch."""
    return [{"id": k, "label": v["label"], "description": v["description"], "accent": v["accent"], "font": v["font"],
             "heading": "rule", "align": v["align"], "caps": v["caps"]} for k, v in STYLES.items()]
