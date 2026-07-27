"""
Vellum OS — WebSocket Manager

Broadcasts real-time agent events to connected UI clients.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from vellum.config.logging import get_logger

log = get_logger("ws")


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("ws_client_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        log.info("ws_client_disconnected", total=len(self.active_connections))

    async def broadcast(self, data: dict[str, Any]):
        """Send an event to all connected clients."""
        message = json.dumps(data, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_event(self, event: dict):
        """Convenience wrapper for AgentEvent broadcasting."""
        await self.broadcast(event)


# Singleton instance
manager = ConnectionManager()
