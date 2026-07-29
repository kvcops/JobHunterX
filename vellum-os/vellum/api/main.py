"""
Vellum OS — FastAPI Application Entry Point

Initialises database, logging, and serves the API + WebSocket + static frontend.
"""

from __future__ import annotations

# Windows: Force ProactorEventLoop for subprocess/Playwright compatibility.
# Must be set before ANY asyncio usage (including imports that trigger it).
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

from vellum.config.logging import setup_logging, get_logger
from vellum.config.settings import get_settings
from vellum.config.database import set_db_path, init_db
from vellum.api.routes import router
from vellum.api.ws import manager

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
    log.info("starting_vellum_os", providers=settings.available_providers)

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

    log.info("vellum_os_ready", host=settings.host, port=settings.port)
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
    title="Vellum OS",
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
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Browser CDP Live Stream WebSocket
# ---------------------------------------------------------------------------

_browser_ws_clients: list[WebSocket] = []
_browser_screencast_task: asyncio.Task | None = None
_browser_screencast_running = False


async def _screencast_broadcaster(page: Any):
    """Stream CDP screenshots to all connected browser WS clients."""
    global _browser_screencast_running
    _browser_screencast_running = True

    while _browser_ws_clients and _browser_screencast_running:
        try:
            # page is browser_use.actor.page.Page
            b64_data = await page.screenshot(format="jpeg", quality=40)
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
            log.warning("screencast_frame_error", error=str(exc))
            # Break loop if page is closed/destroyed
            break
        await asyncio.sleep(0.15)

    _browser_screencast_running = False


async def _screencast_manager():
    """Periodically check for the active page and start screencasting if needed."""
    global _browser_screencast_task, _browser_screencast_running
    from vellum.agents import browser_agent as ba
    
    last_session = None
    while True:
        try:
            if _browser_ws_clients:
                sess = ba.get_active_browser_session()
                if sess:
                    try:
                        page = await sess.get_current_page()
                    except Exception:
                        page = None
                    
                    if page:
                        if sess != last_session or not _browser_screencast_running:
                            _stop_screencast()
                            last_session = sess
                            _browser_screencast_task = asyncio.create_task(_screencast_broadcaster(page))
                    else:
                        if _browser_screencast_running:
                            _stop_screencast()
                            last_session = None
                else:
                    if _browser_screencast_running:
                        _stop_screencast()
                    last_session = None
            else:
                if _browser_screencast_running:
                    _stop_screencast()
                last_session = None
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
                from vellum.agents import browser_agent as ba
                current_page = await ba.get_active_page()
            except Exception:
                current_page = None

            if current_page:
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

    try:
        if event_type == "mouse":
            action = msg.get("action")
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            button = msg.get("button", 0)
            pw_button = "left" if button == 0 else "right" if button == 2 else "middle"

            mouse = await page.mouse
            if action == "click":
                await mouse.click(x, y, button=pw_button)
            elif action == "down":
                await mouse.down(button=pw_button)
            elif action == "up":
                await mouse.up(button=pw_button)
            elif action == "move":
                await mouse.move(x, y)
            elif action == "dblclick":
                await mouse.click(x, y, button=pw_button, click_count=2)

        elif event_type == "wheel":
            delta_x = msg.get("deltaX", 0)
            delta_y = msg.get("deltaY", 0)
            mouse = await page.mouse
            await mouse.scroll(delta_x=delta_x, delta_y=delta_y)

        elif event_type == "keyboard":
            action = msg.get("action")
            key = msg.get("key", "")
            code = msg.get("code", "")
            text = msg.get("text", "")

            session_id = await page._ensure_session()
            params = {
                "type": action,  # "keyDown" or "keyUp"
                "key": key,
                "code": code,
                "text": text,
            }
            if text:
                params["unmodifiedText"] = text
            await page._client.send.Input.dispatchKeyEvent(params, session_id=session_id)

        elif event_type == "scroll":
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            delta_y = msg.get("deltaY", 0)
            mouse = await page.mouse
            await mouse.scroll(x=x, y=y, delta_y=delta_y)

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
    uvicorn.run(
        "vellum.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False if sys.platform == "win32" else True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
