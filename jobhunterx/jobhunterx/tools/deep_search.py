"""
JobHunterX Deep Search — keyless web search built for finding job postings.

Paid search APIs (Tavily, Exa…) do three things a single free scraper does not:
they ask several indexes, they read the pages, and they rank by meaning. This
module does the same with free parts:

1. **Fan-out** — every query goes to several free engines at once through
   `ddgs` (Bing, Yandex, Mullvad-Google, Mullvad-Brave, Yahoo, DuckDuckGo).
   Engines that fail are rested for a while instead of slowing every query.
2. **Fusion** — results are merged with reciprocal-rank fusion (a page several
   engines agree on rises), deduplicated by URL, and boosted when they are
   employer job pages (ATS postings, careers pages) rather than aggregators.
3. **Crawl** — the best non-ATS pages (company careers pages, listing pages)
   are opened and mined for links to the employer's own job board and to
   individual postings (Greenhouse, Lever, Ashby, Workday, Keka…). One careers
   page can turn into many first-party postings.
4. **Rerank** — when an AI model is available, it scores the top candidates for
   "is this a real, open posting that matches the search?" and reorders them.

Everything degrades gracefully: no AI → fusion order; a blocked engine → the
others answer; a page that will not load → its search snippet is kept.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger

log = get_logger("deep_search")

ENGINES = ["bing", "yandex", "mullvad_google", "mullvad_brave", "yahoo", "duckduckgo"]
PER_ENGINE = 10
RRF_K = 60
CRAWL_PAGES = 6               # pages opened per query
CRAWL_LINKS_PER_PAGE = 12     # job links taken from one page
ENGINE_REST_S = 600           # an engine that keeps failing sits out for 10 minutes
RERANK_TOP = 20

# Hosts that only aggregate other employers' posts: fine as discovery leads, never better than the employer's own page.
AGGREGATORS = ("linkedin.com", "naukri.com", "indeed.", "glassdoor.", "foundit.in", "monsterindia.com", "shine.com",
               "timesjobs.com", "simplyhired", "ziprecruiter", "jooble", "talent.com", "apna.co", "internshala.com")
# People-lookup / contact-scraping sites: never job postings, often rank high for role names.
NOISE = ("rocketreach.co", "zoominfo.com", "signalhire.com", "contactout.com", "apollo.io", "lusha.com", "theorg.com",
         "crunchbase.com", "youtube.com", "medium.com", "quora.com", "reddit.com", "wikipedia.org")
# A site whose own name is about jobs ("linuxcareers", "sherjobs", "jobsora", "hirist") lists many employers' roles:
# treat it as an aggregator, never as one employer's careers page.
_JOB_SITE_NAME = re.compile(r"(?i)(jobs?|careers?|hiring|vacanc|recruitment|naukri)")
MAX_PER_SITE = 3              # results kept from one site (an ATS counts per employer board, not per host)
_CAREERS_PATH = re.compile(r"/(careers?|jobs?|join-us|join|work-with-us|openings|vacancies|positions)(/|$|\?)", re.I)
_JOB_ANCHOR = re.compile(r"\b(engineer|developer|scientist|analyst|manager|architect|intern|lead|specialist|consultant|designer)\b", re.I)


@dataclass
class _Engine:
    name: str
    fails: int = 0
    rest_until: float = 0.0


_engines = {n: _Engine(n) for n in ENGINES}


@dataclass
class Hit:
    url: str
    title: str
    snippet: str
    score: float = 0.0
    engines: set = field(default_factory=set)
    kind: str = "page"            # posting | board | careers | aggregator | page
    via: str = ""                 # how it was found: engine names or "crawl:<page>"


def _norm(url: str) -> str:
    u = re.sub(r"[#?].*$", "", (url or "").strip())
    return u.rstrip("/").lower()


def _host(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def classify(url: str) -> str:
    from jobhunterx.discovery import ats
    ref = ats.parse_ats_url(url)
    if ref:
        return "posting" if ref.job_id else "board"
    h = _host(url)
    if any(h == n or h.endswith("." + n) for n in NOISE):
        return "noise"
    if any(a in h for a in AGGREGATORS):
        return "aggregator"
    site_name = h.split(".")[-2] if h.count(".") >= 1 else h
    if _JOB_SITE_NAME.search(site_name):
        return "aggregator"
    if _CAREERS_PATH.search(urlparse(url).path or "") or h.startswith(("careers.", "jobs.")):
        return "careers"
    return "page"


KIND_BOOST = {"posting": 1.6, "board": 1.4, "careers": 1.25, "page": 1.0, "aggregator": 0.75, "noise": 0.2}


# ---------------------------------------------------------------- 1. fan-out
async def _engine_search(engine: _Engine, query: str) -> list[dict]:
    def run():
        from ddgs import DDGS
        with DDGS(timeout=10) as d:
            return list(d.text(query, max_results=PER_ENGINE, region="in-en", backend=engine.name))
    try:
        res = await asyncio.wait_for(asyncio.to_thread(run), timeout=14)
        engine.fails = 0
        return res
    except Exception as exc:
        msg = str(exc).lower()
        if "no results" not in msg:              # "no results" is an answer, not a failure
            engine.fails += 1
            if engine.fails >= 2:
                engine.rest_until = time.monotonic() + ENGINE_REST_S
                log.info("deep_search_engine_resting", engine=engine.name, error=str(exc)[:80])
        return []


async def fan_out(query: str) -> dict[str, Hit]:
    now = time.monotonic()
    live = [e for e in _engines.values() if e.rest_until <= now] or list(_engines.values())
    results = await asyncio.gather(*(_engine_search(e, query) for e in live))
    hits: dict[str, Hit] = {}
    for engine, rows in zip(live, results):
        for rank, r in enumerate(rows):
            url = r.get("href") or r.get("url") or ""
            if not url.startswith("http"):
                continue
            key = _norm(url)
            h = hits.get(key)
            if not h:
                h = hits[key] = Hit(url=url, title=r.get("title", ""), snippet=r.get("body") or "", kind=classify(url))
            h.score += 1.0 / (RRF_K + rank + 1)
            h.engines.add(engine.name)
            if len(r.get("body") or "") > len(h.snippet):
                h.snippet = r.get("body") or ""
    for h in hits.values():
        h.score *= KIND_BOOST.get(h.kind, 1.0)
        h.via = ",".join(sorted(h.engines))
    return hits


# ---------------------------------------------------------------- 3. crawl
async def _crawl_page(hit: Hit, sem: asyncio.Semaphore) -> list[Hit]:
    from jobhunterx.discovery import ats, net
    from jobhunterx.discovery.htmltext import html_to_text
    async with sem:
        res = await net.fetch(hit.url, timeout=10)
    if not res.ok or not res.text:
        return []
    html = res.text
    base = res.url or hit.url
    found: dict[str, Hit] = {}
    # links and embedded job-board frames (Greenhouse/Lever/Ashby/Workday embeds sit in iframes or scripts)
    for m in re.finditer(r"""<(?:a|iframe)\b[^>]*?(?:href|src|data-url)=["']([^"'#\s]+)["'][^>]*>(.{0,600}?)(?:</a>|</iframe>|<a\b)""",
                         html, re.I | re.S):
        url = urljoin(base, m.group(1))
        if not url.startswith("http"):
            continue
        anchor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2) or "")).strip()[:140]
        ref = ats.parse_ats_url(url)
        kind = ("posting" if ref.job_id else "board") if ref else None
        if (not kind and hit.kind == "careers" and _host(url) == _host(base) and _JOB_ANCHOR.search(anchor)
                and _CAREERS_PATH.search(urlparse(url).path or "") and (urlparse(url).path or "").count("/") >= 3):
            kind = "posting"                       # a job link on the company's own careers page
        if not kind:
            continue
        key = _norm(url)
        if key in found or key == _norm(hit.url):
            continue
        if kind == "posting" and not ref and not anchor:
            continue
        found[key] = Hit(url=url, title=anchor or hit.title, snippet=f"Found on {_host(base)}", kind=kind,
                         score=hit.score * (0.9 if kind == "posting" else 0.8), via=f"crawl:{_host(base)}")
        if len(found) >= CRAWL_LINKS_PER_PAGE:
            break
    # a page that is itself a posting (schema.org JobPosting) gets its real text as the snippet
    if '"JobPosting"' in html or "'JobPosting'" in html:
        hit.kind = "posting"
        hit.score *= 1.3
    if len(hit.snippet) < 160:
        text = html_to_text(html)[:600]
        if text:
            hit.snippet = text
    return list(found.values())


async def crawl(hits: list[Hit]) -> list[Hit]:
    targets = [h for h in hits if h.kind in ("careers", "page", "aggregator")][:CRAWL_PAGES]
    if not targets:
        return []
    sem = asyncio.Semaphore(4)
    out = await asyncio.gather(*(_crawl_page(h, sem) for h in targets), return_exceptions=True)
    return [h for group in out if isinstance(group, list) for h in group]


# ---------------------------------------------------------------- 4. rerank
class _Score(BaseModel):
    i: int
    score: int = Field(ge=0, le=10, description="10 = an individual open job posting that matches the search; 0 = unrelated")


class _Rerank(BaseModel):
    scores: list[_Score] = Field(default_factory=list)


_RERANK_SYS = """You rank web search results for a job search. For each numbered result give a score 0-10:
10 = a single, currently open job posting that matches the role and place in the query;
7 = the employer's own careers page or job board listing several matching roles;
4 = a job board listing page with relevant roles; 0 = news, blogs, courses, salary pages, unrelated.
Judge only from the title, URL and snippet given. Return every index."""


async def rerank(query: str, hits: list[Hit]) -> list[Hit]:
    top = hits[:RERANK_TOP]
    if len(top) < 3:
        return hits
    try:
        from jobhunterx.intelligence.llm_structured import call_structured
        lines = "\n".join(f"[{i}] {h.title[:110]} | {h.url[:120]} | {h.snippet[:180]}" for i, h in enumerate(top))
        res, _ = await call_structured(task="deep_rerank", version="v1", model=_Rerank, system=_RERANK_SYS,
                                       user=f"Search: {query}\n\nResults:\n{lines}", chain="fast", max_tokens=700,
                                       cache_parts=(query, *[h.url for h in top]))
    except Exception as exc:                       # no AI available: keep fusion order
        log.debug("deep_rerank_skipped", error=str(exc)[:80])
        return hits
    if not res or not res.scores:
        return hits
    by_i = {s.i: s.score for s in res.scores if 0 <= s.i < len(top)}
    for i, h in enumerate(top):
        if i in by_i:
            h.score = h.score * (0.35 + by_i[i] / 10)     # meaning decides, fusion breaks ties
    return sorted(hits, key=lambda h: -h.score)


# ---------------------------------------------------------------- entry point
async def search(query: str, max_results: int = 10, use_ai: bool = True) -> list[Hit]:
    t0 = time.monotonic()
    hits = await fan_out(query)
    ranked = sorted(hits.values(), key=lambda h: -h.score)
    extra = await crawl(ranked)
    for h in extra:
        key = _norm(h.url)
        if key in hits:
            hits[key].score += h.score * 0.5
        else:
            hits[key] = h
    ranked = sorted(hits.values(), key=lambda h: -h.score)
    if use_ai:
        ranked = await rerank(query, ranked)
    ranked = diversify(ranked)
    log.info("deep_search", query=query[:60], engines=sum(1 for e in _engines.values() if e.rest_until <= time.monotonic()),
             candidates=len(hits), crawled=len(extra), ms=int((time.monotonic() - t0) * 1000))
    return ranked[:max_results]


def site_key(url: str) -> str:
    """One employer board per key on shared ATS hosts (greenhouse.io/acme ≠ greenhouse.io/other); else the host."""
    from jobhunterx.discovery import ats
    ref = ats.parse_ats_url(url)
    return f"{ref.kind}:{ref.token.lower()}" if ref else _host(url)


def diversify(hits: list, per_site: int = MAX_PER_SITE) -> list:
    """Keep order, but at most `per_site` results from one site and one copy of a title per site."""
    seen_site: dict[str, int] = {}
    seen_title: set[tuple[str, str]] = set()
    out = []
    for h in hits:
        k = site_key(h.url)
        t = (k, re.sub(r"\W+", " ", (h.title or "").lower()).strip())
        if seen_site.get(k, 0) >= per_site or (t[1] and t in seen_title):
            continue
        seen_site[k] = seen_site.get(k, 0) + 1
        seen_title.add(t)
        out.append(h)
    return out


def engine_status() -> dict:
    now = time.monotonic()
    return {e.name: ("resting" if e.rest_until > now else "ok") for e in _engines.values()}
