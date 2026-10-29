"""
JobHunterX desktop backend — the same FastAPI app, started for one person on this computer.

The desktop window (desktop/src-tauri) starts this program and shows the page it serves. It:

* keeps .env and data/ in the user's app-data folder (an installed app's own folder is read-only)
* listens on 127.0.0.1 only, on a stable port so the page's saved settings (theme, last view) survive restarts
* prints `JHX_READY <url>` once the server answers, so the window knows where to go
* exits as soon as the window goes away (its stdin closes), so no server is left running in the background

Run it by hand for debugging: `python desktop/backend/launcher.py` (Ctrl+C to stop).
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

APP_NAME = "JobHunterX"
PREFERRED_PORTS = range(47821, 47831)


def app_home() -> Path:
    """Where this user's settings and data live (the usual place for apps on each system)."""
    if os.environ.get("JOBHUNTERX_HOME"):
        return Path(os.environ["JOBHUNTERX_HOME"])
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_NAME


def pick_port() -> int:
    """The first free port of a small fixed range (same address every launch), else any free port."""
    for port in PREFERRED_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _exit_with_parent() -> None:
    """The window holds our stdin open; when it closes (window quit or crashed), stop."""
    try:
        while sys.stdin.read(1024):
            pass
    except (OSError, ValueError):
        pass
    os._exit(0)


def self_test() -> int:
    """`--self-test`: prove a build really works (CI runs this on every platform before publishing).
    Imports the heavy parts and renders a real PDF; prints one line per check."""
    import tempfile
    os.environ.setdefault("JOBHUNTERX_HOME", tempfile.mkdtemp(prefix="jhx-selftest-"))
    checks = []

    def check(name, fn):
        try:
            fn()
            checks.append((name, True, ""))
        except Exception as exc:                       # report every failure, not just the first
            checks.append((name, False, f"{type(exc).__name__}: {exc}"[:300]))

    def app():
        from fastapi.testclient import TestClient
        from jobhunterx.api.main import app as _app
        with TestClient(_app, base_url="http://127.0.0.1") as c:
            for path in ("/", "/api/settings", "/js/app.js"):
                r = c.get(path)
                assert r.status_code == 200, f"{path} → HTTP {r.status_code}"

    def pdf():
        from jobhunterx.generation import render
        content = {"header": {"name": "Test User", "email": "test@example.com", "phone": "", "location": "Hyderabad", "links": []},
                   "headline": "AI Engineer", "summary": "Builds LLM apps in Python.", "skills": [{"category": "AI", "items": ["Python"]}],
                   "experience": [], "projects": [], "education": [], "certifications": [], "achievements": [], "competitions": [],
                   "languages": [], "item_links": {}}
        data, pages = render.render_resume(content, "classic")
        assert data[:4] == b"%PDF" and pages >= 1

    def pdf_read():
        import fitz
        doc = fitz.open()
        doc.new_page()
        assert doc.page_count == 1

    check("app serves the UI and API", app)
    check("resume PDF", pdf)
    check("PDF reader", pdf_read)
    check("AI router", lambda: __import__("litellm"))
    check("browser agent", lambda: __import__("browser_use"))
    check("web search", lambda: __import__("ddgs"))
    check("page reader", lambda: __import__("trafilatura"))
    for name, ok, why in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f" — {why}" if why else ""), flush=True)
    return 0 if all(ok for _, ok, _ in checks) else 1


def main() -> None:
    if not getattr(sys, "frozen", False):   # run from the repo: use the project next to desktop/
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "jobhunterx"))
    home = app_home()
    (home / "data").mkdir(parents=True, exist_ok=True)
    port = pick_port()
    os.environ.update({
        "JOBHUNTERX_HOME": str(home),
        "DESKTOP": "true",
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "APP_ENV": "",                      # always the local single-user mode, whatever an old .env says
    })
    if getattr(sys, "frozen", False):
        os.chdir(home)                      # relative paths in third-party code land in the data folder, not the install
    if sys.stdin and not sys.stdin.isatty():
        threading.Thread(target=_exit_with_parent, name="parent-watch", daemon=True).start()

    import uvicorn
    from jobhunterx.api.main import app

    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=port, workers=1, log_level="warning",
        timeout_keep_alive=15, timeout_graceful_shutdown=5, ws_max_size=1 << 20,
    ))

    def announce() -> None:
        while not server.started:
            if server.should_exit:
                return
            time.sleep(0.05)
        print(f"JHX_READY http://127.0.0.1:{port}/", flush=True)

    threading.Thread(target=announce, name="announce", daemon=True).start()
    print(f"JHX_HOME {home}", flush=True)
    server.run()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()        # frozen builds: child processes must not start a second server
    if "--self-test" in sys.argv:
        if not getattr(sys, "frozen", False):
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "jobhunterx"))
        sys.exit(self_test())
    main()
