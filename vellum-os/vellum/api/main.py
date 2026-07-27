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

# Monkeypatch legacy langchain_community import for scrapegraphai compatibility
try:
    import langchain_community.chat_models
    from langchain_ollama import ChatOllama
    langchain_community.chat_models.ChatOllama = ChatOllama
    sys.modules['langchain_community.chat_models.ChatOllama'] = ChatOllama
except Exception:
    pass

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vellum.config.logging import setup_logging, get_logger
from vellum.config.settings import get_settings
from vellum.config.database import set_db_path, init_db
from vellum.api.routes import router
from vellum.api.ws import manager


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

    log.info("vellum_os_ready", host=settings.host, port=settings.port)
    yield
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
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
