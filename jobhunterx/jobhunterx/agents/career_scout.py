"""
Company Scout — a browser agent that finds one company's real careers site, applies the filters (location, role
keyword) the way a person would, and learns how to list those jobs again without a browser.

One-time work per company + place. While the agent clicks through the site, every JSON / HTML answer the page loads
is recorded. Afterwards the recording is read (no AI): a known job board (Greenhouse, Workday…), the site's own
search API, or the shape of job links on the results page. The best one that also works from plain Python is stored
as a recipe (discovery/recipes.py); from then on the company is checked in seconds on every search and watch.

Runs on the browser worker loop with its own throw-away headless Chrome, so it never touches the auto-apply browser.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import recipes
from jobhunterx.discovery.recipes import JobLink, Recipe

log = get_logger("career_scout")

MAX_STEPS = 30
MAX_CAPTURE = 120                  # responses kept per scout
MAX_BODY = 3_000_000

Step = Callable[..., Awaitable[None]]          # on_step(message, url="")

SCOUT_PROMPT = """You are the Company Scout. Your job: open {company}'s OWN careers website and show its open jobs
filtered the way a candidate needs, so the result page can be read again later.

COMPANY: {company}
LOCATION FILTER: {location_line}
ROLE KEYWORD: {keyword_line}

STEPS
1. Find the company's official careers job search. Start with the search engine page that is open, or go straight to
   a URL you are sure of (for example careers.<company>.com, <company>.com/careers, jobs.<company>.com). Use ONLY the
   company's own site or the job board it links to (Workday, Greenhouse, Lever, SuccessFactors, iCIMS, Eightfold,
   Phenom…). NEVER use LinkedIn, Naukri, Indeed, Glassdoor, Instahyre, Foundit, Cutshort or any other job portal.
2. Open the page that LISTS jobs (a "Search jobs" / "View all jobs" / "Find your role" page), not one job.
3. Apply the filters on the site itself:
   - Location: use the site's location filter or location search box. Type the place, WAIT for the suggestions,
     and pick the option for that place (use `choose_option` for every dropdown or suggestion list).
     If the site lists the place several ways (city / "City, State, Country" / country), pick the city.
   - Keyword: type the role keyword into the site's job search box and run the search. If it returns no jobs,
     try ONE broader keyword (e.g. "Engineer"); if still none, clear the keyword and keep only the location.
4. Check that the results list shows jobs in that place. Scroll down once so the list fully loads.
5. Finish with `done` and success=true. Write exactly:
   RESULTS_URL: <the address of the filtered results page>
   KEYWORD_USED: <the keyword that is in the search box now, or none>
   JOBS_SHOWN: <how many jobs the page says it found, or how many you see>
   NOTES: <one short line, e.g. "location filter is a dropdown; results load as you scroll">

RULES
- Close cookie banners ("Accept" / "Reject all") and pop-ups. Never sign in, create an account, apply, or upload.
- If a security check appears, call `wait_for_human_check` once. If it does not clear, finish with success=false and
  NOTES: blocked.
- If the company truly has no careers site with a job list, finish with success=false and say so in NOTES.
- Keep your thinking to one short sentence per step."""


def _prompt(company: str, location: str, keyword: str) -> str:
    return SCOUT_PROMPT.format(
        company=company,
        location_line=location or "none — keep all locations (but prefer India if the site asks for a country)",
        keyword_line=keyword or "none — list all jobs")


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


_API_SYS = """You reverse-engineer a company careers website. A browser searched its jobs (with a location and maybe a
keyword filter) and recorded the JSON answers the page loaded. Pick the ONE answer that is the list of job openings for
that search — the call made AFTER the filters were applied, whose items are individual jobs (not facets, filters,
locations, suggestions, analytics or config). Then map it: the path to the job list and, inside one job item, the
paths to title, link, id, location and posted date (use only keys that really exist in the sample). If items carry no
link, build url_template from PAGE LINKS: a job page address with the item's id replaced by {id}.
Also say where the search keyword and the page number / offset sit in that request so other keywords and pages can be
asked. Paths are lists of keys; list positions are written as numbers in quotes ("0")."""


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


async def _ask_api(captured: list[dict], anchors: list[dict], company: str, location: str,
                   keyword: str) -> Optional[tuple[dict, _ApiChoice]]:
    from jobhunterx.intelligence.llm_structured import call_structured
    cands = []
    for c in captured:
        if "json" not in c:
            continue
        lists = recipes.json_lists(c["json"])
        if lists:
            cands.append((max(n for _, n in lists), c, max(lists, key=lambda x: x[1])[0]))
    cands = [x[1:] for x in sorted(cands, key=lambda x: -x[0])[:8]]
    if not cands:
        return None
    blocks = []
    for i, (c, path) in enumerate(cands):
        blocks.append(f"[{i}] {c['method']} {c['url'][:500]}\n" + (f"BODY: {c['body'][:700]}\n" if c.get("body") else "")
                      + f"JSON (biggest list cut to 2 items): {_sample(_trimmed(c['json'], path))}")
    groups = recipes.link_groups(anchors, "")
    links = [a["href"] for g in sorted(groups.values(), key=len, reverse=True)[:3] for a in g[:4]]
    user = (f"COMPANY: {company}\nLOCATION FILTER: {location or '(none)'}\nKEYWORD TYPED: {keyword or '(none)'}\n\n"
            + "\n\n".join(blocks) + "\n\nPAGE LINKS:\n" + "\n".join(links[:12]))
    try:
        res, _ = await call_structured(task="scout_api", version="v1", model=_ApiChoice, system=_API_SYS, user=user,
                                       chain="extraction", max_tokens=1200, cache_parts=(user,))
    except Exception as exc:
        log.info("scout_api_ai_failed", error=str(exc)[:120])
        return None
    if not res or not (0 <= res.index < len(cands)) or not res.title:
        return None
    return cands[res.index][0], res


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
        res, _ = await call_structured(task="scout_links", version="v1", model=_LinkChoice, system=_LINK_SYS, user=user,
                                       chain="fast", max_tokens=400, cache_parts=(user,))
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


async def _try_api(captured: list[dict], anchors: list[dict], company: str, location: str, keyword: str,
                   results_url: str) -> Optional[tuple[Recipe, list[JobLink]]]:
    picked = await _ask_api(captured, anchors, company, location, keyword)
    if not picked:
        return None
    c, ch = picked
    fields = {k: v for k, v in {"title": ch.title, "url": ch.url, "id": ch.id, "location": ch.location,
                                "posted": ch.posted}.items() if v}
    r = Recipe(kind="api", results_url=results_url, location=location, keyword=keyword, method=c["method"], url=c["url"],
               headers=c["headers"], body=c.get("body"), list_path=ch.list_path, fields=fields,
               url_template=ch.url_template if "{id}" in ch.url_template else "", base_url=c["url"],
               keyword_at={"where": ch.keyword_where, "path": ch.keyword_path} if ch.keyword_where in ("query", "body") and ch.keyword_path else None,
               page_at={"where": ch.page_where, "path": ch.page_path, "start": ch.page_start, "step": max(1, ch.page_step)}
               if ch.page_where in ("query", "body") and ch.page_path else None)
    links = [l for l in await recipes.run_api(r, keyword or None) if l.url]      # replayed from plain Python
    if links:
        return r, links
    log.info("scout_api_not_replayable", url=c["url"][:100], reason=ch.reason[:120])
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


async def build_recipe(captured: list[dict], anchors: list[dict], results_url: str, final_url: str,
                       company: str, location: str, keyword: str) -> tuple[Optional[Recipe], list[JobLink], str]:
    """Pick the best way to list this company's jobs again → (recipe, jobs it lists now, how it was found)."""
    urls = [results_url, final_url, *[c["url"] for c in captured], *[a.get("href", "") for a in anchors[:400]]]
    hit = await _try_ats([u for u in urls if u], keyword, location)
    if hit:
        return hit[0], hit[1], f"{hit[0].ats_kind.title()} job board"
    api = await _try_api(captured, anchors, company, location, keyword, results_url)
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


async def scout(company: str, location: str = "", keyword: str = "", on_step: Optional[Step] = None) -> dict:
    """Find the company's careers site and learn a recipe. Runs on the browser worker loop.

    Returns {"ok", "recipe", "jobs", "found_via", "results_url", "notes", "error"}."""
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
        kwargs: dict[str, Any] = {
            "task": _prompt(company, location, keyword), "llm": llm, "controller": _tools(), "browser_session": bs,
            "register_new_step_callback": on_agent_step, "use_vision": "auto",
            "initial_actions": [{"navigate": {"url": "https://html.duckduckgo.com/html/?q=" + query.replace(" ", "+"),
                                              "new_tab": False}}],
        }
        if fallback is not None:
            kwargs["fallback_llm"] = fallback
        agent = Agent(**kwargs)
        history = await agent.run(max_steps=MAX_STEPS)
        final_text = (history.final_result() or "") if history else ""
        ok_agent = bool(history and history.is_done() and history.is_successful())
        fields = _done_fields(final_text)
        await say("Reading what the careers site loaded")
        await asyncio.sleep(1.5)
        await rec.settle()
        try:
            final_url = await bs.get_current_page_url()
        except Exception:
            final_url = ""
        anchors = await _anchors(bs)
        results_url = fields.get("RESULTS_URL", "").strip("<> ") or final_url
        if not results_url.startswith("http"):
            results_url = final_url
        used = fields.get("KEYWORD_USED", "")
        used = "" if used.lower() in ("", "none", "n/a", "-") else used
        recipe, jobs, via = await build_recipe(rec.captured, anchors, results_url, final_url, company, location, used)
        seen = {"responses": len(rec.captured), "links": len(anchors)}
        if recipe is None:
            why = fields.get("NOTES") or ("the agent could not reach a job list" if not ok_agent else
                                          "the job list could not be read again without the agent")
            return {"ok": False, "error": f"Could not learn how to list {company}'s jobs: {why}.",
                    "results_url": results_url, "notes": fields.get("NOTES", ""), "seen": seen}
        if recipe.kind == "html" and used:            # a search word in the results address can be swapped later
            from urllib.parse import parse_qsl
            for k, v in parse_qsl(urlparse(results_url).query):
                if v.strip().lower() == used.lower():
                    recipe.keyword_at = {"where": "query", "path": [k]}
        log.info("scout_done", company=company, kind=recipe.kind, jobs=len(jobs), via=via)
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
