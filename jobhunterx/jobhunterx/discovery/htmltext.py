"""HTML → readable plain text (structure-preserving, no domain rules)."""

from __future__ import annotations

import html as _html
import re

_BLOCK = ("p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article")


def _lexbor_text(text: str) -> str:
    """selectolax (the C Lexbor engine): many times faster than BeautifulSoup on job pages, same text."""
    from selectolax.lexbor import LexborHTMLParser
    tree = LexborHTMLParser(text)
    for t in tree.css("script, style, noscript, template, svg"):
        t.decompose()
    for li in tree.css("li"):
        li.insert_before("\n• ")
    for t in tree.css(", ".join(_BLOCK)):
        t.insert_after("\n")
    root = tree.root
    return root.text(deep=True) if root is not None else ""


def _soup_text(text: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    for t in soup(["script", "style", "noscript", "template", "svg"]):
        t.decompose()
    for li in soup.find_all("li"):
        li.insert_before("\n• ")
    for t in soup.find_all(_BLOCK):
        t.insert_after("\n")
    return soup.get_text()


def html_to_text(raw: str) -> str:
    if not raw:
        return ""
    text = _html.unescape(raw) if "&lt;" in raw[:2000] else raw
    out = None
    for parse in (_lexbor_text, _soup_text):     # fast C parser first; the slower, forgiving one if it is missing or fails
        try:
            out = parse(text)
            break
        except Exception:
            continue
    if out is None:
        out = re.sub(r"<[^>]+>", "\n", text)
    out = _html.unescape(out)
    out = re.sub(r"[ \t\r\f\v]+", " ", out)
    out = re.sub(r"\n\s*\n+", "\n", out)
    return "\n".join(line.strip() for line in out.split("\n") if line.strip()).strip()
