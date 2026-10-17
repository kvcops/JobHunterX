"""
How much work this machine can take at once, worked out from its real CPU and memory.

Inside a container (Render, Docker…) the whole host's RAM and cores are visible to psutil, but the
app may only use its own share; the cgroup limits are read first so a 512 MB plan is sized as
512 MB, not as the host's 64 GB. Numbers are recomputed every few seconds, so a search started
while memory is tight runs gentler, and new searches wait for a free slot instead of crashing
the server. Any value can be pinned in .env (see .env.example, "Capacity").

The web server itself stays one process on purpose: searches, live updates and the auto-apply
browser are kept in that process's memory, so a second worker would not see them.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from jobhunterx.config.logging import get_logger

log = get_logger("capacity")

_MB = 1024 * 1024
SEARCH_MB = 140          # one running search at its peak (pages being read, parsed and matched)
FETCH_MB = 12            # one page download + parse in flight
_cache: tuple[float, dict] = (0.0, {})


def _read(path: str) -> Optional[str]:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _cgroup_memory() -> tuple[Optional[int], Optional[int]]:
    """(limit, used) bytes from cgroup v2 or v1; (None, None) outside a container."""
    for limit_p, used_p in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
                            ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes")):
        raw = _read(limit_p)
        if raw and raw != "max":
            try:
                limit = int(raw)
            except ValueError:
                continue
            if 0 < limit < 1 << 50:                     # v1 says "no limit" with a huge number
                used = _read(used_p)
                return limit, int(used) if used and used.isdigit() else None
    return None, None


def _cpus() -> float:
    raw = _read("/sys/fs/cgroup/cpu.max")              # "50000 100000" = half a CPU
    if raw and not raw.startswith("max"):
        try:
            quota, period = (int(x) for x in raw.split()[:2])
            if quota > 0 and period > 0:
                return max(0.25, quota / period)
        except ValueError:
            pass
    try:
        return float(len(os.sched_getaffinity(0)))     # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return float(os.cpu_count() or 1)


def _env_int(name: str) -> Optional[int]:
    v = os.getenv(name, "").strip()
    return int(v) if v.isdigit() and int(v) > 0 else None


def _measure() -> dict:
    import psutil
    vm = psutil.virtual_memory()
    limit, used = _cgroup_memory()
    if limit:
        total = limit
        available = max(0, limit - (used if used is not None else psutil.Process().memory_info().rss))
        available = min(available, vm.available)
    else:
        total, available = vm.total, vm.available
    cpus = _cpus()
    avail_mb = available / _MB
    # searches: what is free now after a safety margin, and never more than ~2 per CPU
    by_mem = int((avail_mb - 120) // SEARCH_MB)
    searches = max(1, min(by_mem, max(1, int(cpus * 2)), 6))
    fetch = max(2, min(int(cpus * 4), int(avail_mb // (FETCH_MB * 3)), 12))
    return {
        "cpus": round(cpus, 2),
        "memory_total_mb": round(total / _MB),
        "memory_available_mb": round(avail_mb),
        "in_container": bool(limit),
        "searches": _env_int("MAX_PARALLEL_SEARCHES") or searches,
        "fetch_concurrency": _env_int("FETCH_CONCURRENCY") or fetch,
        "board_concurrency": _env_int("BOARD_CONCURRENCY") or max(2, min(fetch + 2, 10)),
        "query_concurrency": _env_int("QUERY_CONCURRENCY") or max(1, min(int(cpus * 2), 3)),
        "threads": _env_int("THREAD_POOL_SIZE") or max(8, min(int(cpus * 8), 40)),
        "low_memory": avail_mb < 160,
    }


def plan(max_age_s: float = 5.0) -> dict:
    """Current limits (recomputed at most every few seconds)."""
    global _cache
    now = time.monotonic()
    if now - _cache[0] > max_age_s or not _cache[1]:
        try:
            _cache = (now, _measure())
        except Exception as exc:                        # never let sizing break a search
            log.warning("capacity_measure_failed", error=str(exc)[:160])
            _cache = (now, _cache[1] or {"cpus": 1, "memory_total_mb": 0, "memory_available_mb": 0, "in_container": False,
                                         "searches": 1, "fetch_concurrency": 4, "board_concurrency": 4,
                                         "query_concurrency": 2, "threads": 8, "low_memory": False})
    return dict(_cache[1])


def apply_thread_pool() -> None:
    """Size the thread pools used for blocking work (PDF reading, Google SDK calls) to the machine.
    Call from the running server loop (startup)."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    n = plan()["threads"]
    try:
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=n, thread_name_prefix="jhx"))
        import anyio.to_thread
        anyio.to_thread.current_default_thread_limiter().total_tokens = n
    except Exception as exc:
        log.debug("thread_pool_size_skipped", error=str(exc)[:120])


# ---------------------------------------------------------------------------- giving memory back

_libc = None


def _glibc():
    """glibc on Linux (Render, Docker); None elsewhere (Windows / macOS manage this themselves)."""
    global _libc
    if _libc is None:
        _libc = False
        if os.name == "posix":
            try:
                import ctypes
                lib = ctypes.CDLL("libc.so.6")
                lib.malloc_trim  # noqa: B018 — only glibc has it
                _libc = lib
            except (OSError, AttributeError):
                _libc = False
    return _libc or None


def limit_malloc_arenas(n: int = 2) -> None:
    """glibc keeps one memory pool per thread (up to 8 per CPU); with a thread pool that grows RSS by tens of MB that
    is never given back. Two pools are plenty for this app. Call once at startup, before the thread pools fill."""
    lib = _glibc()
    if lib is not None:
        try:
            lib.mallopt(-8, n)              # M_ARENA_MAX
        except Exception:
            pass


def release_memory() -> None:
    """After heavy work (index download, a search, reading a resume): collect garbage and hand freed memory back to
    the system, so the server's RSS goes down again instead of staying at its peak."""
    import gc
    gc.collect()
    lib = _glibc()
    if lib is not None:
        try:
            lib.malloc_trim(0)
        except Exception:
            pass
