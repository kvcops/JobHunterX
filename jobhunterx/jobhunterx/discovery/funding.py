"""
Funding news — startups that just raised money are about to hire, usually before they post on the big boards.

Read from public RSS feeds of Indian startup news (Inc42, Entrackr, YourStory) and a Google News search for funding
headlines in the candidate's cities. Only headlines that say a named company *raised* money are kept ("X raises
₹6 crore…"); "in talks", weekly round-ups and market reports are skipped. Events are remembered for six months, so
the list grows with every refresh.

Used in three places:
* search — openings at a recently funded company found in the daily copy of employer boards go to the front
* reach  — a posting from a company that raised in the last 120 days gets a small "newly funded, hiring" signal
* the Recently funded list in the app (GET /api/funding) — companies worth watching before they post anything
"""

from __future__ import annotations

import asyncio
import html as _html
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote_plus

from jobhunterx.config.logging import get_logger

log = get_logger("funding")

FEEDS = ("https://inc42.com/buzz/feed/", "https://entrackr.com/rss", "https://yourstory.com/feed")
GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
REFRESH_S = 6 * 3600
KEEP_DAYS = 180
SIGNAL_DAYS = 120
KEY = "events"

_VERB = re.compile(r"(?i)\s+(raises|raised|bags|secures|nets|closes|lands|gets|picks\s+up|mops\s+up)\s+")
_AMOUNT = re.compile(r"(?i)((?:us)?\$|₹|rs\.?|inr|usd)\s?\d[\d,.]*\s*(?:mn|million|m|bn|billion|b|cr|crore|crores|lakh|k)?\b"
                     r"|\d[\d,.]*\s*(?:mn|million|bn|billion|cr|crore|crores|lakh)\b")
_SKIP = re.compile(r"(?i)\bin\s+talks\b|\bset\s+to\s+raise\b|\bplans?\s+to\s+raise\b|\bstartups\b|\bthis\s+week\b|\bweekly\b|"
                   r"\bfunding\s+(rises|falls|drops|surges|stays|remains)\b|\bfund\s+of\s+funds\b|\bq[1-4]\b|\bipo\b|\bventures?\s+raises\b"
                   r"|\bcapital\s+raises\b|\bpartners\s+raises\b|\bfund\s+(?:i|ii|iii|iv|v)\b|\bfor\s+(?:its\s+)?(?:\w+\s+){0,3}fund\b"
                   r"|\bto\s+complete\s+the\s+fund\b|\bnew\s+fund\b")
_DESCRIPTOR = re.compile(r"(?i)^.*?\b(?:startup|start-up|platform|firm|company|maker|provider|brand|unicorn|backed|old)\s+")
_LEAD = re.compile(r"(?i)^(?:india['’]s|indian|bengaluru['’]s|bangalore['’]s|hyderabad['’]s|mumbai['’]s|delhi['’]s)\s+")
_GENERIC = {"india", "indian", "india's", "india’s", "the", "a", "an", "it", "this", "exclusive", "startup"}


@dataclass
class FundingEvent:
    company: str
    amount: str
    date: str               # ISO date of the article
    headline: str
    url: str
    source: str

    @property
    def key(self) -> str:
        return company_key(self.company)


def company_key(name: str) -> str:
    n = re.sub(r"(?i)\b(pvt|private|ltd|limited|inc|technologies|technology|labs|ai|tech|india)\b", " ", name or "")
    return re.sub(r"[^a-z0-9]", "", n.lower()) or re.sub(r"[^a-z0-9]", "", (name or "").lower())


def parse_headline(title: str) -> Optional[tuple[str, str]]:
    """'Maasi Raises ₹6 Crore in Pre-Seed Funding' → ('Maasi', '₹6 Crore'). None when it is not one company raising."""
    t = _html.unescape(title or "").strip()
    t = re.sub(r"\s+-\s+[^-]{2,60}$", "", t)                 # Google News appends " - Publisher"
    t = re.sub(r"(?i)^(exclusive|breaking|funding alert)\s*[:|]\s*", "", t)
    if _SKIP.search(t):
        return None
    m = _VERB.search(t)
    if not m:
        return None
    amount = _AMOUNT.search(t[m.end():m.end() + 60])
    if not amount:
        return None
    head = _DESCRIPTOR.sub("", t[:m.start()]).strip(" ,:'\"‘’“”")
    head = _LEAD.sub("", re.split(r"[,:|]", head)[-1].strip())
    words = head.split()
    small = {"of", "and", "&", "the", "for", "by"}
    if any(w[:1].islower() and w not in small for w in words):        # "Bijnis rebrands as Zorit" → "Zorit"
        tail = []
        for w in reversed(words):
            if w[:1].islower() and w not in small:
                break
            tail.insert(0, w)
        words = tail
        head = " ".join(words)
    if words and words[-1].lower() in ("startup", "start-up", "company", "firm", "platform"):
        return None
    if not words or len(words) > 5 or words[0][:1].islower() or head.lower() in _GENERIC:
        return None
    if re.search(r"(?i)^\d|['’]s$", head):
        return None
    return head, amount.group(0).strip()


def _items(xml: str) -> list[tuple[str, str, Optional[datetime]]]:
    out = []
    for it in re.findall(r"(?s)<item>(.*?)</item>", xml or ""):
        title = re.search(r"(?s)<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it)
        link = re.search(r"(?s)<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", it)
        date = re.search(r"(?s)<pubDate>(.*?)</pubDate>", it)
        try:
            when = parsedate_to_datetime(date.group(1).strip()) if date else None
        except (TypeError, ValueError):
            when = None
        if title:
            out.append((title.group(1).strip(), (link.group(1).strip() if link else ""), when))
    return out


def parse_feed(xml: str, source: str) -> list[FundingEvent]:
    out = []
    for title, link, when in _items(xml):
        hit = parse_headline(title)
        if hit:
            out.append(FundingEvent(company=hit[0], amount=hit[1], date=(when or datetime.now(timezone.utc)).date().isoformat(),
                                    headline=_html.unescape(title)[:200], url=link, source=source))
    return out


_store = None


def _cache():
    global _store
    if _store is None:
        from jobhunterx.config import capacity
        from jobhunterx.config.settings import get_settings
        _store = capacity.disk_cache(get_settings().cache_full_path / "funding", 16)
    return _store


def _merge(old: list[dict], new: list[FundingEvent]) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).date().isoformat()
    by: dict[str, dict] = {}
    for e in [*old, *(asdict(x) for x in new)]:
        k = company_key(e["company"])
        if e["date"] < cutoff or not k:
            continue
        if k not in by or e["date"] > by[k]["date"]:      # newest round per company
            by[k] = e
    return sorted(by.values(), key=lambda e: e["date"], reverse=True)


async def refresh(places: Optional[list[str]] = None, force: bool = False) -> int:
    """Fetch the feeds (at most every 6 hours). Returns how many events are known."""
    from jobhunterx.discovery import job_apis
    from jobhunterx.config.settings import get_settings
    if not getattr(get_settings(), "enable_funding_signals", True):
        return 0
    store = _cache()
    if not force and time.time() - (store.get("fetched") or 0) < REFRESH_S:
        return len(store.get(KEY) or [])
    cities = [p for p in (places or []) if p and p.lower() != "india"][:2]
    queries = ["startup raises funding India", *(f"startup raises funding {c}" for c in cities)]
    urls = [(u, u.split("/")[2].removeprefix("www.")) for u in FEEDS] + \
           [(GOOGLE_NEWS.format(q=quote_plus(q)), "Google News") for q in queries]
    pages = await asyncio.gather(*(job_apis.fetch_text(u) for u, _ in urls), return_exceptions=True)
    new: list[FundingEvent] = []
    for (u, src), page in zip(urls, pages):
        if isinstance(page, str):
            new += parse_feed(page, src)
    events = _merge(store.get(KEY) or [], new)
    store.set(KEY, events)
    store.set("fetched", time.time())
    log.info("funding_refresh", new=len(new), known=len(events))
    return len(events)


def recent(days: int = SIGNAL_DAYS) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    try:
        return [e for e in (_cache().get(KEY) or []) if e["date"] >= cutoff]
    except Exception:              # the cache is optional: a broken or locked file never breaks matching
        return []


def lookup(company: str, days: int = SIGNAL_DAYS) -> Optional[dict]:
    k = company_key(company)
    if not k or len(k) < 3:
        return None
    return next((e for e in recent(days) if company_key(e["company"]) == k), None)


def status() -> dict:
    try:
        store = _cache()
        return {"events": len(store.get(KEY) or []), "fetched": store.get("fetched")}
    except Exception:
        return {"events": 0, "fetched": None}
