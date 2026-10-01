"""
JobHunterX — FastAPI Application Entry Point

Initialises database, logging, and serves the API + WebSocket + static frontend.
"""

from __future__ import annotations

import os
os.environ.setdefault("LITELLM_LOCAL_RESOURCES", "true")  # no remote cost-map fetch on import

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from jobhunterx import storage
from jobhunterx.api.routes import router
from jobhunterx.api.ws import manager
from jobhunterx.config.database import init_db, set_db_path
from jobhunterx.config.logging import get_logger, setup_logging
from jobhunterx.config.settings import get_settings

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
        json_output=os.getenv("JOBHUNTERX_JSON_LOG", "").lower() == "true",
    )
    log = get_logger("main")
    log.info("starting_jobhunterx", providers=settings.available_providers)

    # Ensure API keys are in env for litellm
    if settings.google_api_key:
        os.environ.setdefault("GEMINI_API_KEY", settings.google_api_key)
    if settings.groq_api_key:
        os.environ.setdefault("GROQ_API_KEY", settings.groq_api_key)
    if settings.mistral_api_key:
        os.environ.setdefault("MISTRAL_API_KEY", settings.mistral_api_key)

    # Init database (+ v2 migrations); runs left "running" by a dead process are marked failed
    set_db_path(str(settings.db_full_path))
    from jobhunterx import db_health
    from jobhunterx.config import app_state
    from jobhunterx.config import models as model_catalog
    pre = await db_health.preflight(str(settings.db_full_path))   # recover a damaged file before opening it
    if pre["status"] == "recovered":
        log.error("database_recovered", detail=pre["detail"])
    await init_db()                                                # create / migrate schema (idempotent)
    await app_state.load(str(settings.db_full_path))               # seed defaults, load preferences
    await storage.heal_active_person()
    try:
        health = await db_health.check(str(settings.db_full_path), repair=True)
        log.info("database_health", status=health["status"], schema=health["schema_version"], **health["counts"])
    except Exception as exc:          # a health check must never stop the app from starting
        log.warning("database_health_check_failed", error=str(exc)[:200])
    await storage.mark_interrupted_runs()
    await storage.mark_interrupted_apply_sessions()
    from jobhunterx.agents import live_view
    live_view.bind_main_loop(asyncio.get_running_loop())
    # learn which models each configured provider offers (non-blocking)
    asyncio.create_task(model_catalog.refresh_available())

    # Ensure directories
    settings.cache_full_path
    settings.screenshots_full_path

    log.info("jobhunterx_ready", host=settings.host, port=settings.port)
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        from jobhunterx.agents.browser_agent import stop_all_active_browsers
        try:
            await asyncio.wait_for(stop_all_active_browsers(), timeout=10)
        except (asyncio.TimeoutError, Exception):
            pass
        log.info("shutting_down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JobHunterX",
    description="Career Intelligence & Application Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# Local-first app: only the app's own origin (and localhost dev ports) may call the API.
def _allowed_origins() -> list[str]:
    st = get_settings()
    hosts = {st.host, "127.0.0.1", "localhost"}
    return [f"http://{h}:{st.port}" for h in hosts]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

@app.middleware("http")
async def _block_cross_site_writes(request: Request, call_next):
    """CSRF guard: browsers attach Origin to cross-site POST/PUT/PATCH/DELETE (including plain
    form posts that CORS does not block). Only our own origin may change state."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host", "") and origin not in _allowed_origins():
            return _error(403, "Cross-site request blocked.")
    return await call_next(request)


_CODES = {400: "bad_request", 403: "forbidden", 404: "not_found", 405: "bad_request", 409: "conflict", 413: "payload_too_large",
          422: "validation_error", 502: "upstream_error"}


def _error(status: int, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": _CODES.get(status, "internal_error" if status >= 500 else "bad_request"),
                                           "message": message, "details": details}})


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
    first = details[0] if details else {"loc": [], "msg": "Invalid request"}
    return _error(422, f"{'.'.join(str(x) for x in first['loc'][1:]) or 'request'}: {first['msg']}", details)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.error("unhandled_error", path=request.url.path, error=str(exc)[:300], exc_type=type(exc).__name__)
    return _error(500, "Something went wrong on the server. Please try again.")


# API routes
app.include_router(router)


def _ws_origin_ok(websocket: WebSocket) -> bool:
    """Block cross-site WebSocket hijacking: browsers always send Origin; it must be ours."""
    origin = websocket.headers.get("origin")
    if origin is None:
        return True   # non-browser client (tests, CLI)
    host = websocket.headers.get("host", "")
    return urlparse(origin).netloc == host or origin in _allowed_origins()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not _ws_origin_ok(websocket):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Live browser view (the auto-apply agent's browser, streamed into the app)
# ---------------------------------------------------------------------------

@app.websocket("/ws/browser")
async def browser_websocket(websocket: WebSocket):
    """Streams frames of the agent's browser and sends your clicks / keys back (only while you have control)."""
    if not _ws_origin_ok(websocket):
        await websocket.close(code=1008)
        return
    from jobhunterx.agents import browser_agent as ba
    from jobhunterx.agents import live_view
    await websocket.accept()
    await live_view.add_client(websocket)
    try:
        while True:
            try:
                msg = json.loads(await websocket.receive_text())
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("type") in ("mouse", "wheel", "keyboard", "paste"):
                await ba.forward_input(msg)
            elif msg.get("type") == "viewport":
                await ba.resize_view(msg.get("w"), msg.get("h"))
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        log.debug("browser_ws_error", error=str(exc)[:160])
    finally:
        live_view.remove_client(websocket)


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
    try:
        uvicorn.run(
            "jobhunterx.api.main:app",
            host=settings.host,
            port=settings.port,
            reload=is_reload if is_reload else (False if sys.platform == "win32" else True),
            log_level=settings.log_level.lower(),
        )
    except (KeyboardInterrupt, SystemExit):
        pass



if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
