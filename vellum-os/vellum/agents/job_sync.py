"""
Vellum OS — Job Sync Engine (the core of the board-first architecture)

Fully automatic: zero user action beyond uploading a resume.

Flow:
  1. Bootstrap: seed company index auto-loads on first run.
  2. Discovery: live hasjob.co feed surfaces fresh Indian startup jobs +
     the startups that posted them (unknown ones auto-added to company DB).
  3. Probe: every company is probed for a free ATS board (Greenhouse / Ashby /
     Lever / Recruitee / SmartRecruiters / BambooHR).
  4. Fetch: jobs pulled via the free posting JSON APIs.
  5. Score: keyword pre-score then Gemma batch score vs the resume profile.
  6. Store: dedupe by apply_url hash, persist with match_score.

Run from the API layer as a background task; progress events go out over
the WebSocket.

Run from the API layer as a background task; progress events go out over
the WebSocket.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

from vellum.agents import job_scorer
from vellum.config import database as db
from vellum.config.logging import get_logger
from vellum.config.settings import get_settings
from vellum.tools.ats_client import Company, Job, fetch_jobs, probe_company
from vellum.tools import hasjob

log = get_logger("job_sync")

EventCallback = Callable[[dict], Awaitable[None]]

SEED_CSV = Path(__file__).resolve().parents[2] / "data" / "companies.csv"


# ---------------------------------------------------------------------------
# Company store (CSV seed + user-added rows)
# ---------------------------------------------------------------------------

def load_seed_companies() -> list[dict]:
    """Load the bundled seed list. Every row: name, website, careers_url, hub, ats, ats_token."""
    rows: list[dict] = []
    if not SEED_CSV.exists():
        log.warning("seed_csv_missing", path=str(SEED_CSV))
        return rows
    try:
        with open(SEED_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "name": (r.get("name") or "").strip(),
                    "website": (r.get("website") or "").strip(),
                    "careers_url": (r.get("careers_url") or "").strip(),
                    "hub": (r.get("hub") or "").strip(),
                    "ats": (r.get("ats") or "").strip(),
                    "ats_token": (r.get("ats_token") or "").strip(),
                })
    except Exception as exc:
        log.error("seed_csv_read_failed", error=str(exc))
    return [r for r in rows if r["name"]]


async def ensure_companies_in_db(companies: list[dict]) -> int:
    """Insert companies that aren't in the DB yet. Returns inserted count."""
    count = 0
    for c in companies:
        existing = await db.get_company_by_name(c["name"])
        if existing is None:
            await db.insert_company(c)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _slug_role(raw: str) -> str:
    t = re.sub(r"\s+", " ", (raw or "").strip())
    t = t.replace("(Remote)", "").replace("(Hybrid)", "").replace("(On-site)", "").strip()
    return t


def _dedupe_key(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest() if url.strip() else "no_url"


def _normalize_job(job: Job, hub: str = "") -> dict:
    key = f"{job.company}|{job.role}|{job.apply_url}"
    return {
        "id_key": hashlib.sha256(key.encode()).hexdigest(),
        "company": job.company,
        "role": _slug_role(job.role),
        "location": job.location,
        "department": job.department,
        "jd_text": job.jd_text,
        "apply_url": job.apply_url,
        "career_page_url": job.career_page_url,
        "posted_at": job.posted_at,
        "source": job.source,
        "hub": hub,
    }


async def store_jobs(job_dicts: list[dict]) -> dict:
    """Dedupe by apply_url hash and insert. Returns {inserted, duplicates}."""
    import aiosqlite

    hashes = {}
    for job in job_dicts:
        url = job.get("apply_url") or ""
        hashes[job["id_key"]] = hashlib.sha256(url.encode()).hexdigest() if url else None
    existing: set[str] = set()
    try:
        async with aiosqlite.connect(db._db_path) as conn:
            cur = await conn.execute("SELECT apply_url_hash FROM jobs WHERE apply_url_hash IS NOT NULL")
            rows = await cur.fetchall()
            existing = {r[0] for r in rows}
    except Exception:
        pass

    inserted = 0
    duplicates = 0
    for job in job_dicts:
        h = hashes[job["id_key"]]
        if h and h in existing:
            duplicates += 1
            continue
        job_id = await db.insert_job({
            "company": job["company"],
            "role": job["role"],
            "career_page_url": job["career_page_url"],
            "apply_url": job["apply_url"],
            "jd_text": job["jd_text"],
            "source": job["source"],
            "discovery_confidence": 0.8,
            "status": "discovered",
        })
        if job.get("match_score") is not None:
            await db.update_job(job_id, match_score=job["match_score"])
        if h:
            existing.add(h)
        inserted += 1
    return {"inserted": inserted, "duplicates": duplicates}


# ---------------------------------------------------------------------------
# Main sync run
# ---------------------------------------------------------------------------

async def run_sync(
    profile: Optional[dict] = None,
    company_filter: Optional[list[str]] = None,
    limit_companies: int = 0,
    event_cb: Optional[EventCallback] = None,
    discover: bool = True,
    probe_concurrency: int = 6,
) -> dict:
    """Run one full sync pass. Fully automatic — no company selection needed.

    Args:
        profile: candidate profile dict (for scoring). If None, jobs are
                 stored unscored (keyword score only).
        company_filter: only sync these company names (empty = all).
        limit_companies: cap how many companies to probe this run (0 = all).
        discover: also ingest the live hasjob.co feed (auto-discovery of
                  Indian startups + their jobs) before ATS probing.
        probe_concurrency: how many companies to probe in parallel.
    """
    from vellum.config import gemma as g

    async def emit(etype: str, message: str, data: dict | None = None):
        if event_cb:
            try:
                await event_cb({
                    "agent": "job_sync",
                    "event_type": etype,
                    "message": message,
                    "data": data or {},
                })
            except Exception:
                pass

    summary = {"probed": 0, "ats_found": 0, "jobs_fetched": 0, "jobs_stored": 0,
               "scored": 0, "skipped_budget": False, "feed_jobs": 0,
               "companies_discovered": 0, "duplicates": 0}

    # --- Step 1: auto-bootstrap the seed index on first run ---
    companies = await db.get_companies()
    if not companies:
        seeds = load_seed_companies()
        n = await ensure_companies_in_db(seeds)
        companies = await db.get_companies()
        if n:
            await emit("progress",
                       f"First run: auto-loaded {n} Indian startups from the seed index.", {})
            summary["companies_discovered"] = n
    if not companies:
        await emit("error", "No companies available — seed CSV is missing.", {})
        return summary

    # --- Step 2: live feed discovery (hasjob.co — Indian startup jobs) ---
    feed_job_dicts: list[dict] = []
    if discover:
        try:
            feed_jobs = await hasjob.fetch_feed()
        except Exception as exc:
            log.warning("hasjob_fetch_failed", error=str(exc)[:150])
            feed_jobs = []
        summary["feed_jobs"] = len(feed_jobs)
        known = {c["name"].lower() for c in companies}
        for fj in feed_jobs:
            cname = (fj.get("company") or "").strip()
            if not cname:
                continue
            if cname.lower() not in known:
                await db.insert_company({
                    "name": cname,
                    "website": fj.get("website") or "",
                    "careers_url": "",
                    "hub": "",
                })
                known.add(cname.lower())
                summary["companies_discovered"] += 1
            feed_job_dicts.append({
                "id_key": _dedupe_key(fj.get("apply_url") or ""),
                "company": cname,
                "role": _slug_role(fj.get("title") or ""),
                "location": fj.get("location") or "",
                "department": "",
                "jd_text": fj.get("jd_text") or "",
                "apply_url": fj.get("apply_url") or "",
                "career_page_url": fj.get("website") or "",
                "posted_at": fj.get("posted_at") or "",
                "source": "hasjob",
            })
        if feed_job_dicts:
            await emit("progress",
                       f"Feed: {len(feed_jobs)} fresh startup jobs, "
                       f"{summary['companies_discovered']} new companies discovered.", {})
        companies = await db.get_companies()

    # --- Step 3: probe + fetch ATS boards (parallel) ---
    if company_filter:
        fset = {c.lower() for c in company_filter}
        companies = [c for c in companies if c["name"].lower() in fset]
    if limit_companies:
        companies = companies[:limit_companies]

    sem = asyncio.Semaphore(probe_concurrency)

    async def probe_one(comp: dict) -> tuple[dict, list[Job]]:
        cc = Company(
            name=comp["name"],
            website=comp.get("website") or "",
            careers_url=comp.get("careers_url") or "",
            hub=comp.get("hub") or "",
            ats=comp.get("ats") or "",
            ats_token=comp.get("ats_token") or "",
        )
        try:
            cc = await probe_company(cc)
        except Exception as exc:
            log.warning("probe_failed", company=cc.name, error=str(exc)[:150])
            return comp, []
        await db.update_company_ats(comp["id"] or cc.name, cc.ats, cc.ats_token, cc.careers_url)
        if cc.ats == "none":
            return comp, []
        try:
            jobs = await fetch_jobs(cc)
        except Exception as exc:
            log.warning("fetch_failed", company=cc.name, error=str(exc)[:150])
            return comp, []
        return comp, jobs

    async def probe_limited(comp: dict):
        async with sem:
            return await probe_one(comp)

    results: list[tuple[dict, list[Job]]] = []
    for i in range(0, len(companies), probe_concurrency):
        chunk = companies[i:i + probe_concurrency]
        await emit("progress",
                   f"[{min(i + probe_concurrency, len(companies))}/{len(companies)}] "
                   f"Probing ATS boards ...", {})
        results.extend(await asyncio.gather(*(probe_limited(c) for c in chunk)))

    ats_job_dicts: list[dict] = []
    for comp, jobs in results:
        summary["probed"] += 1
        if not jobs:
            continue
        summary["ats_found"] += 1
        summary["jobs_fetched"] += len(jobs)
        ats_job_dicts.extend(_normalize_job(j, hub=comp.get("hub") or "") for j in jobs)
        await emit("jobs_found", f"  {comp['name']}: {len(jobs)} jobs", {
            "company": comp["name"], "jobs": len(jobs),
        })

    all_job_dicts = feed_job_dicts + ats_job_dicts

    # --- Step 4: score (keyword prefilter → Gemma batch, budget-guarded) ---
    if profile and all_job_dicts:
        all_job_dicts = await job_scorer.score_batch(all_job_dicts, profile)
        summary["scored"] = sum(1 for j in all_job_dicts if j.get("match_score") is not None)
        if g.is_exhausted():
            summary["skipped_budget"] = True

    # --- Step 5: store (dedupe by apply_url) ---
    stored = await store_jobs(all_job_dicts)
    summary["jobs_stored"] += stored["inserted"]
    summary["duplicates"] = stored["duplicates"]

    if summary["skipped_budget"]:
        await emit("warning",
                   "Gemma daily budget exhausted — remaining jobs scored by keyword only.", {})
    await emit("complete", "Sync finished.", summary)
    log.info("sync_finished", **summary)
    return summary


async def add_company(name: str, website: str = "", careers_url: str = "", hub: str = "") -> dict:
    """User-added company. Probes it immediately for its ATS board."""
    if not name.strip():
        raise ValueError("Company name required")
    cc = Company(name=name.strip(), website=website.strip(), careers_url=careers_url.strip(), hub=hub.strip())
    cc = await probe_company(cc)
    cid = await db.insert_company({
        "name": cc.name,
        "website": cc.website,
        "careers_url": cc.careers_url,
        "hub": cc.hub,
        "ats": cc.ats,
        "ats_token": cc.ats_token,
    })
    return {"id": cid, **cc.__dict__, "probed": cc.ats != "none"}