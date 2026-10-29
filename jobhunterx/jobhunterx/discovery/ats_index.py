"""
ATS index — today's open postings on employers' own job boards, for India.

The open-source job-board-aggregator (github.com/Feashliaa/job-board-aggregator, data CC BY-NC 4.0) polls the public
Greenhouse, Lever, Ashby, Workday, BambooHR, iCIMS and Paylocity boards of ~28,000 companies every day and publishes
every open posting (~1.4 million) as gzipped JSON chunks. Each row is one posting on the employer's own board: its link,
company, place, title, level and the day it was first seen.

JobHunterX downloads that once a day in the background, keeps only the postings in India (a few MB), and:

* answers searches from it instantly — titles and places matched locally, newest first, then verified live on the
  employer's board like any other lead;
* remembers every employer board with Indian postings in the board registry, so later searches poll them directly.

No search waits for the download unless there is no copy at all yet.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.intelligence.text import common_words, tokens

log = get_logger("ats_index")

SOURCE = "https://raw.githubusercontent.com/Feashliaa/job-board-data/main/data"
REFRESH_S = 20 * 3600               # a copy younger than this is used as is
CHUNK_CONCURRENCY = 3                # each chunk is ~25k rows (~60 MB while parsed); fewer on a small server, see _chunk_slots
INDIA = re.compile(r"(?i)\bindia\b|\b(bengaluru|bangalore|hyderabad|secunderabad|chennai|pune|mumbai|navi mumbai|gurugram|gurgaon|"
                   r"noida|new delhi|delhi|kolkata|kochi|cochin|coimbatore|trivandrum|thiruvananthapuram|ahmedabad|jaipur|"
                   r"chandigarh|indore|visakhapatnam|vizag|mysore|mysuru|mangalore|madurai|nagpur|bhubaneswar|vadodara)\b")
LEVELS = {"intern": 0, "entry": 1, "junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 4, "lead": 3, "manager": 3, "director": 5}


@dataclass(slots=True)                  # tens of thousands of rows: no per-row __dict__
class Row:
    url: str
    company: str
    title: str
    location: str
    level: str
    first_seen: str
    ats: str


def _dir() -> Path:
    from jobhunterx.config.settings import get_settings
    d = get_settings().cache_full_path / "ats_index"
    d.mkdir(parents=True, exist_ok=True)
    return d


_rows: Optional[list[Row]] = None
_meta: dict = {}
_sync_task: Optional[asyncio.Task] = None


def _load() -> list[Row]:
    global _rows, _meta
    if _rows is None:
        try:
            with gzip.open(_dir() / "india.json.gz", "rt", encoding="utf-8") as f:
                data = json.load(f)
            _meta = data.get("meta", {})
            _rows = [_row(r) for r in data.get("rows", [])]
            del data
        except (OSError, ValueError, TypeError):
            _rows, _meta = [], {}
    return _rows


_common_cache: tuple[int, set[str]] = (0, set())


def _common() -> set[str]:
    """Words in many of the index's titles ("engineer", "senior"): ignored when matching titles."""
    global _common_cache
    rows = _rows or []
    if _common_cache[0] != id(rows):
        _common_cache = (id(rows), common_words((r.title for r in rows), share=0.05))
    return _common_cache[1]


def status() -> dict:
    _load()
    return {"rows": len(_rows or []), "updated": _meta.get("source_updated"), "synced_at": _meta.get("synced_at"),
            "boards": _meta.get("boards", 0)}


def stale() -> bool:
    _load()
    return not _rows or time.time() - float(_meta.get("synced_at") or 0) > REFRESH_S


async def _get(client, url: str) -> Optional[bytes]:
    for attempt in range(3):
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
        except Exception as exc:
            log.debug("ats_index_fetch_failed", url=url[-40:], error=str(exc)[:80])
        await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def sync(force: bool = False) -> dict:
    """Download today's data (only when the published copy is newer than ours) and keep the Indian postings."""
    global _rows, _meta
    import httpx
    if not force and not stale():
        return status()
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=60, follow_redirects=True,
                                 headers={"User-Agent": "JobHunterX/2.0 (+local-first job research)"}) as client:
        raw = await _get(client, f"{SOURCE}/metadata.json")
        if not raw:
            log.warning("ats_index_unavailable")
            return status()
        meta = json.loads(raw)
        if not force and _rows and meta.get("last_updated") == _meta.get("source_updated"):
            _meta["synced_at"] = time.time()                 # nothing new published: just note that we checked
            _save(_rows, _meta)
            return status()
        total = int(meta.get("total_jobs") or 0)
        n_chunks = max(1, -(-total // 25000)) if total else 80
        sem = asyncio.Semaphore(_chunk_slots())
        kept: dict[str, Row] = {}
        misses = 0

        async def chunk(i: int) -> None:
            nonlocal misses
            async with sem:
                body = await _get(client, f"{SOURCE}/chunks/jobs_chunk_{i}.json.gz")
            if body is None:
                misses += 1
                return
            rows = await asyncio.to_thread(_india_rows, body)
            for r in rows:
                kept.setdefault(r.url, r)

        await asyncio.gather(*(chunk(i) for i in range(n_chunks + 2)))       # the last two usually do not exist
    if not kept:
        log.warning("ats_index_empty", misses=misses)
        return status()
    rows = sorted(kept.values(), key=lambda r: r.first_seen, reverse=True)
    boards = _remember_boards(rows)
    _meta = {"source_updated": meta.get("last_updated"), "synced_at": time.time(), "boards": boards, "source_jobs": total}
    _rows = rows
    _save(rows, _meta)
    del kept
    from jobhunterx.config import capacity
    capacity.release_memory()            # the downloaded chunks are gone: give their memory back
    log.info("ats_index_synced", india=len(rows), boards=boards, source_jobs=total, ms=int((time.monotonic() - t0) * 1000))
    return status()


def _chunk_slots() -> int:
    """Chunks parsed at once: one on a small server (each is ~60 MB while parsed), up to three with room to spare."""
    from jobhunterx.config import capacity
    free = capacity.plan().get("memory_available_mb") or 0
    return 1 if free < 900 else 2 if free < 1500 else CHUNK_CONCURRENCY


_intern = sys.intern


def _row(r: dict) -> Row:
    # company, place, level and ATS repeat across thousands of rows: one shared copy of each string
    return Row(url=r["url"], company=_intern(r.get("company") or ""), title=r.get("title") or "",
               location=_intern(r.get("location") or ""), level=_intern(r.get("level") or ""),
               first_seen=r.get("first_seen") or "", ats=_intern(r.get("ats") or ""))


def _india_rows(body: bytes) -> list[Row]:
    out = []
    for r in json.loads(gzip.decompress(body)):
        loc = r.get("location") or ""
        if not r.get("url") or not INDIA.search(loc) or r.get("is_recruiter"):
            continue
        out.append(_row({"url": r["url"], "company": (r.get("company") or "").strip(), "title": (r.get("title") or "").strip(),
                         "location": loc.strip(), "level": (r.get("skill_level") or "").lower(),
                         "first_seen": r.get("first_seen") or r.get("scraped_at") or "", "ats": (r.get("ats") or "").lower()}))
    return out


def _save(rows: list[Row], meta: dict) -> None:
    path = _dir() / "india.json.gz"
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump({"meta": meta, "rows": [asdict(r) for r in rows]}, f)
    tmp.replace(path)


def _remember_boards(rows: list[Row]) -> int:
    from jobhunterx.discovery import ats, registry
    boards = {}
    for r in rows:
        ref = ats.parse_ats_url(r.url)
        if ref and ref.kind in ats.ADAPTERS:
            boards.setdefault((ref.kind, ref.token.lower()), (ref.model_copy(update={"job_id": ""}), r.company))
    registry.remember(list(boards.values()), source="ats_index")
    return len(boards)


def ensure_background() -> Optional[asyncio.Task]:
    """Start a refresh in the background when our copy is old (at most one at a time)."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        return _sync_task
    if not stale():
        return None

    async def run() -> None:
        try:
            await sync()
        except Exception as exc:                # a failed refresh never breaks anything: the old copy stays
            log.warning("ats_index_sync_failed", error=str(exc)[:160])

    _sync_task = asyncio.create_task(run())
    return _sync_task


# ------------------------------------------------------------------ search
def _age_days(r: Row) -> float:
    try:
        d = datetime.fromisoformat(r.first_seen.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - d).total_seconds() / 86400
    except ValueError:
        return 99.0


def search(labels: list[str], places: list[str], *, level: Optional[str] = None, include_remote: bool = False,
           max_age_days: int = 30, limit: int = 60) -> list[tuple[Row, float]]:
    """Postings whose title shares the meaning-bearing words of the candidate's titles, in their places; best first."""
    rows = _load()
    if not rows:
        return []
    want = [set(tokens(l)) for l in labels if l]
    want = [w for w in want if w]
    if not want:
        return []
    local_place = _local(places)
    me = LEVELS.get((level or "").lower())
    common = _common()
    want_pairs = [(w, w - common) for w in want]
    out = []
    for r in rows:
        local = local_place(r.location)
        remote = include_remote and "remote" in r.location.lower()
        if not (local or remote):
            continue
        age = _age_days(r)
        if age > max_age_days:
            continue
        # meaning-bearing words only: "Platform Engineer" is not an "AI Engineer" match through "Engineer"
        full = set(tokens(r.title))
        rel = 0.0
        for w_full, w_core in want_pairs:
            jt, w = full - common, w_core
            if not w:                   # the candidate's own title is all common words ("Software Engineer")
                jt, w = full, w_full
            if jt and w:
                rel = max(rel, len(jt & w) / len(jt | w))
        if rel < 0.25:
            continue
        lv = LEVELS.get(r.level)
        # the candidate's own level first, one step away next, far above or below sinks
        fit = 1.0 if me is None or lv is None else {0: 1.0, 1: 0.8}.get(abs(lv - me), 0.35)
        score = rel * fit * (1.25 if age <= 3 else 1.1 if age <= 7 else 1.0 if age <= 14 else 0.8)
        out.append((r, score))
    out.sort(key=lambda x: -x[1])
    # one employer's ten copies of "Storage AI Engineer" must not take ten of the slots
    per: dict[str, int] = {}
    capped = []
    for r, sc in out:
        per[r.company] = per.get(r.company, 0) + 1
        if per[r.company] <= PER_COMPANY:
            capped.append((r, sc))
    return capped[:limit]


PER_COMPANY = 2


def _local(places: list[str]):
    forms = {p.lower() for p in places if p}
    if forms & {"bengaluru", "bangalore"}:
        forms |= {"bengaluru", "bangalore"}
    if forms & {"hyderabad", "secunderabad"}:
        forms |= {"hyderabad", "secunderabad"}
    return lambda loc: any(f in loc.lower() for f in forms) if forms else True


def level_titles(labels: list[str], places: list[str], level: str, *, max_age_days: int = 45, limit: int = 40) -> list[tuple[str, int]]:
    """Real titles of openings at this level in these places, from employers' own boards: [(title, employers)].

    The search plan picks its wording from these instead of inventing titles nobody uses ("RAG Engineer Junior"):
    for a fresher they are what entry-level openings are really called here ("Associate Data Scientist",
    "Data Scientist 1", "Graduate Engineer Trainee"). Kept: titles sharing a meaningful word with the candidate's
    titles, and titles made only of common words ("Associate Software Engineer"), which fit any field."""
    rows = _load()
    me = LEVELS.get((level or "").lower())
    if not rows or me is None:
        return []
    common = _common()
    want = set().union(*[set(tokens(l)) - common for l in labels if l]) if labels else set()
    local = _local(places)
    seen: dict[str, tuple[str, set[str]]] = {}
    for r in rows:
        lv = LEVELS.get(r.level)
        if lv is None or abs(lv - me) > 0 or _age_days(r) > max_age_days or not local(r.location):
            continue
        title = re.sub(r"\s+", " ", r.title).strip()[:80]
        core = set(tokens(title)) - common
        if core and not (core & want):
            continue
        key = title.lower()
        seen.setdefault(key, (title, set()))[1].add(r.company)
    ranked = sorted(seen.values(), key=lambda x: -len(x[1]))
    return [(t, len(cos)) for t, cos in ranked[:limit]]
