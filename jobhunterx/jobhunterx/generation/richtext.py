"""
Inline formatting inside document text: the few things a resume line needs.

  **bold**   *italic*   [label](https://link)   \\* \\[ \\] \\\\ for the literal characters

Stored as plain strings, so every existing consumer (fact-checker, AI editor, search) still reads text; the PDF template
(`|rich` filter) and the in-app editor (web/js/lib/richtext.js — same rules) draw it. Everything is HTML-escaped first,
and a link becomes clickable only for http(s) and mailto addresses, so a pasted `javascript:` URL is printed as text.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

_ESC = re.compile(r"\\([\\*\[\]])")
_LINK = re.compile(r"\[([^\[\]]+)\]\(([^()\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*([^*]+?)\*")
_SAFE_URL = re.compile(r"^(https?://|mailto:)", re.I)


def _hide_escapes(s: str) -> str:
    return _ESC.sub(lambda m: f"\x00{ord(m.group(1))}\x01", s)


def _show_escapes(s: str) -> str:
    return re.sub(r"\x00(\d+)\x01", lambda m: chr(int(m.group(1))), s)


def to_html(text: object) -> Markup:
    """Escaped HTML with <b>, <i> and safe <a> — for templates."""
    s = _hide_escapes(str(escape(str(text or ""))))

    def link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        raw = url.replace("&amp;", "&")
        return f'<a href="{url}">{label}</a>' if _SAFE_URL.match(raw) else label

    s = _LINK.sub(link, s)
    s = _BOLD.sub(r"<b>\1</b>", s)
    s = _ITALIC.sub(r"<i>\1</i>", s)
    return Markup(_show_escapes(s))


def plain(text: object) -> str:
    """The words without the markers (link labels kept)."""
    s = _hide_escapes(str(text or ""))
    s = _LINK.sub(r"\1", s)
    s = _BOLD.sub(r"\1", s)
    s = _ITALIC.sub(r"\1", s)
    return _show_escapes(s)
