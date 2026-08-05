"""
Vellum OS — Job Sync Engine (DuckDuckGo Discovery + Career Page Scraping)

Fully automatic: zero user action beyond uploading a resume.

New Flow (replaces broken ATS-only approach):
  1. Search Plan: Gemma builds smart search queries from the candidate profile
  2. DuckDuckGo Discovery: free web search finds real job postings at Indian
     companies — startups, mid-size, everything except mass-hiring spam
  3. Career Page Scraping: for seed companies, directly scrape career pages
  4. ATS Fetch: for companies with known ATS boards (Greenhouse/Lever/Ashby),
     still pull structured data (kept as a bonus, not the primary source)
  5. Eligibility Gate: zero-token seniority/location/role filter
  6. Score: Gemma batch score vs the resume profile
  7. Liveness: verify top matches still exist
  8. Store: dedupe by apply_url hash, persist with match_score

Why DuckDuckGo:
  - FREE, no API key, no credits, no limits (with rate limiting)
  - Actually finds jobs at real Indian companies
  - Surfaces startups people don't know about
  - Filters out TCS/Infosys/Wipro mass-hiring spam
  - No expired/false links like the old ATS-only approach
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
from vellum.tools import job_discovery

log = get_logger("job_sync")

EventCallback = Callable[[dict], Awaitable[None]]

SEED_CSV = Path(__file__).resolve().parents[2] / "data" / "companies.csv"


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


def _normalize_discovered_job(raw: dict) -> dict:
    """Convert a job dict from the new discovery engine into the standard format."""
    url = raw.get("apply_url") or ""
    company = raw.get("company") or ""
    role = raw.get("title") or raw.get("role") or ""
    key = f"{company}|{role}|{url}"
    return {
        "id_key": hashlib.sha256(key.encode()).hexdigest(),
        "company": company,
        "role": _slug_role(role),
        "location": raw.get("location") or "",
        "department": "",
        "jd_text": raw.get("jd_text") or raw.get("search_snippet") or "",
        "apply_url": url,
        "career_page_url": raw.get("career_page_url") or url,
        "posted_at": "",
        "source": raw.get("source") or "ddg_search",
    }


async def store_jobs(job_dicts: list[dict]) -> dict:
    """Dedupe by apply_url hash AND by normalized (company, role) across
    sources (same job posted on search + career page must not duplicate).

    Source preference: ATS > career_page > ddg_search > hasjob.
    Returns {inserted, duplicates}.
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

    SRC_PRIORITY = {"hasjob": 0, "ddg_search": 1, "career_page": 2}
    role_index: dict[tuple[str, str], dict] = {}
    for job in job_dicts:
        key = ((job.get("company") or "").lower(),
               re.sub(r"[^a-z0-9]+", " ", (job.get("role") or "").lower()).strip())
        if not key[1]:
            continue
        prior = role_index.get(key)
        src = str(job.get("source") or "")
        src_base = src.split(":")[0] if ":" in src else src
        if prior is None or SRC_PRIORITY.get(src_base, 3) > SRC_PRIORITY.get(
            str(prior.get("source") or "").split(":")[0], 3
        ):
            role_index[key] = job

    final_jobs = list(role_index.values())

    inserted = 0
    duplicates = 0
    for job in final_jobs:
        h = hashes.get(job["id_key"])
        if h and h in existing:
            duplicates += 1
            continue
        job_id = await db.insert_job({
            "company": job["company"],
            "role": job["role"],
            "career_page_url": job.get("career_page_url", ""),
            "apply_url": job.get("apply_url", ""),
            "jd_text": job.get("jd_text", ""),
            "source": job.get("source", ""),
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


async def run_sync(
    profile: Optional[dict] = None,
    company_filter: Optional[list[str]] = None,
    limit_companies: int = 0,
    event_cb: Optional[EventCallback] = None,
    discover: bool = True,
    probe_concurrency: int = 6,
    probe_freshness_hours: float = 24.0,
    max_probe_per_run: int = 30,
    liveness_max_checks: int = 40,
    preferred_location: Optional[str] = None,
) -> dict:
    """Run one full sync pass. Fully automatic — no company selection needed.

    New value chain:
      1. Search plan (Gemma, 1 call)
      2. DuckDuckGo discovery (FREE, main source)
      3. Career page scraping (seed companies, FREE)
      4. ATS board fetch (bonus for companies with Greenhouse/Lever etc.)
      5. Strict eligibility gate (zero tokens)
      6. Store eligible jobs
      7. Gemma ranking of survivors
      8. Liveness check on top matches
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

    summary = {
        "probed": 0, "ats_found": 0, "jobs_fetched": 0, "jobs_stored": 0,
        "scored": 0, "skipped_budget": False, "feed_jobs": 0,
        "companies_discovered": 0, "eligible": 0,
        "rejected": 0, "duplicates": 0, "verified": 0, "gone": 0,
        "ddg_discovered": 0, "career_page_jobs": 0,
        "plan": None,
    }

    # --- Step 0: search plan (Gemma, 1 call) ---
    plan = None
    if profile:
        plan = await search_planner.build_search_plan(profile)
        if preferred_location and preferred_location.strip():
            loc = preferred_location.strip().title()
            plan["locations"] = [loc] + [l for l in (plan.get("locations") or [])
                                         if l.lower() != loc.lower()]
        summary["plan"] = {
            "seniority_max": plan.get("seniority_max"),
            "years_experience": plan.get("years_experience"),
            "locations": plan.get("locations"),
            "reject_terms": plan.get("reject_terms"),
            "target_roles": plan.get("target_roles"),
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
        await emit("warning", "No seed companies — DuckDuckGo discovery will still find jobs.", {})

    all_job_dicts: list[dict] = []

    # --- Step 2: DuckDuckGo Discovery (PRIMARY source) ---
    if discover and profile and plan:
        await emit("progress", "Starting DuckDuckGo job discovery (free, no API key)...", {})
        try:
            ddg_jobs = await job_discovery.discover_jobs(
                profile=profile,
                plan=plan,
                max_queries=12,
                results_per_query=12,
                max_scrape=40,
                scrape_concurrency=6,
                event_cb=event_cb,
            )
            ddg_normalized = [_normalize_discovered_job(j) for j in ddg_jobs]
            all_job_dicts.extend(ddg_normalized)
            summary["ddg_discovered"] = len(ddg_normalized)
            await emit("progress",
                       f"DuckDuckGo: found {len(ddg_normalized)} potential jobs", {})
        except Exception as exc:
            log.warning("ddg_discovery_failed", error=str(exc)[:200])
            await emit("warning", f"DuckDuckGo discovery error: {str(exc)[:100]}", {})

    # --- Step 3: Career page scraping (seed companies) ---
    if discover and companies:
        sample = companies[:40]
        await emit("progress",
                    f"Scraping career pages of {len(sample)} known companies...", {})
        try:
            cp_jobs = await job_discovery.scrape_career_page_jobs(
                companies=sample,
                concurrency=5,
                event_cb=event_cb,
            )
            cp_normalized = [_normalize_discovered_job(j) for j in cp_jobs]
            all_job_dicts.extend(cp_normalized)
            summary["career_page_jobs"] = len(cp_normalized)
        except Exception as exc:
            log.warning("career_page_scrape_failed", error=str(exc)[:200])

    # --- Step 4: ATS board fetch (bonus, not primary) ---
    ats_companies = await db.get_companies_due_probe(stale_after_hours=probe_freshness_hours)
    if company_filter:
        fset = {c.lower() for c in company_filter}
        ats_companies = [c for c in ats_companies if c["name"].lower() in fset]
    if max_probe_per_run:
        ats_companies = ats_companies[:max_probe_per_run]
    if limit_companies:
        ats_companies = ats_companies[:limit_companies]

    # Only probe companies that already have a known ATS (saves time)
    ats_known = [c for c in ats_companies if c.get("ats") and c.get("ats") != "none"]
    ats_unknown = [c for c in ats_companies if not c.get("ats") or c.get("ats") == "none"]
    # Probe unknown ones in smaller batches to not waste time
    to_probe = ats_known + ats_unknown[:15]

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

    if to_probe:
        await emit("progress", f"Probing {len(to_probe)} companies for ATS boards...", {})
        results: list[tuple[dict, list[Job]]] = []
        for i in range(0, len(to_probe), probe_concurrency):
            chunk = to_probe[i:i + probe_concurrency]
            results.extend(await asyncio.gather(*(probe_limited(c) for c in chunk)))

        for comp, jobs in results:
            summary["probed"] += 1
            if not jobs:
                continue
            summary["ats_found"] += 1
            summary["jobs_fetched"] += len(jobs)
            all_job_dicts.extend(
                _normalize_job(j, hub=comp.get("hub") or "") for j in jobs
            )

    # --- Step 5: Hasjob feed (bonus, often unreliable) ---
    if discover:
        try:
            feed_jobs = await hasjob.fetch_feed()
        except Exception as exc:
            log.warning("hasjob_fetch_failed", error=str(exc)[:150])
            feed_jobs = []
        summary["feed_jobs"] = len(feed_jobs)
        if feed_jobs:
            known = {c["name"].lower() for c in (await db.get_companies())}
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
                all_job_dicts.append({
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

    await emit("progress",
               f"Total raw jobs: {len(all_job_dicts)} "
               f"(DDG: {summary['ddg_discovered']}, "
               f"Career pages: {summary['career_page_jobs']}, "
               f"ATS: {summary['jobs_fetched']}, "
               f"Feed: {summary['feed_jobs']})", {})

    # --- Step 6: strict eligibility gate (zero LLM tokens) ---
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

    # --- Step 7: store eligible jobs ---
    stored = await store_jobs(all_job_dicts)
    summary["jobs_stored"] += stored["inserted"]
    summary["duplicates"] = stored["duplicates"]

    # --- Step 8: Gemma ranking of the eligible survivors ---
    if profile and all_job_dicts:
        all_job_dicts = await job_scorer.score_batch(all_job_dicts, profile)
        summary["scored"] = sum(1 for j in all_job_dicts if j.get("match_score") is not None)
        for job in all_job_dicts:
            if job.get("match_score") is not None:
                await _persist_score(job)
        if g.is_exhausted():
            summary["skipped_budget"] = True

    # --- Step 9: liveness check on TOP matches ---
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