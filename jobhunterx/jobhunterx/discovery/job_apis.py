"""
Optional extra job sources: Adzuna (India, needs a free key) and Hacker News (YC jobs + "Who is hiring?", opt-in).

Why these three, and how each is used (see README "Job Sources"):

* Adzuna — official API with an India index, newest-first, filterable by age. Needs a free key (`app_id:app_key`).
  Its listings are aggregated, so the same role is looked up on the employer's own job board first.
* Hacker News — no key. YC startups' job posts and the monthly "Who is hiring?" thread, read through the public
  Algolia/Firebase APIs. Only posts that name India, one of your cities, or an India-friendly remote role are kept.
  Posts often carry a direct hiring email, which the Connector can use.

All of them are discovery only: a lead becomes a JobPosting, goes through the same dedupe, validation and matching as
every other source, and a failing or blocked source never fails the search.
"""

from __future__ import annotations

import asyncio
import html as _html
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

import httpx

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import FieldCheck, JobPosting, Salary, SourceRef
from jobhunterx.intelligence.text import common_words, title_overlap

log = get_logger("job_apis")

CONCURRENCY = 3
BUDGET_S = 40.0
FIRST_PARTY_TIMEOUT_S = 10
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"
HN_JOBS_URL = "https://hacker-news.firebaseio.com/v0/jobstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
HN_MAX_AGE_DAYS = 45
_HEADERS = {"User-Agent": "JobHunterX/1.0 (+https://github.com/kvcops/jobhunterx)", "Accept": "application/json"}
_INDIA = re.compile(r"(?i)\b(india|hyderabad|secunderabad|bengaluru|bangalore|chennai|pune|mumbai|delhi|gurugram|gurgaon|noida|"
                    r"kochi|coimbatore|vizag|visakhapatnam|thiruvananthapuram|trivandrum|ist)\b")
_REMOTE_OPEN = re.compile(r"(?i)\b(remote\s*\(?\s*(worldwide|global|anywhere|apac|asia)|worldwide|anywhere in the world|apac)\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"https?://[^\s<>\"')]+")

Progress = Optional[Callable[[str], Awaitable[None]]]


def _clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _text(s: str) -> str:
    """HN comments are HTML: paragraphs and line breaks become newlines, links keep their address."""
    s = re.sub(r'(?is)<a [^>]*href="([^"]+)"[^>]*>.*?</a>', lambda m: " " + _html.unescape(m.group(1)) + " ", s or "")
    s = re.sub(r"(?i)<br\s*/?>|<p>|</p>|</li>", "\n", s)
    lines = [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", ln))).strip() for ln in s.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _when(value) -> Optional[datetime]:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


_client: Optional[tuple[asyncio.AbstractEventLoop, httpx.AsyncClient]] = None


def _http() -> httpx.AsyncClient:
    global _client
    loop = asyncio.get_running_loop()
    if _client is None or _client[0] is not loop or _client[1].is_closed:
        _client = (loop, httpx.AsyncClient(headers=_HEADERS, timeout=12, follow_redirects=True,
                                           limits=httpx.Limits(max_connections=CONCURRENCY + 2)))
    return _client[1]


async def _json(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None):
    """GET → parsed JSON, or None on any failure (a source that is down or out of quota is simply skipped)."""
    try:
        r = await _http().get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        log.debug("job_api_fetch_failed", host=url.split("/")[2], error=str(exc)[:80])
        return None
    if r.status_code != 200:
        log.info("job_api_status", host=url.split("/")[2], status=r.status_code)
        return None
    try:
        return r.json()
    except ValueError:
        return None


# ------------------------------------------------------------------ keys
def adzuna_credentials(key: Optional[str]) -> Optional[tuple[str, str]]:
    """`app_id:app_key` as one pasted value."""
    if not key or ":" not in key:
        return None
    app_id, app_key = (x.strip() for x in key.split(":", 1))
    return (app_id, app_key) if app_id and app_key else None


# ------------------------------------------------------------------ Adzuna
def parse_adzuna(data: dict, query: str = "") -> list[JobPosting]:
    out = []
    for r in (data or {}).get("results") or []:
        title = _clean(r.get("title", ""))
        company = _clean((r.get("company") or {}).get("display_name", ""))
        url = r.get("redirect_url") or ""
        if not (title and company and url):
            continue
        loc = r.get("location") or {}
        where = _clean(loc.get("display_name", "")) or ", ".join(loc.get("area") or [])
        p = JobPosting(title=title, company=company, location_raw=where, posted_at=_when(r.get("created")),
                       description=_clean(r.get("description", "")), canonical_url=url, apply_url=url,
                       employment_type={"full_time": "full_time", "part_time": "part_time"}.get(r.get("contract_time") or "", "")
                       or ("contract" if r.get("contract_type") == "contract" else ""),
                       discovered_by_query=query,
                       sources=[SourceRef(name="adzuna", kind="aggregator", url=url, confidence=0.5)])
        lo, hi = r.get("salary_min"), r.get("salary_max")
        if (lo or hi) and str(r.get("salary_is_predicted", "0")) != "1":          # a guessed salary is not a salary
            p.salary = Salary(min=lo, max=hi, currency="INR", period="year", raw=f"{lo or ''}–{hi or ''} INR/yr")
        p.validation.checks["title"] = FieldCheck(status="verified", value=title, evidence="Adzuna listing")
        if p.posted_at:
            p.validation.checks["posted_at"] = FieldCheck(status="verified", value=p.posted_at.date().isoformat(), evidence="Adzuna listing")
        out.append(p)
    return out


async def adzuna_search(creds: tuple[str, str], what: str, where: str, *, days: int = 14, per_page: int = 30) -> list[JobPosting]:
    params = {"app_id": creds[0], "app_key": creds[1], "what": what, "results_per_page": per_page,
              "max_days_old": days, "sort_by": "date", "content-type": "application/json"}
    if where and where.lower() != "india":
        params["where"] = where
    return parse_adzuna(await _json(ADZUNA_URL.format(page=1), params=params) or {}, query=f"{what} · {where or 'India'}")


# ------------------------------------------------------------------ Hacker News
def _hn_role(header: str, body: str, labels: list[str]) -> str:
    """The role named in a "Company | Role | Place | …" line; the best-matching part, else the second one."""
    parts = [p.strip() for p in header.split("|") if p.strip()]
    if len(parts) > 1:
        scored = sorted(parts[1:], key=lambda p: -title_overlap(p, labels))
        if title_overlap(scored[0], labels) > 0:
            return scored[0][:120]
        return parts[1][:120]
    return (body.split("\n", 1)[0])[:120]


def _hn_contact(text: str) -> tuple[str, str]:
    email = next(iter(_EMAIL.findall(text)), "")
    urls = [u.rstrip(".,;") for u in _URL.findall(text) if "ycombinator.com/item" not in u]
    return email, (urls[0] if urls else "")


def parse_hn_comment(hit: dict, labels: list[str], places: list[str], include_remote: bool) -> Optional[JobPosting]:
    """One "Who is hiring?" comment → a posting, or None when it is not for India / the candidate's field."""
    body = _text(hit.get("comment_text") or "")
    if not body:
        return None
    header = body.split("\n", 1)[0]
    head = f"{header} {body[:600]}"
    named = [p for p in places if p and p.lower() != "india" and re.search(rf"(?i)\b{re.escape(p)}\b", head)]
    in_india = bool(_INDIA.search(head))
    remote_open = include_remote and bool(_REMOTE_OPEN.search(head)) and not re.search(r"(?i)\b(us|usa|u\.s\.)\s*(only|based)\b", head)
    if not (named or in_india or remote_open):
        return None
    if title_overlap(_hn_role(header, body, labels), labels) <= 0:     # the role the post names, not any word in it
        return None
    company = re.sub(r"\s*\(.*?\)", "", header.split("|")[0]).strip()[:80] or "Hacker News employer"
    if not company or len(company) < 2:
        return None
    email, apply_link = _hn_contact(body)
    item = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
    parts = [x.strip() for x in header.split("|")]
    where = next((x for x in parts[1:] if _INDIA.search(x) or re.search(r"(?i)remote|onsite|hybrid", x)), "")
    desc = body[:20000] + (f"\n\nApply by email: {email}" if email else "")
    p = JobPosting(title=_hn_role(header, body, labels), company=company, location_raw=where or ("India" if in_india else "Remote"),
                   posted_at=_when(hit.get("created_at")), description=desc, canonical_url=item, apply_url=apply_link or item,
                   work_mode=WorkMode.REMOTE if re.search(r"(?i)\bremote\b", head) else WorkMode.UNKNOWN,
                   discovered_by_query="Hacker News: Who is hiring?",
                   sources=[SourceRef(name="hackernews", kind="job_board", url=item, confidence=0.55)])
    p.validation.checks["title"] = FieldCheck(status="inferred", value=p.title, evidence="Hacker News 'Who is hiring?' post")
    return p


def parse_hn_job(item: dict, labels: list[str]) -> Optional[JobPosting]:
    """A YC "X is hiring" job story from /jobstories (these have no location field: keep only India-friendly ones)."""
    if not item or item.get("type") != "job" or item.get("dead") or item.get("deleted"):
        return None
    title, body = _clean(item.get("title", "")), _text(item.get("text") or "")
    head = f"{title} {body[:600]}"
    if not (_INDIA.search(head) or _REMOTE_OPEN.search(head)) or title_overlap(head, labels) <= 0:
        return None
    company = re.split(r"(?i)\s+(?:\(yc|is hiring|are hiring|\(s\d|\(w\d|—|-\s)", title, maxsplit=1)[0].strip()[:80]
    email, apply_link = _hn_contact(body)
    url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
    p = JobPosting(title=title[:140], company=company or "YC startup", location_raw="India" if _INDIA.search(head) else "Remote",
                   posted_at=_when(item.get("time")), description=(body + (f"\n\nApply by email: {email}" if email else ""))[:20000],
                   canonical_url=url, apply_url=apply_link or url, discovered_by_query="Hacker News: YC jobs",
                   sources=[SourceRef(name="hackernews", kind="job_board", url=url, confidence=0.55)])
    p.validation.checks["title"] = FieldCheck(status="inferred", value=p.title, evidence="Hacker News job story")
    return p


async def hackernews_search(labels: list[str], places: list[str], *, include_remote: bool = True, limit: int = 30) -> list[JobPosting]:
    out: list[JobPosting] = []
    now = datetime.now(timezone.utc)
    # YC startups' own job posts (newest 200, any field) -------------------------------------------------------------
    ids = (await _json(HN_JOBS_URL) or [])[:60]
    sem = asyncio.Semaphore(CONCURRENCY + 3)

    async def story(i: int) -> Optional[JobPosting]:
        async with sem:
            return parse_hn_job(await _json(HN_ITEM_URL.format(id=i)) or {}, labels)
    out += [p for p in await asyncio.gather(*(story(i) for i in ids)) if p]
    # The monthly "Who is hiring?" thread (this month and, early in a month, the last one) -------------------------
    threads = await _json(HN_ALGOLIA, params={"tags": "story,author_whoishiring", "query": "who is hiring", "hitsPerPage": 4}) or {}
    stories = [h for h in threads.get("hits") or [] if re.search(r"(?i)who is hiring", h.get("title", ""))
               and not re.search(r"(?i)wants to be hired|freelancer", h.get("title", ""))][:2]
    cutoff = now - timedelta(days=HN_MAX_AGE_DAYS)
    seen: set[str] = set()
    terms = ["India", *[p for p in places if p and p.lower() != "india"][:3]]
    for s in stories:
        for term in terms:
            data = await _json(HN_ALGOLIA, params={"tags": f"comment,story_{s.get('objectID')}", "query": term, "hitsPerPage": 50}) or {}
            for hit in data.get("hits") or []:
                if hit.get("objectID") in seen or hit.get("parent_id") != int(s.get("objectID") or 0):   # top-level posts only
                    continue
                seen.add(hit.get("objectID"))
                d = _when(hit.get("created_at"))
                if d and d < cutoff:
                    continue
                p = parse_hn_comment(hit, labels, places, include_remote)
                if p:
                    out.append(p)
    out.sort(key=lambda p: p.posted_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return out[:limit]


# ------------------------------------------------------------------ orchestration
async def _prefer_first_party(p: JobPosting) -> JobPosting:
    """The same role on the employer's own board beats an aggregator copy (fresh, verifiable, less crowded)."""
    from jobhunterx.discovery import linkedin
    card = linkedin.Card(id="", title=p.title, company=p.company, location=p.location_raw, posted=p.posted_at,
                         url=p.canonical_url, query=p.discovered_by_query)
    try:
        fp = await asyncio.wait_for(linkedin._first_party(card), FIRST_PARTY_TIMEOUT_S)
    except Exception:
        return p
    if not fp:
        return p
    fp.sources = [s for s in fp.sources if s.name != "linkedin"] + list(p.sources)
    return fp


def status(settings) -> dict:
    """Which of these sources are on (for the UI and for the search's own log)."""
    return {"adzuna": adzuna_credentials(getattr(settings, "adzuna_api_key", None)) is not None,
            "hackernews": bool(getattr(settings, "enable_hn_source", False))}


async def discover(settings, titles: list[str], places: list[str], *, labels: list[str], include_remote: bool = False,
                   max_postings: int = 30, skip: Optional[Callable[[JobPosting], Awaitable[bool]]] = None,
                   on_progress: Progress = None) -> tuple[list[JobPosting], dict]:
    """Postings from every enabled source for titles × places. Returns (postings, stats per source)."""
    from jobhunterx.discovery import linkedin
    t0 = time.monotonic()
    on = status(settings)
    stats: dict = {"enabled": [k for k, v in on.items() if v], "adzuna": 0, "hackernews": 0,
                   "agencies": 0, "seen": 0, "first_party": 0}
    if not stats["enabled"]:
        return [], stats
    places = [p for p in (places or []) if p] or ["India"]
    sem = asyncio.Semaphore(CONCURRENCY)

    async def guarded(name: str, coro) -> list[JobPosting]:
        try:
            return await coro
        except Exception as exc:                  # a blocked, changed or out-of-quota source never fails the search
            log.warning("job_api_failed", source=name, error=str(exc)[:160])
            return []

    async def adzuna() -> list[JobPosting]:
        creds = adzuna_credentials(settings.adzuna_api_key)
        async def one(t: str, w: str):
            async with sem:
                return await adzuna_search(creds, t, w)
        batches = await asyncio.gather(*(one(t, w) for t in titles[:3] for w in places[:3]))
        return [p for b in batches for p in b]

    jobs: list[tuple[str, Awaitable]] = []
    if on["adzuna"] and titles:
        jobs.append(("adzuna", guarded("adzuna", adzuna())))
    if on["hackernews"]:
        jobs.append(("hackernews", guarded("hackernews", hackernews_search(labels, places, include_remote=include_remote))))
    results = await asyncio.gather(*(j for _, j in jobs))
    found: list[JobPosting] = []
    for (name, _), res in zip(jobs, results):
        stats[name] = len(res)
        found += res
    if on_progress and found:
        await on_progress("Job APIs: " + ", ".join(f"{n} {stats[n]}" for n in ("adzuna", "hackernews") if on[n]) + " leads")

    common = common_words(p.title for p in found)
    kept: list[JobPosting] = []
    ids: set[str] = set()
    for p in found:
        if linkedin._bad_company(p.company):
            stats["agencies"] += 1
        elif p.sources[0].name == "hackernews" or title_overlap(p.title, labels, common) > 0:   # HN titles are free text; matched already
            if p.canonical_url not in ids:
                ids.add(p.canonical_url)
                kept.append(p)
    now = datetime.now(timezone.utc)
    kept.sort(key=lambda p: (-round(title_overlap(p.title, labels, common), 1), (now - p.posted_at).days if p.posted_at else 99))
    out: list[JobPosting] = []

    async def one(p: JobPosting) -> None:
        if len(out) >= max_postings or time.monotonic() - t0 > BUDGET_S:
            return
        if skip and await skip(p):
            stats["seen"] += 1
            return
        if p.sources[0].name == "adzuna":
            async with sem:
                better = await _prefer_first_party(p)
            if better is not p:
                stats["first_party"] += 1
            p = better
        if len(out) < max_postings:
            out.append(p)

    await asyncio.gather(*(one(p) for p in kept[: max_postings * 3]), return_exceptions=True)
    stats["ms"] = int((time.monotonic() - t0) * 1000)
    log.info("job_apis_discover", **{k: v for k, v in stats.items() if k != "enabled"}, postings=len(out))
    return out, stats
