"""
Tests for cross-source dedupe + fresh-DB behaviour in store_jobs, plus the
probe-freshness machinery (last_probed_at stamping + due query).

Locked in from the review fixes:
  - ATS jobs win over hasjob/HN for the same (company, role).
  - A URL-hash duplicate is counted, not re-inserted.
  - Companies probed recently are skipped by get_companies_due_probe.
"""

import asyncio

from vellum.config import database as db
from vellum.agents import job_sync


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def make_job(company, role, source, apply_url=""):
    return {
        "id_key": job_sync._dedupe_key(apply_url or f"{company}|{role}"),
        "company": company,
        "role": role,
        "location": "Bengaluru",
        "department": "",
        "jd_text": "",
        "apply_url": apply_url,
        "career_page_url": "",
        "posted_at": "",
        "source": source,
    }


# --- Cross-source dedupe --------------------------------------------------


def test_ats_wins_over_hasjob_same_role():
    hn_job = make_job("Acme", "Frontend Engineer", "hn")
    ats_job = make_job("Acme", "Frontend Engineer", "greenhouse:acme",
                       apply_url="https://boards.greenhouse.io/acme/1")
    result = run(job_sync.store_jobs([hn_job, ats_job]))
    assert result["inserted"] == 1
    assert result["duplicates"] == 0  # the HN one is dropped pre-insert

    jobs = run(db.get_jobs(limit=50))
    assert len(jobs) == 1
    assert jobs[0]["source"] == "greenhouse:acme"


def test_same_url_hash_counts_as_duplicate():
    a = make_job("Acme", "Role A", "hn", apply_url="https://jobs.example.com/1")
    b = make_job("Acme", "Role B", "hn", apply_url="https://jobs.example.com/1")
    r1 = run(job_sync.store_jobs([a]))
    assert r1["inserted"] == 1
    r2 = run(job_sync.store_jobs([b]))
    assert r2["duplicates"] == 1
    assert r2["inserted"] == 0


def test_distinct_roles_both_inserted():
    a = make_job("Acme", "Frontend Engineer", "hn")
    b = make_job("Acme", "Backend Engineer", "hn")
    result = run(job_sync.store_jobs([a, b]))
    assert result["inserted"] == 2


def test_inserted_jobs_get_real_id():
    job = make_job("Acme", "Role", "hn")
    r = run(job_sync.store_jobs([job]))
    assert r["inserted"] == 1
    assert job.get("id"), "store_jobs must set job['id'] to the inserted row id"


# --- Probe freshness ------------------------------------------------------


def test_update_company_stamps_last_probed_at():
    cid = run(db.insert_company({"name": "FreshCo", "website": "https://f.com",
                                 "careers_url": "", "hub": "Bengaluru"}))
    run(db.update_company_ats(cid, "greenhouse", "freshco", "https://f.com/careers"))
    c = run(db.get_company_by_name("FreshCo"))
    assert c["ats"] == "greenhouse"
    assert c["ats_token"] == "freshco"
    assert c["last_probed_at"]  # stamped


def test_due_probe_skips_fresh_company():
    cid = run(db.insert_company({"name": "OldCo", "website": "https://o.com",
                                 "careers_url": "", "hub": ""}))
    due = run(db.get_companies_due_probe(stale_after_hours=24.0))
    assert any(c["id"] == cid for c in due)

    run(db.update_company_ats(cid, "none", "", ""))
    due = run(db.get_companies_due_probe(stale_after_hours=24.0))
    assert not any(c["id"] == cid for c in due), "freshly-probed company should be excluded"


def test_due_probe_orders_oldest_first():
    cid_a = run(db.insert_company({"name": "A", "website": "https://a.com", "careers_url": "", "hub": ""}))
    cid_b = run(db.insert_company({"name": "B", "website": "https://b.com", "careers_url": "", "hub": ""}))
    run(db.update_company_ats(cid_b, "none", "", ""))  # B probed AFTER A → A older
    due = run(db.get_companies_due_probe(stale_after_hours=24.0))
    due_ids = [c["id"] for c in due]
    assert due_ids[0] == cid_a, "never-probed / oldest first"

    due_two = run(db.get_companies_due_probe(stale_after_hours=24.0))
    assert due_two == due

# --- Closed-hide query ----------------------------------------------------


def test_get_jobs_excluding_hides_closed():
    job = make_job("Acme", "Role", "hn")
    run(job_sync.store_jobs([job]))
    jid = job["id"]
    run(db.update_job(jid, status="closed"))

    visible = run(db.get_jobs_excluding(["closed"], limit=50))
    assert len(visible) == 0

    all_jobs = run(db.get_jobs(limit=50))
    assert len(all_jobs) == 1
    assert all_jobs[0]["status"] == "closed"