"""
JobHunterX — auto-apply browser agent (browser-use 0.13, CDP based).

* Runs on the dedicated browser worker loop (agents/browser_worker.py).
* The browser is headless and shown live inside the app (agents/live_view.py).
* Stop is immediate and keeps the browser; you can take over, continue or close.
* Steps are recorded in plain language and saved (apply_sessions table).
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



from jobhunterx.config.logging import get_logger
from jobhunterx.config import database as db
from jobhunterx.config.settings import get_settings, Settings
from jobhunterx.models import AgentEvent, HITLType

log = get_logger("browser_agent")

# Persistent profile path reused across runs. A stable profile accumulates
# cookies, localStorage and an auth "history" that Cloudflare scores as a
# real returning user rather than a fresh headless instance.
_STEALTH_USER_DATA_DIR = Path("./data/browser_profile")

# Where a real Google Chrome usually lives. A real Chrome (not Playwright's test Chromium) carries the
# codecs, brand list and GPU behaviour bot checks expect.
_CHROME_PATHS = {
    "win32": [r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe", r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
              r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe", r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
              r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"],
    "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
    "linux": ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/opt/google/chrome/chrome",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"],
}


def _real_chrome() -> Optional[str]:
    custom = os.getenv("BROWSER_EXECUTABLE_PATH")
    if custom and Path(custom).exists():
        return custom
    for p in _CHROME_PATHS.get(sys.platform if sys.platform in _CHROME_PATHS else "linux", []):
        p = os.path.expandvars(p)
        if Path(p).exists():
            return p
    return None


def _chrome_major(path: str) -> Optional[str]:
    """The browser's real major version, so the User-Agent never claims a different Chrome than the one running."""
    try:
        for d in Path(path).parent.iterdir():                 # Windows: Application\154.0.8037.98\
            if d.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", d.name):
                return d.name.split(".")[0]
        import subprocess
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"(\d+)\.\d+\.\d+", out or "")
        return m.group(1) if m else None
    except Exception:
        return None


def _user_agent(major: Optional[str]) -> Optional[str]:
    """Headless Chrome says "HeadlessChrome/…" — swap in the plain form for the SAME version (a mismatch with the
    browser's client hints is one of the first things Cloudflare checks)."""
    if not major:
        return None
    platform = {"win32": "Windows NT 10.0; Win64; x64", "darwin": "Macintosh; Intel Mac OS X 10_15_7"}.get(sys.platform, "X11; Linux x86_64")
    return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"


def _has_display() -> bool:
    return sys.platform in ("win32", "darwin") or bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


# ---------------------------------------------------------------------------
# HITL state detection heuristics
# ---------------------------------------------------------------------------

LOGIN_INDICATORS = [
    "sign in", "log in", "login", "email address", "password",
    "forgot password", "create account", "register",
]

CAPTCHA_INDICATORS = [
    "captcha", "recaptcha", "hcaptcha", "verify you are human",
    "i'm not a robot", "turnstile",
]

MFA_INDICATORS = [
    "verification code", "otp", "two-factor", "2fa",
    "authenticator", "verify your identity",
]


def _detect_page_type(page_text: str) -> str:
    """Detect if the page requires special handling.

    Returns: "simple_form", "login_required", "captcha_detected",
             "mfa_required", "complex_form", or "unknown".
    """
    text_lower = page_text.lower()

    for indicator in CAPTCHA_INDICATORS:
        if indicator in text_lower:
            return "captcha_detected"

    for indicator in MFA_INDICATORS:
        if indicator in text_lower:
            return "mfa_required"

    for indicator in LOGIN_INDICATORS:
        if indicator in text_lower:
            return "login_required"

    return "simple_form"


# ---------------------------------------------------------------------------
# Stealth browser profile builder (Cloudflare / bot-detection mitigation)
# ---------------------------------------------------------------------------

async def _build_stealth_profile(settings: Settings) -> Any:
    """Build a BrowserProfile that bot checks (Cloudflare, reCAPTCHA v3, hCaptcha) score as a normal person.

    What actually gets agents flagged, and what is done about each:
      * A browser that is not real Chrome (Playwright's test Chromium) → the installed Google Chrome / Edge is used.
      * A User-Agent that claims another version than the browser's client hints → the real version is used.
      * Headless mode → on a desktop the window is real but parked off-screen (the live view still streams it);
        headless only where there is no display at all (a server).
      * A fresh, cookie-less profile every time → one persistent profile keeps "challenge passed" cookies and logins.
      * A data-centre IP → the one thing no browser setting fixes. Point BROWSER_CDP_URL at your own Chrome (your home
        connection, your logins) or a hosted stealth browser when running on a server.

    Tiers: BROWSER_CDP_URL (any Chrome you started, or a hosted browser) → browser-use cloud → local real Chrome.
    """
    from browser_use import BrowserProfile

    cdp_url = (getattr(settings, "browser_cdp_url", "") or os.getenv("BROWSER_CDP_URL") or "").strip()
    if cdp_url:
        log.info("browser_profile_cdp", url=cdp_url.split("?")[0][:60])
        return BrowserProfile(cdp_url=cdp_url, keep_alive=True,
                              viewport=dict(zip(("width", "height"), live_view.viewport_size())))

    use_cloud = bool(os.getenv("BROWSER_USE_API_KEY")) and bool(getattr(settings, "browser_use_cloud", False))

    if use_cloud:
        log.info("browser_profile_cloud", reason="BROWSER_USE_API_KEY present + cloud enabled")
        return BrowserProfile(use_cloud=True, captcha_solver=True)

    # Local stealth profile
    resolved_dir = str(_STEALTH_USER_DATA_DIR.resolve())
    try:
        _STEALTH_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Kill any zombie Chrome processes still holding the user data dir
        _kill_zombie_chrome(resolved_dir)
        # Clean up stale lock files to prevent Chrome startup delay
        for lock_name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            lock_file = _STEALTH_USER_DATA_DIR / lock_name
            if lock_file.exists() or lock_file.is_symlink():
                try:
                    lock_file.unlink()
                except Exception:
                    pass
    except Exception:
        pass

    show = bool(getattr(settings, "browser_show_window", False))
    mode = (getattr(settings, "browser_window_mode", "auto") or "auto").lower()    # auto | offscreen | headless | window
    if show:
        mode = "window"
    elif mode == "auto":
        mode = "offscreen" if _has_display() else "headless"
    w, h = live_view.viewport_size()
    exe = _real_chrome()
    if exe:
        # Started by us, not by browser-use: browser-use copies a real Chrome's profile to a throw-away temp folder
        # (so cookies and logins would never stick) and forces its own window position.
        url = await _launch_chrome(exe, resolved_dir, mode, w, h)
        if url:
            return BrowserProfile(cdp_url=url, keep_alive=True, viewport={"width": w, "height": h})
    log.info("browser_profile_bundled", mode=mode)
    return BrowserProfile(
        headless=mode == "headless",
        user_data_dir=resolved_dir,
        viewport={"width": w, "height": h},   # same shape as the in-app panel
        enable_default_extensions=False,  # DISABLED: extension downloads from Chrome Web Store hang on Windows, blocking CDP
        disable_security=False,
        captcha_solver=False,  # DISABLED: cloud-only feature that adds startup overhead locally
        keep_alive=True,  # keep the browser after the agent stops: the user can take over, continue or close it
        args=["--disable-blink-features=AutomationControlled", "--disable-popup-blocking", "--no-first-run",
              "--no-default-browser-check"],
    )


_chrome_proc: Any = None          # the Chrome we started (one browser at a time)


async def _launch_chrome(exe: str, user_data_dir: str, mode: str, w: int, h: int) -> Optional[str]:
    """Start the installed Chrome with a debugging port and return its CDP address (None if it would not start)."""
    import socket
    import subprocess
    import httpx
    global _chrome_proc
    await _stop_own_chrome()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    major = _chrome_major(exe)
    args = [exe, f"--remote-debugging-port={port}", f"--user-data-dir={user_data_dir}",
            "--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled",
            "--disable-popup-blocking", "--hide-crash-restore-bubble", "--disable-session-crashed-bubble",
            # keep rendering while nobody looks at the window, so the live view never freezes
            "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
            "--disable-features=CalculateNativeWinOcclusion,Translate,MediaRouter,OptimizationHints",
            f"--lang={os.getenv('BROWSER_LANG', 'en-IN')}"]
    if mode == "headless":
        args += ["--headless=new", f"--window-size={w},{h}"]
        ua = _user_agent(major)
        if ua:
            args.append(f"--user-agent={ua}")
        if sys.platform.startswith("linux"):
            args += ["--disable-dev-shm-usage", *(["--no-sandbox"] if hasattr(os, "geteuid") and os.geteuid() == 0 else [])]
    else:
        args.append(f"--window-size={w + 16},{h + 140}")
        if mode == "offscreen":
            # a real, GPU-rendered window parked where nobody sees it — the live view streams it into the app
            args.append("--window-position=-2400,-2400")
    args.append("about:blank")
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        _chrome_proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    except OSError as exc:
        log.warning("chrome_launch_failed", error=str(exc)[:160])
        return None
    base = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient(timeout=2) as client:
        for _ in range(60):
            if _chrome_proc.poll() is not None:
                break
            try:
                r = await client.get(base + "/json/version")
                if r.status_code == 200:
                    log.info("chrome_started", mode=mode, version=major, port=port)
                    return base
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
    log.warning("chrome_no_debug_port", exited=_chrome_proc.poll() is not None)
    await _stop_own_chrome()
    return None


async def _stop_own_chrome() -> None:
    global _chrome_proc
    proc, _chrome_proc = _chrome_proc, None
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    for _ in range(20):
        if proc.poll() is not None:
            return
        await asyncio.sleep(0.1)
    proc.kill()


def _kill_zombie_chrome(user_data_dir: str) -> None:
    """Kill any Chrome processes still holding the given user_data_dir.

    On Windows, Chrome locks the user data dir while running. If a previous
    browser-use session crashed or wasn't cleaned up, the zombie Chrome
    blocks the new launch from binding to the profile, causing a 60s CDP
    timeout.
    """
    try:
        import psutil
        normalized = os.path.normcase(os.path.normpath(user_data_dir))
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() in ("chrome.exe", "chromium.exe"):
                    cmdline = proc.info.get("cmdline") or []
                    for arg in cmdline:
                        if arg.startswith("--user-data-dir="):
                            proc_dir = os.path.normcase(os.path.normpath(arg.split("=", 1)[1]))
                            if proc_dir == normalized:
                                log.info("killing_zombie_chrome", pid=proc.pid)
                                proc.kill()
                                break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as exc:
        log.warning("zombie_chrome_cleanup_error", error=str(exc))


# ---------------------------------------------------------------------------
# Auto-apply sessions
# ---------------------------------------------------------------------------
# One session per job. The browser lives on the browser worker loop
# (agents/browser_worker.py) and is shown inside the app through a CDP
# screencast (agents/live_view.py). After the agent finishes, stops or needs
# help, the browser stays open so the user can take over, continue or close it.

import json
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.agents import browser_worker, live_view

ACTIVE = {"preparing", "launching", "running", "paused", "stopping"}

_sessions: dict[str, "ApplySession"] = {}
_current: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApplySession:
    """State of one application attempt; every change is pushed to the UI and saved."""

    def __init__(self, job: dict):
        self.job = job
        self.agent: Any = None
        self.browser_session: Any = None
        self.screencast: Optional[live_view.Screencast] = None
        self.task: Optional[asyncio.Task] = None
        self.files: dict[str, str] = {}
        self.profile: dict = {}
        self.data: dict[str, Any] = {
            "job_id": job["id"], "company": job.get("company", ""), "role": job.get("role", ""),
            "apply_url": job.get("apply_url", ""), "person_id": job.get("person_id"),
            "status": "preparing", "message": "Getting your application kit ready…", "control": "agent",
            "started_at": _now(), "updated_at": _now(), "url": "", "title": "", "live": False,
            "kit": {}, "steps": [], "notice": "", "result": "", "runs": 0,
        }

    def snapshot(self) -> dict:
        snap = dict(self.data)
        snap["steps"] = self.data["steps"][-80:]
        return snap

    def update(self, **changes: Any) -> None:
        self.data.update(changes)
        self.data["updated_at"] = _now()
        self.publish()

    def publish(self) -> None:
        snap = self.snapshot()
        live_view.broadcast_event({"type": "apply.session", "job_id": snap["job_id"], "data": {"session": snap}})
        from jobhunterx import storage
        live_view._on_main(storage.save_apply_session(snap))


def get_session(job_id: str) -> Optional[ApplySession]:
    return _sessions.get(job_id)


def current_session() -> Optional[ApplySession]:
    return _sessions.get(_current) if _current else None


def _alive(sess: ApplySession) -> bool:
    bs = sess.browser_session
    return bool(bs is not None and getattr(bs, "_cdp_client_root", None) is not None)


# ---------------------------------------------------------------------------- readable steps

def _host(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def _label(state: Any, index: Any) -> str:
    """Human name for an element index from the page the model looked at."""
    try:
        node = state.dom_state.selector_map.get(int(index))
    except Exception:
        node = None
    if node is None:
        return f"element #{index}"
    try:
        ax = getattr(node, "ax_node", None)
        if ax is not None and getattr(ax, "name", None):
            return str(ax.name).strip()[:48]
        attrs = getattr(node, "attributes", {}) or {}
        for k in ("aria-label", "placeholder", "title", "name", "value", "alt"):
            if attrs.get(k):
                return str(attrs[k]).strip()[:48]
        text = node.get_all_children_text(max_depth=2).strip()
        if text:
            return text[:48]
    except Exception:
        pass
    return f"element #{index}"


def describe_action(name: str, params: dict, state: Any) -> str:
    p = params or {}
    idx = p.get("index")
    lbl = _label(state, idx) if idx is not None else ""
    if name == "navigate":
        return f"Open {_host(str(p.get('url', '')))}"
    if name == "click":
        return f"Click “{lbl}”" if idx is not None else "Click on the page"
    if name == "input":
        text = str(p.get("text", ""))
        shown = "••••" if any(w in lbl.lower() for w in ("password", "otp", "code")) else (text if len(text) <= 40 else text[:37] + "…")
        return f"Type “{shown}” into {lbl}"
    if name == "upload_file":
        return f"Upload {Path(str(p.get('path', 'file'))).name}"
    if name == "select_dropdown":
        return f"Choose “{p.get('text', '')}” in {lbl}"
    if name == "dropdown_options":
        return f"Look at the options in {lbl}"
    if name == "set_checkbox_by_text":
        return f"{'Tick' if p.get('checked', True) else 'Untick'} “{str(p.get('text', ''))[:40]}”"
    if name == "set_checkbox":
        return f"{'Tick' if p.get('checked', True) else 'Untick'} “{lbl}”"
    if name == "scroll":
        return "Scroll down" if p.get("down", True) else "Scroll up"
    if name == "send_keys":
        return f"Press {p.get('keys', '')}"
    if name == "wait":
        return f"Wait {p.get('seconds', 3)}s for the page"
    if name in ("extract", "search_page", "find_text", "find_elements"):
        return "Read the page"
    if name == "go_back":
        return "Go back"
    if name == "switch":
        return "Switch tab"
    if name == "done":
        txt = str(p.get("text", "")).strip()
        head = txt.split(":", 1)[0].split()[0].upper() if txt else ""
        if head == "SUCCESS":
            return "Finish — application submitted"
        if _verdict(head):
            return "Finish — needs your help (" + head.replace("_", " ").lower() + ")"
        return f"Finish — {txt[:90]}" if txt else "Finish"
    if name == "wait_for_human_check":
        return "Wait for the security check to clear"
    if name == "prefill_basic_fields":
        return "Fill name, email and profile links"
    if name == "get_email_otp":
        return "Read the verification code from email"
    return name.replace("_", " ").capitalize()


def _actions_of(model_output: Any, state: Any) -> list[str]:
    out = []
    for act in (getattr(model_output, "action", None) or []):
        try:
            dumped = act.model_dump(exclude_unset=True)
        except Exception:
            continue
        for name, params in dumped.items():
            if params is None:
                continue
            out.append(describe_action(name, params if isinstance(params, dict) else {}, state))
    return out


# ---------------------------------------------------------------------------- building blocks

def _build_llms() -> tuple[Any, Any]:
    from browser_use.llm.google.chat import ChatGoogle
    try:
        from browser_use.llm.groq.chat import ChatGroq
    except ImportError:
        ChatGroq = None
    try:
        from browser_use.llm.mistral.chat import ChatMistral
    except ImportError:
        ChatMistral = None
    from jobhunterx.config import app_state as _app_state
    s = get_settings()
    google_key = (s.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) if _app_state.llm_provider_enabled("google") else None
    groq_key = (s.groq_api_key or os.getenv("GROQ_API_KEY")) if _app_state.llm_provider_enabled("groq") else None
    mistral_key = (s.mistral_api_key or os.getenv("MISTRAL_API_KEY")) if _app_state.llm_provider_enabled("mistral") else None
    candidates: list[Any] = []
    if google_key:
        candidates.append(ChatGoogle(model="gemini-3.5-flash-lite", api_key=google_key, temperature=0.2, max_retries=6,
                                     retry_base_delay=4.0, retry_max_delay=40.0, retryable_status_codes=[429, 500, 502, 503, 504]))
    if groq_key and ChatGroq is not None:
        candidates.append(ChatGroq(model="openai/gpt-oss-120b", api_key=groq_key, temperature=0.2, max_retries=6))
    if mistral_key and ChatMistral is not None:
        candidates.append(ChatMistral(model="mistral-small-latest", api_key=mistral_key, temperature=0.2, max_retries=6))
    if google_key and len(candidates) < 2:
        # last resort only: free Gemma is slow and often overloaded, so don't sit in long retry loops on it
        candidates.append(ChatGoogle(model="gemma-4-31b-it", api_key=google_key, temperature=0.2, max_retries=1,
                                     retry_base_delay=2.0, retry_max_delay=5.0))
    if not candidates:
        raise RuntimeError("No AI provider is available for the browser agent. Add a key or turn a provider on in Settings.")
    return candidates[0], (candidates[1] if len(candidates) > 1 else None)


# Runs on the element the agent picked: finds the real checkbox (native input, its <label>, or an ARIA
# role=checkbox/switch), reports its state, and — when asked to — tries label/box clicks then React-safe events.
_CHECKBOX_JS = """function(want, act) {
  const isBox = (e) => e && e.tagName === 'INPUT' && (e.type === 'checkbox' || e.type === 'radio');
  const el = this;
  let box = isBox(el) ? el : (el.querySelector && el.querySelector('input[type=checkbox],input[type=radio]'));
  if (!box && el.tagName === 'LABEL' && el.control) box = el.control;
  if (!box && el.closest) { const lab = el.closest('label'); if (lab && isBox(lab.control)) box = lab.control; }
  if (!box && el.id) { const lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (lab && isBox(lab.control)) box = lab.control; }
  const sel = '[role=checkbox],[role=radio],[role=switch],[aria-checked]';
  const aria = box ? null : ((el.matches && el.matches(sel)) ? el : (el.closest && el.closest(sel)) || (el.querySelector && el.querySelector(sel)));
  const state = () => box ? box.checked : aria ? aria.getAttribute('aria-checked') === 'true' : null;
  if (!act || state() === want || state() === null) return { state: state(), found: !!(box || aria) };
  const targets = [];
  if (box) { if (box.labels) targets.push(...box.labels); targets.push(box); }
  if (aria) targets.push(aria);
  for (const t of targets) {
    try { t.scrollIntoView({ block: 'center' }); t.click(); } catch (e) {}
    if (state() === want) return { state: want, found: true, via: t.tagName.toLowerCase() };
  }
  if (box) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked').set;
    setter.call(box, want);
    for (const ev of ['input', 'change']) box.dispatchEvent(new Event(ev, { bubbles: true }));
  }
  return { state: state(), found: true, via: 'events' };
}"""


async def _checkbox_js(browser_session: Any, node: Any, want: bool, act: bool) -> dict:
    cdp = await browser_session.cdp_client_for_node(node)
    res = await cdp.cdp_client.send.DOM.resolveNode(params={"backendNodeId": node.backend_node_id}, session_id=cdp.session_id)
    obj = (res.get("object") or {}).get("objectId")
    if not obj:
        return {"found": False, "state": None}
    out = await cdp.cdp_client.send.Runtime.callFunctionOn(
        params={"objectId": obj, "functionDeclaration": _CHECKBOX_JS, "returnByValue": True,
                "arguments": [{"value": bool(want)}, {"value": bool(act)}]}, session_id=cdp.session_id)
    return (out.get("result") or {}).get("value") or {"found": False, "state": None}


async def _set_checkbox(browser_session: Any, index: int, checked: bool) -> Any:
    """Real mouse click first (what custom widgets expect), verified; then label / React-safe fallbacks."""
    from browser_use import ActionResult
    from browser_use.browser.events import ClickElementEvent
    try:
        node = await browser_session.get_element_by_index(index)
        if node is None:
            return ActionResult(error=f"Element {index} is not on the page any more — refresh the page state and try again.")
        before = await _checkbox_js(browser_session, node, checked, act=False)
        if not before.get("found"):
            return ActionResult(error=f"Element {index} is not a checkbox, toggle or switch. Pick the box itself or its label.")
        word = "ticked" if checked else "unticked"
        if before.get("state") == checked:
            return ActionResult(extracted_content=f"Checkbox {index} was already {word}.")
        ev = browser_session.event_bus.dispatch(ClickElementEvent(node=node))
        await ev
        try:
            await ev.event_result(raise_if_any=False, raise_if_none=False)
        except Exception:
            pass
        mid = await _checkbox_js(browser_session, node, checked, act=False)
        if mid.get("state") != checked:
            mid = await _checkbox_js(browser_session, node, checked, act=True)
        if mid.get("state") == checked:
            return ActionResult(extracted_content=f"Checkbox {index} is now {word}.")
        return ActionResult(error=f"Could not change checkbox {index} — click the visible text next to it once instead.")
    except Exception as exc:
        return ActionResult(error=f"Checkbox {index}: {str(exc)[:160]}")


# Finds a checkbox / radio / switch by the words next to it — including the hidden <input> behind a custom-styled box,
# which never shows up in the agent's element list — in the page and its same-origin iframes, then sets and verifies it.
_CHECKBOX_BY_TEXT_JS = """(text, want) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const t = norm(text);
  if (!t) return { found: false };
  const docs = [document];
  for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch (e) {} }
  const cands = [];
  for (const d of docs) {
    for (const box of d.querySelectorAll('input[type=checkbox],input[type=radio]')) {
      const texts = [...(box.labels || [])].map((l) => norm(l.innerText || l.textContent));
      texts.push(norm(box.getAttribute('aria-label')), norm(box.value));
      const wrap = box.closest('label,li,p,div');
      if (wrap) texts.push(norm(wrap.innerText || wrap.textContent));
      const hits = texts.filter((x) => x && x.includes(t));
      if (hits.length) cands.push({ kind: 'box', el: box, exact: texts.includes(t), len: Math.min(...hits.map((x) => x.length)) });
    }
    for (const el of d.querySelectorAll('[role=checkbox],[role=radio],[role=switch]')) {
      const lb = el.getAttribute('aria-labelledby');
      const s = norm((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (lb && d.getElementById(lb) ? d.getElementById(lb).innerText : ''));
      if (s.includes(t)) cands.push({ kind: 'aria', el, exact: s === t, len: s.length });
    }
  }
  if (!cands.length) return { found: false };
  cands.sort((a, b) => (b.exact - a.exact) || (a.len - b.len));
  const c = cands[0], el = c.el;
  const state = () => c.kind === 'box' ? el.checked : el.getAttribute('aria-checked') === 'true';
  const label = (c.kind === 'box' && el.labels && el.labels[0] ? el.labels[0].innerText : el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 80);
  if (state() === want) return { found: true, state: want, already: true, label, matches: cands.length };
  const targets = c.kind === 'box' ? [...(el.labels || []), el] : [el];
  for (const x of targets) {
    try { x.scrollIntoView({ block: 'center' }); x.click(); } catch (e) {}
    if (state() === want) return { found: true, state: want, label, matches: cands.length };
  }
  if (c.kind === 'box') {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked').set;
    setter.call(el, want);
    for (const ev of ['input', 'change']) el.dispatchEvent(new Event(ev, { bubbles: true }));
  }
  return { found: true, state: state(), label, matches: cands.length };
}"""


async def _set_checkbox_by_text(browser_session: Any, text: str, checked: bool) -> Any:
    import json as _json
    from browser_use import ActionResult
    try:
        cdp = await browser_session.get_or_create_cdp_session()
        out = await cdp.cdp_client.send.Runtime.evaluate(
            params={"expression": f"({_CHECKBOX_BY_TEXT_JS})({_json.dumps(text)}, {_json.dumps(bool(checked))})",
                    "returnByValue": True}, session_id=cdp.session_id)
        r = (out.get("result") or {}).get("value") or {}
    except Exception as exc:
        return ActionResult(error=f"Checkbox “{text}”: {str(exc)[:160]}")
    word = "ticked" if checked else "unticked"
    if not r.get("found"):
        return ActionResult(error=f"No checkbox next to the words “{text}” — use a shorter exact phrase from the label. "
                                  "If the form sits inside an embedded frame, open the form's own page first.")
    name = r.get("label") or text
    if r.get("state") == checked:
        return ActionResult(extracted_content=f"Checkbox “{name}” is {'already ' if r.get('already') else 'now '}{word}.")
    return ActionResult(error=f"Found “{name}” but could not change it — click its visible text once instead.")


# What kind of human check is on the page right now. The small "protected by reCAPTCHA" badge (invisible v3 scoring)
# is NOT a challenge: it needs nothing from anyone and must never stop the agent.
_CHALLENGE_JS = """(() => {
  const vis = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return (r.width > 20 && r.height > 20 && s.visibility !== 'hidden' && s.display !== 'none') ? r : null; };
  const box = (r) => r && { x: r.left, y: r.top, w: r.width, h: r.height };
  const t = (document.title || '').toLowerCase();
  const interstitial = /just a moment|attention required|checking your browser|verify you are human/.test(t)
    || !!document.querySelector('#challenge-form, #challenge-stage, #cf-challenge-running');
  let widget = null, kind = '';
  for (const [k, sel] of [['turnstile', 'iframe[src*="challenges.cloudflare.com"], .cf-turnstile, #cf-turnstile, [data-sitekey][class*=turnstile]'],
                          ['hcaptcha', 'iframe[src*="hcaptcha.com"][src*="checkbox"], iframe[title*="hCaptcha" i]:not([title*="challenge" i])'],
                          ['recaptcha', 'iframe[src*="recaptcha/api2/anchor"]:not(.grecaptcha-badge iframe), iframe[src*="recaptcha/enterprise/anchor"]:not(.grecaptcha-badge iframe)']]) {
    for (const el of document.querySelectorAll(sel)) {
      if (el.closest('.grecaptcha-badge')) continue;
      const r = vis(el); if (r) { widget = box(r); kind = k; break; }
    }
    if (widget) break;
  }
  const puzzle = [...document.querySelectorAll('iframe[src*="recaptcha/api2/bframe"], iframe[src*="hcaptcha.com"][src*="challenge"]')].some((e) => { const r = vis(e); return r && r.height > 150; });
  return { interstitial, kind, widget, puzzle };
})()"""


async def _wait_for_human_check(browser_session: Any, max_seconds: int = 25) -> Any:
    """Most checks clear by themselves in a real browser; a Turnstile / 'I'm not a robot' box usually passes with one
    real mouse click. Image puzzles are left to the person."""
    from browser_use import ActionResult
    cdp = await browser_session.get_or_create_cdp_session()

    async def state() -> dict:
        out = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": _CHALLENGE_JS, "returnByValue": True},
                                                         session_id=cdp.session_id)
        return (out.get("result") or {}).get("value") or {}

    async def click(x: float, y: float) -> None:
        import random
        for typ, extra in (("mouseMoved", {}), ("mousePressed", {"button": "left", "clickCount": 1}),
                           ("mouseReleased", {"button": "left", "clickCount": 1})):
            await cdp.cdp_client.send.Input.dispatchMouseEvent(params={"type": typ, "x": x, "y": y, **extra}, session_id=cdp.session_id)
            await asyncio.sleep(random.uniform(0.06, 0.18))

    clicked = 0
    deadline = time.monotonic() + max(5, min(int(max_seconds or 25), 45))
    first = None
    while time.monotonic() < deadline:
        try:
            s = await state()
        except Exception as exc:                       # the page is navigating (often: the check just passed)
            log.debug("challenge_state_failed", error=str(exc)[:80])
            await asyncio.sleep(1.5)
            continue
        first = first or s
        if not s.get("interstitial") and not s.get("widget") and not s.get("puzzle"):
            return ActionResult(extracted_content="No human check is blocking the page (any check that was there has passed). Carry on.")
        if s.get("puzzle"):
            return ActionResult(error="An image puzzle CAPTCHA is showing. Stop and report CAPTCHA_DETECTED.")
        w = s.get("widget")
        if w and clicked < 2:
            await asyncio.sleep(1.2 + clicked)          # widgets need a moment to become clickable
            import random
            await click(w["x"] + min(30, w["w"] / 2) + random.uniform(-3, 3), w["y"] + w["h"] / 2 + random.uniform(-3, 3))
            clicked += 1
            await asyncio.sleep(3)
            continue
        await asyncio.sleep(1.5)
    kind = (first or {}).get("kind") or "security"
    return ActionResult(error=f"The {kind} check did not clear after waiting{' and clicking it' if clicked else ''}. "
                              "Stop and report CAPTCHA_DETECTED.")


# Fills the plain identity fields (name, email, profile links) by their HTML meaning — autocomplete / name / label —
# so the model spends its steps on the real questions. Only empty, visible, editable fields are touched.
_PREFILL_JS = """(p) => {
  const docs = [document];
  for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch (e) {} }
  const rules = [
    ['first', (a, t) => a === 'given-name' || /(^|[^a-z])(first|given|f)[\\s_-]*name|fname|first$/.test(t)],
    ['last', (a, t) => a === 'family-name' || /(last|family|sur)[\\s_-]*name|lname|surname|last$/.test(t)],
    ['email', (a, t, el) => a === 'email' || el.type === 'email' || /e-?mail/.test(t)],
    ['linkedin', (a, t) => /linked\\s*in/.test(t)],
    ['github', (a, t) => /git\\s*hub/.test(t)],
    ['website', (a, t) => a === 'url' || /portfolio|personal (web)?site|^website|website$|personal url/.test(t)],
    ['name', (a, t) => a === 'name' || /^(full[\\s_-]*)?name\\*?$|^your name|legal name|full[\\s_-]*name/.test(t)],
  ];
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  const filled = [];
  for (const d of docs) {
    for (const el of d.querySelectorAll('input')) {
      if (!['text', 'email', 'url', ''].includes(el.type) || el.disabled || el.readOnly || el.value) continue;
      const r = el.getBoundingClientRect(); if (r.width < 5 || r.height < 5) continue;
      const lab = [...(el.labels || [])].map((l) => l.innerText).join(' ');
      const t = [el.name, el.id, el.getAttribute('aria-label'), el.placeholder, lab].join(' ').replace(/\\s+/g, ' ').trim().toLowerCase();
      if (!t || /company|employer|school|college|university|reference|referr|manager|emergency|hiring|recruiter|city|country/.test(t)) continue;
      const a = (el.getAttribute('autocomplete') || '').toLowerCase();
      const hit = rules.find(([k, f]) => p[k] && f(a, t, el));
      if (!hit) continue;
      el.focus(); setter.call(el, p[hit[0]]);
      for (const ev of ['input', 'change']) el.dispatchEvent(new Event(ev, { bubbles: true }));
      el.blur();
      filled.push((lab || el.placeholder || el.name || hit[0]).trim().slice(0, 40));
    }
  }
  return filled;
}"""


async def _prefill(browser_session: Any, profile: dict) -> Any:
    import json as _json
    from browser_use import ActionResult
    name = (profile.get("name") or "").strip()
    parts = name.split()
    vals = {"name": name, "first": parts[0] if parts else "", "last": " ".join(parts[1:]) if len(parts) > 1 else "",
            "email": profile.get("email") or "", "linkedin": profile.get("linkedin") or "", "github": profile.get("github") or "",
            "website": profile.get("portfolio") or ""}
    try:
        cdp = await browser_session.get_or_create_cdp_session()
        filled = []
        for _ in range(8):                               # single-page forms render a moment after load
            out = await cdp.cdp_client.send.Runtime.evaluate(
                params={"expression": f"({_PREFILL_JS})({_json.dumps(vals)})", "returnByValue": True}, session_id=cdp.session_id)
            filled = (out.get("result") or {}).get("value") or []
            if filled:
                break
            await asyncio.sleep(0.75)
    except Exception as exc:
        return ActionResult(extracted_content=f"Pre-fill skipped ({str(exc)[:80]}). Fill the form normally.")
    if not filled:
        return ActionResult(extracted_content="No basic fields to pre-fill here (maybe an Apply button must be clicked first).")
    return ActionResult(extracted_content="Pre-filled: " + ", ".join(filled) + ". Check them once; do not retype them.")


def _build_tools(profile: Optional[dict] = None) -> Any:
    from browser_use import ActionResult, Controller
    controller = Controller()

    @controller.action("Wait for a security check (Cloudflare 'Just a moment', Turnstile, 'I'm not a robot' box) to clear; "
                       "clicks the checkbox once if there is one. Use this BEFORE reporting CAPTCHA_DETECTED.")
    async def wait_for_human_check(browser_session, max_seconds: int = 25) -> ActionResult:
        return await _wait_for_human_check(browser_session, max_seconds)

    @controller.action("Fill the basic identity fields of the application form (name, email, LinkedIn, GitHub, website) "
                       "in one go. Use it once when a form first appears, then fill the remaining fields.")
    async def prefill_basic_fields(browser_session) -> ActionResult:
        return await _prefill(browser_session, profile or {})

    @controller.action("Tick or untick a checkbox / toggle / switch by its index, and verify it changed. "
                       "Use this instead of click for every checkbox.")
    async def set_checkbox(index: int, checked: bool, browser_session) -> ActionResult:
        return await _set_checkbox(browser_session, index, checked)

    @controller.action("Tick or untick a checkbox / radio / toggle by the words written next to it, e.g. "
                       "text='I agree to the privacy policy'. Use this when the box is not in the element list "
                       "(custom-styled boxes are often hidden) or set_checkbox could not find it.")
    async def set_checkbox_by_text(text: str, checked: bool, browser_session) -> ActionResult:
        return await _set_checkbox_by_text(browser_session, text, checked)

    @controller.action("Read verification code from email and return it")
    async def get_email_otp(email_address: str, sender_filter: str = "", timeout_seconds: int = 30) -> ActionResult:
        """Retrieve an OTP/verification code from the candidate's email inbox.

        Uses IMAP to poll for new emails matching the sender filter,
        extracts the 4-8 digit code, and returns it.

        Args:
            email_address: The email address to check
            sender_filter: Optional sender email/domain to filter by
            timeout_seconds: How long to wait for the OTP email
        """
        import email
        import imaplib
        import re
        import time as _time

        try:
            settings = get_settings()
            imap_host = "imap.gmail.com"
            email_pass = getattr(settings, "email_app_password", None)

            if not email_pass:
                return ActionResult(error="Email app password not configured. Set EMAIL_APP_PASSWORD in .env")

            otp_pattern = re.compile(r'(?<!\d)(\d{4,8})(?!\d)')
            deadline = _time.time() + timeout_seconds

            while _time.time() < deadline:
                try:
                    with imaplib.IMAP4_SSL(imap_host) as conn:
                        conn.login(email_address, email_pass)
                        conn.select("INBOX")

                        criteria = ['UNSEEN']
                        if sender_filter:
                            criteria.append(f'FROM "{sender_filter}"')
                        search_str = '(' + ' '.join(criteria) + ')'
                        _, msg_ids = conn.search(None, search_str)

                        if msg_ids[0]:
                            latest_id = msg_ids[0].split()[-1]
                            _, data = conn.fetch(latest_id, '(RFC822)')
                            msg = email.message_from_bytes(data[0][1])

                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            body = payload.decode(errors="ignore")
                                        break
                            else:
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="ignore")

                            match = otp_pattern.search(body)
                            if match:
                                return ActionResult(extracted_content=f"OTP_CODE:{match.group(1)}")
                except Exception:
                    pass
                _time.sleep(2)

            return ActionResult(error=f"OTP not received within {timeout_seconds}s")
        except Exception as exc:
            return ActionResult(error=f"Email OTP error: {str(exc)}")


    return controller


# Calling codes for the countries candidates here usually live in; others fall back to the number as written.
_CALLING_CODES = {"india": "+91", "united states": "+1", "usa": "+1", "canada": "+1", "united kingdom": "+44", "uk": "+44",
                  "singapore": "+65", "united arab emirates": "+971", "uae": "+971", "germany": "+49", "australia": "+61"}


def prefs_country(profile: dict) -> str:
    return ((profile.get("preferences") or {}).get("home_country") or "").strip()


def split_phone(phone: str, country: str = "") -> tuple[str, str]:
    """'+91 80747 49058' → ('+91', '8074749058'); '08074749058' with India → ('+91', '8074749058')."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return "", ""
    if raw.startswith("+") or raw.startswith("00"):
        if raw.startswith("00"):
            digits = digits[2:]
        for code in sorted({c.lstrip("+") for c in _CALLING_CODES.values()}, key=len, reverse=True):
            if digits.startswith(code) and 7 <= len(digits) - len(code) <= 12:
                return "+" + code, digits[len(code):]
        m = re.match(r"\+?\s*(\d{1,3})[\s\-()]+(.+)", raw.lstrip("0"))
        return ("+" + m.group(1), re.sub(r"\D", "", m.group(2))) if m else ("", digits)
    code = _CALLING_CODES.get(country.lower(), "")
    if code == "+91":
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        digits = digits.lstrip("0") if len(digits) == 11 else digits
    return code, digits


def _profile_block(profile: dict) -> str:
    edu = "\n".join(
        f"  • {ed.get('degree', '')} ({ed.get('start', '')} – {ed.get('end', '')})"
        + f"\n    - College / school attended: {ed.get('institution') or '(not given)'}"
        + f"\n    - Affiliated / degree-awarding university: {ed.get('university') or '(not given — same as the college, or not stated)'}"
        + (f"\n    - Grade: {ed.get('grade')}" if ed.get("grade") else "")
        for ed in profile.get("education", [])) or "  (Not provided)"
    code, national = split_phone(profile.get("phone", ""), prefs_country(profile))
    exp = "\n".join(
        f"  • {e.get('role', '')} at {e.get('company', '')} ({e.get('start', '')} – {e.get('end') or 'Present'})"
        + "".join(f"\n    - {b}" for b in (e.get("bullets") or [])[:3])
        for e in profile.get("experience", [])) or "  (Not provided)"
    qa = profile.get("qa_memory", {}) or {}
    labels = {"current_ctc": "Current CTC", "expected_ctc": "Expected CTC", "expected_salary": "Expected salary",
              "notice_period": "Notice period", "work_authorization": "Work authorization",
              "requires_sponsorship": "Requires visa sponsorship", "preferred_work_mode": "Preferred work mode",
              "willing_to_relocate": "Willing to relocate", "years_of_experience": "Years of experience"}
    qa_lines = [f"  • {lbl}: {qa[k]}" for k, lbl in labels.items() if qa.get(k)]
    qa_lines += [f"  • {k}: {v}" for k, v in (qa.get("custom_answers") or {}).items()]
    prefs = profile.get("preferences", {}) or {}
    if prefs.get("notice_period_days") is not None and not qa.get("notice_period"):
        qa_lines.append(f"  • Notice period: {prefs['notice_period_days']} days")
    langs = profile.get("languages", [])
    other = [f"{l.get('label') or 'Link'}: {l.get('url')}" for l in profile.get("links") or [] if l.get("url")]
    proj_links = []
    for pr in profile.get("projects") or []:
        urls = [f"{l.get('label') or 'link'} {l.get('url')}" for l in pr.get("links") or [] if l.get("url")] or ([pr["url"]] if pr.get("url") else [])
        if urls:
            proj_links.append(f"  • {pr.get('title', '')}: " + ", ".join(urls))
    links_block = ("\n- Other links: " + "; ".join(other) if other else "") + \
        ("\n- Project links (use for 'portfolio / work samples / website' questions):\n" + "\n".join(proj_links[:6]) if proj_links else "")
    return f"""=== CANDIDATE ===
- Full name: {profile.get('name', '')}
- Email: {profile.get('email', '')}
- Phone (full, international): {(code + ' ' + national).strip() if national else profile.get('phone', '')}
- Phone country code: {code or '(unknown)'}
- Phone number WITHOUT country code: {national or profile.get('phone', '')}
- Current location: {profile.get('location', '')}
- Home country: {prefs.get('home_country', '')}
- Languages: {', '.join(langs) if isinstance(langs, list) else langs}
- LinkedIn: {profile.get('linkedin', '')}
- GitHub: {profile.get('github', '')}
- Portfolio: {profile.get('portfolio', '')}{links_block}
- Summary: {profile.get('summary', '')}

=== SKILLS ===
{', '.join((profile.get('skills') or [])[:30])}

=== EDUCATION ===
{edu}

=== EXPERIENCE ===
{exp}

=== Q&A ANSWERS (salary, notice period, authorization…) ===
{chr(10).join(qa_lines) or '  (none)'}"""


def _files_block(files: dict[str, str]) -> str:
    names = {"resume": "RESUME (one page, tailored to this job)", "cover_letter": "COVER LETTER", "cv": "CV (full career, multi-page)"}
    lines = [f"- {names[k]}: {v}" for k, v in files.items() if v and k in names]
    return "=== FILES YOU CAN UPLOAD (exact paths) ===\n" + ("\n".join(lines) if lines else "- (none)")


RULES = """CRITICAL TOKEN SAVING & SPEED RULE:
Keep your thinking extremely brief and short (1 concise sentence max). Do NOT write long explanations or reasoning. Execute actions directly to minimize token usage and complete the task fast!

=== FORM FILLING RULES ===

BASIC RULES:
1. Fill in all required fields with the candidate information above. Name, email and profile links may already be
   pre-filled (see the pre-fill result) — check them, don't retype them. On a new form page, `prefill_basic_fields` does them in one go.
2. Use the Q&A answers for dropdown/select/radio/input questions about salary, CTC, notice period, work authorization, etc.
3. Do NOT fill in Current CTC or Expected CTC unless the application form explicitly asks.
4. If a generic "salary" is asked, prioritize expected salary / expected CTC.
5. For education and work experience fields, use the detailed history provided above (see EDUCATION and PHONE rules below).
6. Upload files with the `upload_file` action (give the file input's index and the exact path):
   - Resume / CV / "Resume/CV" upload → the RESUME file below (one page, tailored to this job).
   - Cover letter upload → the COVER LETTER file. If there is a cover letter text box instead, paste a short version of it.
   - Only if the form has a SEPARATE field that explicitly asks for a full / detailed CV in addition to the resume → the CV file.
7. After filling, click the Submit/Apply button.
8. Report the final status: SUCCESS or the reason for stopping.

DROPDOWN / SELECT FIELD RULES:
- For native <select> elements: Use the built-in `dropdown_options` action to see available options, then `select_dropdown` to pick the best match.
- For custom dropdowns (React Select, Material UI, etc.): Click the dropdown to open it, then click the matching option text.
- For combobox/autocomplete fields: Type the value slowly (50ms delay per character), wait 500ms for suggestions to appear, then click the matching suggestion.
- ALWAYS use the `dropdown_options` action first to see what options are available before trying to select.
- If an option says "Other" and the form has a text field next to it, select "Other" and type the specific value.
- For "Years of Experience" dropdowns, pick the option that matches the candidate's total experience.
- For "Salary" / "Expected CTC" dropdowns, use the Q&A answers provided above.

DATE / CALENDAR FIELD RULES:
- For <input type="date"> fields: Type the date directly in MM/DD/YYYY or YYYY-MM-DD format (check the placeholder for the expected format).
- For datepicker calendar widgets: Click the input to open the calendar, then navigate to the correct month/year and click the day.
- For education dates: Use the start/end dates from the education history above.
- For work experience dates: Use the start/end dates from the work experience above.
- If a date field has a calendar popup, try clicking the input first, then type the date directly — most modern datepickers accept typed input.
- Format dates as MM/DD/YYYY unless the field clearly shows a different format.

EDUCATION RULES (college vs university — they are different things):
- "College", "School", "Institute", "Institution name" → the COLLEGE / SCHOOL ATTENDED above.
- "University", "Affiliated university", "Board", "Degree awarded by" → the AFFILIATED UNIVERSITY above.
  If no university is given, use the college name there too.
- If there is only ONE field ("School / University", "Education institution"), enter the college attended.
- For a college / university dropdown or autocomplete: FIRST search for the exact college name (type it, or its distinctive
  part, e.g. "CVR College" — not just "College of Engineering"), wait for suggestions and pick the matching one. Try one
  short variant or common abbreviation if nothing matches (e.g. "JNTU" for "Jawaharlal Nehru Technological University").
  Only if it is truly not in the list, choose "Other" / "Not listed" and type the full name in the text box that appears.
  Never pick a different college or the university in place of the college.

PHONE RULES:
- Look at the phone field first. If the form has a SEPARATE country-code picker or prefix box (a flag, "+1" dropdown,
  "Country code" field), set it to the candidate's country code above and type ONLY the number WITHOUT country code.
- If the field already shows a prefix such as "+91" inside or beside the input, type only the number without the code.
- If it is a single plain phone field with no country code shown, type the full international number (with the code).
- Never type the country code twice (no "+91 +91…" or "9191…"), no leading 0 before the number.

RADIO BUTTON / CHECKBOX RULES:
- To tick or untick a checkbox (or a toggle / switch), use the `set_checkbox` action with the box's index and
  checked=true/false. It verifies the box really changed. Do not click checkboxes repeatedly: a second click unticks it.
- Required consent boxes ("I agree to the privacy policy / terms", "I confirm the information is correct") → tick them.
- Marketing / newsletter / "send me job alerts" boxes → leave unticked unless required.
- For a group of checkboxes (e.g. skills, locations, "which roles interest you"), tick only the options that match the
  candidate; for a radio group, pick exactly one.
- Custom-styled checkboxes are often NOT in the element list at all. If you cannot find the box's index (or
  `set_checkbox` says it is not a checkbox), use `set_checkbox_by_text` with a short exact phrase from its label,
  e.g. text="I agree to the privacy policy". The same action works for radio options ("Yes", "Immediate joiner").
- If both report they could not change the box, click its visible text once, then move on.
- For "Yes/No" questions about work authorization, visa sponsorship, etc., use the Work Authorization Rule below.
- For gender/ethnicity questions, these are usually optional — skip unless required.
- For "How did you hear about us?" dropdowns, select "LinkedIn" or "Job Board" if available.

WORK AUTHORIZATION RULE:
- If the job is located inside the candidate's home country, answer work authorization "Yes" (no sponsorship needed).
- If the job is remote or abroad: answer from the Q&A answers above (work authorization / sponsorship).

SECURITY CHECKS:
- The small "protected by reCAPTCHA" badge or text, or a "This site is protected by hCaptcha" note, is NOT a CAPTCHA.
  It needs nothing from you — ignore it and keep filling and submitting.
- A "Just a moment…" / "Verify you are human" page, a Cloudflare Turnstile box or an "I'm not a robot" checkbox:
  call `wait_for_human_check` first. It waits and clicks the box once; most checks pass that way.
- If a submit seems to do nothing and a check box appeared near the button, call `wait_for_human_check`, then submit again.

ERROR DETECTION — STOP AND REPORT:
- If you encounter a login page, STOP and report "LOGIN_REQUIRED".
- Only if `wait_for_human_check` says the check did not clear (or an image puzzle shows), STOP and report "CAPTCHA_DETECTED".
- If you see an OTP/MFA prompt, STOP and report "MFA_REQUIRED".
- If the form is too complex to fill automatically, STOP and report "TOO_COMPLEX"."""


def build_task(sess: ApplySession, continuing: bool) -> str:
    job = sess.job
    steps = sess.data["steps"][-12:]
    history = "\n".join(f"  {s['n']}. {s['goal']} — {'; '.join(s['actions'])}" for s in steps if s.get("goal") or s.get("actions"))
    if continuing:
        intro = (f"You are CONTINUING a job application for “{job.get('role', '')}” at {job.get('company', '')} that is already open "
                 f"in the current browser tab. Do NOT start over. First look at what is already filled in, then complete what is "
                 f"missing, upload the files if not uploaded yet, and submit.\n\nWhat was done before:\n{history or '  (nothing recorded)'}")
    else:
        intro = (f"Fill out and submit the job application for “{job.get('role', '')}” at {job.get('company', '')}. "
                 f"The application page is already open ({job.get('apply_url', '')}).")
    return f"{intro}\n\n{_profile_block(sess.profile)}\n\n{_files_block(sess.files)}\n\n{RULES}"


# ---------------------------------------------------------------------------- the run (worker loop)

async def _attach_live_view(sess: ApplySession, agent: Any) -> None:
    for _ in range(240):
        bs = getattr(agent, "browser_session", None)
        if bs is not None and getattr(bs, "_cdp_client_root", None) is not None:
            sess.browser_session = bs
            if sess.screencast is None or sess.screencast.session is not bs:
                if sess.screencast:
                    await sess.screencast.stop()
                sess.screencast = live_view.Screencast(bs)
            sess.screencast.start()
            if sess.data["status"] == "launching":
                sess.update(status="running", live=True, message="Filling in the application…")
            else:
                sess.update(live=True)
            return
        await asyncio.sleep(0.5)


def _verdict(text: str) -> Optional[HITLType]:
    t = (text or "").upper()
    if "CAPTCHA" in t:
        return HITLType.CAPTCHA
    if "MFA" in t or "OTP" in t:
        return HITLType.MFA
    if "LOGIN_REQUIRED" in t or "LOGIN REQUIRED" in t:
        return HITLType.LOGIN
    if "TOO_COMPLEX" in t:
        return HITLType.TOO_COMPLEX
    return None


HELP_TEXT = {
    HITLType.LOGIN: "This site needs you to sign in. Take over, sign in, then press Continue.",
    HITLType.CAPTCHA: "A CAPTCHA appeared. Take over, solve it, then press Continue.",
    HITLType.MFA: "A verification code is needed. Take over, enter it, then press Continue.",
    HITLType.TOO_COMPLEX: "This form needs a human touch. Take over to finish it, or press Continue to let the agent retry.",
    HITLType.MANUAL_FORM: "The agent stopped before submitting. Check the form, then submit it yourself or press Continue.",
}


async def _run_agent(sess: ApplySession, continuing: bool) -> None:
    try:
        from browser_use import Agent
    except ImportError:
        sess.update(status="failed", message="Browser agent not installed",
                    notice="The browser-use package is missing. Run: pip install -r requirements.txt")
        return
    settings = get_settings()
    reuse = continuing and _alive(sess)
    start_url = None if reuse else (sess.data.get("url") if continuing and sess.data.get("url") else sess.job.get("apply_url"))
    sess.data["runs"] += 1
    sess.update(status="running" if reuse else "launching", control="agent", notice="", result="",
                message="Continuing where it left off…" if continuing else "Starting a private browser…")

    try:
        llm, fallback = _build_llms()
    except Exception as exc:
        sess.update(status="failed", message="Could not start the agent", notice=str(exc))
        return

    delay = float(getattr(settings, "browser_step_delay_s", 3.0) or 0)

    async def on_step(state: Any, model_output: Any, step_num: int) -> None:
        steps = sess.data["steps"]
        evaluation = (getattr(model_output, "evaluation_previous_goal", "") or "").strip()
        if steps and steps[-1]["status"] == "running":
            failed = any(w in evaluation.lower() for w in ("fail", "unable", "could not", "error", "not found"))
            steps[-1]["status"] = "failed" if failed else "done"
            if failed and evaluation:
                steps[-1]["note"] = evaluation[:160]
        goal = (getattr(model_output, "next_goal", "") or "").strip()
        actions = _actions_of(model_output, state)
        url = getattr(state, "url", "") or ""
        entry = {"n": len(steps) + 1, "ts": _now(), "goal": goal[:200], "actions": actions[:6], "status": "running", "url": url, "repeat": 1}
        if steps and steps[-1]["goal"] == entry["goal"] and steps[-1]["actions"] == entry["actions"]:
            steps[-1]["repeat"] = steps[-1].get("repeat", 1) + 1          # same thing again: count it, don't duplicate it
            steps[-1]["status"] = "running"
        else:
            steps.append(entry)
        sess.update(url=url, title=getattr(state, "title", "") or sess.data["title"], message=goal[:140] or "Working…")
        if delay:
            await asyncio.sleep(delay)

    kwargs: dict[str, Any] = {
        "task": build_task(sess, continuing), "llm": llm, "controller": _build_tools(sess.profile),
        "register_new_step_callback": on_step, "use_vision": "auto",
        "available_file_paths": [p for p in sess.files.values() if p],
    }
    if fallback is not None:
        kwargs["fallback_llm"] = fallback
    if start_url:
        kwargs["initial_actions"] = [{"navigate": {"url": start_url, "new_tab": False}}, {"prefill_basic_fields": {}}]
    if reuse:
        kwargs["browser_session"] = sess.browser_session
    else:
        kwargs["browser_profile"] = await _build_stealth_profile(settings)
    agent = Agent(**kwargs)
    sess.agent = agent
    attach = asyncio.ensure_future(_attach_live_view(sess, agent))

    try:
        history = await agent.run(max_steps=int(getattr(settings, "browser_max_steps", 40) or 40))
    except asyncio.CancelledError:
        return                                  # stop() owns the status
    except Exception as exc:
        log.error("apply_agent_error", job_id=sess.data["job_id"], error=str(exc)[:300])
        sess.update(status="failed", message="The agent hit an error", notice=str(exc)[:300], live=_alive(sess))
        await db.update_job(sess.data["job_id"], status="apply_failed")
        return
    finally:
        if not attach.done():
            attach.cancel()

    steps = sess.data["steps"]
    if steps and steps[-1]["status"] == "running":
        steps[-1]["status"] = "done"
    try:
        final = history.final_result() or ""
        ok = bool(history.is_done() and history.is_successful())
    except Exception:
        final, ok = str(history)[:500], False
    hitl = _verdict(final)
    job_id = sess.data["job_id"]
    if ok and hitl is None and "SUCCESS" in final.upper():
        from jobhunterx import storage
        await db.update_job(job_id, status="applied")
        await storage.set_tracking(job_id, "applied")
        await db.resolve_job_interventions(job_id, "resolved")
        sess.update(status="applied", message="Application submitted 🎉", result=final[:400], live=_alive(sess))
        return
    hitl = hitl or HITLType.MANUAL_FORM
    await db.update_job(job_id, status="needs_attention")
    try:
        await db.open_intervention(job_id=job_id, hitl_type=hitl.value, url=sess.data.get("url") or sess.job.get("apply_url", ""),
                                   company=sess.job.get("company", ""), role=sess.job.get("role", ""))
    except Exception as exc:
        log.warning("intervention_create_failed", error=str(exc)[:160])
    sess.update(status="needs_you", message="Waiting for you", notice=HELP_TEXT.get(hitl, "The agent needs your help."),
                result=final[:400], live=_alive(sess))
    live_view.broadcast_event({"agent": "browser_agent", "event_type": "hitl_request", "job_id": job_id, "message": HELP_TEXT.get(hitl, "")})


# ---------------------------------------------------------------------------- public API (call from the server loop)

def new_session(job: dict) -> ApplySession:
    global _current
    sess = ApplySession(job)
    _sessions[job["id"]] = sess
    _current = job["id"]
    sess.publish()
    return sess


async def launch(sess: ApplySession, profile: dict, files: dict[str, str], continuing: bool = False) -> None:
    """Hand the session to the browser worker (returns immediately)."""
    global _current
    for other_id, other in list(_sessions.items()):
        if other is not sess and _alive(other):
            await close(other_id)               # one browser at a time
    _current = sess.data["job_id"]
    sess.profile = profile
    sess.files = files

    async def _go() -> None:
        sess.task = asyncio.current_task()
        try:
            await _run_agent(sess, continuing)
        except asyncio.CancelledError:
            pass
        except Exception as exc:                 # never leave the UI stuck on "running"
            log.error("apply_run_crashed", job_id=sess.data["job_id"], error=str(exc)[:300])
            sess.update(status="failed", message="The agent stopped unexpectedly", notice=str(exc)[:300], live=_alive(sess))

    browser_worker.submit(_go())


async def stop(job_id: str) -> Optional[dict]:
    """Stop at once. The browser stays open (and visible) so you can take over, continue or close it."""
    sess = _sessions.get(job_id)
    if not sess:
        return None
    if sess.data["status"] not in ACTIVE:
        return sess.snapshot()
    sess.update(status="stopping", message="Stopping…")

    async def _do() -> None:
        if sess.agent is not None:
            try:
                sess.agent.stop()
            except Exception:
                pass
        if sess.task is not None and not sess.task.done():
            sess.task.cancel()
            await asyncio.wait({sess.task}, timeout=5)
        steps = sess.data["steps"]
        if steps and steps[-1]["status"] == "running":
            steps[-1]["status"] = "stopped"
        sess.update(status="stopped", control="agent", live=_alive(sess),
                    message="Stopped", notice="Stopped by you. Progress is saved — take over, continue, or close the browser.")
        await db.update_job(job_id, status="needs_attention")
        try:   # an unfinished application stays in Interventions until it is submitted or dismissed
            await db.open_intervention(job_id=job_id, hitl_type=HITLType.STOPPED.value,
                                       url=sess.data.get("url") or sess.job.get("apply_url", ""),
                                       company=sess.job.get("company", ""), role=sess.job.get("role", ""))
        except Exception as exc:
            log.warning("intervention_create_failed", error=str(exc)[:160])

    await browser_worker.run(_do())
    return sess.snapshot()


async def take_over(job_id: str) -> Optional[dict]:
    sess = _sessions.get(job_id)
    if not sess:
        return None

    async def _do() -> None:
        if sess.agent is not None and sess.data["status"] == "running":
            try:
                sess.agent.pause()
            except Exception:
                pass
            sess.update(status="paused", control="you", message="You have control")
        else:
            sess.update(control="you")
    await browser_worker.run(_do())
    return sess.snapshot()


async def release(job_id: str) -> Optional[dict]:
    sess = _sessions.get(job_id)
    if not sess:
        return None

    async def _do() -> None:
        if sess.data["status"] == "paused" and sess.agent is not None:
            try:
                sess.agent.resume()
            except Exception:
                pass
            sess.update(status="running", control="agent", message="Back to the agent…")
        else:
            sess.update(control="agent")
    await browser_worker.run(_do())
    return sess.snapshot()


async def close(job_id: str) -> Optional[dict]:
    sess = _sessions.get(job_id)
    if not sess:
        return None

    async def _do() -> None:
        if sess.task is not None and not sess.task.done():
            if sess.agent is not None:
                try:
                    sess.agent.stop()
                except Exception:
                    pass
            sess.task.cancel()
            await asyncio.wait({sess.task}, timeout=5)
        if sess.screencast:
            await sess.screencast.stop()
            sess.screencast = None
        if sess.browser_session is not None:
            try:
                await asyncio.wait_for(sess.browser_session.kill(), timeout=15)
            except Exception as exc:
                log.warning("browser_close_failed", error=str(exc)[:160])
        await _stop_own_chrome()             # a Chrome we started ourselves outlives browser-use's disconnect
        sess.browser_session = None
        sess.agent = None
    await browser_worker.run(_do())
    live_view.clear_frame()
    status = sess.data["status"]
    sess.update(live=False, control="agent", status="closed" if status in ACTIVE else status,
                message="Browser closed" if status in ACTIVE or status in ("stopped", "needs_you") else sess.data["message"])
    return sess.snapshot()


async def forward_input(msg: dict) -> None:
    """Mouse / keyboard from the live panel. Only while the user has control or the agent is not running."""
    sess = current_session()
    if not sess or not _alive(sess):
        return
    if sess.data["control"] != "you" and sess.data["status"] in ("launching", "running", "stopping"):
        return
    try:
        await browser_worker.run(live_view.dispatch_input(sess.browser_session, msg))
    except Exception as exc:
        log.debug("live_input_failed", error=str(exc)[:120])


async def resize_view(w: Any, h: Any) -> None:
    """The live-view panel changed size: match the browser's shape to it."""
    if not live_view.set_panel(w, h):
        return
    sess = current_session()
    if not sess or not _alive(sess):
        return
    try:
        await browser_worker.run(live_view.apply_viewport(sess.browser_session))
    except Exception as exc:
        log.debug("live_resize_failed", error=str(exc)[:120])


async def stop_all_active_browsers() -> None:
    for job_id in list(_sessions):
        try:
            await close(job_id)
        except Exception:
            pass


# Backwards-compatible names used by older routes ----------------------------------------------

async def clear_paused_session(job_id: str) -> None:
    return None


async def focus_browser_session(job_id: str = "") -> bool:
    sess = _sessions.get(job_id) if job_id else current_session()
    return bool(sess and _alive(sess))
