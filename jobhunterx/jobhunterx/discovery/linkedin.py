"""
LinkedIn public job feed — thousands of fresh Indian postings, no login, no key.

LinkedIn's logged-out job search (the same pages Google indexes) answers a plain GET with job cards: title,
company, place and posting date, sorted newest first and filterable to the last 24 hours / week. One posting's
public page also shows how many people already applied.

A LinkedIn post is where the crowd applies, so it is used for *discovery*, not as the place to apply:

1. Newest first — last 24 hours, then the last week (a different slice of it every run).
2. Mass IT-services recruiters and staffing agencies are dropped on the card.
3. The employer is looked up on its own job board (watchlist, the board registry, or a probe of Greenhouse /
   Lever / Ashby). When the same role is there, the first-party posting is used and the board is remembered.
4. Otherwise the public page is read: full description, seniority, and the applicant count. Posts that already
   have a crowd (LINKEDIN_MAX_APPLICANTS) are skipped — that is exactly where a 1–2 year candidate goes unread.
"""

from __future__ import annotations

import asyncio
import html as _html
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import httpx

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.job import FieldCheck, JobPosting, SourceRef
from jobhunterx.intelligence.text import tokens

log = get_logger("linkedin")

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"
PAGE = 10                        # cards per page of the guest API
ROTATE_PAGES = 5                 # the week-old slice walks through this many pages over successive runs
CONCURRENCY = 3                  # LinkedIn starts refusing (HTTP 429 / 999) when hammered
BUDGET_S = 40.0
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}
_STAFFING = re.compile(r"(?i)\b(staffing|recruit(ment|ers?|ing)|placements?|manpower|consultants?|hr services|talent acquisition|"
                       r"hiring solutions|outsourcing|careers? (india|hub))\b")
_STATE = {"hyderabad": "Hyderabad, Telangana, India", "secunderabad": "Hyderabad, Telangana, India",
          "bengaluru": "Bengaluru, Karnataka, India", "bangalore": "Bengaluru, Karnataka, India",
          "chennai": "Chennai, Tamil Nadu, India", "pune": "Pune, Maharashtra, India", "mumbai": "Mumbai, Maharashtra, India",
          "kochi": "Kochi, Kerala, India", "coimbatore": "Coimbatore, Tamil Nadu, India",
          "visakhapatnam": "Visakhapatnam, Andhra Pradesh, India", "vizag": "Visakhapatnam, Andhra Pradesh, India",
          "trivandrum": "Thiruvananthapuram, Kerala, India", "thiruvananthapuram": "Thiruvananthapuram, Kerala, India",
          "delhi": "Delhi, India", "gurugram": "Gurugram, Haryana, India", "noida": "Noida, Uttar Pradesh, India"}


@dataclass
class Card:
    id: str
    title: str
    company: str
    location: str
    posted: Optional[datetime]
    url: str
    query: str = ""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _place(p: str) -> str:
    low = (p or "").strip().lower()
    if low in ("remote", "remote india", "india", ""):
        return "India"
    return _STATE.get(low, p if "india" in low else f"{p}, India")


_client: Optional[tuple[asyncio.AbstractEventLoop, httpx.AsyncClient]] = None


def _http() -> httpx.AsyncClient:
    global _client
    loop = asyncio.get_running_loop()
    if _client is None or _client[0] is not loop or _client[1].is_closed:
        _client = (loop, httpx.AsyncClient(headers=_HEADERS, timeout=12, follow_redirects=True,
                                           limits=httpx.Limits(max_connections=CONCURRENCY + 1)))
    return _client[1]


_blocked_until = 0.0


async def _get(url: str, params: Optional[dict] = None) -> str:
    global _blocked_until
    if time.monotonic() < _blocked_until:
        return ""
    for attempt in range(2):
        try:
            r = await _http().get(url, params=params)
        except httpx.HTTPError as exc:
            log.debug("linkedin_fetch_failed", error=str(exc)[:80])
            return ""
        if r.status_code == 200:
            return r.text
        if r.status_code in (429, 999):                      # throttled: back off once, then rest for 10 minutes
            if attempt == 0:
                await asyncio.sleep(2.5 + random.random() * 2)
                continue
            _blocked_until = time.monotonic() + 600
            log.info("linkedin_throttled", status=r.status_code)
        return ""
    return ""


def parse_cards(page: str, query: str = "") -> list[Card]:
    out = []
    for block in page.split("<li")[1:]:
        m = re.search(r"jobPosting:(\d+)", block)
        if not m:
            continue
        title = _clean((re.search(r'base-search-card__title">(.*?)</h3>', block, re.S) or [None, ""])[1])
        company = _clean((re.search(r'base-search-card__subtitle">(.*?)</h4>', block, re.S) or [None, ""])[1])
        loc = _clean((re.search(r'job-search-card__location">(.*?)</span>', block, re.S) or [None, ""])[1])
        d = re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})"', block)
        posted = datetime.fromisoformat(d.group(1)).replace(tzinfo=timezone.utc) if d else None
        if title and company:
            out.append(Card(id=m.group(1), title=title, company=company, location=loc, posted=posted,
                            url=f"https://www.linkedin.com/jobs/view/{m.group(1)}/", query=query))
    return out


async def search(keywords: str, place: str, *, hours: int = 168, start: int = 0, remote: bool = False) -> list[Card]:
    params = {"keywords": keywords, "location": _place(place), "f_TPR": f"r{hours * 3600}", "start": start, "sortBy": "DD"}
    if remote:
        params["f_WT"] = "2"
    return parse_cards(await _get(SEARCH_URL, params), query=f"{keywords} · {place}")


_APPLICANTS = re.compile(r"(?i)(over\s+)?(\d[\d,]*)\s+applicants")


async def details(card: Card) -> Optional[dict]:
    page = await _get(DETAIL_URL.format(id=card.id))
    if not page:
        return None
    desc = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', page, re.S)
    text = (desc.group(1) if desc else "")
    text = re.sub(r"(?i)<br\s*/?>|</(p|li|ul|ol|h\d)>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n• ", text)
    text = "\n".join(_clean(line) for line in _html.unescape(re.sub(r"<[^>]+>", "", text)).split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    crit = dict(re.findall(r'description__job-criteria-subheader">\s*([^<]+?)\s*</h3>\s*<span[^>]*>\s*([^<]+?)\s*</span>', page))
    applicants = _clean((re.search(r"num-applicants__caption[^>]*>(.*?)<", page, re.S) or [None, ""])[1])
    if not applicants:
        applicants = _clean((re.search(r"(Be among the first \d+ applicants)", page) or [None, ""])[1])
    m = _APPLICANTS.search(applicants)
    count = int(m.group(2).replace(",", "")) if m else None
    return {"description": text, "criteria": crit, "applicants": applicants, "count": count,
            "closed": "No longer accepting applications" in page}


def _relevance(title: str, labels: list[str]) -> float:
    jt = set(tokens(title))
    best = 0.0
    for label in labels:
        lt = set(tokens(label))
        if jt and lt:
            best = max(best, len(jt & lt) / len(jt | lt))
    return best


def _bad_company(name: str) -> bool:
    from jobhunterx.discovery import watchlist
    return watchlist.is_mass_recruiter(name) or bool(_STAFFING.search(name or ""))


# ------------------------------------------------------------------ employer's own board
async def _first_party(card: Card) -> Optional[JobPosting]:
    """The same role on the employer's own ATS board, if we can find the board. Remembers boards that exist."""
    from jobhunterx.discovery import ats, registry, watchlist
    from jobhunterx.domain.candidate import norm_term
    from jobhunterx.tools import deep_search as ds
    boards: list[tuple[str, str, str]] = []
    by_name = watchlist._index()[1]
    wc = by_name.get(norm_term(card.company))
    if wc and wc.board:
        boards.append((wc.board.kind, wc.board.token, wc.name))
    else:
        for slug in ds._slugs(card.company)[:2]:
            for kind in ("greenhouse", "lever", "ashby"):
                if await ds._probe(kind, slug, card.company):
                    boards.append((kind, slug, card.company))
            if boards:
                break
    from jobhunterx.domain.job import AtsRef
    registry.remember([(AtsRef(kind=k, token=t), n) for k, t, n in boards], source="linkedin")
    want = set(tokens(card.title))
    for kind, token, name in boards:
        adapter = ats.ADAPTERS.get(kind)
        if not adapter:
            continue
        jobs = await (adapter.search_jobs(token, [card.title]) if kind in ("workday", "oracle") else adapter.list_jobs(token))
        best, score = None, 0.0
        for j in jobs or []:
            jt = set(tokens(j.title))
            s = len(want & jt) / len(want | jt) if want and jt else 0.0
            if s > score:
                best, score = j, s
        if best and score >= 0.6:
            best.company = name if wc else (best.company or name)
            best.sources.append(SourceRef(name="linkedin", kind="job_board", url=card.url, confidence=0.5))
            best.discovered_by_query = card.query
            return best
    return None


def _posting(card: Card, d: dict) -> JobPosting:
    crit = d.get("criteria") or {}
    head = [f"{k}: {v}" for k, v in crit.items() if k in ("Seniority level", "Employment type", "Job function")]
    if d.get("applicants"):
        head.append(f"LinkedIn: {d['applicants']}")
    p = JobPosting(title=card.title, company=card.company, location_raw=card.location, posted_at=card.posted,
                   description=("\n".join(head) + "\n\n" + d.get("description", "")).strip()[:20000],
                   canonical_url=card.url, apply_url=card.url, discovered_by_query=card.query,
                   employment_type={"Full-time": "full_time", "Part-time": "part_time", "Contract": "contract",
                                    "Internship": "internship", "Temporary": "temporary"}.get(crit.get("Employment type", ""), ""),
                   sources=[SourceRef(name="linkedin", kind="job_board", url=card.url, confidence=0.6)])
    p.validation.checks["title"] = FieldCheck(status="verified", value=card.title, evidence="LinkedIn job card")
    if card.posted:
        p.validation.checks["posted_at"] = FieldCheck(status="verified", value=card.posted.date().isoformat(), evidence="LinkedIn job card")
    if d.get("closed"):
        p.validation.status = "closed"
        p.validation.notes.append("LinkedIn says it is no longer accepting applications.")
    return p


# ------------------------------------------------------------------ the source
_rot_store = None


def _rotation(key: str) -> int:
    """How many times this title × place was searched before — picks the next slice of the week's postings."""
    global _rot_store
    if _rot_store is None:
        from diskcache import Cache
        from jobhunterx.config.settings import get_settings
        _rot_store = Cache(str(get_settings().cache_full_path / "linkedin_rotation"))
    n = _rot_store.get(key, 0)
    _rot_store.set(key, n + 1, expire=14 * 86400)
    return n


async def discover(titles: list[str], places: list[str], *, labels: list[str], include_remote: bool = False,
                   max_postings: int = 40, max_applicants: int = 150,
                   skip: Optional[Callable[[JobPosting], Awaitable[bool]]] = None,
                   on_progress: Optional[Callable[[str], Awaitable[None]]] = None) -> tuple[list[JobPosting], dict]:
    """Fresh postings for titles × places. Returns (postings, stats)."""
    t0 = time.monotonic()
    stats = {"cards": 0, "agencies": 0, "crowded": 0, "first_party": 0, "seen": 0, "read": 0}
    combos = [(t, p, False) for t in titles[:4] for p in places[:3]]
    if include_remote:
        combos += [(t, "India", True) for t in titles[:2]]
    sem = asyncio.Semaphore(CONCURRENCY)

    async def pages(title: str, place: str, remote: bool) -> list[Card]:
        n = _rotation(f"{title.lower()}|{place.lower()}|{remote}")
        start = PAGE * (1 + n % ROTATE_PAGES)                 # 10, 20, … 50, then round again
        out = []
        async with sem:
            out += await search(title, place, hours=24, remote=remote)
            await asyncio.sleep(0.3 + random.random() * 0.5)
            out += await search(title, place, hours=24 * 7, start=0 if n == 0 else start, remote=remote)
        return out

    batches = await asyncio.gather(*(pages(t, p, r) for t, p, r in combos), return_exceptions=True)
    cards: dict[str, Card] = {}
    for b in batches:
        for c in (b if isinstance(b, list) else []):
            cards.setdefault(c.id, c)
    stats["cards"] = len(cards)
    kept = []
    for c in cards.values():
        if _bad_company(c.company):
            stats["agencies"] += 1
        elif _relevance(c.title, labels) > 0:
            kept.append(c)
    now = datetime.now(timezone.utc)
    kept.sort(key=lambda c: (-round(_relevance(c.title, labels), 1), (now - c.posted).days if c.posted else 99))
    if on_progress:
        await on_progress(f"LinkedIn: {len(cards)} fresh posts, {len(kept)} in your field")

    out: list[JobPosting] = []

    async def one(card: Card) -> None:
        if len(out) >= max_postings or time.monotonic() - t0 > BUDGET_S:
            return
        probe = JobPosting(title=card.title, company=card.company, location_raw=card.location, canonical_url=card.url)
        if skip and await skip(probe):
            stats["seen"] += 1
            return
        async with sem:
            if len(out) >= max_postings or time.monotonic() - t0 > BUDGET_S:
                return
            try:
                fp = await asyncio.wait_for(_first_party(card), 10)
            except Exception:
                fp = None
            if fp:
                stats["first_party"] += 1
                out.append(fp)
                return
            d = await details(card)
            await asyncio.sleep(0.2 + random.random() * 0.4)
        if not d:
            return
        stats["read"] += 1
        if d["count"] is not None and d["count"] >= max_applicants:
            stats["crowded"] += 1
            return
        out.append(_posting(card, d))

    await asyncio.gather(*(one(c) for c in kept[: max_postings * 3]), return_exceptions=True)
    stats["ms"] = int((time.monotonic() - t0) * 1000)
    log.info("linkedin_discover", **stats, postings=len(out))
    return out, stats
