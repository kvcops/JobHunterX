"""API contract tests (docs/API.md): validation, error envelope, async flows, idempotency, security."""

import time

import pytest
from fastapi.testclient import TestClient

from jobhunterx.api.main import app
from tests.fixtures import scenario


@pytest.fixture
def client(monkeypatch):
    scenario.install(monkeypatch)
    from jobhunterx.services.search import manager
    manager._run = None
    manager._task = None
    with TestClient(app, raise_server_exceptions=False) as c:   # no lifespan: DB set by conftest
        yield c


@pytest.fixture(autouse=True)
def _no_lifespan_db(monkeypatch):
    # TestClient's context manager runs lifespan, which would point the DB at ./data.
    from jobhunterx.api import main
    from jobhunterx.config import database as db
    path = db._db_path
    monkeypatch.setattr(main, "set_db_path", lambda p: db.set_db_path(path))


def _wait_run(client, run_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        run = client.get(f"/api/searches/{run_id}").json()["run"]
        if run["status"] not in ("queued", "running"):
            return run
        time.sleep(0.1)
    raise AssertionError("search did not finish")


def test_error_envelope_and_validation(client):
    r = client.get("/api/jobs/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.post("/api/searches", json={})
    assert r.status_code == 400 and "profile" in r.json()["error"]["message"].lower()
    r = client.put("/api/profile", json={"preferences": {"notice_period_days": "abc"}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.get("/api/jobs", params={"view": "bogus"})
    assert r.status_code == 400


def test_upload_rejects_non_pdf_and_large_files(client):
    r = client.post("/api/profile/upload", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 422
    r = client.post("/api/profile/upload", files={"file": ("x.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024 + 10), "application/pdf")})
    assert r.status_code == 413


def test_full_flow_search_save_track_generate(client):
    r = client.put("/api/profile", json=scenario.PROFILE)
    assert r.status_code == 200
    env = r.json()
    assert env["snapshot"]["method"] == "llm" and env["profile_hash"]

    run = client.post("/api/searches", json={}).json()["run"]
    run = _wait_run(client, run["id"])
    assert run["status"] == "completed", run
    assert [s["status"] for s in run["stages"]] == ["done"] * 10

    data = client.get("/api/jobs", params={"view": "recommended", "run_id": run["id"]}).json()
    titles = [j["title"] for j in data["jobs"]]
    assert "AI Engineer" in titles and "Senior AI Engineer" not in titles and "Frontend Engineer" not in titles
    assert data["counts"]["rejected"] >= 3          # the Berlin job is dropped before scoring
    job = next(j for j in data["jobs"] if j["title"] == "AI Engineer")
    assert job["match"]["verdict"] in ("strong", "good") and job["source"]["first_party"]

    # save is idempotent and reflected in counts
    for _ in range(2):
        assert client.put(f"/api/jobs/{job['id']}/saved").json()["job"]["saved"] is True
    assert client.get("/api/jobs", params={"view": "saved"}).json()["counts"]["saved"] == 1
    assert client.delete(f"/api/jobs/{job['id']}/saved").json()["job"]["saved"] is False

    r = client.patch(f"/api/jobs/{job['id']}", json={"tracking_status": "teleported"})
    assert r.status_code == 422
    assert client.patch(f"/api/jobs/{job['id']}", json={"tracking_status": "applied"}).json()["job"]["tracking_status"] == "applied"

    detail = client.get(f"/api/jobs/{job['id']}").json()["job"]
    assert detail["match"]["hard_constraints"] and detail["validation"]["checks"]["ats_confirmed"]["status"] == "verified"

    doc = client.post(f"/api/jobs/{job['id']}/documents", json={"kind": "resume"}).json()["document"]
    assert doc["kind"] == "resume" and doc["job_id"] == job["id"] and doc["has_pdf"]
    pdf = client.get(f"/api/documents/{doc['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    cv = client.post("/api/documents/cv", json={}).json()["document"]
    assert cv["kind"] == "cv" and cv["job_id"] is None
    kinds = {d["kind"] for d in client.get("/api/documents").json()["documents"]}
    assert kinds == {"resume", "cv"}

    # profile change marks matches and documents stale
    p2 = {**scenario.PROFILE, "summary": "Changed summary for staleness."}
    client.put("/api/profile", json=p2)
    j2 = client.get(f"/api/jobs/{job['id']}").json()["job"]
    assert j2["match_stale"] is True and all(d["stale"] for d in j2["document_list"])


def test_new_search_cancels_previous(client):
    client.put("/api/profile", json=scenario.PROFILE)
    first = client.post("/api/searches", json={}).json()["run"]
    second = client.post("/api/searches", json={}).json()["run"]
    assert first["id"] != second["id"]
    assert client.get(f"/api/searches/{first['id']}").json()["run"]["status"] in ("cancelled", "completed")
    assert _wait_run(client, second["id"])["status"] == "completed"


def test_websocket_rejects_foreign_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_text()
    with client.websocket_connect("/ws", headers={"origin": "http://testserver", "host": "testserver"}):
        pass


def test_settings_reject_injection_and_mask_keys(client, tmp_path, monkeypatch):
    from jobhunterx.config import settings as st
    monkeypatch.setattr(st, "_BASE_DIR", tmp_path)
    r = client.post("/api/settings", json={"tavily_api_key": "abc\nEVIL=1"})
    assert r.status_code == 422
    r = client.post("/api/settings", json={"tavily_api_key": "tvly-1234567890"})
    assert r.json()["tavily_key_masked"].endswith("7890") and "1234567890" not in r.text


def test_ssrf_guard_blocks_private_addresses():
    import asyncio
    from jobhunterx.discovery import net
    for url in ("http://127.0.0.1:8000/api/reset", "http://169.254.169.254/latest/meta-data", "file:///etc/passwd"):
        res = asyncio.new_event_loop().run_until_complete(net.fetch(url))
        assert not res.ok and res.error


def test_cross_site_writes_are_blocked(client):
    r = client.post("/api/reset", headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert client.get("/api/meta", headers={"origin": "https://evil.example"}).status_code == 200
