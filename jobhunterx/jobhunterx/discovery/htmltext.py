"""HTML → readable plain text (structure-preserving, no domain rules)."""

from __future__ import annotations

import html as _html
import re

_BLOCK = ("p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article")


def html_to_text(raw: str) -> str:
    if not raw:
        return ""
    text = _html.unescape(raw) if "&lt;" in raw[:2000] else raw
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")
        for t in soup(["script", "style", "noscript", "template", "svg"]):
            t.decompose()
        for li in soup.find_all("li"):
            li.insert_before("\n• ")
        for t in soup.find_all(_BLOCK):
            t.insert_after("\n")
        out = soup.get_text()
    except Exception:
        out = re.sub(r"<[^>]+>", "\n", text)
    out = _html.unescape(out)
    out = re.sub(r"[ \t\r\f\v]+", " ", out)
    out = re.sub(r"\n\s*\n+", "\n", out)
    return "\n".join(line.strip() for line in out.split("\n") if line.strip()).strip()
