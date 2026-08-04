"""
API end-to-end tests for the job-listing surface (Fix 6):
  - GET /api/jobs hides status='closed' jobs by default
  - include_closed=true shows them
  - status filter works
  - freshness_json is parsed into the response
  - apply statuses ('applied' / 'apply_failed') survive listing
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from vellum.config import database as db
from vellum.agents import job_sync

from fastapi import FastAPI
from vellum.api.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def make_job(company, role, source="hn", status="discovered", apply_url=""):
    return {
        "id_key": job_sync._dedupe_key(apply_url or f"{company}|{role}"),
        "company": company,
        "role": role,
        "location": "Bengaluru",
        "department": "",
        "jd_text": "A good software engineering role for someone early in their career.",
        "apply_url": apply_url,
        "career_page_url": "",
        "posted_at": "",
        "source": source,
    }


def seed():
    """Insert 3 jobs: one discovered, one closed, one applied."""
    run(db.clear_jobs())
    a = make_job("Acme", "Frontend Engineer", "hn", apply_url="https://a.example.com/1")
    b = make_job("Beta", "Backend Engineer", "hn", apply_url="https://b.example.com/2")
    c = make_job("Gamma", "DevOps Engineer", "hn", apply_url="https://c.example.com/3")
    run(job_sync.store_jobs([a, b, c]))
    run(db.update_job(b["id"], status="closed"))
    run(db.update_job(c["id"], status="applied",
                      freshness_json=json.dumps({"liveness": "live", "liveness_checked_at": "2026-08-04T00:00:00Z"})))


def test_default_list_hides_closed():
    seed()
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) == 2
    statuses = {j["status"] for j in jobs}
    assert "closed" not in statuses
    assert {"discovered", "applied"} == statuses


def test_include_closed_shows_everything():
    seed()
    resp = client.get("/api/jobs", params={"include_closed": True})
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) == 3
    assert any(j["status"] == "closed" for j in jobs)


def test_status_filter_returns_only_that_status():
    seed()
    resp = client.get("/api/jobs", params={"status": "closed"})
    jobs = resp.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "closed"
    assert jobs[0]["company"] == "Beta"


def test_freshness_parsed_into_response():
    seed()
    resp = client.get("/api/jobs", params={"include_closed": True})
    jobs = resp.json()["jobs"]
    gamma = next(j for j in jobs if j["company"] == "Gamma")
    assert gamma["freshness"]["liveness"] == "live"
    assert gamma["freshness"]["liveness_checked_at"] == "2026-08-04T00:00:00Z"


def test_apply_statuses_survive_listing():
    seed()
    resp = client.get("/api/jobs", params={"status": "applied"})
    jobs = resp.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Gamma"


def test_get_single_job_parses_freshness():
    seed()
    resp = client.get("/api/jobs", params={"include_closed": True})
    jid = next(j["id"] for j in resp.json()["jobs"] if j["company"] == "Gamma")
    one = client.get(f"/api/jobs/{jid}")
    assert one.status_code == 200
    assert one.json()["job"]["freshness"]["liveness"] == "live"


def test_sync_route_wiring_does_not_400():
    """The /api/companies/sync route used to pass a bad kwarg (event_callback
    instead of event_cb) → TypeError every call. Now it must at least accept
    the request (it may 409 if another sync is running, or 200 if not)."""
    resp = client.post("/api/companies/sync")
    assert resp.status_code in (200, 409)