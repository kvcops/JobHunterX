"""
One long-lived event loop (on its own thread) that owns the auto-apply browser.

Why: the browser's CDP connection belongs to the loop that created it. Running
the agent here — instead of a throw-away loop per run — means the browser stays
usable after the agent pauses or stops, so the user can take over, continue or
close it, and nothing else ever touches the connection from another thread.
On Windows the loop is a Proactor loop (needed to launch Chrome as a subprocess).
"""

from __future__ import annotations

import asyncio
import sys
import threading
from concurrent.futures import Future
from typing import Any, Awaitable, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    with _lock:
        if _loop is not None and _thread is not None and _thread.is_alive():
            return _loop
        if sys.platform == "win32":
            new_loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()   # type: ignore[attr-defined]
        else:
            new_loop = asyncio.new_event_loop()
        ready = threading.Event()

        def _run() -> None:
            asyncio.set_event_loop(new_loop)
            ready.set()
            new_loop.run_forever()

        _thread = threading.Thread(target=_run, name="jhx-browser-worker", daemon=True)
        _thread.start()
        ready.wait(5)
        _loop = new_loop
        return _loop


def submit(coro: Awaitable[Any]) -> Future:
    """Schedule a coroutine on the browser loop from any thread."""
    return asyncio.run_coroutine_threadsafe(coro, loop())   # type: ignore[arg-type]


async def run(coro: Awaitable[Any]) -> Any:
    """Await a coroutine that runs on the browser loop."""
    return await asyncio.wrap_future(submit(coro))


def on_worker() -> bool:
    try:
        return asyncio.get_running_loop() is _loop
    except RuntimeError:
        return False
