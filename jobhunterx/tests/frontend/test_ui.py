"""
Browser tests against the real app (tests/frontend/e2e_server.py: real backend, fake network + LLM).

Run: cd jobhunterx && python -m pytest tests/frontend -q
Requires the `playwright` Python package and a Chromium binary (PLAYWRIGHT_BROWSERS_PATH or /opt/pw-browsers).
"""

import glob
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from tests.fixtures import scenario  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _chromium() -> str | None:
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    hits = sorted(glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"))
    return hits[-1] if hits else None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = _free_port()
    data = tmp_path_factory.mktemp("e2e")
    proc = subprocess.Popen([sys.executable, "-m", "tests.frontend.e2e_server", str(port), str(data)], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "E2E_LLM_DELAY": "0.05"})
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/meta", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    req = urllib.request.Request(f"{base}/api/profile", data=json.dumps(scenario.PROFILE).encode(), method="PUT",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=_chromium()) if _chromium() else p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and pg.errors.append(m.text))
    yield pg
    ctx.close()


def run_search(page, base):
    page.goto(f"{base}/#/discover")
    page.get_by_role("button", name="Search now").click()
    expect(page.get_by_text("Search complete", exact=True)).to_be_visible(timeout=30000)


def test_search_stream_and_explanations(page, server):
    run_search(page, server)
    cards = page.locator(".job-card")
    expect(cards.first).to_contain_text("AI Engineer")
    page.get_by_role("tab", name="Not a fit").click()
    expect(page.locator(".job-card", has_text="Senior AI Engineer")).to_contain_text("Requires 6+ years")
    expect(page.locator(".job-card", has_text="Frontend Engineer")).to_contain_text("Different career track")
    expect(page.locator(".job-card", has_text="Berlin")).to_contain_text("not one of your locations")
    expect(page.locator(".job-card", has_text="Platform")).to_contain_text("Kubernetes")
    assert not page.errors


def test_detail_shows_breakdown_and_honest_unknowns(page, server):
    run_search(page, server)
    page.locator(".job-main", has_text="AI Engineer").first.click()
    drawer = page.locator(".drawer")
    expect(drawer.get_by_text("Hard requirements", exact=True)).to_be_visible()
    expect(drawer.get_by_text("How the score was built")).to_be_visible()
    drawer.get_by_role("tab", name="Verification").click()
    expect(drawer.locator(".checks")).to_contain_text("Confirmed on company ATS")
    row = drawer.locator("tr", has_text="Salary")
    expect(row).to_contain_text("Unknown")
    page.keyboard.press("Escape")
    expect(drawer).to_have_count(0)


def test_save_failure_rolls_back_and_double_click_sends_one_request(page, server):
    run_search(page, server)
    calls = []

    def fail(route):
        calls.append(route.request.method)
        time.sleep(0.3)
        route.fulfill(status=500, json={"error": {"code": "internal_error", "message": "Database is busy", "details": None}})

    page.route("**/api/jobs/*/saved", fail)
    star = page.locator(".job-card").first.locator(".save-btn")
    star.dblclick()
    expect(page.get_by_text("Database is busy")).to_be_visible()
    expect(star).to_have_attribute("aria-pressed", "false")
    assert len(calls) == 1
    page.unroute("**/api/jobs/*/saved")
    star.click()
    expect(star).to_have_attribute("aria-pressed", "true")


def test_stale_run_events_are_ignored(page, server):
    sockets = []

    def on_ws(ws):
        ws.connect_to_server()
        sockets.append(ws)

    page.route_web_socket(server.replace("http", "ws") + "/ws", on_ws)
    run_search(page, server)
    before = page.locator(".job-card").count()
    ghost = {"id": "ghost", "run_id": "old-run", "title": "Ghost Job", "company": "X", "location": "", "locations": [],
             "countries": [], "work_mode": "remote", "employment_type": "", "seniority": "junior", "role_family": "",
             "posted_at": None, "valid_through": None, "discovered_at": "2026-01-01T00:00:00Z", "apply_url": "",
             "source": None, "sources_count": 1, "salary": None,
             "validation": {"status": "active", "confidence": 1, "checked_at": None},
             "match": {"score": 99, "verdict": "strong", "headline": "ghost", "required_matched": 1, "required_total": 1,
                       "missing_required": [], "experience": {"fit": "within"}, "rejected_reasons": []},
             "match_stale": False, "saved": False, "tracking_status": "new", "pipeline_status": "discovered", "documents": {}}
    # A late event from an older run, and a run update for that run: both must be ignored.
    sockets[0].send(json.dumps({"type": "search.job", "run_id": "old-run", "data": {"job": ghost}}))
    sockets[0].send(json.dumps({"type": "search.run", "run_id": "old-run",
                                "data": {"run": {"id": "old-run", "status": "running", "stages": [], "counts": {}}}}))
    page.wait_for_timeout(400)
    expect(page.get_by_text("Search complete", exact=True)).to_be_visible()
    expect(page.get_by_text("Ghost Job")).to_have_count(0)
    assert page.locator(".job-card").count() == before


def test_out_of_order_list_responses(page, server):
    run_search(page, server)
    page.get_by_role("tab", name="All").click()
    expect(page.locator(".job-card")).to_have_count(6)

    def slow(route):
        if "q=Senior" in route.request.url:
            time.sleep(1.2)      # the older, slower request
        route.continue_()

    page.route("**/api/jobs?*", slow)
    box = page.get_by_label("Filter jobs")
    box.fill("Senior")
    page.wait_for_timeout(450)           # debounce fires → slow request in flight
    box.fill("Frontend")
    expect(page.locator(".job-card")).to_have_count(1)
    expect(page.locator(".job-card").first).to_contain_text("Frontend Engineer")
    page.wait_for_timeout(1500)          # slow response arrives late and must be ignored
    expect(page.locator(".job-card")).to_have_count(1)
    expect(page.locator(".job-card").first).to_contain_text("Frontend Engineer")


def test_resume_is_associated_with_its_job_and_failure_can_retry(page, server):
    run_search(page, server)
    page.locator(".job-main", has_text="AI Engineer").first.click()
    drawer = page.locator(".drawer")
    state = {"fail": True}

    def maybe_fail(route):
        if state["fail"]:
            state["fail"] = False
            route.fulfill(status=502, json={"error": {"code": "upstream_error", "message": "AI provider timed out", "details": None}})
        else:
            route.continue_()

    page.route("**/api/jobs/*/documents", maybe_fail)
    drawer.get_by_role("button", name="Generate", exact=True).first.click()
    expect(drawer.get_by_text("AI provider timed out")).to_be_visible()
    drawer.get_by_role("button", name="Retry").click()
    expect(drawer.get_by_role("button", name="Open", exact=True)).to_be_visible(timeout=30000)
    drawer.get_by_role("button", name="Open", exact=True).click()
    expect(page.locator(".paper")).to_contain_text("Asha Rao")
    expect(page.get_by_text("for AI Engineer @ Acme")).to_be_visible()
    expect(page.get_by_text("Rejected").first).to_be_visible()      # fact-check visible in provenance


def test_cv_is_separate_from_resume(page, server):
    page.goto(f"{server}/#/documents")
    page.get_by_role("button", name="Generate CV").click()
    expect(page.get_by_text("Download PDF", exact=True)).to_be_visible(timeout=30000)
    paper = page.locator(".paper")
    expect(paper).to_contain_text("Orbit Analytics")        # internship included in the comprehensive CV
    expect(paper).to_contain_text("VisionSort")
    page.get_by_role("button", name="All documents").click()
    expect(page.get_by_role("heading", name="CVs")).to_be_visible()


def test_untrusted_text_is_rendered_as_text(page, server):
    page.route("**/api/jobs?*", lambda r: r.fulfill(json={"jobs": [{
        "id": "x1", "run_id": None, "title": "<img src=x onerror=window.__pwned=1>", "company": "<b>Evil</b>",
        "location": "", "locations": [], "countries": [], "work_mode": "unknown", "employment_type": "", "seniority": "unknown",
        "role_family": "", "posted_at": None, "valid_through": None, "discovered_at": "2026-01-01T00:00:00Z", "apply_url": "javascript:alert(1)",
        "source": None, "sources_count": 0, "salary": None, "validation": {"status": "unverified", "confidence": 0, "checked_at": None},
        "match": None, "match_stale": False, "saved": False, "tracking_status": "new", "pipeline_status": "discovered", "documents": {}}],
        "counts": {"recommended": 1, "all": 1, "rejected": 0, "saved": 0, "applied": 0}}))
    page.goto(f"{server}/#/discover")
    expect(page.get_by_text("<img src=x onerror=window.__pwned=1>")).to_be_visible()
    assert page.evaluate("window.__pwned") is None
    assert page.locator(".job-card img").count() == 0


def test_mobile_layout_has_no_horizontal_scroll(browser, server):
    ctx = browser.new_context(viewport={"width": 375, "height": 812})
    pg = ctx.new_page()
    for route in ("discover", "profile", "documents", "settings"):
        pg.goto(f"{server}/#/{route}")
        pg.wait_for_timeout(600)
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375, route
    ctx.close()
