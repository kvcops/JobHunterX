"""
Visual styles for resumes, CVs and cover letters.

A style changes only how the same content looks — fonts, colours, heading treatment, header alignment. The content
never changes, so switching style cannot alter a single fact. The same ids drive:

* the PDF templates (xhtml2pdf: tables + simple CSS, built-in fonts only), and
* the live preview in the app (`.paper[data-style=…]` in web/styles.css), which switches instantly with no server call.

`get()` accepts only ids from this table, so a style id from a request can never reach a template path.
"""

from __future__ import annotations

from typing import Any

DEFAULT_STYLE = "classic"

# heading: rule (underline) | bar (left bar) | band (filled strip) | plain (coloured small caps) | center (centred, hairline)
# font: Helvetica | Times-Roman (the PDF's built-in fonts; no files to ship, no glyph surprises)
STYLES: dict[str, dict[str, Any]] = {
    "classic": {"label": "Classic", "description": "Black headings with a thin rule. The safe default.",
                "font": "Helvetica", "ink": "#111827", "text": "#1f2937", "muted": "#4b5563", "accent": "#111827",
                "link": "#1d4ed8", "heading": "rule", "align": "left"},
    "modern": {"label": "Modern", "description": "Blue accent with a bar beside each heading.",
               "font": "Helvetica", "ink": "#0f172a", "text": "#1e293b", "muted": "#475569", "accent": "#2563eb",
               "link": "#2563eb", "heading": "bar", "align": "left"},
    "elegant": {"label": "Elegant", "description": "Serif type, centred header, quiet hairlines.",
                "font": "Times-Roman", "ink": "#1c1917", "text": "#292524", "muted": "#57534e", "accent": "#44403c",
                "link": "#44403c", "heading": "center", "align": "center"},
    "minimal": {"label": "Minimal", "description": "No rules, soft grey headings, lots of air.",
                "font": "Helvetica", "ink": "#18181b", "text": "#27272a", "muted": "#71717a", "accent": "#71717a",
                "link": "#3f3f46", "heading": "plain", "align": "left"},
    "bold": {"label": "Bold", "description": "Dark filled heading strips. Stands out on a pile.",
             "font": "Helvetica", "ink": "#111827", "text": "#1f2937", "muted": "#4b5563", "accent": "#1f2937",
             "link": "#1d4ed8", "heading": "band", "align": "left"},
    "emerald": {"label": "Emerald", "description": "Fresh green accent with underlined headings.",
                "font": "Helvetica", "ink": "#064e3b", "text": "#1f2937", "muted": "#4b5563", "accent": "#047857",
                "link": "#047857", "heading": "rule", "align": "left"},
    "ats": {"label": "ATS plain", "description": "Pure black on white, no colour. Easiest for résumé-parsing software.",
            "font": "Helvetica", "ink": "#000000", "text": "#000000", "muted": "#222222", "accent": "#000000",
            "link": "#000000", "heading": "rule", "align": "left"},
}


def get(style_id: str | None) -> dict[str, Any]:
    """The style for an id; anything unknown (or hostile) falls back to the default."""
    sid = style_id if isinstance(style_id, str) and style_id in STYLES else DEFAULT_STYLE
    return {"id": sid, **STYLES[sid]}


def valid(style_id: object) -> bool:
    return isinstance(style_id, str) and style_id in STYLES


def listing() -> list[dict[str, Any]]:
    """For the UI: id, label, description and the colours needed to draw a swatch."""
    return [{"id": k, "label": v["label"], "description": v["description"], "accent": v["accent"], "font": v["font"],
             "heading": v["heading"], "align": v["align"]} for k, v in STYLES.items()]
