"""
Careers-site recipes — how to list one company's open jobs again, without a browser or an AI.

The Company Scout agent (agents/career_scout.py) opens a company's own careers site once, applies the filters
(location, keyword) and records every answer the page loads. The AI then reads that recording and says which call is
the job search API, where the job list and its fields are, and where the keyword / page number go. That is stored as a
recipe:

* ``ats``     — the site is a known applicant-tracking board: the board adapter lists it.
* ``api``     — the site's own search API: the same call is replayed (keyword and page swapped in).
* ``html``    — the results page is plain HTML: fetched, and the job links the AI picked are read from it.
* ``browser`` — the results only appear after JavaScript: a headless browser opens the page (no AI) and reads links.

This module holds no knowledge of any site: only structure (JSON paths, link shapes) and plain HTTP.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import net

log = get_logger("recipes")

MAX_PAGES = 3
MAX_JOBS = 150


class Recipe(BaseModel):
    kind: Literal["ats", "api", "html", "browser"]
    results_url: str = ""                       # the filtered results page the agent reached
    location: str = ""
    keyword: str = ""
    # ats
    ats_kind: str = ""
    ats_token: str = ""
    # api
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    list_path: list[Any] = Field(default_factory=list)
    fields: dict[str, list[Any]] = Field(default_factory=dict)   # title / url / location / id / posted → path in item
    url_template: str = ""                      # "https://…/job/{id}" when items carry an id but no link
    base_url: str = ""                          # for relative links
    keyword_at: Optional[dict] = None           # {"where": "query"|"body", "path": [...]}: where the search word goes
    page_at: Optional[dict] = None              # {"where", "path", "start", "step"}
    # html / browser
    link_pattern: str = ""                      # regex the job links match
    title_from: str = "text"                    # "text" (the link's words) or "heading" (the card's heading)


class JobLink(BaseModel):
    title: str
    url: str
    location: str = ""
    posted: str = ""


# --------------------------------------------------------------------------- JSON: structure only (the AI names the fields)

def json_lists(obj: Any, path: tuple = (), depth: int = 0) -> list[tuple[list, int]]:
    """Every list of objects inside a JSON answer → [(path, length)]. What they mean is the AI's call."""
    found: list[tuple[list, int]] = []
    if depth > 7:
        return found
    if isinstance(obj, list):
        if obj and sum(isinstance(x, dict) for x in obj) >= max(1, len(obj) * 0.8):
            found.append((list(path), len(obj)))
        for i, x in enumerate(obj[:2]):
            found += json_lists(x, path + (i,), depth + 1)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found += json_lists(v, path + (k,), depth + 1)
    return found


def get_path(obj: Any, path: list) -> Any:
    for k in path or []:
        if isinstance(obj, dict):
            obj = obj.get(k)
        elif isinstance(obj, list):
            try:
                obj = obj[int(k)]
            except (ValueError, IndexError, TypeError):
                return None
        else:
            return None
    return obj


def _text(v: Any) -> str:
    """Any value as short plain text (strings, numbers, lists, small objects)."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "; ".join(t for t in (_text(x) for x in v[:8]) if t)
    if isinstance(v, dict):
        return ", ".join(t for t in (_text(x) for x in v.values() if not isinstance(x, (dict, list))) if t)[:160]
    return ""


def items_to_links(items: list[dict], fields: dict[str, list], base_url: str = "", url_template: str = "") -> list[JobLink]:
    out = []
    for it in items:
        title = get_path(it, fields.get("title", []))
        if not isinstance(title, str) or not title.strip():
            continue
        url = get_path(it, fields["url"]) if fields.get("url") else None
        if isinstance(url, str) and url.strip():
            url = urljoin(base_url, url.strip()) if base_url else url.strip()
        elif url_template and fields.get("id") and get_path(it, fields["id"]) not in (None, ""):
            url = url_template.replace("{id}", str(get_path(it, fields["id"])))
        else:
            url = ""
        out.append(JobLink(title=title.strip(), url=url or "",
                           location=_text(get_path(it, fields["location"])) if fields.get("location") else "",
                           posted=_text(get_path(it, fields["posted"])) if fields.get("posted") else ""))
    return out


# --------------------------------------------------------------------------- the request: keyword and page slots

def _body_obj(body: Optional[str]) -> tuple[Any, str]:
    """A request body as an object to edit: JSON, form fields, or None."""
    if not body:
        return None, ""
    try:
        return json.loads(body), "json"
    except ValueError:
        pass
    if "=" in body and "{" not in body:
        return dict(parse_qsl(body, keep_blank_values=True)), "form"
    return None, ""


def _set_path(obj: Any, path: list, value: Any) -> None:
    for k in path[:-1]:
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    last = int(path[-1]) if isinstance(obj, list) else path[-1]
    old = obj[last] if (isinstance(obj, list) or last in obj) else ""
    obj[last] = str(value) if isinstance(old, str) else value


def build_request(r: Recipe, keyword: Optional[str], page: int) -> tuple[str, Optional[str]]:
    """The recipe's call for one search word and page number → (url, body)."""
    p = urlparse(r.url)
    query = dict(parse_qsl(p.query, keep_blank_values=True))
    obj, kind = _body_obj(r.body)
    for at, value in ((r.keyword_at, keyword), (r.page_at, None)):
        if not at or not at.get("path"):
            continue
        if at is r.page_at:
            value = int(at.get("start") or 0) + page * int(at.get("step") or 1)
        elif value is None:
            continue
        target = query if at.get("where") == "query" else obj
        if target is None:
            continue
        try:
            _set_path(target, at["path"], value)
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    url = urlunparse(p._replace(query=urlencode(query, doseq=True))) if query else r.url
    body = r.body
    if obj is not None:
        body = json.dumps(obj) if kind == "json" else urlencode(obj)
    return url, body


# --------------------------------------------------------------------------- HTML results pages (structure only)

def _signature(href: str) -> str:
    """'https://x.com/jobs/12345-ml-engineer?src=a' → 'x.com/jobs/{n}'; ids and slugs become slots."""
    p = urlparse(href)
    segs = []
    for s in p.path.strip("/").split("/"):
        if re.match(r"\d{3,}", s):
            segs.append("{n}")
        elif re.search(r"\d{4,}", s) or (s.count("-") >= 2 and len(s) > 12):
            segs.append("{s}")
        else:
            segs.append(s)
    return p.netloc.lower() + "/" + "/".join(segs)


def link_groups(anchors: list[dict], results_url: str) -> dict[str, list[dict]]:
    """Links on the results page grouped by the shape of their address → {signature: anchors}."""
    groups: dict[str, list[dict]] = {}
    for a in anchors:
        href = (a.get("href") or "").split("#")[0]
        if not href.startswith("http") or href.rstrip("/") == results_url.rstrip("/"):
            continue
        sig = _signature(href)
        if "{" in sig and all(x.get("href") != href for x in groups.get(sig, [])):
            groups.setdefault(sig, []).append({**a, "href": href})
    return {k: v for k, v in groups.items() if len(v) >= 2}


def signature_regex(sig: str) -> str:
    host, _, path = sig.partition("/")
    rx = re.escape(path).replace(re.escape("{n}"), r"\d{3,}[^/?#\"']*").replace(re.escape("{s}"), r"[^/?#\"']+")
    return rf"https?://{re.escape(host)}/{rx}/?(?:\?[^\"'#\s<>]*)?"


def _anchor_title(a: Any, title_from: str) -> str:
    """The job title of a link: its own text, or (title_from="heading") the heading of the card around it."""
    text = re.sub(r"\s+", " ", a.text(separator=" ") or "").strip()
    if title_from == "heading":
        node = a
        for _ in range(5):
            h = node.css_first("h1, h2, h3, h4")
            if h is not None and h.text(strip=True):
                return re.sub(r"\s+", " ", h.text(separator=" ")).strip()
            node = node.parent
            if node is None:
                break
    return text or (a.attributes.get("aria-label") or "").strip()


def links_from_html(html: str, page_url: str, pattern: str, title_from: str = "text") -> list[JobLink]:
    from selectolax.lexbor import LexborHTMLParser
    rx = re.compile(pattern)
    out, seen = [], set()
    tree = LexborHTMLParser(html)
    base = tree.css_first("base[href]")
    page_url = urljoin(page_url, base.attributes.get("href") or "") if base is not None else page_url   # as a browser does
    for a in tree.css("a[href]"):
        href = urljoin(page_url, a.attributes.get("href") or "").split("#")[0]
        if href in seen or not rx.fullmatch(href):
            continue
        text = _anchor_title(a, title_from)
        if not text:
            continue
        seen.add(href)
        out.append(JobLink(title=text[:160], url=href))
    return out


# --------------------------------------------------------------------------- running a recipe

async def run_api(r: Recipe, keyword: Optional[str] = None) -> list[JobLink]:
    out: list[JobLink] = []
    seen: set[str] = set()
    for page in range(MAX_PAGES if r.page_at else 1):
        url, body = build_request(r, keyword if r.keyword_at else None, page)
        # only gzip/deflate: some sites answer zstd/brotli streams the HTTP client cannot always decode
        res = await net.fetch(url, method=r.method, headers={**r.headers, "accept-encoding": "gzip, deflate"},
                              content=body, accept=r.headers.get("accept") or "application/json")
        if not res.ok:
            log.info("recipe_api_failed", url=url[:90], status=res.status, error=res.error[:80])
            break
        try:
            data = json.loads(res.text)
        except ValueError:
            break
        items = get_path(data, r.list_path)
        if not isinstance(items, list) or not items:
            break
        new = [l for l in items_to_links(items, r.fields, r.base_url, r.url_template) if (l.url or l.title) not in seen]
        if not new:
            break
        seen |= {l.url or l.title for l in new}
        out += new
        if len(out) >= MAX_JOBS:
            break
    return out


def page_url_for(r: Recipe, keyword: Optional[str]) -> str:
    """The results address with another search word in it (when the site keeps the word in the address)."""
    if not keyword or not r.keyword_at or r.keyword_at.get("where") != "query" or not r.keyword_at.get("path"):
        return r.results_url
    p = urlparse(r.results_url)
    query = dict(parse_qsl(p.query, keep_blank_values=True))
    query[str(r.keyword_at["path"][0])] = keyword
    return urlunparse(p._replace(query=urlencode(query)))


async def run_html(r: Recipe, keyword: Optional[str] = None) -> list[JobLink]:
    res = await net.fetch(page_url_for(r, keyword), headers={"accept-encoding": "gzip, deflate"})
    if not res.ok:
        return []
    return links_from_html(res.text, res.url, r.link_pattern, r.title_from)


async def run_ats(r: Recipe, keywords: Optional[list[str]] = None) -> list[JobLink]:
    from jobhunterx.discovery import ats
    adapter = ats.ADAPTERS.get(r.ats_kind)
    if adapter is None:
        return []
    jobs = await adapter.search_jobs(r.ats_token, keywords or ([r.keyword] if r.keyword else None)) or []
    out = []
    for j in jobs:
        url = j.canonical_url or (j.primary_source.url if j.primary_source else "")
        out.append(JobLink(title=j.title, url=url, location=j.location_raw or "; ".join(j.locations),
                           posted=j.posted_at.isoformat() if j.posted_at else ""))
    return out


def in_location(link: JobLink, location: str) -> bool:
    """Keep a job when the recipe has no place, the job states none, or it names the place."""
    if not location or not link.location:
        return True
    words = [w for w in re.split(r"[\s,]+", location.lower()) if len(w) > 2]
    return any(w in link.location.lower() for w in words[:2])


async def run(r: Recipe, keywords: Optional[list[str]] = None) -> list[JobLink]:
    """List the company's open jobs with a stored recipe (no browser except for the `browser` kind)."""
    if r.kind == "ats":
        links = await run_ats(r, keywords)
    elif r.kind in ("api", "html"):
        links, seen = [], set()
        for kw in (keywords or [None])[:3] if r.keyword_at else [None]:
            for l in await (run_api(r, kw) if r.kind == "api" else run_html(r, kw)):
                if (l.url or l.title) not in seen:
                    seen.add(l.url or l.title)
                    links.append(l)
    else:
        from jobhunterx.agents import career_scout
        links = await career_scout.read_listing(r)
    return [l for l in links if in_location(l, r.location)][:MAX_JOBS]
