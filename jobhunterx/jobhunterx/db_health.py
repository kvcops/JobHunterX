"""
SQLite health: open-time integrity check with automatic recovery, plus on-demand
checks and repairs (also shown in Settings → Data).

* preflight(): before anything opens the DB. A corrupt file is moved to
  data/backups/ and everything still readable is copied into a fresh database,
  so the app always starts.
* check(repair=True): integrity, foreign keys, full-text index, orphaned rows,
  rows without an owner, WAL checkpoint — fixing what can be fixed safely.
"""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jobhunterx.config.logging import get_logger

log = get_logger("db_health")

_last_report: dict[str, Any] = {}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _backup_dir(db_path: Path) -> Path:
    d = db_path.parent / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _salvage(src: Path, dst: Path) -> int:
    """Copy every readable table row from a damaged DB into a new one. Returns rows copied."""
    copied = 0
    old = sqlite3.connect(str(src))
    new = sqlite3.connect(str(dst))
    try:
        for stmt in old.iterdump():
            try:
                new.execute(stmt)
                if stmt.startswith("INSERT"):
                    copied += 1
            except sqlite3.DatabaseError:
                continue          # skip what cannot be read; keep the rest
        new.commit()
    finally:
        old.close()
        new.close()
    return copied


def _preflight_sync(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"status": "new", "detail": "Database created."}
    try:
        con = sqlite3.connect(str(p))
        try:
            result = con.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        result = f"unreadable: {exc}"
    if result == "ok":
        return {"status": "ok", "detail": "Integrity check passed."}

    # Damaged: keep the original, rebuild from what is readable.
    backup = _backup_dir(p) / f"{p.stem}-corrupt-{_stamp()}{p.suffix}"
    shutil.move(str(p), str(backup))
    for ext in ("-wal", "-shm"):
        side = Path(str(p) + ext)
        if side.exists():
            shutil.move(str(side), str(backup) + ext)
    rows = 0
    try:
        rows = _salvage(backup, p)
    except Exception as exc:   # nothing salvageable: start clean, the backup stays on disk
        log.error("db_salvage_failed", error=str(exc)[:200])
        if p.exists():
            p.unlink()
    log.error("db_corruption_recovered", backup=str(backup), rows_recovered=rows, check=str(result)[:200])
    return {"status": "recovered", "detail": f"The database was damaged ({str(result)[:120]}). "
                                              f"A copy was saved to {backup.name} and {rows} rows were recovered.",
            "backup": str(backup)}


async def preflight(path: str) -> dict[str, Any]:
    report = await asyncio.to_thread(_preflight_sync, path)
    _last_report["preflight"] = report
    return report


def _check_sync(path: str, repair: bool) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    con = sqlite3.connect(path)
    try:
        integ = con.execute("PRAGMA quick_check").fetchone()[0]
        add("Integrity", "ok" if integ == "ok" else "error", "No problems found." if integ == "ok" else str(integ)[:200])

        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
        if mode.lower() != "wal" and repair:
            con.execute("PRAGMA journal_mode=WAL")
            add("Journal mode", "fixed", "Switched to WAL for safer concurrent writes.")
        else:
            add("Journal mode", "ok", mode.upper())

        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        add("Foreign keys", "ok" if not fk else "warn", "All references valid." if not fk else f"{len(fk)} broken references.")

        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        required = {"profiles", "jobs", "documents", "search_runs", "snapshots", "people", "app_state", "schema_meta"}
        missing = sorted(required - tables)
        add("Tables", "ok" if not missing else "error", "All present." if not missing else "Missing: " + ", ".join(missing))

        if "jobs_fts" in tables:
            try:
                con.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('integrity-check')")
                add("Search index", "ok", "Full-text index is consistent.")
            except sqlite3.DatabaseError:
                if repair:
                    con.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')")
                    add("Search index", "fixed", "Full-text index was rebuilt.")
                else:
                    add("Search index", "warn", "Full-text index needs a rebuild.")

        if {"documents", "jobs"} <= tables:
            n = con.execute("SELECT COUNT(*) FROM documents WHERE job_id IS NOT NULL AND job_id NOT IN (SELECT id FROM jobs)").fetchone()[0]
            if n and repair:
                con.execute("DELETE FROM documents WHERE job_id IS NOT NULL AND job_id NOT IN (SELECT id FROM jobs)")
                add("Orphaned documents", "fixed", f"Removed {n} documents whose job no longer exists.")
            else:
                add("Orphaned documents", "ok" if not n else "warn", "None." if not n else f"{n} found.")

        if "people" in tables:
            ownerless = 0
            for t in ("profiles", "jobs", "documents", "search_runs"):
                if t in tables:
                    cols = {r[1] for r in con.execute(f"PRAGMA table_info({t})")}
                    if "person_id" in cols:
                        ownerless += con.execute(f"SELECT COUNT(*) FROM {t} WHERE person_id IS NULL OR person_id NOT IN (SELECT id FROM people)").fetchone()[0]
            if ownerless and repair:
                row = con.execute("SELECT id FROM people ORDER BY COALESCE(last_used_at, created_at) DESC LIMIT 1").fetchone()
                if row:
                    for t in ("profiles", "jobs", "documents", "search_runs"):
                        con.execute(f"UPDATE {t} SET person_id = ? WHERE person_id IS NULL OR person_id NOT IN (SELECT id FROM people)", (row[0],))
                    add("Ownership", "fixed", f"{ownerless} rows were re-attached to the most recent profile.")
                else:
                    add("Ownership", "warn", f"{ownerless} rows have no profile.")
            else:
                add("Ownership", "ok" if not ownerless else "warn", "Every row belongs to a profile." if not ownerless else f"{ownerless} rows without a profile.")

        version = None
        if "schema_meta" in tables:
            r = con.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
            version = r[0] if r else None
        con.commit()
        if repair:
            for pragma in ("PRAGMA wal_checkpoint(PASSIVE)", "PRAGMA optimize"):
                try:
                    con.execute(pragma)
                except sqlite3.OperationalError:
                    pass       # busy / locked by another connection: harmless, retried next time
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("people", "profiles", "jobs", "documents", "search_runs") if t in tables}
    finally:
        con.close()
    size = Path(path).stat().st_size if Path(path).exists() else 0
    worst = "error" if any(c["status"] == "error" for c in checks) else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {"status": worst, "checks": checks, "schema_version": version, "counts": counts, "size_bytes": size,
            "checked_at": datetime.now(timezone.utc).isoformat()}


async def check(path: str, repair: bool = True) -> dict[str, Any]:
    report = await asyncio.to_thread(_check_sync, path, repair)
    report["preflight"] = _last_report.get("preflight")
    _last_report["check"] = report
    if report["status"] != "ok":
        log.warning("db_health_issues", status=report["status"], checks=[c for c in report["checks"] if c["status"] != "ok"])
    return report


def last_report() -> dict[str, Any]:
    return dict(_last_report)


async def backup(path: str) -> str:
    """Consistent online copy (VACUUM INTO) into data/backups/."""
    dst = _backup_dir(Path(path)) / f"{Path(path).stem}-{_stamp()}.db"

    def _do() -> None:
        con = sqlite3.connect(path)
        try:
            con.execute("VACUUM INTO ?", (str(dst),))
        finally:
            con.close()
    await asyncio.to_thread(_do)
    return str(dst)
