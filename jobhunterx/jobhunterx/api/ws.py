"""
JobHunterX — WebSocket Manager

Broadcasts real-time agent events to connected UI clients.

Prod mode (login on): every connection belongs to one login, and an event goes only to the user
whose request (or background task started by it) produced it. Events with no user (server
background work) go to the admin. Without login every client gets every event, as before.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket

from jobhunterx.config import auth_ctx
from jobhunterx.config.logging import get_logger

log = get_logger("ws")


def conn_meta(websocket: WebSocket) -> dict:
    """Who opened this socket (set by the login gate in prod mode; empty otherwise)."""
    auth = (websocket.scope.get("state") or {}).get("auth") or {}
    user = auth_ctx.current()
    return {"user_id": auth.get("user_id"), "token_hash": auth.get("token_hash"), "expires": auth.get("expires") or 0.0,
            "is_admin": bool(user and user.is_admin)}


def may_receive(meta: dict, owner: Optional[str]) -> bool:
    """Should a client with `meta` get an event that belongs to user `owner`?"""
    if not meta.get("user_id"):
        return True                                   # local single-user app: everyone
    if meta.get("expires") and meta["expires"] < time.time():
        return False                                  # this login has ended
    return meta["user_id"] == owner if owner else meta.get("is_admin", False)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._meta: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._meta[websocket] = conn_meta(websocket)
        log.info("ws_client_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self._meta.pop(websocket, None)
        log.info("ws_client_disconnected", total=len(self.active_connections))

    async def broadcast(self, data: dict[str, Any]):
        """Send an event to the connected clients allowed to see it.

        Legacy browser-agent events ({agent, event_type, ...}) are wrapped as
        {type: "browser", data: <event>} per the v2 WebSocket contract.
        """
        if "type" not in data:
            data = {"type": "browser", "job_id": data.get("job_id"), "message": data.get("message", ""),
                    "data": data, "ts": datetime.now(timezone.utc).isoformat()}
        user = auth_ctx.current()
        owner = user.id if user else None
        message = json.dumps(data, default=str)
        disconnected = []
        for connection in list(self.active_connections):
            meta = self._meta.get(connection, {})
            if not may_receive(meta, owner):
                if meta.get("expires") and meta["expires"] < time.time():
                    disconnected.append(connection)
                continue
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            await self._close(conn)

    async def _close(self, conn: WebSocket, code: int = 4401) -> None:
        self.disconnect(conn)
        try:
            await conn.close(code=code)
        except Exception:
            pass

    async def close_for(self, user_id: Optional[str] = None, token_hash: Optional[str] = None, keep: Optional[str] = None):
        """Close the sockets of one login (logout) or of every login of a user (except `keep`)."""
        for conn, meta in list(self._meta.items()):
            if (token_hash and meta.get("token_hash") == token_hash) or \
                    (user_id and meta.get("user_id") == user_id and meta.get("token_hash") != keep):
                await self._close(conn)

    async def broadcast_event(self, event: dict):
        """Convenience wrapper for AgentEvent broadcasting."""
        await self.broadcast(event)

    def broadcast_threadsafe(self, data: dict[str, Any], main_loop=None):
        """Thread-safe broadcast for calls originating from background worker threads."""
        import asyncio
        if main_loop is None:
            try:
                main_loop = asyncio.get_event_loop()
            except Exception:
                return
        if main_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(data), main_loop)


# Singleton instance
manager = ConnectionManager()
