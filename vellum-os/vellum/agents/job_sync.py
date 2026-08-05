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
from vellum.tools import hasjob, liveness

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
    """Dedupe by apply_url hash AND by normalized (company, role) across
    sources (same job posted on hasjob + Greenhouse must not duplicate).

    Source preference for the same role at the same company:
    ATS (structured, richest) > hasjob > hn. Returns {inserted, duplicates}.
    """
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

    # Cross-source dedupe: prefer ATS data for identical (company, role).
    SRC_PRIORITY = {"hn": 0, "hasjob": 1}
    role_index: dict[tuple[str, str], dict] = {}
    for job in job_dicts:
        key = ((job.get("company") or "").lower(),
               re.sub(r"[^a-z0-9]+", " ", (job.get("role") or "").lower()).strip())
        if not key[1]:
            continue
        prior = role_index.get(key)
        src = str(job.get("source") or "")
        if prior is None or SRC_PRIORITY.get(src, 2) > SRC_PRIORITY.get(str(prior.get("source") or ""), 2):
            role_index[key] = job

    final_jobs = list(role_index.values())
    for job in job_dicts:
        key = ((job.get("company") or "").lower(),
               re.sub(r"[^a-z0-9]+", " ", (job.get("role") or "").lower()).strip())
        if key[1] and role_index.get(key) is not job:
            job["_cross_dupe"] = True

    inserted = 0
    duplicates = 0
    for job in final_jobs:
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
        job["id"] = job_id
        extras = {}
        if job.get("match_score") is not None:
            extras["match_score"] = job["match_score"]
        if job.get("eligibility") is not None:
            extras["freshness_json"] = json.dumps({"eligibility": job["eligibility"]})
        if job.get("score_reason"):
            extras["validation_json"] = json.dumps({"score_reason": job["score_reason"]})
        if extras:
            await db.update_job(job_id, **extras)
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
    probe_freshness_hours: float = 24.0,
    max_probe_per_run: int = 60,
    liveness_max_checks: int = 40,
    preferred_location: Optional[str] = None,
) -> dict:
    """Run one full sync pass. Fully automatic — no company selection needed.

    Value chain: search plan (Gemma) → hasjob.co feed + ATS boards → strict
    eligibility gate (zero tokens) → store → liveness check (top matches) →
    Gemma ranking of survivors.

    Args:
        profile: candidate profile (required for eligibility + scoring).
        company_filter: only sync these company names (empty = all).
        limit_companies: cap how many companies to probe this run (0 = all).
        discover: also ingest live feeds before ATS probing.
        probe_concurrency: how many companies to probe in parallel.
        probe_freshness_hours: skip companies probed within this window.
        max_probe_per_run: hard cap on companies probed per run. Feed
            discovery grows the company DB unboundedly; without a cap a
            sync could probe hundreds of never-checked companies and take
            forever. Oldest-first cycling drains the backlog across runs.
        liveness_max_checks: how many top matches get a liveness GET-check.
        preferred_location: the user's explicitly chosen city. Overrides the
            plan's location list — the resume's city alone must never decide
            where jobs are accepted (that's the "search ruined" bug).
    """
    from vellum.config import gemma as g
    from vellum.agents import eligibility, search_planner

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
               "companies_discovered": 0, "eligible": 0,
               "rejected": 0, "duplicates": 0, "verified": 0, "gone": 0,
               "plan": None}

    # --- Step 0: search plan — the intelligence anchor (Gemma, 1 call) ---
    plan = None
    if profile:
        plan = await search_planner.build_search_plan(profile)
        # The user's explicit location wins over whatever the resume says.
        if preferred_location and preferred_location.strip():
            loc = preferred_location.strip().title()
            plan["locations"] = [loc] + [l for l in (plan.get("locations") or [])
                                         if l.lower() != loc.lower()]
        summary["plan"] = {
            "seniority_max": plan.get("seniority_max"),
            "years_experience": plan.get("years_experience"),
            "locations": plan.get("locations"),
            "reject_terms": plan.get("reject_terms"),
        }
        await emit("progress",
                   f"Plan: {plan.get('seniority_max')} ceiling, "
                   f"{plan.get('years_experience')} yrs, roles: "
                   f"{', '.join((plan.get('target_roles') or [])[:3])}", {})

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

    # --- Step 2: live feed discovery (hasjob.co) ---
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
                "id_key": _dedupe_key(fj.get("apply_url") or
                                      f"{cname}|{fj.get('role') or ''}"),
                "company": cname,
                "role": _slug_role(fj.get("title") or fj.get("role") or ""),
                "location": fj.get("location") or "",
                "department": "",
                "jd_text": fj.get("jd_text") or "",
                "apply_url": fj.get("apply_url") or "",
                "career_page_url": fj.get("website") or "",
                "posted_at": fj.get("posted_at") or "",
                "source": fj.get("source") or "hasjob",
            })
        if feed_job_dicts:
            await emit("progress",
                       f"Feeds: {summary['feed_jobs']} hasjob jobs, "
                       f"{summary['companies_discovered']} new companies.", {})
        companies = await db.get_companies()

    # --- Step 3: probe + fetch ATS boards (parallel, freshness-aware) ---
    # Only companies not probed in the last N hours get re-probed. This keeps
    # sync time bounded as the company DB grows from feed discovery.
    companies = await db.get_companies_due_probe(stale_after_hours=probe_freshness_hours)
    if company_filter:
        fset = {c.lower() for c in company_filter}
        companies = [c for c in companies if c["name"].lower() in fset]
    if max_probe_per_run:
        companies = companies[:max_probe_per_run]
    if limit_companies:
        companies = companies[:limit_companies]
    summary["companies_due_probe"] = len(companies)

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

    # --- Step 4: strict eligibility gate (zero LLM tokens) ---
    if plan:
        all_job_dicts, rejected = eligibility.filter_jobs(all_job_dicts, plan)
        summary["eligible"] = len(all_job_dicts)
        summary["rejected"] = len(rejected)
        if rejected:
            sample = [{"company": j["company"], "role": j["role"],
                       "why": j["eligibility"]["reason"]} for j in rejected[:5]]
            await emit("progress",
                       f"Gate: {len(rejected)} jobs rejected "
                       f"(seniority/location/role) → {len(all_job_dicts)} eligible.", {})
            log.info("eligibility_gate", rejected=len(rejected),
                     eligible=len(all_job_dicts), sample=sample)

    # --- Step 5: store eligible jobs ---
    stored = await store_jobs(all_job_dicts)
    summary["jobs_stored"] += stored["inserted"]
    summary["duplicates"] = stored["duplicates"]

    # --- Step 6: Gemma ranking of the eligible survivors ---
    if profile and all_job_dicts:
        all_job_dicts = await job_scorer.score_batch(all_job_dicts, profile)
        summary["scored"] = sum(1 for j in all_job_dicts if j.get("match_score") is not None)
        # Persist scores/reasons (store_jobs only wrote what it had pre-scoring)
        for job in all_job_dicts:
            if job.get("match_score") is not None:
                await _persist_score(job)
        if g.is_exhausted():
            summary["skipped_budget"] = True

    # --- Step 7: liveness check on TOP matches (prove they still exist) ---
    if stored["inserted"]:
        checkable = list(all_job_dicts)
        verdicts = await liveness.verify_top_jobs(checkable,
                                                  max_checks=liveness_max_checks)
        from datetime import datetime, timezone
        checked_at = datetime.now(timezone.utc).isoformat()
        for job in checkable:
            jid = job.get("id") or job.get("id_key")
            verdict = verdicts.get(jid or "")
            if not verdict or not job.get("id"):
                continue
            # Persist the verdict so the UI can show "verified live X ago"
            try:
                row = await db.get_job(job["id"])
                fj = {}
                if row and row.get("freshness_json"):
                    try:
                        fj = json.loads(row["freshness_json"])
                    except Exception:
                        fj = {}
                fj["liveness"] = verdict
                fj["liveness_checked_at"] = checked_at
                await db.update_job(job["id"], freshness_json=json.dumps(fj))
            except Exception as exc:
                log.debug("liveness_persist_failed", error=str(exc)[:100])
            if verdict == "gone":
                summary["gone"] += 1
                try:
                    await db.update_job(job["id"], status="closed")
                except Exception:
                    pass
        summary["verified"] = sum(1 for v in verdicts.values() if v != "unknown")
        if verdicts:
            await emit("progress",
                       f"Liveness: verified {summary['verified']} top matches, "
                       f"{summary['gone']} closed.", {})

    if summary["skipped_budget"]:
        await emit("warning",
                   "Gemma daily budget exhausted — remaining jobs scored by keyword only.", {})
    await emit("complete", "Sync finished.", summary)
    log.info("sync_finished", **summary)
    return summary


async def _persist_score(job: dict) -> None:
    """Write match_score + reason back to the stored job row."""
    jid = job.get("id") or job.get("id_key")
    if not jid:
        return
    row = await db.get_job(jid)
    if row is None:
        return
    await db.update_job(jid, match_score=job["match_score"])
    reason = job.get("score_reason")
    if reason:
        vj = {}
        if row.get("validation_json"):
            try:
                vj = json.loads(row["validation_json"])
            except Exception:
                vj = {}
        vj["score_reason"] = reason
        await db.update_job(jid, validation_json=json.dumps(vj))


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