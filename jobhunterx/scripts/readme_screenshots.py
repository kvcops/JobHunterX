"""Re-take the README screenshots (assets/ui_*.png) from the real app running against the fake outside world
(tests/fixtures/scenario.py: sample candidate, sample jobs, fake AI) — same data every time, no keys needed.

Run from jobhunterx/:  python -m scripts.readme_screenshots [--only documents,match,...]
Needs the `playwright` package and a Chromium (PLAYWRIGHT_BROWSERS_PATH or /opt/pw-browsers).
Screens that need a live external state (the auto-apply browser, CAPTCHA hand-over, the first-run key screen,
onboarding) are not re-taken here.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # jobhunterx/
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
sys.path.insert(0, HERE)
from tests.fixtures import scenario  # noqa: E402

JD = ("AI Engineer at Zeta Labs, Hyderabad. You will build retrieval-augmented generation (RAG) assistants and LLM "
      "features in Python with LangChain and PyTorch, ship APIs with FastAPI and Docker, and evaluate models.\n"
      "Requirements: Python, LangChain, RAG, PyTorch, FastAPI, Docker, SQL; 0-2 years of experience.")


def _port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _chromium() -> str | None:
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    hits = sorted(glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"))
    return hits[-1] if hits else None


def _api(base: str, path: str, method: str = "GET", body=None):
    req = urllib.request.Request(f"{base}{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read() or b"{}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated shot names")
    args = ap.parse_args()
    want = set(filter(None, args.only.split(",")))
    take = (lambda name: not want or name in want)

    port, data = _port(), tempfile.mkdtemp(prefix="jhx-shots-")
    proc = subprocess.Popen([sys.executable, "-m", "tests.frontend.e2e_server", str(port), data], cwd=HERE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "E2E_LLM_DELAY": "0.35"})
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(150):
            try:
                urllib.request.urlopen(f"{base}/api/meta", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        _api(base, "/api/profile", "PUT", scenario.PROFILE)
        active = _api(base, "/api/people")["active"]
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=_chromium()) if _chromium() else p.chromium.launch()

            def context(**kw):
                ctx = browser.new_context(**kw)
                ctx.add_init_script(f"try {{ sessionStorage.setItem('jhx-picked', '{active}'); }} catch (e) {{}}")
                return ctx

            def shot(page, name, **kw):
                page.wait_for_timeout(700)                         # let entrance animations settle
                path = os.path.join(ASSETS, f"ui_{name}.png")
                page.screenshot(path=path, **kw)
                print("saved", os.path.relpath(path, os.path.dirname(HERE)))

            desk = context(viewport={"width": 1440, "height": 900})
            pg = desk.new_page()

            # search, live, then a match explained
            pg.goto(f"{base}/#/discover")
            pg.get_by_role("button", name="Search now").click()
            pg.wait_for_timeout(3500)
            if take("live_progress"):
                shot(pg, "live_progress")
            pg.get_by_role("heading", name="Search complete").wait_for(timeout=60000)
            pg.locator(".job-main", has_text="AI Engineer").first.click()
            pg.locator(".detail-pane .detail").first.wait_for(timeout=20000)
            if take("match"):
                shot(pg, "match")

            if take("companies"):
                pg.goto(f"{base}/#/companies")
                pg.wait_for_timeout(1500)
                shot(pg, "companies")

            # documents: a resume for a pasted job, edited on the page; then two columns
            if take("custom_resume") or take("documents") or take("resume_two_column"):
                pg.goto(f"{base}/#/documents")
                pg.get_by_role("button", name="Resume for a job").click()
                dlg = pg.get_by_role("dialog", name="Resume for a job")
                dlg.get_by_placeholder("Paste the full description").fill(JD)
                dlg.get_by_label("Company").fill("Zeta Labs")
                if take("custom_resume"):
                    shot(pg, "custom_resume")
                dlg.get_by_role("button", name="Create resume").click()
                pg.locator(".paper").wait_for(timeout=60000)
                pg.locator('.paper [data-p="summary"]').click()
                if take("documents"):
                    shot(pg, "documents")
                pg.locator(".ed-toolbar").get_by_role("radio", name="Two columns").click()
                pg.locator(".ed-status", has_text="Saved").wait_for(timeout=30000)
                pg.locator(".paper-stage").evaluate("el => el.scrollTo(0, 0)")
                pg.locator(".paper .paper-head h2").click()
                if take("resume_two_column"):
                    shot(pg, "resume_two_column")

            if take("tracker"):
                jobs = _api(base, "/api/jobs?view=all")["jobs"]
                for j, status in zip(jobs, ("applied", "interviewing", "saved")):
                    try:
                        _api(base, f"/api/jobs/{j['id']}", "PATCH", {"tracking_status": status})
                    except Exception:
                        pass
                pg.goto(f"{base}/#/tracker")
                pg.wait_for_timeout(1500)
                shot(pg, "tracker")

            if take("profile"):
                pg.goto(f"{base}/#/profile")
                pg.wait_for_timeout(1500)
                shot(pg, "profile")

            if take("settings"):
                pg.goto(f"{base}/#/settings")
                pg.wait_for_timeout(1500)
                shot(pg, "settings")

            if take("dark"):
                dark = context(viewport={"width": 1440, "height": 900})
                dk = dark.new_page()
                dk.add_init_script("try { localStorage.setItem('jhx-theme', 'dark'); } catch (e) {}")
                dk.goto(f"{base}/#/discover")
                dk.wait_for_timeout(1500)
                dk.get_by_role("tab", name="All").click()
                dk.locator(".job-main", has_text="AI Engineer").first.click()
                dk.locator(".detail-pane .detail").first.wait_for(timeout=20000)
                shot(dk, "dark")
                dark.close()

            if take("mobile"):
                phone = context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
                ph = phone.new_page()
                ph.goto(f"{base}/#/discover")
                ph.wait_for_timeout(1800)
                shot(ph, "mobile")
                phone.close()

            desk.close()
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
