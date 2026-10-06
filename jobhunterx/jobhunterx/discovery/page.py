"""
Turn an arbitrary job URL into a JobPosting.

Order of trust:
  1. The URL (or the page's apply link) belongs to a supported ATS → fetch
     the posting from the ATS API (first-party, verified).
  2. The page has schema.org `JobPosting` JSON-LD → structured fields from
     the publisher (verified as "published on page"; first-party when the
     hiring organisation's site is the page's site).
  3. Otherwise → readable text + <title>; everything is *unverified* and
     the LLM understanding stage decides whether it is a real posting.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import ats
from jobhunterx.discovery.htmltext import html_to_text
from jobhunterx.discovery import net
from jobhunterx.discovery.net import FetchResult
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import FieldCheck, JobPosting, Salary, SourceRef
from jobhunterx.intelligence.text import parse_iso_datetime

log = get_logger("page")


def _host(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def registrable(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _jsonld_blocks(html: str) -> list[str]:
    try:                                   # selectolax: same blocks, many times faster than BeautifulSoup
        from selectolax.lexbor import LexborHTMLParser
        return [n.text() for n in LexborHTMLParser(html).css('script[type*="ld+json" i]')]
    except Exception:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return [t.string or t.get_text() or "" for t in soup.find_all("script", type=re.compile("ld\\+json", re.I))]


def _iter_jsonld(html: str):
    for raw in _jsonld_blocks(html):
        try:
            data = json.loads(raw.strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, list):
                stack.extend(cur)
            elif isinstance(cur, dict):
                if "@graph" in cur:
                    stack.append(cur["@graph"])
                t = cur.get("@type")
                types = t if isinstance(t, list) else [t]
                if "JobPosting" in types:
                    yield cur


def _text(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("name") or v.get("@value") or "")
    if isinstance(v, list):
        return ", ".join(_text(x) for x in v if x)
    return str(v or "")


def _ld_location(ld: dict) -> tuple[str, list[str]]:
    locs = ld.get("jobLocation") or []
    locs = locs if isinstance(locs, list) else [locs]
    parts, countries = [], []
    for loc in locs:
        addr = (loc or {}).get("address") if isinstance(loc, dict) else None
        if isinstance(addr, dict):
            country = _text(addr.get("addressCountry"))
            bits = [_text(addr.get("addressLocality")), _text(addr.get("addressRegion")), country]
            parts.append(", ".join(b for b in bits if b))
            if country:
                countries.append(country)
        elif isinstance(addr, str):
            parts.append(addr)
    return "; ".join(p for p in parts if p), countries


def posting_from_jsonld(ld: dict, page_url: str) -> JobPosting:
    org = ld.get("hiringOrganization") or {}
    org_name = _text(org) if not isinstance(org, dict) else str(org.get("name") or "")
    org_site = (org.get("sameAs") or org.get("url") or "") if isinstance(org, dict) else ""
    first_party = bool(org_site) and registrable(_host(str(org_site))) == registrable(_host(page_url))
    loc, countries = _ld_location(ld)
    mode = WorkMode.UNKNOWN
    if "TELECOMMUTE" in json.dumps(ld.get("jobLocationType") or "").upper():
        mode = WorkMode.REMOTE
    remote_countries = []
    req = ld.get("applicantLocationRequirements")
    if req:
        reqs = req if isinstance(req, list) else [req]
        remote_countries = [_text(r) for r in reqs if _text(r)]
    etype = _text(ld.get("employmentType")).split(",")[0].strip()
    salary = None
    bs = ld.get("baseSalary")
    if isinstance(bs, dict):
        val = bs.get("value") or {}
        if isinstance(val, dict):
            lo, hi = val.get("minValue", val.get("value")), val.get("maxValue")
            unit = str(val.get("unitText") or "YEAR").lower()
            try:
                salary = Salary(min=float(lo) if lo is not None else None, max=float(hi) if hi is not None else None,
                                currency=str(bs.get("currency") or ""),
                                period="month" if "month" in unit else "hour" if "hour" in unit else "year",
                                raw=f"{lo}–{hi} {bs.get('currency', '')}/{unit}")
            except (TypeError, ValueError):
                salary = None
    p = JobPosting(
        title=_text(ld.get("title")).strip(),
        company=org_name.strip(),
        company_domain=registrable(_host(str(org_site))) if org_site else "",
        location_raw=loc,
        countries=countries,
        remote_countries=remote_countries,
        work_mode=mode,
        employment_type=etype.lower(),
        description=html_to_text(_text(ld.get("description"))),
        apply_url=str(ld.get("url") or page_url),
        canonical_url=page_url,
        posted_at=parse_iso_datetime(ld.get("datePosted")),
        valid_through=parse_iso_datetime(ld.get("validThrough")),
        salary=salary,
        sources=[SourceRef(name=_host(page_url), kind="career_page" if first_party else "job_board",
                           url=page_url, first_party=first_party, confidence=0.8 if first_party else 0.6)],
    )
    ev = "schema.org JobPosting on " + _host(page_url)
    for key, val in (("title", p.title), ("company", p.company), ("location", p.location_raw)):
        if val:
            p.validation.checks[key] = FieldCheck(status="verified" if first_party else "inferred", value=val, evidence=ev)
    if p.posted_at:
        p.validation.checks["posted_at"] = FieldCheck(status="verified" if first_party else "inferred",
                                                      value=p.posted_at.isoformat(), evidence=ev)
    if p.valid_through:
        p.validation.checks["valid_through"] = FieldCheck(status="inferred", value=p.valid_through.isoformat(), evidence=ev)
    return p


def _find_ats_link(html: str, base: str) -> Optional[str]:
    for m in re.finditer(r"""href=["']([^"'#]+)["']""", html or ""):
        url = urljoin(base, m.group(1))
        ref = ats.parse_ats_url(url)
        if ref and ref.job_id:
            return url
    return None


async def posting_from_url(url: str, hint_title: str = "", hint_snippet: str = "") -> tuple[Optional[JobPosting], FetchResult | None]:
    """Resolve a URL to the best available JobPosting (None if unusable)."""
    ref = ats.parse_ats_url(url)
    if ref and ref.job_id:
        state, posting = await ats.ADAPTERS[ref.kind].check(ref)
        if state == "live" and posting:
            return posting, None
        if state == "gone":
            p = JobPosting(title=hint_title, canonical_url=url, apply_url=url, ats=ref,
                           sources=[SourceRef(name=ref.kind, kind="ats_api", url=url, first_party=True)])
            p.validation.status = "closed"
            p.validation.notes.append(f"No longer listed on the {ref.kind.title()} board.")
            return p, None

    res = await net.fetch(url)
    if not res.ok:
        return None, res
    html = res.text
    for ld in _iter_jsonld(html):
        p = posting_from_jsonld(ld, res.url)
        if p.title and len(p.description) > 100:
            return p, res
    ats_link = _find_ats_link(html, res.url)
    if ats_link:
        ref2 = ats.parse_ats_url(ats_link)
        state, posting = await ats.ADAPTERS[ref2.kind].check(ref2)
        if state == "live" and posting:
            posting.sources.append(SourceRef(name=_host(url), kind="job_board", url=url, confidence=0.5))
            return posting, res

    try:
        import trafilatura
        body = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    except Exception:
        body = ""
    body = body or html_to_text(html)
    title = ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S) or re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        title = html_to_text(m.group(1))[:200]
    if len(body) < 200:
        return None, res
    p = JobPosting(
        title=title or hint_title,
        description=body[:20000],
        apply_url=res.url,
        canonical_url=res.url,
        sources=[SourceRef(name=_host(res.url), kind="search_result", url=res.url, first_party=False, confidence=0.35)],
    )
    p.validation.checks["title"] = FieldCheck(status="unverified", value=p.title, evidence="page title")
    return p, res
