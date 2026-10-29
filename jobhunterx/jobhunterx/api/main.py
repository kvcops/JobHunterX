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
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from jobhunterx import auth, storage
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
    await auth.init()                                              # prod mode: users table + admin from .env
    from jobhunterx.config import capacity
    capacity.apply_thread_pool()
    log.info("capacity", mode="prod" if settings.prod else "local", web_workers=1, **capacity.plan())
    from jobhunterx.discovery import ats_index
    ats_index.ensure_background()        # today's India postings from employers' own boards, refreshed in the background
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
    # check watchlist companies' own job boards every few hours while the app runs
    from jobhunterx.api.routes import emit as api_emit
    from jobhunterx.config import auth_ctx
    from jobhunterx.services.watcher import watcher
    # prod mode: the background checks run as the admin (their profile, the server's keys); users press "Check now"
    admin = await auth.admin_user() if settings.prod else None
    ctx_token = auth_ctx.set_current(admin) if admin else None
    watcher.start(api_emit)
    if ctx_token is not None:
        auth_ctx.reset(ctx_token)
    # the office's dialogue bank: AI writes conversations in batches every hour or two (none while a search runs)
    from jobhunterx.services import office
    office.start_refills()

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
        from jobhunterx.config.database import close_pool
        try:
            await close_pool()
        except Exception:
            pass
        log.info("shutting_down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

_PROD = get_settings().prod
app = FastAPI(
    title="JobHunterX",
    description="Career Intelligence & Application Agent",
    version="0.1.0",
    lifespan=lifespan,
    # prod mode: no Swagger / ReDoc / OpenAPI schema at all (the login gate would also send them to /login)
    docs_url=None if _PROD else "/docs",
    redoc_url=None if _PROD else "/redoc",
    openapi_url=None if _PROD else "/openapi.json",
)


def _csv(value: str) -> list[str]:
    return [x.strip().rstrip("/") for x in (value or "").split(",") if x.strip()]


# Without CORS_ORIGINS: only the app's own origin (and localhost) may call the API, as before.
def _allowed_origins() -> list[str]:
    st = get_settings()
    hosts = {st.host, "127.0.0.1", "localhost"}
    return [f"http://{h}:{st.port}" for h in hosts] + _csv(st.cors_origins)


def _cors_options() -> dict:
    st = get_settings()
    creds = st.cors_allow_credentials
    if creds is None:
        creds = bool(_csv(st.cors_origins)) and st.prod       # the login cookie must travel with cross-site calls
    return {"allow_origins": _allowed_origins(), "allow_credentials": creds,
            "allow_methods": _csv(st.cors_methods) or ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "allow_headers": _csv(st.cors_headers) or ["Content-Type"]}


# Responses over 1 KB are gzipped (the 3D office's three.js shrinks from ~690 KB to ~170 KB on the wire).
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
class PinPerson:
    """Fix the open profile for each request (after the login gate knows who it is) — see storage.pin_person."""

    def __init__(self, app_):
        self.app = app_

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not (scope.get("path") or "").startswith("/api/"):
            await self.app(scope, receive, send)
            return
        token = storage.pin_person(storage.active_person())
        try:
            await self.app(scope, receive, send)
        finally:
            storage._pinned.reset(token)


app.add_middleware(PinPerson)
# The login gate runs inside CORS (so preflight requests are answered) and before everything else.
app.add_middleware(auth.AuthGate)
app.add_middleware(CORSMiddleware, **_cors_options())

def _local_host_ok(host: str) -> bool:
    """Desktop app: only requests addressed to this computer by name. A web page that points its own domain at
    127.0.0.1 (DNS rebinding) sends its domain in Host, so it never reaches the API."""
    if not get_settings().desktop:
        return True
    name = (host or "").rsplit(":", 1)[0].strip("[]").lower()
    return name in ("127.0.0.1", "localhost", "::1")


@app.middleware("http")
async def _desktop_hosts_only(request: Request, call_next):
    if not _local_host_ok(request.headers.get("host", "")):
        return _error(403, "This address is not allowed.")
    return await call_next(request)


@app.middleware("http")
async def _block_cross_site_writes(request: Request, call_next):
    """CSRF guard: browsers attach Origin to cross-site POST/PUT/PATCH/DELETE (including plain
    form posts that CORS does not block). Only our own origin may change state."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host", "") and origin not in _allowed_origins():
            return _error(403, "Cross-site request blocked.")
    return await call_next(request)


_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "bad_request", 409: "conflict",
          413: "payload_too_large", 422: "validation_error", 429: "too_many_requests", 502: "upstream_error"}


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
app.include_router(auth.router)
app.include_router(router)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Liveness for start scripts and hosting health checks (no login needed, no data)."""
    return {"ok": True}


@app.get("/signup", include_in_schema=False)
async def signup_page():
    if not auth.signup_open():
        return RedirectResponse("/login" if auth.enabled() else "/", status_code=303)
    return FileResponse(str(_web_dir / "signup.html"), headers={"Cache-Control": "no-store"})


@app.get("/login", include_in_schema=False)
async def login_page():
    if not auth.enabled():
        return RedirectResponse("/", status_code=303)     # no login on this server
    return FileResponse(str(_web_dir / "login.html"), headers={"Cache-Control": "no-store"})


def _ws_origin_ok(websocket: WebSocket) -> bool:
    """Block cross-site WebSocket hijacking: browsers always send Origin; it must be ours."""
    if not _local_host_ok(websocket.headers.get("host", "")):
        return False
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


# Static files (frontend) — mounted last so API routes take priority
_web_dir = Path(__file__).resolve().parent.parent / "web"


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
    from jobhunterx.api.ws import conn_meta
    await websocket.accept()
    await live_view.add_client(websocket, meta=conn_meta(websocket))
    try:
        while True:
            try:
                msg = json.loads(await websocket.receive_text())
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue                     # input goes only to this user's own browser (ba.current_session is per user)
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


@app.websocket("/ws/scout")
async def scout_websocket(websocket: WebSocket):
    """Watch-only stream of the Company Scout's browser (no input: the scout never needs a hand)."""
    if not _ws_origin_ok(websocket):
        await websocket.close(code=1008)
        return
    from jobhunterx.agents import live_view
    from jobhunterx.api.ws import conn_meta
    await websocket.accept()
    await live_view.add_client(websocket, "scout", meta=conn_meta(websocket))
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        log.debug("scout_ws_error", error=str(exc)[:160])
    finally:
        live_view.remove_client(websocket, "scout")


# JobHunterX has no service worker. A browser that once ran another web app on this address keeps asking for that
# app's /sw.js (a 404 every page load); this one removes itself, so the browser drops the leftover worker for good.
_SW_UNREGISTER = """self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.registration.unregister()));
"""


@app.get("/sw.js", include_in_schema=False)
@app.get("/service-worker.js", include_in_schema=False)
async def leftover_service_worker():
    from fastapi.responses import Response
    return Response(_SW_UNREGISTER, media_type="application/javascript", headers={"Cache-Control": "no-store"})


class _FreshStatic(StaticFiles):
    """App code is revalidated on every load (cheap 304s), so an update shows without a hard refresh."""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if path.replace("\\", "/").startswith(("vendor/", "assets/")):     # Windows paths use backslashes
            # third-party libraries, fonts, the robot model and icons change only with a release: a week in the cache
            resp.headers["Cache-Control"] = "public, max-age=604800"
        elif path == "" or path.endswith((".js", ".css", ".html")) or path in (".", "index.html"):
            resp.headers["Cache-Control"] = "no-cache"
        return resp


if _web_dir.exists():
    app.mount("/", _FreshStatic(directory=str(_web_dir), html=True), name="static")


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main():
    """Run the server from command line."""
    import uvicorn

    settings = get_settings()
    from jobhunterx.config import capacity
    capacity.limit_malloc_arenas()       # Linux: fewer memory pools per thread, so RSS stays low
    is_reload = "--reload" in sys.argv
    tls = {"ssl_certfile": settings.ssl_certfile, "ssl_keyfile": settings.ssl_keyfile} if settings.ssl_certfile else {}
    reload = is_reload or (not settings.prod and sys.platform != "win32")   # never auto-reload a production server
    try:
        uvicorn.run(
            "jobhunterx.api.main:app",
            host=settings.host,
            port=settings.port,
            # one process on purpose: searches, live updates and the browser live in its memory (see config/capacity.py)
            workers=1,
            reload=reload,
            log_level=settings.log_level.lower(),
            proxy_headers=True,
            forwarded_allow_ips=settings.forwarded_allow_ips or ("*" if settings.prod else "127.0.0.1"),
            server_header=not settings.prod,
            timeout_keep_alive=15,           # idle keep-alive connections are closed after 15 s (memory, slow clients)
            timeout_graceful_shutdown=10,
            ws_max_size=1 << 20,             # the app's own WebSocket messages are tiny: refuse anything over 1 MB
            h11_max_incomplete_event_size=64 * 1024,   # cap on request headers held in memory
            **tls,                           # TLS directly from uvicorn when SSL_CERTFILE / SSL_KEYFILE are set
        )
    except (KeyboardInterrupt, SystemExit):
        pass



if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
