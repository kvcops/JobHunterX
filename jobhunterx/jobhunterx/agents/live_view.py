"""
Live view of the auto-apply browser inside the app (no separate Chrome window).

* Frames come from Chrome's own screencast (CDP Page.startScreencast), started on
  the browser worker's event loop — the same loop that owns the browser — so the
  agent and the stream never fight over the CDP connection.
* Frames, session updates and step events are handed to the server's event loop
  thread-safely and pushed to WebSocket clients.
* Mouse / keyboard input from the panel is sent back to the browser on the
  worker loop (only while the user has control).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from jobhunterx.config.logging import get_logger

log = get_logger("live_view")

_main_loop: Optional[asyncio.AbstractEventLoop] = None
_clients: set[Any] = set()
_latest_frame: Optional[str] = None          # last frame message (JSON) for late joiners
# The Company Scout's browser streams on its own channel, so it never mixes with the auto-apply view.
_scout_clients: set[Any] = set()
_scout_latest: Optional[str] = None
_frame_meta: dict[str, float] = {}           # deviceWidth / deviceHeight of the last frame
_panel: tuple[int, int] = (0, 0)             # size of the live-view area in the app (CSS px)

VIEWPORT_WIDTH = 1280                        # desktop layout for every site; the height follows the panel's shape


def set_panel(w: Any, h: Any) -> bool:
    """Remember the live-view area's size. True when the shape changed enough to resize the browser."""
    global _panel
    try:
        w, h = int(w), int(h)
    except (TypeError, ValueError):
        return False
    if w < 200 or h < 200:
        return False
    old = _panel
    _panel = (w, h)
    if not old[0]:
        return True
    return abs(old[1] / old[0] - h / w) > 0.04


def viewport_size() -> tuple[int, int]:
    """Browser viewport with the same shape as the panel, so the picture fills it edge to edge.

    The width stays a desktop width (sites switch to mobile layouts below ~1024px) but is kept
    close to the panel's width, so text in the live view is shown as large as possible.
    """
    w, h = _panel
    if not w:
        return VIEWPORT_WIDTH, 900
    width = max(1024, min(VIEWPORT_WIDTH, round(w * 1.25)))
    return width, max(600, min(1800, round(width * h / w)))


async def apply_viewport(browser_session: Any) -> None:
    """Resize the open browser to the panel's shape (runs on the worker loop)."""
    width, height = viewport_size()
    profile = getattr(browser_session, "browser_profile", None)
    try:
        if profile is not None and getattr(profile, "viewport", None) is not None:
            profile.viewport.width, profile.viewport.height = width, height     # new tabs get it too
    except Exception:
        pass
    cdp = await browser_session.get_or_create_cdp_session(focus=False)
    await cdp.cdp_client.send.Emulation.setDeviceMetricsOverride(
        params={"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False}, session_id=cdp.session_id)


def bind_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _on_main(coro) -> None:
    """Run a coroutine on the server loop from any thread."""
    if _main_loop is None or _main_loop.is_closed():
        coro.close()
        return
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is _main_loop:
        _main_loop.create_task(coro)
    else:
        asyncio.run_coroutine_threadsafe(coro, _main_loop)


def broadcast_event(event: dict) -> None:
    """Send an app event (search/apply/etc.) to the main /ws clients from any thread."""
    from jobhunterx.api.ws import manager as ws_manager
    _on_main(ws_manager.broadcast(event))


# ---------------------------------------------------------------------------- frames

async def _send_all(msg: str) -> None:
    dead = []
    for ws in list(_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


def publish_frame(data_b64: str, metadata: dict, channel: str = "apply") -> None:
    global _latest_frame, _scout_latest
    if channel == "scout":
        _scout_latest = json.dumps({"type": "frame", "data": data_b64, "w": metadata.get("deviceWidth"),
                                    "h": metadata.get("deviceHeight")})
        if _scout_clients:
            _on_main(_send_to(_scout_clients, _scout_latest))
        return
    _frame_meta.update({k: metadata.get(k) for k in ("deviceWidth", "deviceHeight") if metadata.get(k)})
    msg = json.dumps({"type": "frame", "data": data_b64, "w": _frame_meta.get("deviceWidth"), "h": _frame_meta.get("deviceHeight")})
    _latest_frame = msg
    if _clients:
        _on_main(_send_all(msg))


def clear_frame(channel: str = "apply") -> None:
    global _latest_frame, _scout_latest
    if channel == "scout":
        _scout_latest = None
        if _scout_clients:
            _on_main(_send_to(_scout_clients, json.dumps({"type": "idle"})))
        return
    _latest_frame = None
    if _clients:
        _on_main(_send_all(json.dumps({"type": "idle"})))


async def _send_to(clients: set[Any], msg: str) -> None:
    for ws in list(clients):
        try:
            await ws.send_text(msg)
        except Exception:
            clients.discard(ws)


async def add_client(ws: Any, channel: str = "apply") -> None:
    clients, latest = (_scout_clients, _scout_latest) if channel == "scout" else (_clients, _latest_frame)
    clients.add(ws)
    if latest:
        try:
            await ws.send_text(latest)
        except Exception:
            clients.discard(ws)


def remove_client(ws: Any, channel: str = "apply") -> None:
    (_scout_clients if channel == "scout" else _clients).discard(ws)


def frame_size() -> tuple[float, float]:
    return float(_frame_meta.get("deviceWidth") or 1280), float(_frame_meta.get("deviceHeight") or 800)


# ---------------------------------------------------------------------------- screencast (runs on the worker loop)

class Screencast:
    """Keeps a CDP screencast running on whichever tab the agent is focused on."""

    PARAMS = {"format": "jpeg", "quality": 62, "maxWidth": 1280, "maxHeight": 1600, "everyNthFrame": 1}

    def __init__(self, browser_session: Any, channel: str = "apply"):
        self.session = browser_session
        self.channel = channel
        self.sid: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._registered = False

    def _on_frame(self, event: dict, session_id: Optional[str] = None) -> None:
        if self.sid and session_id and session_id != self.sid:
            return
        try:
            publish_frame(event["data"], event.get("metadata") or {}, self.channel)
        finally:
            client = self.session.cdp_client
            asyncio.ensure_future(self._ack(client, event.get("sessionId"), session_id))

    @staticmethod
    async def _ack(client: Any, frame_session: Any, session_id: Optional[str]) -> None:
        try:
            await client.send.Page.screencastFrameAck(params={"sessionId": frame_session}, session_id=session_id)
        except Exception:
            pass

    async def _follow_focus(self) -> None:
        while True:
            try:
                if getattr(self.session, "_cdp_client_root", None) is not None:
                    if not self._registered:
                        self.session.cdp_client.register.Page.screencastFrame(self._on_frame)
                        self._registered = True
                    cdp = await self.session.get_or_create_cdp_session(focus=False)
                    if cdp.session_id != self.sid:
                        if self.sid:
                            try:
                                await self.session.cdp_client.send.Page.stopScreencast(session_id=self.sid)
                            except Exception:
                                pass
                        await cdp.cdp_client.send.Page.startScreencast(params=self.PARAMS, session_id=cdp.session_id)
                        self.sid = cdp.session_id
            except asyncio.CancelledError:
                raise
            except Exception as exc:    # tab closing / navigation in flight — retry on the next tick
                log.debug("screencast_follow_retry", error=str(exc)[:120])
                self.sid = None
            await asyncio.sleep(1.0)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.ensure_future(self._follow_focus())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self.sid:
            try:
                await self.session.cdp_client.send.Page.stopScreencast(session_id=self.sid)
            except Exception:
                pass
            self.sid = None


# ---------------------------------------------------------------------------- input (runs on the worker loop)

_SPECIAL_KEYS = {"Enter": 13, "Backspace": 8, "Tab": 9, "Escape": 27, "Delete": 46, "ArrowLeft": 37, "ArrowUp": 38,
                 "ArrowRight": 39, "ArrowDown": 40, "Home": 36, "End": 35, "PageUp": 33, "PageDown": 34, " ": 32}


async def dispatch_input(browser_session: Any, msg: dict) -> None:
    """Replay a mouse / wheel / key event from the panel into the focused tab."""
    cdp = await browser_session.get_or_create_cdp_session(focus=False)
    send = cdp.cdp_client.send
    sid = cdp.session_id
    w, h = frame_size()
    kind = msg.get("type")
    if kind in ("mouse", "wheel"):
        x = max(0.0, min(1.0, float(msg.get("fx", 0)))) * w
        y = max(0.0, min(1.0, float(msg.get("fy", 0)))) * h
        if kind == "wheel":
            await send.Input.dispatchMouseEvent(params={"type": "mouseWheel", "x": x, "y": y,
                                                        "deltaX": float(msg.get("deltaX", 0)), "deltaY": float(msg.get("deltaY", 0))}, session_id=sid)
            return
        button = {0: "left", 1: "middle", 2: "right"}.get(int(msg.get("button", 0)), "left")
        action = msg.get("action", "click")
        if action == "move":
            await send.Input.dispatchMouseEvent(params={"type": "mouseMoved", "x": x, "y": y}, session_id=sid)
            return
        clicks = 2 if action == "dblclick" else 1
        await send.Input.dispatchMouseEvent(params={"type": "mousePressed", "x": x, "y": y, "button": button, "clickCount": clicks}, session_id=sid)
        await send.Input.dispatchMouseEvent(params={"type": "mouseReleased", "x": x, "y": y, "button": button, "clickCount": clicks}, session_id=sid)
    elif kind == "keyboard":
        key = str(msg.get("key", ""))
        if msg.get("action") != "keyDown":
            return
        if key in _SPECIAL_KEYS and key != " ":
            code = _SPECIAL_KEYS[key]
            for t in ("rawKeyDown", "keyUp"):
                await send.Input.dispatchKeyEvent(params={"type": t, "key": key, "windowsVirtualKeyCode": code,
                                                          "nativeVirtualKeyCode": code}, session_id=sid)
            if key == "Enter":
                await send.Input.dispatchKeyEvent(params={"type": "char", "text": "\r"}, session_id=sid)
        elif len(key) == 1:
            await send.Input.insertText(params={"text": key}, session_id=sid)
    elif kind == "paste":
        text = str(msg.get("text", ""))[:2000]
        if text:
            await send.Input.insertText(params={"text": text}, session_id=sid)
