"""
Kuro OS — FastAPI Application Entry Point

Initialises database, logging, and serves the API + WebSocket + static frontend.
"""

from __future__ import annotations

# Windows: Set ProactorEventLoop policy by default
import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



# Silence legacy langchain_community deprecation warnings on startup
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import langchain_community.chat_models
    from langchain_ollama import ChatOllama
    langchain_community.chat_models.ChatOllama = ChatOllama
    sys.modules['langchain_community.chat_models.ChatOllama'] = ChatOllama
except Exception:
    pass



import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kuro.config.logging import setup_logging, get_logger
from kuro.config.settings import get_settings
from kuro.config.database import set_db_path, init_db
from kuro.api.routes import router
from kuro.api.ws import manager

log = get_logger("main")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()

    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        json_output=os.getenv("VELLUM_JSON_LOG", "").lower() == "true",
    )
    log = get_logger("main")
    log.info("starting_kuro_os", providers=settings.available_providers)

    # Ensure API keys are in env for litellm
    if settings.google_api_key:
        os.environ.setdefault("GEMINI_API_KEY", settings.google_api_key)
    if settings.groq_api_key:
        os.environ.setdefault("GROQ_API_KEY", settings.groq_api_key)
    if settings.mistral_api_key:
        os.environ.setdefault("MISTRAL_API_KEY", settings.mistral_api_key)

    # Init database
    set_db_path(str(settings.db_full_path))
    await init_db()

    # Ensure directories
    settings.cache_full_path
    settings.screenshots_full_path

    # Start screencast manager task
    screencast_mgr_task = asyncio.create_task(_screencast_manager())

    log.info("kuro_os_ready", host=settings.host, port=settings.port)
    yield
    
    # Clean up screencast manager on shutdown
    screencast_mgr_task.cancel()
    try:
        await screencast_mgr_task
    except asyncio.CancelledError:
        pass
    log.info("shutting_down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Kuro OS",
    description="Career Intelligence & Application Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Could handle client commands here in the future
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Browser CDP Live Stream WebSocket
# ---------------------------------------------------------------------------

_browser_ws_clients: list[WebSocket] = []
_browser_screencast_task: asyncio.Task | None = None
_browser_screencast_running = False


async def _safe_call(obj: Any, fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Safely execute a function or coroutine on the object's owning event loop across threads."""
    obj_loop = None
    try:
        client = getattr(obj, "_client", None)
        if client is not None:
            loop = getattr(client, "_loop", None)
            if loop is not None and loop.is_running():
                obj_loop = loop
    except Exception:
        pass
    if obj_loop is None:
        try:
            loop = getattr(obj, "_loop", None)
            if loop is not None and loop.is_running():
                obj_loop = loop
        except Exception:
            pass

    current_loop = asyncio.get_running_loop()
    if obj_loop is None or obj_loop is current_loop:
        res = fn(*args, **kwargs) if callable(fn) else fn
        if asyncio.iscoroutine(res):
            return await res
        return res

    async def _runner():
        coro = fn(*args, **kwargs) if callable(fn) else fn
        if asyncio.iscoroutine(coro):
            return await coro
        return coro

    fut = asyncio.run_coroutine_threadsafe(_runner(), obj_loop)
    return await asyncio.wrap_future(fut)



async def _is_page_usable(page: Any) -> bool:
    """Check whether a Playwright page is still attached and usable."""
    if page is None:
        return False
    try:
        closed = getattr(page, "is_closed", None)
        if callable(closed):
            try:
                if closed():
                    return False
            except Exception:
                return False
    except Exception:
        return False
    try:
        client = getattr(page, "_client", None)
        if client is not None:
            if getattr(client, "_disconnected", False):
                return False
            connection = getattr(client, "_connection", None)
            if connection is not None and (
                getattr(connection, "_closed", False)
                or getattr(connection, "_disconnected", False)
            ):
                return False
    except Exception:
        return False
    return True


async def _screencast_broadcaster(page: Any):
    """Stream CDP screenshots to all connected browser WS clients.

    Resilient to page navigations, tab closures, and detached targets:
    - Validates page usability before each screenshot attempt.
    - On failure, tries to recover a fresh page from the same browser session
      before giving up, so that navigations and reloads cause minimal frame loss.
    - Falls back to the manager watchdog only when recovery is impossible.
    """
    global _browser_screencast_running
    _browser_screencast_running = True
    current_page = page
    consecutive_failures = 0
    max_recovery_attempts = 3

    while _browser_ws_clients and _browser_screencast_running:
        try:
            # Validate page is still attached before screenshot
            if not await _is_page_usable(current_page):
                log.debug("screencast_page_detached", msg="Page no longer usable, attempting recovery")
                recovered = await _try_recover_page(current_page)
                if recovered:
                    current_page = recovered
                    consecutive_failures = 0
                    log.info("screencast_page_recovered", msg="Got fresh page after detachment")
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_recovery_attempts:
                        log.debug("screencast_ended", msg="No usable page available, ending screencast")
                        break
                    await asyncio.sleep(0.3)
                    continue

            # Use a short timeout to detect browser hang early instead of
            # waiting for the default 60s CDP timeout.
            # Use _safe_call with a lambda so the screenshot call itself is evaluated on current_page's owning loop.
            try:
                b64_data = await asyncio.wait_for(
                    _safe_call(current_page, lambda: current_page.screenshot(format="jpeg", quality=40)),
                    timeout=8.0,
                )
            except asyncio.TimeoutError:
                consecutive_failures += 1
                log.warning(
                    "screencast_screenshot_timeout",
                    attempt=consecutive_failures,
                    msg="Screenshot timed out in 8s — browser may be unresponsive",
                )
                if consecutive_failures >= max_recovery_attempts:
                    break
                # Try to recover from a hung browser
                recovered = await _try_recover_page(current_page)
                if recovered:
                    current_page = recovered
                    consecutive_failures = 0
                    log.info("screencast_page_recovered_after_timeout")
                continue

            consecutive_failures = 0
            msg = json.dumps({
                "type": "frame",
                "data": b64_data,
                "width": 1280,
                "height": 720,
            })
            dead = []
            for ws in list(_browser_ws_clients):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in _browser_ws_clients:
                    _browser_ws_clients.remove(ws)
        except Exception as exc:
            consecutive_failures += 1
            err_str = str(exc).lower()
            # Clean session shutdown / CDP detached / page closed — try recovery or exit gracefully
            is_stopped = (
                "client is not started" in err_str
                or "browser has been closed" in err_str
                or "context has been closed" in err_str
                or "target closed" in err_str
                or "session closed" in err_str
                or "connection closed" in err_str
                or "event loop is closed" in err_str
            )
            is_detached = (
                is_stopped
                or "not attached" in err_str
                or "-32000" in err_str
                or "execution context was destroyed" in err_str
                or "did not respond within" in err_str
                or "unresponsive" in err_str
                or "silent websocket" in err_str
                or "container crashed" in err_str
            )
            if is_detached and consecutive_failures <= max_recovery_attempts:
                log.debug("screencast_frame_recovery", error=str(exc)[:120], attempt=consecutive_failures)
                recovered = await _try_recover_page(current_page)
                if recovered:
                    current_page = recovered
                    consecutive_failures = 0
                    log.info("screencast_page_recovered_after_error")
                    continue
                elif is_stopped:
                    log.debug("screencast_session_stopped", msg="Browser session closed cleanly")
                    break
            log.warning("screencast_frame_error", error=str(exc)[:200])
            if consecutive_failures >= max_recovery_attempts:
                break
        await asyncio.sleep(0.15)

    _browser_screencast_running = False


async def _try_recover_page(old_page: Any) -> Any:
    """Attempt to obtain a fresh page from the browser session after detachment.

    Tries multiple strategies:
      1. Get current page from the active browser session (handles navigation).
      2. Check existing pages in the browser context (handles tab switches).
    Returns a usable page or None.
    """
    from kuro.agents import browser_agent as ba
    try:
        sess = ba.get_active_browser_session()
        if sess is None:
            return None
        try:
            page = await _safe_call(sess, lambda: sess.get_current_page())
            if page and await _is_page_usable(page) and page is not old_page:
                return page
        except Exception:
            pass
        # Fallback: try to find any usable page in the browser context
        try:
            browser_obj = getattr(sess, "browser", None)
            if browser_obj is not None:
                contexts = getattr(browser_obj, "contexts", [])
                for ctx in contexts:
                    pages = getattr(ctx, "pages", [])
                    for p in pages:
                        if await _is_page_usable(p):
                            return p
        except Exception:
            pass
    except Exception:
        pass
    return None


async def _screencast_manager():
    """Periodically check for the active page and start screencasting if needed.

    Detects page changes within the same session (navigations, reloads) and
    restarts the screencast with the fresh page to avoid prolonged frame gaps.
    """
    global _browser_screencast_task, _browser_screencast_running
    from kuro.agents import browser_agent as ba
    
    last_session = None
    last_page_id = None
    while True:
        try:
            if _browser_ws_clients:
                sess = ba.get_active_browser_session()
                if sess:
                    try:
                        page = await _safe_call(sess, lambda: sess.get_current_page())
                    except Exception:
                        page = None

                    if page:
                        # Detect page change (navigation/reload/new tab) even
                        # within the same session by comparing the object id.
                        page_id = id(page) if await _is_page_usable(page) else None
                        needs_restart = (
                            sess != last_session
                            or page_id != last_page_id
                            or not _browser_screencast_running
                        )
                        if needs_restart:
                            _stop_screencast()
                            last_session = sess
                            last_page_id = page_id
                            _browser_screencast_task = asyncio.create_task(
                                _screencast_broadcaster(page)
                            )
                    else:
                        if _browser_screencast_running:
                            _stop_screencast()
                            last_session = None
                            last_page_id = None
                else:
                    if _browser_screencast_running:
                        _stop_screencast()
                    last_session = None
                    last_page_id = None
            else:
                if _browser_screencast_running:
                    _stop_screencast()
                last_session = None
                last_page_id = None
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.warning("screencast_manager_error", error=str(exc))
        await asyncio.sleep(0.5)


@app.websocket("/ws/browser")
async def browser_websocket(websocket: WebSocket):
    """CDP live-stream WebSocket: streams browser frames + receives input events."""
    await websocket.accept()
    _browser_ws_clients.append(websocket)
    log.info("browser_ws_client_connected", total=len(_browser_ws_clients))

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Handle input events by dynamically getting the active page
            try:
                from kuro.agents import browser_agent as ba
                current_page = await ba.get_active_page()
            except Exception:
                current_page = None

            if current_page and await _is_page_usable(current_page):
                await _forward_input_event(current_page, msg)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("browser_ws_error", error=str(exc))
    finally:
        if websocket in _browser_ws_clients:
            _browser_ws_clients.remove(websocket)
        log.info("browser_ws_client_disconnected", total=len(_browser_ws_clients))
        # If no clients left, stop screencast
        if not _browser_ws_clients:
            _stop_screencast()


def _stop_screencast():
    """Stop the screencast broadcaster."""
    global _browser_screencast_running, _browser_screencast_task
    _browser_screencast_running = False
    if _browser_screencast_task and not _browser_screencast_task.done():
        _browser_screencast_task.cancel()
        _browser_screencast_task = None


async def _forward_input_event(page: Any, msg: dict):
    """Forward mouse/keyboard input events from the client to the browser page."""
    event_type = msg.get("type")

    # Guard: skip input if page is detached or closed
    if not await _is_page_usable(page):
        log.debug("input_forward_skipped_detached", type=event_type)
        return

    try:
        if event_type == "mouse":
            action = msg.get("action")
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            button = msg.get("button", 0)
            pw_button = "left" if button == 0 else "right" if button == 2 else "middle"

            mouse = page.mouse
            if action == "click":
                await _safe_call(page, lambda: mouse.click(x, y, button=pw_button))
            elif action == "down":
                await _safe_call(page, lambda: mouse.down(button=pw_button))
            elif action == "up":
                await _safe_call(page, lambda: mouse.up(button=pw_button))
            elif action == "move":
                await _safe_call(page, lambda: mouse.move(x, y))
            elif action == "dblclick":
                await _safe_call(page, lambda: mouse.click(x, y, button=pw_button, click_count=2))

        elif event_type == "wheel":
            delta_x = msg.get("deltaX", 0)
            delta_y = msg.get("deltaY", 0)
            mouse = page.mouse
            await _safe_call(page, lambda: mouse.scroll(delta_x=delta_x, delta_y=delta_y))

        elif event_type == "keyboard":
            action = msg.get("action")
            key = msg.get("key", "")
            code = msg.get("code", "")
            text = msg.get("text", "")

            keyboard = page.keyboard
            if action == "keyDown":
                await _safe_call(page, lambda: keyboard.down(key))
                if text:
                    await _safe_call(page, lambda: keyboard.insert_text(text))
            elif action == "keyUp":
                await _safe_call(page, lambda: keyboard.up(key))

        elif event_type == "scroll":
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            delta_y = msg.get("deltaY", 0)
            mouse = page.mouse
            await _safe_call(page, lambda: mouse.scroll(x=x, y=y, delta_y=delta_y))

    except Exception as exc:
        log.warning("input_forward_error", error=str(exc), type=event_type)


# Static files (frontend) — mounted last so API routes take priority
_web_dir = Path(__file__).resolve().parent.parent / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="static")


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main():
    """Run the server from command line."""
    import uvicorn

    settings = get_settings()
    is_reload = "--reload" in sys.argv
    uvicorn.run(
        "kuro.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=is_reload if is_reload else (False if sys.platform == "win32" else True),
        log_level=settings.log_level.lower(),
    )



if __name__ == "__main__":
    main()
