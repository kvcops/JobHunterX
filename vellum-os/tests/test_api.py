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


def test_locations_route_returns_supported_cities():
    """The frontend calls GET /api/locations on every page load; it used to
    404 (missing route). Must return a list of supported target cities."""
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    locs = resp.json()["locations"]
    assert isinstance(locs, list) and len(locs) >= 3
    assert "Bengaluru" in locs


def test_full_search_wires_event_cb_to_run_sync(monkeypatch):
    """graph.run_full_search passed `event_callback=` to job_sync.run_sync,
    which expects `event_cb=` → TypeError raised inside the background task
    (surfaced as search_error in the log). Must now call through cleanly."""
    import asyncio

    from vellum.agents import graph, job_sync

    calls = {}

    async def fake_run_sync(**kwargs):
        calls["kwargs"] = kwargs
        return {"jobs_stored": 3}

    monkeypatch.setattr(job_sync, "run_sync", fake_run_sync)

    async def run():
        return await graph.run_full_search(
            location="Hyderabad",
            profile={"name": "Test Candidate", "skills": ["python"], "experience": []},
            event_callback=lambda e: None,
        )

    result = asyncio.new_event_loop().run_until_complete(run())
    assert result["jobs_discovered"] == 3
    assert "event_cb" in calls["kwargs"], (
        f"run_sync must receive event_cb, got keys: {sorted(calls['kwargs'])}"
    )
    assert calls["kwargs"]["preferred_location"] == "Hyderabad", (
        "the user's chosen location must reach run_sync"
    )