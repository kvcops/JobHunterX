"""
Company Scout — a browser agent that finds one company's real careers site, applies the filters (location, role
keyword) the way a person would, and learns how to list those jobs again without a browser.

One-time work per company + place. A web search finds the careers page first; when it is a known job board
(Greenhouse, Workday…) no browser is needed at all. Otherwise the agent starts on that page, and while it clicks
through the site every JSON / HTML answer the page loads is recorded. The finished page is checked (a job list, the
place applied) and the agent gets one more try with the exact problem. The recording is then read: a known job board,
the site's own search API, or the shape of job links on the results page. A candidate is kept only when replaying it
from plain Python gives the jobs the page showed; it is stored as a recipe (discovery/recipes.py), and from then on the
company is checked in seconds on every search and watch.

Runs on the browser worker loop with its own throw-away headless Chrome, so it never touches the auto-apply browser.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field, field_validator

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import recipes
from jobhunterx.discovery.recipes import JobLink, Recipe

log = get_logger("career_scout")

MAX_STEPS = 24
FOLLOW_UP_STEPS = 10               # one second chance when the finished page fails the check
MAX_CAPTURE = 120                  # responses kept per scout
MAX_BODY = 3_000_000
PAGE_MATCH = 0.4                   # a replayed list is the page's list when this share of its titles is on the page

Step = Callable[..., Awaitable[None]]          # on_step(message, url="")

SCOUT_PROMPT = """You are the Company Scout. Open {company}'s OWN careers website and leave the browser on a page that
LISTS its open jobs, filtered the way the candidate needs, so that list can be read again later.

COMPANY: {company}
LOCATION FILTER: {location_line}
ROLE KEYWORD: {keyword_line}
START: {start_line}

HOW TO WORK (fast and exact)
1. Get to the job LIST. On a careers home page, look for "Search jobs", "View all jobs", "Open positions", "Job
   openings", "Find your role", "Explore jobs" or a country / "India" chooser. Use ONLY the company's own site or the
   job board it sends you to (Workday, Greenhouse, Lever, SuccessFactors, iCIMS, Eightfold, Phenom, Oracle…), never a
   job portal (LinkedIn, Naukri, Indeed, Glassdoor, Foundit, Instahyre, Cutshort…). If you land on ONE job, go back
   to the list.
2. Apply the location on the site itself:
   - Location box or typeahead: type the place, then use `choose_option` so you WAIT for the suggestions and pick the
     one for the place (prefer the city; else "City, State, India"; else the state; else India).
   - Filter panel / checkboxes / dropdowns: open the location (or country → city) filter and tick the place.
   - Address bar: if the results address already has a search or location parameter (e.g. ...?location=...,
     ...?q=...), you may simply open that address with the place / keyword changed — often the most reliable way.
3. Keyword: type the role keyword in the job search box and search. If that gives 0 jobs, try ONE broader word (the
   main noun, e.g. "Engineer"); still 0 → clear the keyword and keep only the location. No search box → skip it.
4. CHECK before you finish: the page shows at least one job card, and the place is applied (a filter chip, the
   address, or the jobs' locations show it). Scroll once if the list loads as you scroll.
5. Finish with `done`, success=true, and write exactly:
   RESULTS_URL: <the address of the filtered results page>
   KEYWORD_USED: <the keyword in the search box now, or none>
   JOBS_SHOWN: <the number of jobs the page says it found, or how many you see>
   NOTES: <one short line on how the filters work here>

RULES
- Close cookie banners and pop-ups first. Never sign in, create an account, apply or upload anything.
- Several simple actions in one step are fine (type, then choose). Do not wait more than 3 seconds at a time.
- A security check: call `wait_for_human_check` once; if it does not clear, finish with success=false, NOTES: blocked.
- If the company truly has no careers site with a job list, finish with success=false and say why in NOTES.
- Keep your thinking to one short sentence per step."""

FOLLOW_UP = """The page you finished on does not pass the check: {problem}
Fix exactly that on {company}'s careers site (same filters as before), then finish again with `done` and the same four
lines (RESULTS_URL, KEYWORD_USED, JOBS_SHOWN, NOTES)."""


def _prompt(company: str, location: str, keyword: str, start: str = "") -> str:
    return SCOUT_PROMPT.format(
        company=company,
        location_line=location or "none — keep all locations (but prefer India if the site asks for a country)",
        keyword_line=keyword or "none — list all jobs",
        start_line=(f"the browser is already on {start} (found by a web search; check it is {company}'s own careers "
                    "site, else search again)") if start else "a web search results page is open; pick the official careers site")


# --------------------------------------------------------------------------- network recording

_KEEP_HEADERS = ("content-type", "accept", "accept-language", "origin", "referer")


class Recorder:
    """Records the JSON and HTML answers the pages load while the agent works (XHR / fetch / documents)."""

    def __init__(self, browser_session: Any):
        self.bs = browser_session
        self.requests: dict[str, dict] = {}
        self.captured: list[dict] = []
        self.sessions: set[str] = set()
        self._tasks: set[asyncio.Task] = set()

    def start(self) -> None:
        client = self.bs.cdp_client
        client.register.Network.requestWillBeSent(self._on_request)
        client.register.Network.loadingFinished(self._on_finished)

    async def watch_focus(self) -> None:
        """Turn recording on for the tab the agent is in (new tabs get a new session)."""
        try:
            cdp = await self.bs.get_or_create_cdp_session(focus=False)
            if cdp.session_id not in self.sessions:
                await cdp.cdp_client.send.Network.enable(params={"maxResourceBufferSize": 10_000_000,
                                                                  "maxTotalBufferSize": 60_000_000},
                                                          session_id=cdp.session_id)
                self.sessions.add(cdp.session_id)
        except Exception as exc:
            log.debug("scout_network_enable_failed", error=str(exc)[:100])

    def _on_request(self, ev: dict, session_id: Optional[str]) -> None:
        req = ev.get("request") or {}
        url = req.get("url") or ""
        if ev.get("type") not in ("XHR", "Fetch", "Document") or not url.startswith("http"):
            return
        headers = {k.lower(): v for k, v in (req.get("headers") or {}).items()}
        keep = {k: v for k, v in headers.items() if k in _KEEP_HEADERS or (k.startswith("x-") and "client-data" not in k)}
        self.requests[ev["requestId"]] = {"url": url, "method": req.get("method", "GET"), "body": req.get("postData"),
                                          "headers": keep, "type": ev.get("type"), "session": session_id}

    def _on_finished(self, ev: dict, session_id: Optional[str]) -> None:
        meta = self.requests.pop(ev.get("requestId"), None)
        if meta is None or len(self.captured) >= MAX_CAPTURE or (ev.get("encodedDataLength") or 0) > MAX_BODY:
            return
        task = asyncio.ensure_future(self._grab(ev["requestId"], session_id, meta))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _grab(self, request_id: str, session_id: Optional[str], meta: dict) -> None:
        try:
            out = await self.bs.cdp_client.send.Network.getResponseBody(params={"requestId": request_id}, session_id=session_id)
        except Exception:
            return
        text = out.get("body") or ""
        if out.get("base64Encoded"):
            try:
                text = base64.b64decode(text).decode("utf-8", errors="replace")
            except Exception:
                return
        text = text[:MAX_BODY]
        if meta["type"] != "Document":
            s = text.lstrip()
            if not s.startswith(("{", "[")):
                return
            try:
                meta["json"] = json.loads(s)
            except ValueError:
                return
            if not recipes.json_lists(meta["json"]):     # no list of objects: cannot be a job list
                return
        else:
            meta["html"] = text
        self.captured.append(meta)

    async def settle(self) -> None:
        if self._tasks:
            await asyncio.wait(set(self._tasks), timeout=10)


# --------------------------------------------------------------------------- reading the page

# Every link with its own words and the heading of the card it sits in; the AI decides which one is the job title.
_ANCHORS_JS = """(() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href]')) {
    let heading = '', c = a;
    for (let i = 0; i < 5 && c && !heading; i++, c = c.parentElement) {
      const h = c.querySelector('h1,h2,h3,h4');
      if (h && h.innerText) heading = h.innerText.trim();
    }
    out.push({ href: a.href, text: (a.innerText || a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim().slice(0, 160),
               heading: heading.split('\\n')[0].slice(0, 160) });
    if (out.length > 3000) break;
  }
  return out;
})()"""


async def _anchors(bs: Any) -> list[dict]:
    try:
        cdp = await bs.get_or_create_cdp_session()
        out = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": _ANCHORS_JS, "returnByValue": True},
                                                         session_id=cdp.session_id)
        return (out.get("result") or {}).get("value") or []
    except Exception as exc:
        log.debug("scout_anchors_failed", error=str(exc)[:100])
        return []


async def _page_text(bs: Any) -> str:
    """The visible text of the page the agent finished on (to check filters and to recognise its job titles)."""
    try:
        cdp = await bs.get_or_create_cdp_session()
        out = await cdp.cdp_client.send.Runtime.evaluate(
            params={"expression": "(document.body && document.body.innerText || '').slice(0, 300000)", "returnByValue": True},
            session_id=cdp.session_id)
        return (out.get("result") or {}).get("value") or ""
    except Exception as exc:
        log.debug("scout_text_failed", error=str(exc)[:100])
        return ""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _place_words(location: str) -> list[str]:
    return [w for w in re.split(r"[\s,/]+", _norm(location)) if len(w) > 2][:2]


def _page_problem(text: str, anchors: list[dict], captured: list[dict], url: str, location: str) -> str:
    """Why the finished page is not a usable job list ('' when it is): structure only, no knowledge of any site."""
    has_links = any(len(g) >= 3 for g in recipes.link_groups(anchors, url).values())
    has_json = any(n >= 3 for c in captured if "json" in c for _, n in recipes.json_lists(c["json"]))
    if not has_links and not has_json:
        return ("no list of jobs is visible. Open the page that lists the jobs (search results), not the careers home "
                "page and not a single job.")
    words = _place_words(location)
    if words and text and not any(w in _norm(text) for w in words):
        return (f"the page does not mention {location} anywhere, so the location filter is not applied yet. Apply it "
                "(location filter, location search box, or the place in the results address).")
    return ""


def _shown_count(fields: dict[str, str]) -> int:
    m = re.search(r"\d[\d,]*", fields.get("JOBS_SHOWN", ""))
    return int(m.group(0).replace(",", "")) if m else 0


def _done_fields(text: str) -> dict[str, str]:
    out = {}
    for key in ("RESULTS_URL", "KEYWORD_USED", "JOBS_SHOWN", "NOTES"):
        m = re.search(rf"{key}\s*:\s*(.+)", text or "")
        if m:
            out[key] = m.group(1).strip()
    return out


# --------------------------------------------------------------------------- from a recording to a recipe (the AI reads it)

class _ApiChoice(BaseModel):
    index: int = Field(-1, description="number of the response that is the job search answer; -1 if none is")
    list_path: list[str] = Field(default_factory=list, description="keys from the top of that JSON to the list of jobs")
    title: list[str] = Field(default_factory=list, description="path inside ONE job item to its title")
    url: list[str] = Field(default_factory=list, description="path inside one item to its job page link, if it has one")
    id: list[str] = Field(default_factory=list, description="path inside one item to its job id")
    location: list[str] = Field(default_factory=list, description="path inside one item to its location(s)")
    posted: list[str] = Field(default_factory=list, description="path inside one item to its posted date")
    url_template: str = Field("", description="when items have no link: the full job page address with {id}, taken from PAGE LINKS")
    keyword_where: str = Field("", description="'query' or 'body' — where the search keyword sits in that request; '' if not")
    keyword_path: list[str] = Field(default_factory=list, description="query parameter name, or key path in the JSON/form body")
    page_where: str = Field("", description="'query' or 'body' — where the page number / offset sits; '' if not")
    page_path: list[str] = Field(default_factory=list)
    page_start: int = 0
    page_step: int = Field(1, description="1 for a page number; the page size for an offset")
    reason: str = ""

    @field_validator("list_path", "title", "url", "id", "location", "posted", "keyword_path", "page_path", mode="before")
    @classmethod
    def _as_path(cls, v: Any) -> Any:
        """Models sometimes write a path as one string ("data.jobs"): read it as the list of keys it means."""
        if isinstance(v, str):
            return [k for k in re.split(r"[./]", v) if k] if v.strip() else []
        return [str(k) for k in v] if isinstance(v, list) else v


_API_SYS = """You reverse-engineer a company careers website. A browser searched its jobs (with a location and maybe a
keyword filter) and recorded the JSON answers the page loaded. Pick the ONE answer that is the list of job openings for
that search — the call made AFTER the filters were applied, whose items are individual jobs (not facets, filters,
locations, suggestions, analytics or config). Then map it: the path to the job list and, inside one job item, the
paths to title, link, id, location and posted date (use only keys that really exist in the sample). If items carry no
link, build url_template from PAGE LINKS: a job page address with the item's id replaced by {id}.
Also say where the search keyword and the page number / offset sit in that request so other keywords and pages can be
asked. Paths are lists of keys; list positions are written as numbers in quotes ("0").
When JOB TITLES THE PAGE SHOWS are given, the right answer is the one whose items carry those titles."""


class _LinkChoice(BaseModel):
    group: int = Field(-1, description="number of the link group whose links each open ONE job posting; -1 if none")
    title_from: str = Field("text", description="'text' if the link's own words are the job title, 'heading' if the card heading is")
    reason: str = ""


_LINK_SYS = """You read the links of a company careers search results page, grouped by the shape of their address.
Pick the ONE group whose links each open a single job posting (not categories, locations, pagination, social or
navigation links). Say whether the job title is the link's own text or the heading of the card around it."""


def _sample(obj: Any, limit: int = 1800) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…"


def _trimmed(data: Any, path: list) -> Any:
    """The JSON with its biggest job-like list cut to 2 items, so the AI sees the real structure in a few tokens."""
    import copy
    d = copy.deepcopy(data)
    parent = recipes.get_path(d, path[:-1]) if path else None
    if path and isinstance(parent, (dict, list)):
        key = int(path[-1]) if isinstance(parent, list) else path[-1]
        try:
            parent[key] = parent[key][:2]
        except (KeyError, IndexError, TypeError):
            pass
    elif isinstance(d, list):
        d = d[:2]
    return d


async def _ask_links(anchors: list[dict], results_url: str, company: str) -> Optional[tuple[str, str]]:
    from jobhunterx.intelligence.llm_structured import call_structured
    groups = sorted(recipes.link_groups(anchors, results_url).items(), key=lambda kv: -len(kv[1]))[:10]
    if not groups:
        return None
    blocks = []
    for i, (sig, links) in enumerate(groups):
        ex = "; ".join(f"text='{a.get('text', '')[:60]}' heading='{a.get('heading', '')[:60]}'" for a in links[:3])
        blocks.append(f"[{i}] {sig}  ({len(links)} links)  e.g. {ex}")
    user = f"COMPANY: {company}\nRESULTS PAGE: {results_url}\n\nLINK GROUPS:\n" + "\n".join(blocks)
    try:
        res, _ = await call_structured(task="scout_links", version="v2", model=_LinkChoice, system=_LINK_SYS, user=user,
                                       chain="extraction", max_tokens=400, cache_parts=(user,))
    except Exception as exc:
        log.info("scout_links_ai_failed", error=str(exc)[:120])
        return None
    if not res or not (0 <= res.group < len(groups)):
        return None
    return groups[res.group][0], ("heading" if res.title_from.strip().lower() == "heading" else "text")


async def _try_ats(urls: list[str], keyword: str, location: str) -> Optional[tuple[Recipe, list[JobLink]]]:
    from jobhunterx.discovery import ats
    seen = set()
    for url in urls:
        ref = ats.parse_ats_url(url)
        if not ref or ref.kind not in ats.ADAPTERS or (ref.kind, ref.token.lower()) in seen:
            continue
        seen.add((ref.kind, ref.token.lower()))
        r = Recipe(kind="ats", ats_kind=ref.kind, ats_token=ref.token, location=location, keyword=keyword)
        links = [l for l in await recipes.run_ats(r) if recipes.in_location(l, location)]
        if not links and keyword:                     # the keyword may be too narrow on this board
            r.keyword = ""
            links = [l for l in await recipes.run_ats(r) if recipes.in_location(l, location)]
        if links:
            return r, links
    return None


def _site(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    return ".".join(host.split(".")[-2:])


def _on_page(items: list, text: str) -> int:
    """How many items of a list show one of their own words on the page (a job list shows its titles)."""
    hits = 0
    for it in items[:15]:
        vals = [v for v in (it.values() if isinstance(it, dict) else []) if isinstance(v, str) and 5 <= len(v) <= 160]
        hits += any(_norm(v) in text for v in vals)
    return hits


def _rank_responses(captured: list[dict], page_text: str, results_url: str, skip: set[int]) -> list[tuple[dict, list, int]]:
    """The recorded answers most likely to be the job list → [(response, path to its list, index)]. Ranked by how many
    of the list's items appear on the page, then by coming from the careers site itself, then by size — so cookie
    banners, analytics and menus (often the biggest lists) do not crowd out the job search answer."""
    text, site = _norm(page_text), _site(results_url)
    scored = []
    for i, c in enumerate(captured):
        if "json" not in c or i in skip:
            continue
        lists = recipes.json_lists(c["json"])
        if not lists:
            continue
        best = max(lists, key=lambda x: (_on_page(recipes.get_path(c["json"], x[0]) or [], text), x[1]))
        items = recipes.get_path(c["json"], best[0]) or []
        scored.append(((_on_page(items, text), _site(c["url"]) == site, best[1]), c, best[0], i))
    return [x[1:] for x in sorted(scored, key=lambda x: x[0], reverse=True)[:6]]


async def _ask_api(captured: list[dict], anchors: list[dict], company: str, location: str, keyword: str,
                   page_titles: list[str], skip: set[int], page_text: str = "",
                   results_url: str = "") -> Optional[tuple[dict, _ApiChoice, int]]:
    from jobhunterx.intelligence.llm_structured import call_structured
    cands = _rank_responses(captured, page_text, results_url, skip)
    if not cands:
        return None
    blocks = []
    for i, (c, path, _) in enumerate(cands):
        blocks.append(f"[{i}] {c['method']} {c['url'][:500]}\n" + (f"BODY: {c['body'][:700]}\n" if c.get("body") else "")
                      + f"JSON (biggest list cut to 2 items): {_sample(_trimmed(c['json'], path))}")
    groups = recipes.link_groups(anchors, "")
    links = [a["href"] for g in sorted(groups.values(), key=len, reverse=True)[:3] for a in g[:4]]
    user = (f"COMPANY: {company}\nLOCATION FILTER: {location or '(none)'}\nKEYWORD TYPED: {keyword or '(none)'}\n"
            + (f"JOB TITLES THE PAGE SHOWS: {' | '.join(page_titles[:10])}\n" if page_titles else "") + "\n"
            + "\n\n".join(blocks) + "\n\nPAGE LINKS:\n" + "\n".join(links[:12]))
    try:
        res, _ = await call_structured(task="scout_api", version="v2", model=_ApiChoice, system=_API_SYS, user=user,
                                       chain="extraction", max_tokens=1200, cache_parts=(user,))
    except Exception as exc:
        log.info("scout_api_ai_failed", error=str(exc)[:120])
        return None
    if not res or not (0 <= res.index < len(cands)) or not res.title:
        return None
    c, _, orig = cands[res.index]
    return c, res, orig


def _page_match(links: list[JobLink], page_text: str) -> float:
    """Share of a list's first titles that appear on the page the agent finished on (1.0 when the text is unknown)."""
    if not page_text:
        return 1.0
    titles = [_norm(l.title) for l in links[:12] if len(l.title.strip()) >= 5]
    if not titles:
        return 0.0
    text = _norm(page_text)
    return sum(t in text for t in titles) / len(titles)


def _looks_right(links: list[JobLink], page_text: str, page_count: int) -> str:
    """'' when a replayed list is the list the page shows; else why not."""
    if not links:
        return "no jobs"
    match = _page_match(links, page_text)
    if match < PAGE_MATCH:
        return f"only {round(match * 100)}% of its titles are on the page (a different list)"
    if page_count >= 6 and len(links) < page_count / 3:
        return f"{len(links)} jobs while the page shows about {page_count}"
    return ""


async def _try_api(captured: list[dict], anchors: list[dict], company: str, location: str, keyword: str,
                   results_url: str, page_text: str, page_titles: list[str],
                   page_count: int) -> Optional[tuple[Recipe, list[JobLink]]]:
    """The AI picks the job search call; it is replayed from plain Python and must give the list the page showed.
    A pick that does not is set aside and the AI picks again (at most 3 times)."""
    skip: set[int] = set()
    for _ in range(3):
        picked = await _ask_api(captured, anchors, company, location, keyword, page_titles, skip, page_text, results_url)
        if not picked:
            return None
        c, ch, idx = picked
        skip.add(idx)
        fields = {k: v for k, v in {"title": ch.title, "url": ch.url, "id": ch.id, "location": ch.location,
                                    "posted": ch.posted}.items() if v}
        r = Recipe(kind="api", results_url=results_url, location=location, keyword=keyword, method=c["method"], url=c["url"],
                   headers=c["headers"], body=c.get("body"), list_path=ch.list_path, fields=fields,
                   url_template=ch.url_template if "{id}" in ch.url_template else "", base_url=c["url"],
                   keyword_at={"where": ch.keyword_where, "path": ch.keyword_path} if ch.keyword_where in ("query", "body") and ch.keyword_path else None,
                   page_at={"where": ch.page_where, "path": ch.page_path, "start": ch.page_start, "step": max(1, ch.page_step)}
                   if ch.page_where in ("query", "body") and ch.page_path else None)
        # session headers (csrf tokens, request times) expire: keep them only if the call fails without them
        full = dict(r.headers)
        r.headers = {k: v for k, v in full.items() if not k.startswith("x-")}
        links = [l for l in await recipes.run_api(r, keyword or None) if l.url]
        why = _looks_right(links, page_text, page_count)
        if why and r.headers != full:
            r.headers = full
            links = [l for l in await recipes.run_api(r, keyword or None) if l.url]
            why = _looks_right(links, page_text, page_count)
        if why:
            log.info("scout_api_rejected", url=c["url"][:100], why=why, reason=ch.reason[:100])
            continue
        if r.keyword_at and keyword:                  # a keyword slot that changes nothing would hide every other role
            other = await recipes.run_api(r, "")
            if other and {l.url for l in other} == {l.url for l in links}:
                r.keyword_at = None
        return r, links
    return None


async def _try_html(anchors: list[dict], results_url: str, company: str, location: str,
                    keyword: str) -> Optional[tuple[Recipe, list[JobLink], bool]]:
    picked = await _ask_links(anchors, results_url, company)
    if not picked:
        return None
    sig, title_from = picked
    r = Recipe(kind="html", results_url=results_url, location=location, keyword=keyword,
               link_pattern=recipes.signature_regex(sig), title_from=title_from)
    seen = [JobLink(title=(a.get("heading") if title_from == "heading" else a.get("text")) or a.get("text") or "", url=a["href"])
            for a in recipes.link_groups(anchors, results_url).get(sig, [])]
    plain = await recipes.run_html(r)
    if plain and len(plain) >= len(seen) // 2:
        return r, plain, True
    r.kind = "browser"                                # the list only appears after JavaScript runs
    return r, seen, False


def _page_jobs(anchors: list[dict], url: str) -> tuple[list[str], int]:
    """The titles of the biggest group of same-shaped links on the page (its job cards, usually) and how many there are."""
    groups = sorted(recipes.link_groups(anchors, url).values(), key=len, reverse=True)
    if not groups:
        return [], 0
    titles = [(a.get("text") or a.get("heading") or "").strip() for a in groups[0]]
    return [t for t in titles if len(t) >= 5][:15], min(len(groups[0]), 25)


async def build_recipe(captured: list[dict], anchors: list[dict], results_url: str, final_url: str,
                       company: str, location: str, keyword: str,
                       page_text: str = "") -> tuple[Optional[Recipe], list[JobLink], str]:
    """Pick the best way to list this company's jobs again → (recipe, jobs it lists now, how it was found).
    Every candidate is replayed from plain Python and must give the jobs the page showed before it is kept."""
    urls = [results_url, final_url, *[c["url"] for c in captured], *[a.get("href", "") for a in anchors[:400]]]
    hit = await _try_ats([u for u in urls if u], keyword, location)
    if hit:
        return hit[0], hit[1], f"{hit[0].ats_kind.title()} job board"
    titles, count = _page_jobs(anchors, results_url or final_url)
    api = await _try_api(captured, anchors, company, location, keyword, results_url, page_text, titles, count)
    if api:
        return api[0], api[1], "the site's own job search API"
    html = await _try_html(anchors, results_url or final_url, company, location, keyword)
    if html:
        return html[0], html[1], "the careers results page" if html[2] else "the careers results page (needs a browser)"
    return None, [], ""


# --------------------------------------------------------------------------- the run

async def _new_browser() -> Any:
    import os
    from browser_use import BrowserProfile, BrowserSession
    from jobhunterx.agents import browser_agent as ba
    from jobhunterx.config.settings import get_settings
    cdp_url = (getattr(get_settings(), "browser_cdp_url", "") or os.getenv("BROWSER_CDP_URL") or "").strip()
    if cdp_url:
        profile = BrowserProfile(cdp_url=cdp_url, keep_alive=True)
    else:
        exe = ba._real_chrome()
        profile = BrowserProfile(
            headless=True, executable_path=exe, user_data_dir=None, keep_alive=True,     # closed by us, after reading
            user_agent=ba._user_agent(ba._chrome_major(exe)) if exe else None,
            viewport={"width": 1280, "height": 900}, enable_default_extensions=False,
            args=["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check",
                  f"--lang={os.getenv('BROWSER_LANG', 'en-IN')}"])
    bs = BrowserSession(browser_profile=profile)
    await bs.start()
    return bs


def _tools() -> Any:
    from browser_use import ActionResult, Controller
    from jobhunterx.agents import browser_agent as ba
    controller = Controller()

    @controller.action("Pick an option in ANY dropdown, filter list, combobox or location suggestion list. Give the "
                       "element index and the value (e.g. value='Hyderabad'); optional search = what to type. It opens "
                       "the list, types, WAITS for the options to load, clicks the best match and checks it stuck.")
    async def choose_option(index: int, value: str, browser_session, search: str = "", wait_seconds: float = 8) -> ActionResult:
        return await ba._choose_option(browser_session, index, value, search, wait_seconds)

    @controller.action("Wait for a security check (Cloudflare 'Just a moment', Turnstile, 'I'm not a robot') to clear; "
                       "clicks its checkbox once if there is one.")
    async def wait_for_human_check(browser_session, max_seconds: int = 25) -> ActionResult:
        return await ba._wait_for_human_check(browser_session, max_seconds)

    return controller


class _StartPick(BaseModel):
    index: int = Field(-1, description="number of the result that is the company's own careers site or its job board; -1 if none is")
    reason: str = ""


_START_SYS = """You choose where a browser should start to find one company's open jobs. From web search results, pick
the company's OWN careers site: best its job search / job list page, else its careers home page, or the job board it
uses (Workday, Greenhouse, Lever, SuccessFactors, iCIMS, Eightfold, Phenom, Oracle…). Never a job portal or aggregator
(LinkedIn, Naukri, Indeed, Glassdoor, Foundit, Instahyre…), a news or review page, or a different company with a
similar name. When the place is in India and the company has an India careers site or page, prefer it."""


async def _find_start(company: str, location: str) -> str:
    """The company's careers page from one free web search and one small AI call ('' when unsure). Cached per company."""
    from jobhunterx.discovery.search import router_config
    from jobhunterx.intelligence.llm_structured import call_structured
    from jobhunterx.tools.search_router import SearchRouter
    q = f"{company} careers jobs" + (f" {location}" if location else "")
    try:
        items = await SearchRouter(config=router_config()).execute_query(q, max_results=10, providers=["ddgs"])
    except Exception as exc:
        log.info("scout_search_failed", error=str(exc)[:120])
        return ""
    items = [it for it in items if (it.url or "").startswith("http")][:10]
    if not items:
        return ""
    user = f"COMPANY: {company}\nPLACE: {location or '(any)'}\n\nRESULTS:\n" + "\n".join(
        f"[{i}] {(it.title or '')[:90]} | {it.url[:200]} | {(it.snippet or '')[:140]}" for i, it in enumerate(items))
    try:
        res, _ = await call_structured(task="scout_start", version="v1", model=_StartPick, system=_START_SYS, user=user,
                                       chain="fast", max_tokens=300, cache_parts=(user,))
    except Exception as exc:
        log.info("scout_start_ai_failed", error=str(exc)[:120])
        return ""
    return items[res.index].url if res and 0 <= res.index < len(items) else ""


async def _page_urls(url: str) -> list[str]:
    """Where a careers page leads without a browser: its final address and every link / frame on it."""
    from jobhunterx.discovery import net
    res = await net.fetch(url)
    out = [u for u in (url, res.url) if u]
    if not res.ok or not res.text:
        return out
    try:
        from selectolax.lexbor import LexborHTMLParser
        tree = LexborHTMLParser(res.text)
        for n in tree.css("a[href], iframe[src]"):
            v = n.attributes.get("href") or n.attributes.get("src") or ""
            if v and not v.startswith(("#", "javascript:", "mailto:")):
                out.append(urljoin(res.url or url, v))
            if len(out) > 800:
                break
    except Exception as exc:
        log.debug("scout_page_parse_failed", error=str(exc)[:100])
    return out


async def scout(company: str, location: str = "", keyword: str = "", on_step: Optional[Step] = None) -> dict:
    """Find the company's careers site and learn a recipe.

    1. A web search and one small AI call find the careers page. If it is (or leads to) a known job board, the board is
       listed straight away — no browser at all.
    2. Otherwise the browser agent starts ON that page (not on a search engine), applies the filters and finishes.
    3. The finished page is checked (a job list is visible, the place is applied); if not, the agent gets the exact
       problem and a few more steps.
    4. A recipe is learned from what the page loaded, and it is kept only if replaying it gives the jobs the page showed.

    Runs on the browser worker loop. Returns {"ok", "recipe", "jobs", "found_via", "results_url", "notes", "error"}."""
    from browser_use import Agent
    from jobhunterx.agents import browser_agent as ba

    async def say(msg: str, url: str = "") -> None:
        if on_step:
            try:
                await on_step(msg, url)
            except Exception:
                pass

    try:
        llm, fallback = ba._build_llms()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    await say(f"Looking up {company}'s careers site")
    start = await _find_start(company, location)
    if start:
        await say(f"Found {urlparse(start).netloc} — checking which job board it uses", start)
        hit = await _try_ats(await _page_urls(start), keyword, location)
        if hit:
            r, links = hit
            via = f"{r.ats_kind.title()} job board"
            r.results_url = start
            log.info("scout_done", company=company, kind=r.kind, jobs=len(links), via=via, browser=False)
            return {"ok": True, "recipe": r.model_dump(), "jobs": [j.model_dump() for j in links[:50]], "found_via": via,
                    "results_url": start, "notes": "listed straight from its job board (no browser needed)",
                    "careers_host": urlparse(start).netloc, "seen": {"responses": 0, "links": 0}}

    await say("Starting a private browser")
    bs = await _new_browser()
    rec = Recorder(bs)
    from jobhunterx.agents import live_view
    cast = asyncio.ensure_future(_cast(bs))          # shown live in the app (Companies → scout window)
    try:
        rec.start()
        await rec.watch_focus()

        async def on_agent_step(state: Any, model_output: Any, step_num: int) -> None:
            await rec.watch_focus()
            goal = (getattr(model_output, "next_goal", "") or "").strip()
            if goal:
                try:
                    url = await bs.get_current_page_url()
                except Exception:
                    url = ""
                await say(goal[:160], url)

        query = f"{company} careers jobs" + (f" {location}" if location else "")
        first = start or "https://html.duckduckgo.com/html/?q=" + query.replace(" ", "+")
        kwargs: dict[str, Any] = {
            "task": _prompt(company, location, keyword, start), "llm": llm, "controller": _tools(), "browser_session": bs,
            "register_new_step_callback": on_agent_step, "use_vision": "auto",
            "initial_actions": [{"navigate": {"url": first, "new_tab": False}}],
            # token-lean: no end-of-run judge call, a smaller page outline per step, a few actions per step
            "use_judge": False, "max_clickable_elements_length": 24000, "max_actions_per_step": 4,
        }
        if fallback is not None:
            kwargs["fallback_llm"] = fallback
        agent = Agent(**kwargs)
        history = await agent.run(max_steps=MAX_STEPS)

        async def finished_page() -> tuple[str, list[dict], str]:
            await asyncio.sleep(1.5)
            await rec.settle()
            try:
                url = await bs.get_current_page_url()
            except Exception:
                url = ""
            return url, await _anchors(bs), await _page_text(bs)

        final_url, anchors, page_text = await finished_page()
        problem = _page_problem(page_text, anchors, rec.captured, final_url, location)
        if problem and history and history.is_done():
            await say("Not right yet: " + problem.split(".")[0])
            agent.add_new_task(FOLLOW_UP.format(problem=problem, company=company))
            history = await agent.run(max_steps=agent.state.n_steps + FOLLOW_UP_STEPS)   # steps count across runs
            final_url, anchors, page_text = await finished_page()
        final_text = (history.final_result() or "") if history else ""
        ok_agent = bool(history and history.is_done() and history.is_successful())
        fields = _done_fields(final_text)
        await say("Reading what the careers site loaded")
        results_url = fields.get("RESULTS_URL", "").strip("<> ") or final_url
        if not results_url.startswith("http"):
            results_url = final_url
        used = fields.get("KEYWORD_USED", "")
        used = "" if used.lower() in ("", "none", "n/a", "-") else used
        log.info("scout_recording", company=company, responses=len(rec.captured),
                 json_lists=sum(1 for x in rec.captured if "json" in x), links=len(anchors),
                 link_groups=len(recipes.link_groups(anchors, results_url)), page_chars=len(page_text), problem=problem[:60])
        recipe, jobs, via = await build_recipe(rec.captured, anchors, results_url, final_url, company, location, used,
                                               page_text)
        seen = {"responses": len(rec.captured), "links": len(anchors)}
        if recipe is None:
            why = fields.get("NOTES") or (problem.split(".")[0] if problem else "the agent could not reach a job list"
                                          if not ok_agent else "the job list could not be read again without the agent")
            return {"ok": False, "error": f"Could not learn how to list {company}'s jobs: {why}.",
                    "results_url": results_url, "notes": fields.get("NOTES", ""), "seen": seen}
        if recipe.kind in ("html", "browser") and used:   # a search word in the results address can be swapped later
            from urllib.parse import parse_qsl
            for k, v in parse_qsl(urlparse(results_url).query):
                if v.strip().lower() == used.lower():
                    recipe.keyword_at = {"where": "query", "path": [k]}
        shown = _shown_count(fields)
        log.info("scout_done", company=company, kind=recipe.kind, jobs=len(jobs), shown=shown, via=via, browser=True)
        return {"ok": True, "recipe": recipe.model_dump(), "jobs": [j.model_dump() for j in jobs[:50]],
                "found_via": via, "results_url": results_url, "notes": fields.get("NOTES", ""),
                "careers_host": urlparse(results_url).netloc, "seen": seen}
    except Exception as exc:
        log.warning("scout_failed", company=company, error=str(exc)[:300])
        return {"ok": False, "error": f"The scout stopped: {str(exc)[:200]}"}
    finally:
        cast.cancel()
        live_view.clear_frame("scout")
        try:
            await asyncio.wait_for(bs.kill(), timeout=15)
        except Exception:
            pass


async def _cast(bs: Any) -> None:
    """Screenshots of the scout's tab, a few per second, to the app's scout window (watch-only)."""
    from jobhunterx.agents import live_view
    while True:
        try:
            cdp = await bs.get_or_create_cdp_session(focus=False)
            shot = await cdp.cdp_client.send.Page.captureScreenshot(params={"format": "jpeg", "quality": 55},
                                                                     session_id=cdp.session_id)
            if shot.get("data"):
                live_view.publish_frame(shot["data"], {}, "scout")
        except asyncio.CancelledError:
            raise
        except Exception as exc:                       # navigation in flight / tab switching: next tick
            log.debug("scout_cast_retry", error=str(exc)[:100])
        await asyncio.sleep(0.7)


async def read_listing(r: Recipe) -> list[JobLink]:
    """`browser` recipes: open the results page headless (no AI) and read the job links once they render."""
    from jobhunterx.agents import browser_worker

    async def _go() -> list[JobLink]:
        bs = await _new_browser()
        try:
            await bs.navigate_to(r.results_url)
            rx = re.compile(r.link_pattern)
            links: list[JobLink] = []
            for _ in range(12):
                await asyncio.sleep(1)
                anchors = await _anchors(bs)
                seen, links = set(), []
                for a in anchors:
                    href = (a.get("href") or "").split("#")[0]
                    if href and href not in seen and rx.fullmatch(href) and len(a.get("text") or "") >= 4:
                        seen.add(href)
                        links.append(JobLink(title=a["text"], url=href))
                if len(links) >= 3:
                    break
            return links
        finally:
            try:
                await asyncio.wait_for(bs.kill(), timeout=15)
            except Exception:
                pass

    if browser_worker.on_worker():
        return await _go()
    return await browser_worker.run(_go())
