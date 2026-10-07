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
      * Headless Chrome announcing itself → the new headless mode of the real Chrome with the "Headless" word removed
        from the User-Agent at the true version (passes Cloudflare's test page). No window ever opens: the browser is
        only seen through the live view in the app. BROWSER_WINDOW_MODE=window shows it for debugging.
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
        mode = "headless"           # a parked window still shows in the taskbar (and on some monitor setups, on screen)
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
    if name == "choose_option":
        return f"Choose “{p.get('value', '')}” in {lbl}"
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
        return "Fill name, email, phone and profile links"
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

# Kilo free models that drive the browser well. Measured Oct 2026 with browser-use's output format: all four answer in
# 1-4 s. Nemotron 3 Nano Omni is left out: it returns no choices for agent-style prompts.
_KILO_BROWSER = ["nvidia/nemotron-3-super-120b-a12b:free", "kilo-auto/free", "poolside/laguna-s-2.1:free", "inclusionai/ling-3.1-flash"]
# LLM7 free models (no key) after Kilo: a quick backup (small daily quota), the next model answers when it says no.
_LLM7_BROWSER = ["deepseek-v4-pro", "minimax-m3"]


def _json_only(text: str) -> str:
    """Free models often wrap the JSON in ```json fences or a sentence: keep the outer {...}."""
    i, j = text.find("{"), text.rfind("}")
    return text[i:j + 1] if 0 <= i < j else text


def _free_llm(provider: str, model: str, key: str) -> Any:
    """A no-key pool (Kilo, LLM7) through browser-use's OpenAI client. Kilo's free pool rejects any Authorization header
    and most free models refuse strict JSON-schema output, so: no auth header, the schema goes in the prompt, Kilo's
    reasoning is off (see openai_compat.KILO_EXTRA), and screenshots are dropped (text models; the page text is still sent)."""
    import openai
    from browser_use.llm.openai.chat import ChatOpenAI
    from jobhunterx.config import models as M
    from jobhunterx.config import openai_compat as oc

    def text_only(msg: dict) -> dict:
        parts = msg.get("content")
        if not isinstance(parts, list):
            return msg
        return {**msg, "content": [p for p in parts if not (isinstance(p, dict) and p.get("type") == "image_url")] or ""}

    class FreeChat(ChatOpenAI):
        def get_client(self) -> Any:
            client = super().get_client()
            create = client.chat.completions.create

            async def create_free(*, messages: list, **kw: Any) -> Any:
                if provider == "kilo":
                    kw["extra_body"] = oc.KILO_EXTRA
                resp = await create(messages=[text_only(m) for m in messages], **kw)
                for choice in resp.choices or []:
                    if choice.message.content:
                        choice.message.content = _json_only(choice.message.content)
                return resp

            client.chat.completions.create = create_free
            return client

    free = key == M.KILO_FREE
    base = oc.KILO_BASE if provider == "kilo" else oc.LLM7_BASE
    return FreeChat(model=model, api_key="no-key" if free else key, base_url=base,
                    default_headers={"Authorization": openai.Omit()} if free else None,
                    temperature=0.2, frequency_penalty=None, max_retries=0, timeout=90,
                    dont_force_structured_output=True, add_schema_to_system_prompt=True)


class _LLMChain:
    """Many models behind one. browser-use switches to its fallback_llm only once per run and then stops, so a
    Gemini "RESOURCE_EXHAUSTED" followed by one busy fallback ended the whole run. Here every call walks the list
    (Gemini → Kilo free models → LLM7 → Groq → Mistral → Gemma) and skips models the app's AI router already knows are
    resting or rate limited (shared state in config.models), so the browser agent and the rest of the app agree."""

    def __init__(self, links: list[tuple[str, Any]]):
        self._links = links
        self._cur = links[0][1]

    @property
    def model(self) -> str:
        return self._cur.model

    @property
    def provider(self) -> str:
        return self._cur.provider

    @property
    def name(self) -> str:
        return self._cur.name

    @property
    def model_name(self) -> str:
        return self._cur.model

    async def ainvoke(self, messages: list, output_format: Any = None, **kwargs: Any) -> Any:
        from browser_use.llm.exceptions import ModelProviderError
        from jobhunterx.config import models as M
        ready = [(mid, llm) for mid, llm in self._links
                 if not M.resting(mid) and not M.key_rejected(M.provider_of(mid))] or self._links
        last: Optional[Exception] = None
        for mid, llm in ready:
            self._cur = llm
            try:
                out = await llm.ainvoke(messages, output_format, **kwargs)
            except ModelProviderError as exc:          # rate limits, server errors, bad output: the next model takes over
                last = exc
                M.mark_failure(mid, f"{getattr(exc, 'status_code', '')} {exc.message}")
                log.warning("browser_llm_handover", model=mid, error=str(exc.message)[:160])
                continue
            M.mark_success(mid)
            return out
        raise last or RuntimeError("No AI model answered")


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
    from jobhunterx.config import models as M
    s = get_settings()
    google_key = (s.google_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) if _app_state.llm_provider_enabled("google") else None
    groq_key = (s.groq_api_key or os.getenv("GROQ_API_KEY")) if _app_state.llm_provider_enabled("groq") else None
    mistral_key = (s.mistral_api_key or os.getenv("MISTRAL_API_KEY")) if _app_state.llm_provider_enabled("mistral") else None
    kilo_key = M.provider_key("kilo") if _app_state.llm_provider_enabled("kilo") else None
    llm7_on = _app_state.llm_provider_enabled("llm7")
    links: list[tuple[str, Any]] = []
    if google_key:
        # 429 / RESOURCE_EXHAUSTED is not retried here: the next model in the chain answers at once instead
        links.append(("gemini/gemini-3.5-flash-lite", ChatGoogle(
            model="gemini-3.5-flash-lite", api_key=google_key, temperature=0.2, max_retries=3,
            retry_base_delay=2.0, retry_max_delay=10.0, retryable_status_codes=[500, 502, 503, 504])))
    if kilo_key:
        links += [(f"kilo/{m}", _free_llm("kilo", m, kilo_key)) for m in _KILO_BROWSER]
    if llm7_on:
        links += [(f"llm7/{m}", _free_llm("llm7", m, M.KILO_FREE)) for m in _LLM7_BROWSER]
    if groq_key and ChatGroq is not None:
        links.append(("groq/openai/gpt-oss-120b", ChatGroq(model="openai/gpt-oss-120b", api_key=groq_key, temperature=0.2, max_retries=1)))
    if mistral_key and ChatMistral is not None:
        links.append(("mistral/mistral-small-latest", ChatMistral(model="mistral-small-latest", api_key=mistral_key, temperature=0.2, max_retries=1)))
    if google_key:
        # last resort only: free Gemma is slow and often overloaded, so don't sit in long retry loops on it
        links.append(("gemini/gemma-4-31b-it", ChatGoogle(model="gemma-4-31b-it", api_key=google_key, temperature=0.2, max_retries=1,
                                                          retry_base_delay=2.0, retry_max_delay=5.0)))
    if not links:
        raise RuntimeError("No AI provider is available for the browser agent. Add a key or turn a provider on in Settings.")
    return _LLMChain(links), None        # the chain does the falling back; browser-use's one-time fallback is not needed


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


# Fills the plain identity fields (name, email, profile links) by their HTML meaning. Each field is judged by ONE source
# at a time — autocomplete, then its visible label, aria-label, placeholder, and last its name/id — so a stray attribute
# ("name" on a Last-name box) cannot flip it. Only empty, visible, editable fields are touched; a link goes only into the
# box made for that site (no GitHub in a LinkedIn or Twitter box).
_PREFILL_JS = """(p) => {
  const docs = [document];
  for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch (e) {} }
  const norm = (s) => (s || '').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_\\-\\[\\].:*]+/g, ' ').replace(/\\s+/g, ' ').trim().toLowerCase();
  const SKIP = /company|employer|organi[sz]ation|school|college|university|reference|referr|manager|emergency|hiring|recruiter|city|country|\\bstate\\b|(home|street|postal|current|permanent|mailing|residential) address|^address|nominee|father|mother|spouse|guardian|parent|middle|nick|maiden|alternate|secondary|confirm|search|keyword/;
  const kinds = [
    ['full', (t) => /first\\s*(name)?\\s*(and|&|\\/)\\s*last|full\\s*name|^name$|^your name|legal name|candidate name|applicant name|name as per/.test(t)],
    ['last', (t) => /last\\s*name|family\\s*name|sur\\s*name|^last$|^l\\s?name$|\\blname\\b/.test(t)],
    ['first', (t) => /first\\s*name|given\\s*name|fore\\s*name|^first$|^f\\s?name$|\\bfname\\b|preferred\\s*first/.test(t)],
    ['email', (t) => /e\\s?mail/.test(t)],
    ['linkedin', (t) => /linked\\s*in/.test(t)],
    ['github', (t) => /git\\s*hub/.test(t)],
    ['gitlab', (t) => /git\\s*lab/.test(t)],
    ['twitter', (t) => /twitter|\\bx\\.com|^x( handle| profile| url)?$/.test(t)],
    ['kaggle', (t) => /kaggle/.test(t)], ['leetcode', (t) => /leet\\s*code/.test(t)], ['medium', (t) => /\\bmedium\\b/.test(t)],
    ['behance', (t) => /behance/.test(t)], ['dribbble', (t) => /dribbble/.test(t)], ['stackoverflow', (t) => /stack\\s*overflow/.test(t)],
    ['scholar', (t) => /scholar/.test(t)], ['other_social', (t) => /facebook|instagram|youtube|tiktok|threads|social/.test(t)],
    ['portfolio', (t) => /portfolio|personal\\s*(web)?\\s*site|^web\\s*site|website|personal url|home\\s*page|^url$|^link$|blog/.test(t)],
  ];
  const labelOf = (el, d) => {
    let s = [...(el.labels || [])].map((l) => l.innerText).join(' ');
    const lb = el.getAttribute('aria-labelledby');
    if (!s && lb) s = lb.split(/\\s+/).map((i) => (d.getElementById(i) || {}).innerText || '').join(' ');
    let c = el.parentElement;
    for (let i = 0; !s && c && i < 4; i++, c = c.parentElement) {
      if (c.querySelectorAll('input,textarea,select').length > 1) break;
      const l = c.querySelector('label,legend,[class*=label i]');
      if (l && !l.contains(el)) s = l.innerText;
    }
    return s || '';
  };
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  const filled = [], seen = new Set();
  for (const d of docs) {
    for (const el of d.querySelectorAll('input')) {
      if (!['text', 'email', 'url', ''].includes(el.type) || el.disabled || el.readOnly || el.value) continue;
      if (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-autocomplete')) continue;
      const r = el.getBoundingClientRect(); if (r.width < 5 || r.height < 5) continue;
      const a = (el.getAttribute('autocomplete') || '').toLowerCase();
      const lab = norm(labelOf(el, d));
      const sources = [lab, norm(el.getAttribute('aria-label')), norm(el.placeholder), norm(el.name + ' ' + el.id)].filter(Boolean);
      if (!sources.length || sources.slice(0, 2).some((t) => SKIP.test(t))) continue;
      let kind = ({ 'given-name': 'first', 'family-name': 'last', name: 'full', email: 'email' })[a] || (el.type === 'email' ? 'email' : '');
      for (const t of sources) {
        if (kind) break;
        const hit = kinds.find(([, f]) => f(t));
        if (hit) kind = hit[0];
      }
      if (!kind && a === 'url') kind = 'portfolio';
      if (!kind || !p[kind] || (seen.has(kind) && !['first', 'last', 'full', 'email'].includes(kind))) continue;
      seen.add(kind);
      el.focus(); setter.call(el, p[kind]);
      for (const ev of ['input', 'change']) el.dispatchEvent(new Event(ev, { bubbles: true }));
      el.blur();
      filled.push((labelOf(el, d) || el.placeholder || el.name || kind).replace(/\\s+/g, ' ').replace(/\\*/g, '').trim().slice(0, 40) + ' = ' + p[kind]);
    }
  }
  return filled;
}"""


# Puts the phone number in the way the phone box expects: sets the country flag / code picker of the common phone widgets
# (intl-tel-input, react-phone-input-2, react-phone-number-input, a <select> of codes next to the box) to the candidate's
# country, then types only the national number; a plain box gets the full international number unless it is clearly a
# 10-digit-only box. Anything it cannot handle safely is reported back for the agent to do with choose_option.
_PHONE_JS = """(p) => {
  const docs = [document];
  for (const f of document.querySelectorAll('iframe')) { try { if (f.contentDocument) docs.push(f.contentDocument); } catch (e) {} }
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  const selSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
  const put = (el, v) => { el.focus(); setter.call(el, v); for (const ev of ['input', 'change']) el.dispatchEvent(new Event(ev, { bubbles: true })); el.blur(); };
  const tap = (el) => { for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: el.ownerDocument.defaultView })); };
  const codeRe = new RegExp('\\\\+\\\\s?' + p.code + '(?!\\\\d)');
  const digits = (s) => (s || '').replace(/\\D/g, '');
  const out = [];
  for (const d of docs) {
    const w = d.defaultView;
    for (const el of d.querySelectorAll('input')) {
      const r = el.getBoundingClientRect(); if (r.width < 5 || r.height < 5 || el.disabled || el.readOnly) continue;
      const lab = [...(el.labels || [])].map((l) => l.innerText).join(' ');
      const t = [el.name, el.id, el.getAttribute('aria-label'), el.placeholder, lab, el.getAttribute('autocomplete')].join(' ').toLowerCase();
      const isTel = el.type === 'tel' || /phone|mobile|contact\\s*(no|number)|whats\\s*app|\\btel\\b/.test(t);
      if (!isTel || /country\\s*code|dial|extension|\\bext\\b|emergency|reference|alternate|fax/.test(t) || el.type === 'search') continue;
      const v = (el.value || '').trim();
      if (digits(v).length > p.code.length + 2) continue;                    // already holds a number
      const iti = (w.intlTelInputGlobals && w.intlTelInputGlobals.getInstance && w.intlTelInputGlobals.getInstance(el))
               || (w.intlTelInput && w.intlTelInput.getInstance && w.intlTelInput.getInstance(el));
      if (iti && p.iso) {
        try { iti.setCountry(p.iso); } catch (e) {}
        put(el, p.national);
        out.push('phone (flag picker set to ' + p.code_plus + ') = ' + p.national);
        continue;
      }
      const rtel = el.closest('.react-tel-input');
      if (rtel) {
        const flag = rtel.querySelector('.selected-flag');
        if (!codeRe.test(v) && flag) {
          tap(flag);
          const li = rtel.querySelector('li.country[data-country-code="' + p.iso + '"]') || [...rtel.querySelectorAll('li.country')].find((x) => x.getAttribute('data-dial-code') === p.code);
          if (li) tap(li);
        }
        put(el, p.code_plus + ' ' + p.national);
        out.push('phone (with ' + p.code_plus + ' built in) = ' + p.code_plus + ' ' + p.national);
        continue;
      }
      let box = el.parentElement, sel = null, prefix = null;
      for (let i = 0; box && i < 4 && !sel && !prefix; i++, box = box.parentElement) {
        if (box.querySelectorAll('input[type=tel],input[type=text],input:not([type])').length > 2) break;
        sel = [...box.querySelectorAll('select')].find((s) => [...s.options].some((o) => codeRe.test(o.text) || (p.iso && o.value.toUpperCase() === p.iso.toUpperCase()) || (digits(o.value) === p.code && o.value.length <= 5))) || null;
        if (!sel) {
          prefix = [...box.querySelectorAll('button,span,div,[role=combobox]')].find((x) => x !== el && !x.contains(el) && /^\\s*(\\S{0,4}\\s*)?\\+\\d{1,4}\\s*$/.test(x.innerText || '')) || null;
        }
      }
      if (sel) {
        const o = [...sel.options].find((o) => codeRe.test(o.text)) || [...sel.options].find((o) => p.iso && o.value.toUpperCase() === p.iso.toUpperCase()) || [...sel.options].find((o) => digits(o.value) === p.code);
        selSetter.call(sel, o.value);
        for (const ev of ['input', 'change']) sel.dispatchEvent(new Event(ev, { bubbles: true }));
        put(el, p.national);
        out.push('phone code picker = ' + o.text.trim().slice(0, 30) + '; phone = ' + p.national);
        continue;
      }
      if (prefix) {
        if (codeRe.test(prefix.innerText)) { put(el, p.national); out.push('phone (box already shows ' + p.code_plus + ') = ' + p.national); }
        else out.push('NOT DONE: the phone box has a country-code picker showing "' + prefix.innerText.trim() + '" — set it to ' + p.code_plus + ' with choose_option, then type ' + p.national);
        continue;
      }
      if (codeRe.test(v)) { put(el, v.replace(/\\s+$/, '') + ' ' + p.national); out.push('phone = ' + p.code_plus + ' ' + p.national); continue; }
      const ml = parseInt(el.getAttribute('maxlength') || '0', 10);
      const ph = (el.placeholder || '').trim();
      const nationalOnly = (ml > 0 && ml <= p.national.length + 1) || (/^[\\d\\s-]{8,14}$/.test(ph) && !ph.startsWith('+')) || /10\\s*digit/.test(t);
      const val = nationalOnly ? p.national : p.code_plus + ' ' + p.national;
      put(el, val);
      out.push('phone = ' + val);
    }
  }
  return out;
}"""


async def _eval(browser_session: Any, expression: str) -> Any:
    cdp = await browser_session.get_or_create_cdp_session()
    out = await cdp.cdp_client.send.Runtime.evaluate(params={"expression": expression, "returnByValue": True},
                                                     session_id=cdp.session_id)
    return (out.get("result") or {}).get("value")


async def _prefill(browser_session: Any, profile: dict) -> Any:
    import json as _json
    from browser_use import ActionResult
    first, last, full = name_parts(profile)
    vals = {"full": full, "first": first, "last": last, "email": profile.get("email") or "", **profile_links(profile)}
    code, national = split_phone(profile.get("phone", ""), home_country(profile))
    phone = {"code": code.lstrip("+"), "code_plus": code, "iso": _ISO.get(code, ""), "national": national}
    try:
        filled: list = []
        for _ in range(8):                               # single-page forms render a moment after load
            filled = await _eval(browser_session, f"({_PREFILL_JS})({_json.dumps(vals)})") or []
            if filled:
                break
            await asyncio.sleep(0.75)
        if code and national:
            filled += await _eval(browser_session, f"({_PHONE_JS})({_json.dumps(phone)})") or []
    except Exception as exc:
        return ActionResult(extracted_content=f"Pre-fill skipped ({str(exc)[:80]}). Fill the form normally.")
    if not filled:
        return ActionResult(extracted_content="No basic fields to pre-fill here (maybe an Apply button must be clicked first).")
    return ActionResult(extracted_content="Pre-filled: " + "; ".join(filled) + ". Check them once; do not retype them.")


# Runs on the dropdown the agent picked (`this`). One function, several steps (`op`), so Python can wait between them:
# read a native <select>, find the search box of a custom dropdown, list the options that are showing right now (and say
# whether the list is still loading), scroll a long list, and give the screen point of an option for a real mouse click.
_OPTION_JS = """function(op, arg) {
  const el = this, doc = el.ownerDocument, win = doc.defaultView;
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const vis = (e) => { const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
    const s = win.getComputedStyle(e); return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'; };
  const isText = (e) => e && ((e.tagName === 'INPUT' && /^(text|search|email|tel|url|)$/.test(e.type)) || e.isContentEditable);
  const nativeSelect = () => {
    if (el.tagName === 'SELECT') return el;
    if (el.tagName === 'LABEL' && el.control && el.control.tagName === 'SELECT') return el.control;
    const inner = el.querySelectorAll ? el.querySelectorAll('select') : [];
    return inner.length === 1 ? inner[0] : null;
  };
  const shown = () => {
    let c = el;
    for (let i = 0; i < 3 && c.parentElement && norm(c.parentElement.innerText).length < 160; i++) c = c.parentElement;
    const s = nativeSelect();
    return norm([s && s.selectedOptions[0] ? s.selectedOptions[0].text : '', el.value || '', c.innerText || ''].join(' ')).slice(0, 200);
  };
  const PLACEHOLDER = /^(loading|searching|fetching|please wait|no (options|results|matches|data)|nothing found|not found|type to search|start typing|type (at least|more)|please enter|enter \\d+ or more|select\\.*$|select (an? )?(option|one)|choose\\.*$|--)/i;
  if (op === 'inspect') {
    const s = nativeSelect();
    if (s) return { kind: 'select', options: [...s.options].map((o) => ({ t: norm(o.text), v: o.value, off: o.disabled })) };
    return { kind: 'combo', typable: isText(el), workday: !!el.closest('[data-automation-id]'), expanded: el.getAttribute('aria-expanded') === 'true', shown: shown() };
  }
  if (op === 'set_select') {
    const s = nativeSelect(), o = s.options[arg];
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, o.value);
    for (const ev of ['input', 'change']) s.dispatchEvent(new Event(ev, { bubbles: true }));
    return { shown: s.selectedOptions[0] ? norm(s.selectedOptions[0].text) : '' };
  }
  if (op === 'shown') return { shown: shown(), expanded: el.getAttribute('aria-expanded') === 'true' };
  const scopeOf = () => {
    for (const e of [doc.activeElement, el, el.querySelector && el.querySelector('[aria-controls],[aria-owns]')]) {
      const id = e && (e.getAttribute('aria-controls') || e.getAttribute('aria-owns'));
      const sc = id && doc.getElementById(id);
      if (sc && vis(sc)) return sc;
    }
    return doc;
  };
  if (op === 'focus_input') {
    const a = doc.activeElement;
    let inp = isText(a) ? a : isText(el) ? el : null;
    if (!inp) {
      const sc = scopeOf();
      inp = [...(sc === doc ? doc : sc).querySelectorAll('input[type=search],.iti__search-input,.select2-search__field,input[placeholder*=search i],[role=listbox] input,[role=dialog] input[type=text]')].find(vis) || null;
    }
    if (!inp) return { ok: false };
    inp.focus();
    try { inp.select(); } catch (e) {}
    return { ok: true, value: inp.value || '' };
  }
  if (op === 'options') {
    const sc = scopeOf();
    const SEL = ['[role=option]', '[role=listbox] li', '[role=menuitem]', '[role=menuitemradio]', '[role=treeitem]',
      '[class*=menu] [class*="-option"]', '[id*="-option-"]', '.select__option', 'li.iti__country', '.country-list li.country',
      '[data-automation-id=promptOption]', '.MuiAutocomplete-option', '.ant-select-item-option', '.vs__dropdown-option',
      '.select2-results__option', '.chosen-results li', '.pac-item', 'ul.ui-autocomplete li', '.autocomplete-suggestion',
      '.dropdown-menu.show li', '[class*=suggestion] li', '[class*=dropdown] [class*=item]'];
    const found = new Set();
    for (const q of SEL) { try { for (const e of sc.querySelectorAll(q)) if (!e.contains(el) && !el.contains(e)) found.add(e); } catch (e) {} }
    let cands = [...found].filter(vis);
    cands = cands.filter((c) => !cands.some((o) => o !== c && c.contains(o)));
    const opts = [], els = [];
    let placeholder = '';
    for (const c of cands) {
      const t = norm(c.innerText || c.textContent || c.getAttribute('aria-label'));
      if (!t || t.length > 200) continue;
      if (PLACEHOLDER.test(t) && !c.getAttribute('data-dial-code')) { placeholder = placeholder || t; continue; }
      if (c.getAttribute('aria-disabled') === 'true') continue;
      els.push(c);
      opts.push({ t, dial: c.getAttribute('data-dial-code') || (c.querySelector('[data-dial-code]') || { getAttribute: () => '' }).getAttribute('data-dial-code') || '' });
      if (opts.length >= 400) break;
    }
    const busy = [...(sc === doc ? doc : sc).querySelectorAll('[class*=loading i],[class*=spinner i],[aria-busy=true]')].some((e) => vis(e) && !e.contains(el));
    const list = els.length ? (els[0].closest('[role=listbox],ul,[class*=menu-list],[class*=menu],[class*=list]') || els[0].parentElement) : null;
    win.__jhxOpts = els; win.__jhxList = list;
    return { opts, loading: busy || /^(loading|searching|fetching|please wait)/i.test(placeholder), empty: placeholder,
             scrollable: !!(list && list.scrollHeight > list.clientHeight + 4) };
  }
  if (op === 'scroll_list') {
    const l = win.__jhxList; if (!l) return { moved: false };
    const before = l.scrollTop; l.scrollTop += Math.max(60, l.clientHeight * 0.85);
    return { moved: l.scrollTop !== before };
  }
  if (op === 'point') {
    const o = (win.__jhxOpts || [])[arg]; if (!o) return null;
    o.scrollIntoView({ block: 'nearest' });
    const r = o.getBoundingClientRect();
    const lx = r.left + Math.min(r.width / 2, 40), ly = r.top + r.height / 2;
    const hit = doc.elementFromPoint(lx, ly);
    let x = lx, y = ly, w = win;
    try { while (w !== w.top && w.frameElement) { const f = w.frameElement.getBoundingClientRect(); x += f.left + w.frameElement.clientLeft; y += f.top + w.frameElement.clientTop; w = w.parent; } } catch (e) {}
    return { x, y, top: w === w.top, hit: !!hit && (o === hit || o.contains(hit) || hit.contains(o)) };
  }
  if (op === 'synthetic') {
    const o = (win.__jhxOpts || [])[arg]; if (!o) return false;
    o.scrollIntoView({ block: 'nearest' });
    for (const t of ['pointerover', 'mouseover', 'pointermove', 'mousemove', 'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
      o.dispatchEvent(new (t.startsWith('pointer') ? PointerEvent : MouseEvent)(t, { bubbles: true, cancelable: true, view: win, button: 0 }));
    return true;
  }
  return null;
}"""


def _norm_opt(s: str) -> str:
    s = re.sub(r"[\U0001F1E6-\U0001F1FF]", " ", s or "")                     # flag emoji
    return re.sub(r"\s+", " ", re.sub(r"[^\w+]+", " ", s.lower())).strip()


def _want(value: str) -> tuple[str, str, list[str]]:
    """What the agent asked for → (normalised value, calling code digits if it is a country / code, aliases)."""
    v = _norm_opt(value)
    code, aliases = "", []
    m = re.fullmatch(r"\+?\s?(\d{1,4})", v)
    if m:
        code = m.group(1)
    else:
        for name, c in _CALLING_CODES.items():
            if v == name or re.fullmatch(rf"{re.escape(name)} ?\+?{c.lstrip('+')}", v):
                code = c.lstrip("+")
    if code:
        aliases = [n for n, c in _CALLING_CODES.items() if c == "+" + code] + ["+" + code]
        aliases += _COUNTRY_ALIASES.get(_CODE_COUNTRY.get("+" + code, "").lower(), [])
    return v, code, aliases


def _option_score(text: str, dial: str, want: str, code: str, aliases: list[str]) -> float:
    t = _norm_opt(text)
    if not t:
        return 0
    score = 0.0
    if t == want:
        score = 100
    elif code and ((dial and dial.lstrip("+") == code) or re.search(rf"\+\s?{code}(?!\d)", text) or t == code):
        # "+91" asked: an option carrying that dial code; prefer the one that also names the country ("India +91")
        score = 94 + (3 if any(re.search(rf"(^| ){re.escape(a)}( |$)", t) for a in aliases if len(a) > 2) else 0)
    elif t in aliases:
        score = 92
    elif want and re.search(rf"(^| ){re.escape(want)}( |$)", t):
        score = 82
    elif any(len(a) > 2 and re.search(rf"(^| ){re.escape(a)}( |$)", t) for a in aliases):
        score = 78
    elif want and t.startswith(want):
        score = 72
    elif want and all(w in t.split() for w in want.split()):
        score = 66
    elif want and len(want) > 3 and want in t:
        score = 55
    return score - len(t) / 1000 if score else 0


def _best(options: list[dict], value: str) -> tuple[int, float]:
    want, code, aliases = _want(value)
    best, best_score = -1, 0.0
    for i, o in enumerate(options):
        s = _option_score(o.get("t", ""), o.get("dial", ""), want, code, aliases)
        if s > best_score:
            best, best_score = i, s
    return best, best_score


_GOOD = 60     # below this an option is only loosely related to what was asked: list them and let the agent decide


async def _choose_option(browser_session: Any, index: int, value: str, search: str = "", wait_seconds: float = 8) -> Any:
    """Open a dropdown (native, React-Select, Material, Workday, country-code flag pickers, autocompletes…), type a search
    if it has a search box, WAIT until the list has loaded and stopped changing, click the best-matching option with a
    real mouse click, and check that the field now shows it."""
    from browser_use import ActionResult
    from browser_use.browser.events import ClickElementEvent
    node = await browser_session.get_element_by_index(index)
    if node is None:
        return ActionResult(error=f"Element {index} is not on the page any more — refresh the page state and try again.")
    cdp = await browser_session.cdp_client_for_node(node)
    send, sid = cdp.cdp_client.send, cdp.session_id
    res = await send.DOM.resolveNode(params={"backendNodeId": node.backend_node_id}, session_id=sid)
    obj = (res.get("object") or {}).get("objectId")
    if not obj:
        return ActionResult(error=f"Element {index} cannot be read — refresh the page state and try again.")

    async def js(op: str, arg: Any = None) -> Any:
        out = await send.Runtime.callFunctionOn(params={"objectId": obj, "functionDeclaration": _OPTION_JS, "returnByValue": True,
                                                        "arguments": [{"value": op}, {"value": arg}]}, session_id=sid)
        return (out.get("result") or {}).get("value")

    async def key(k: str, code: int, text: str = "") -> None:
        for typ in ("keyDown", "keyUp"):
            p = {"type": typ, "key": k, "code": k, "windowsVirtualKeyCode": code}
            if text and typ == "keyDown":
                p["text"] = text
            await send.Input.dispatchKeyEvent(params=p, session_id=sid)

    async def type_text(text: str) -> None:
        await key("Backspace", 8)                                     # the focused search box has its text selected
        for ch in text:
            await send.Input.dispatchKeyEvent(params={"type": "keyDown", "key": ch, "text": ch, "unmodifiedText": ch}, session_id=sid)
            await send.Input.dispatchKeyEvent(params={"type": "keyUp", "key": ch}, session_id=sid)
            await asyncio.sleep(0.06)

    async def settled(limit: float) -> dict:
        """Poll the options until the list stops loading and stays the same for a moment (or a good match shows)."""
        deadline = time.monotonic() + limit
        last, since, r = None, time.monotonic(), {"opts": []}
        while True:
            r = await js("options") or {"opts": []}
            sig = tuple(o["t"] for o in r["opts"])
            now = time.monotonic()
            if sig != last:
                last, since = sig, now
            if r["opts"] and not r.get("loading") and now - since >= 0.6:
                if _best(r["opts"], value)[1] >= _GOOD or now - since >= 1.5:
                    return r
            if r.get("empty") and not r.get("loading") and now - since >= 1.2:
                return r                                              # "No options" has stayed: this search found nothing
            if now >= deadline:
                return r
            await asyncio.sleep(0.3)

    async def click_option(i: int) -> None:
        pt = await js("point", i)
        if pt and pt.get("top") and pt.get("hit"):
            for typ, extra in (("mouseMoved", {}), ("mousePressed", {"button": "left", "clickCount": 1}),
                               ("mouseReleased", {"button": "left", "clickCount": 1})):
                await send.Input.dispatchMouseEvent(params={"type": typ, "x": pt["x"], "y": pt["y"], **extra}, session_id=sid)
                await asyncio.sleep(0.05)
        else:
            await js("synthetic", i)

    def confirmed(chosen: str, shown: str) -> bool:
        words = [w for w in _norm_opt(chosen).split() if len(w) > 1]
        have = _norm_opt(shown)
        return bool(words) and sum(w in have for w in words) >= max(1, (len(words) + 1) // 2)

    wait_seconds = max(3.0, min(float(wait_seconds or 8), 20.0))
    try:
        info = await js("inspect") or {}
        if info.get("kind") == "select":
            opts = [o for o in info["options"] if not o.get("off")]
            i, score = _best(opts, value)
            if score < _GOOD:
                names = ", ".join(f"“{o['t']}”" for o in opts[:40] if o["t"])
                return ActionResult(error=f"No option close to “{value}” in this list. The options are: {names}. "
                                          "Call choose_option again with the exact option text.")
            out = await js("set_select", info["options"].index(opts[i])) or {}
            return ActionResult(extracted_content=f"Chose “{opts[i]['t']}”. The field now shows “{out.get('shown', '')}”.")

        if not info.get("expanded"):
            ev = browser_session.event_bus.dispatch(ClickElementEvent(node=node))
            await ev
            try:
                await ev.event_result(raise_if_any=False, raise_if_none=False)
            except Exception:
                pass
            await asyncio.sleep(0.4)

        want_v, code, _aliases = _want(value)
        terms = [search] if search else []
        if code and _CODE_COUNTRY.get("+" + code):
            terms += [_CODE_COUNTRY["+" + code], "+" + code]
        terms.append(value)
        terms = list(dict.fromkeys(t.strip() for t in terms if t and t.strip()))[:3]

        r = await settled(1.2 if info.get("typable") else min(2.5, wait_seconds))                       # some lists show everything on open
        i, score = _best(r["opts"], value)
        typed = ""
        if score < _GOOD:
            for term in terms:
                focus = await js("focus_input") or {}
                if not focus.get("ok"):
                    break
                await type_text(term)
                typed = term
                await asyncio.sleep(0.5)
                r = await settled(wait_seconds)
                if not r["opts"] and not r.get("empty") and info.get("workday"):
                    await key("Enter", 13, "\r")                      # Workday-style boxes search on Enter
                    r = await settled(wait_seconds)
                i, score = _best(r["opts"], value)
                if score >= _GOOD:
                    break
        if score < _GOOD and r.get("scrollable"):                       # long list with no search box: scroll through it
            for _ in range(40):
                if not (await js("scroll_list") or {}).get("moved"):
                    break
                await asyncio.sleep(0.25)
                r = await js("options") or {"opts": []}
                i, score = _best(r["opts"], value)
                if score >= _GOOD:
                    break
        if score < _GOOD:
            await key("Escape", 27)
            if not r["opts"]:
                why = f"“{r['empty']}”" if r.get("empty") else "no option list appeared"
                return ActionResult(error=f"Searched “{typed or value}” but {why}. Try a shorter or different search word "
                                          "(search=...), or click the dropdown to see it, then call choose_option again.")
            names = ", ".join(f"“{o['t']}”" for o in r["opts"][:25])
            return ActionResult(error=f"No option close to “{value}”. Showing now: {names}. Call choose_option again with "
                                      "the exact text of the right option, or a different search word.")

        chosen = r["opts"][i]["t"]
        await click_option(i)
        await asyncio.sleep(0.6)
        st = await js("shown") or {}
        if not confirmed(chosen, st.get("shown", "")):
            again = await js("options") or {"opts": []}
            j = next((k for k, o in enumerate(again["opts"]) if o["t"] == chosen), -1)
            if j >= 0:
                await js("synthetic", j)                                # the list is still open: the click missed
                await asyncio.sleep(0.6)
                st = await js("shown") or {}
        shown = st.get("shown", "")
        if confirmed(chosen, shown):
            return ActionResult(extracted_content=f"Chose “{chosen}”. The field now shows “{shown[:90]}”.")
        return ActionResult(extracted_content=f"Clicked “{chosen}”, but the field shows “{shown[:90]}”. Look at the field once: "
                                              "if it is not set, open it and click the option yourself.")
    except Exception as exc:
        return ActionResult(error=f"Dropdown {index}: {str(exc)[:160]}")


def _build_tools(profile: Optional[dict] = None) -> Any:
    from browser_use import ActionResult, Controller
    controller = Controller()

    @controller.action("Wait for a security check (Cloudflare 'Just a moment', Turnstile, 'I'm not a robot' box) to clear; "
                       "clicks the checkbox once if there is one. Use this BEFORE reporting CAPTCHA_DETECTED.")
    async def wait_for_human_check(browser_session, max_seconds: int = 25) -> ActionResult:
        return await _wait_for_human_check(browser_session, max_seconds)

    @controller.action("Fill the basic identity fields of the application form (first / last / full name, email, phone with "
                       "its country code, LinkedIn, GitHub, portfolio) in one go. Use it once when a form first appears, "
                       "then fill the remaining fields.")
    async def prefill_basic_fields(browser_session) -> ActionResult:
        return await _prefill(browser_session, profile or {})

    @controller.action("Pick an option in ANY dropdown, select, combobox or autocomplete (country, phone country code / flag "
                       "picker, location, college, degree, notice period, 'how did you hear'…). Give the dropdown's index "
                       "and the value you want (e.g. value='India', value='+91', value='Bachelor of Technology'); optional "
                       "search = a shorter word to type into its search box (e.g. 'CVR' for a college). It opens the list, "
                       "types, WAITS for the options to load, clicks the best match and checks the field shows it.")
    async def choose_option(index: int, value: str, browser_session, search: str = "", wait_seconds: float = 8) -> ActionResult:
        return await _choose_option(browser_session, index, value, search, wait_seconds)

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
_CODE_COUNTRY = {"+91": "India", "+1": "United States", "+44": "United Kingdom", "+65": "Singapore",
                 "+971": "United Arab Emirates", "+49": "Germany", "+61": "Australia"}
_ISO = {"+91": "in", "+1": "us", "+44": "gb", "+65": "sg", "+971": "ae", "+49": "de", "+61": "au"}
_COUNTRY_ALIASES = {"india": ["india", "bharat", "ind", "in"], "united states": ["united states of america", "usa", "us"],
                    "united kingdom": ["uk", "great britain", "gb"], "united arab emirates": ["uae", "ae"]}


def prefs_country(profile: dict) -> str:
    return ((profile.get("preferences") or {}).get("home_country") or "").strip()


def home_country(profile: dict) -> str:
    """The country set in preferences; else the one the phone's '+code' names; else India (who this app is for)."""
    country = prefs_country(profile)
    if country:
        return country
    m = re.match(r"\s*(?:\+|00)\s*(\d{1,3})", profile.get("phone") or "")
    if m:
        for code in (m.group(1)[:n] for n in (3, 2, 1)):
            if "+" + code in _CODE_COUNTRY:
                return _CODE_COUNTRY["+" + code]
    return "India"


def split_phone(phone: str, country: str = "India") -> tuple[str, str]:
    """'+91 80747 49058' → ('+91', '8074749058'); '08074749058' / '918074749058' with India → ('+91', '8074749058')."""
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
    code = _CALLING_CODES.get((country or "India").lower(), "")
    if code == "+91":                       # Indian mobiles: 10 digits starting 6-9, never a leading 0 or a doubled 91
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        digits = digits.lstrip("0") if len(digits) == 11 else digits
    return code, digits


def name_parts(profile: dict) -> tuple[str, str, str]:
    """(first name, last name, full name). An answer saved for "First name" / "Last name" wins. Otherwise the LAST word is
    the last name and everything before it the first name ("Vamsi Krishna Kakarla" → "Vamsi Krishna" + "Kakarla"); leading
    initials as in "K. Vamsi Krishna" are the family initial, so they become the last name only when one word is left."""
    full = re.sub(r"\s+", " ", (profile.get("name") or "")).strip()
    saved = {re.sub(r"[^a-z]", "", k.lower()): str(v).strip()
             for k, v in (((profile.get("qa_memory") or {}).get("custom_answers")) or {}).items() if v}
    first, last = saved.get("firstname", ""), saved.get("lastname", "") or saved.get("surname", "")
    words = full.split()
    initials = []
    while len(words) > 1 and re.fullmatch(r"[A-Za-z]\.?", words[0]):
        initials.append(words.pop(0))
    if len(words) == 1:
        auto_first, auto_last = words[0], " ".join(initials)
    else:
        auto_first, auto_last = " ".join(words[:-1]), (words[-1] if words else "")
    return first or auto_first, last or auto_last, full


# Which site a link belongs to, by its address — never by the box it was typed into on the profile.
_LINK_SITES = [("linkedin", "linkedin.com"), ("github", "github.com"), ("gitlab", "gitlab.com"), ("twitter", "twitter.com"),
               ("twitter", "x.com"), ("kaggle", "kaggle.com"), ("leetcode", "leetcode.com"), ("medium", "medium.com"),
               ("behance", "behance.net"), ("dribbble", "dribbble.com"), ("stackoverflow", "stackoverflow.com"),
               ("scholar", "scholar.google.")]


def _link_site(url: str) -> str:
    host = _host(url if "://" in url else "https://" + url).lower().removeprefix("www.")
    for site, domain in _LINK_SITES:
        if host == domain or host.endswith("." + domain) or (domain.endswith(".") and host.startswith(domain)):
            return site
    return ""


def profile_links(profile: dict) -> dict[str, str]:
    """{'linkedin': …, 'github': …, 'portfolio': …, 'twitter': …} sorted by domain, so a GitHub address saved in the
    portfolio box still goes only to GitHub fields, and a portfolio is never a LinkedIn / GitHub / social profile."""
    out: dict[str, str] = {}
    cands = [("portfolio", profile.get("portfolio")), ("linkedin", profile.get("linkedin")), ("github", profile.get("github"))]
    cands += [((l.get("label") or "").lower(), l.get("url")) for l in profile.get("links") or [] if isinstance(l, dict)]
    for hint, url in cands:
        url = (url or "").strip()
        if not url:
            continue
        site = _link_site(url)
        if not site:
            if hint in ("linkedin", "github"):
                continue                       # not a linkedin.com / github.com address: don't trust it for that box
            site = "portfolio"
        out.setdefault(site, url)
    return out


def _profile_block(profile: dict) -> str:
    edu = "\n".join(
        f"  • {ed.get('degree', '')} ({ed.get('start', '')} – {ed.get('end', '')})"
        + f"\n    - College / school attended: {ed.get('institution') or '(not given)'}"
        + f"\n    - Affiliated / degree-awarding university: {ed.get('university') or '(not given — same as the college, or not stated)'}"
        + (f"\n    - Grade: {ed.get('grade')}" if ed.get("grade") else "")
        for ed in profile.get("education", [])) or "  (Not provided)"
    country = home_country(profile)
    code, national = split_phone(profile.get("phone", ""), country)
    first, last, full = name_parts(profile)
    links = profile_links(profile)
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
- First name (given name): {first}
- Last name (surname / family name): {last or first + '  (only one name — repeat it if a last name is required)'}
- Full name: {full}
- Email: {profile.get('email', '')}
- Phone country code: {code or '(unknown)'}{f' ({_CODE_COUNTRY[code]})' if code in _CODE_COUNTRY else ''}
- Phone number WITHOUT country code: {national or profile.get('phone', '')}{'  (10-digit Indian mobile)' if code == '+91' else ''}
- Phone (full, international): {(code + ' ' + national).strip() if national else profile.get('phone', '')}
- Current location: {profile.get('location', '')}
- Home country: {country}
- Languages: {', '.join(langs) if isinstance(langs, list) else langs}
- LinkedIn URL (only for LinkedIn fields): {links.get('linkedin') or '(none — leave LinkedIn fields empty)'}
- GitHub URL (only for GitHub / code fields): {links.get('github') or '(none)'}
- Portfolio / personal website: {links.get('portfolio') or '(none — use the GitHub URL if a portfolio/website is required)'}{links_block}
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

NAME RULES:
- "First name" / "Given name" → the FIRST NAME above. "Last name" / "Surname" / "Family name" → the LAST NAME above.
  "Full name" / "Name" / "Legal name" → the FULL NAME. Never put the full name in a first-name box, never swap them.
- "Middle name" → leave empty. "Preferred name" → the first name.

LINK / URL RULES (each link goes ONLY in its own box):
- LinkedIn box → only the LinkedIn URL (linkedin.com). GitHub box → only the GitHub URL (github.com).
- Portfolio / Personal website / Website box → the portfolio URL (if none and the box is required, the GitHub URL).
- Twitter / X, Facebook, Instagram, Kaggle, Medium, Behance or any other site's box → only a link of THAT site from
  "Other links"; if there is none, leave it empty. Never put the LinkedIn or GitHub URL in another site's box.
- "Any other link" / "Additional links" → the portfolio or a project link, not LinkedIn again.

DROPDOWN / SELECT FIELD RULES:
- For EVERY dropdown, select, combobox, autocomplete or search-as-you-type box (country, phone country code / flag,
  city, college, degree, notice period, gender, "how did you hear"…) use `choose_option` with the field's index and the
  value you want. It opens the list, types the search, WAITS for the options to finish loading, clicks the matching
  option and tells you what the field shows. Do NOT type into a dropdown and click an option yourself.
- If choose_option lists the options instead, call it again with the exact option text (or a shorter `search` word).
- Country fields → the home country above (India → "India"). Never pick "Indiana", "Indian Ocean…" or another country.
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
  part, e.g. choose_option(value="CVR College of Engineering", search="CVR")), and pick the matching one. Try one
  short variant or common abbreviation if nothing matches (e.g. "JNTU" for "Jawaharlal Nehru Technological University").
  Only if it is truly not in the list, choose "Other" / "Not listed" and type the full name in the text box that appears.
  Never pick a different college or the university in place of the college.

PHONE RULES (Indian numbers: country code +91, then a 10-digit mobile number):
- `prefill_basic_fields` usually sets the phone and its country code already — read its result first.
- If the form has a SEPARATE country-code picker or prefix box (a flag, "+1" dropdown, "Country code" field), set it with
  `choose_option` (value="+91", or the country name "India") and type ONLY the 10-digit number WITHOUT the code.
- If the field already shows a prefix such as "+91" inside or beside the input, type only the 10-digit number, with
  clear=false if the "+91" is part of the box's own text.
- If it is a single plain phone field with no country code shown, type the full international number ("+91 98xxxxxxxx").
- Never type the country code twice (no "+91 +91…" or "9191…"), no leading 0 before the number, never "+1" for an Indian number.

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
