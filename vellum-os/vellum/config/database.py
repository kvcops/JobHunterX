"""
Vellum OS — Database Layer (aiosqlite 0.22.x)

SQLite persistence for jobs, profiles, tailored resumes, outreach drafts,
agent runs, and applied-URL deduplication.  Uses FTS5 for full-text
search on job descriptions.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from vellum.config.logging import get_logger

log = get_logger("database")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    data_json   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id                  TEXT PRIMARY KEY,
    company             TEXT NOT NULL,
    role                TEXT,
    career_page_url     TEXT,
    apply_url           TEXT,
    apply_url_hash      TEXT UNIQUE,
    jd_text             TEXT,
    source              TEXT,
    discovery_confidence REAL DEFAULT 0.0,
    freshness_json      TEXT,
    validation_json     TEXT,
    match_score         REAL,
    status              TEXT NOT NULL DEFAULT 'discovered',
    tailored_pdf        BLOB,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS outreach_drafts (
    id              TEXT PRIMARY KEY,
    job_id          TEXT REFERENCES jobs(id),
    company         TEXT NOT NULL,
    contact_name    TEXT,
    contact_role    TEXT,
    email_guesses   TEXT,
    subject         TEXT,
    body            TEXT,
    mailto_uri      TEXT,
    confidence      REAL DEFAULT 0.0,
    status          TEXT NOT NULL DEFAULT 'drafted',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    agent_name  TEXT NOT NULL,
    job_id      TEXT,
    event_type  TEXT NOT NULL,
    message     TEXT,
    data_json   TEXT,
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    model       TEXT,
    latency_ms  REAL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS applied_urls (
    url_hash    TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- FTS5 virtual table for full-text search on job descriptions
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    company,
    role,
    jd_text,
    content='jobs',
    content_rowid='rowid'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, company, role, jd_text)
    VALUES (new.rowid, new.company, new.role, new.jd_text);
END;

CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, company, role, jd_text)
    VALUES ('delete', old.rowid, old.company, old.role, old.jd_text);
END;

CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, company, role, jd_text)
    VALUES ('delete', old.rowid, old.company, old.role, old.jd_text);
    INSERT INTO jobs_fts(rowid, company, role, jd_text)
    VALUES (new.rowid, new.company, new.role, new.jd_text);
END;

CREATE TABLE IF NOT EXISTS intervention_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    hitl_type   TEXT NOT NULL,
    url         TEXT,
    company     TEXT,
    role        TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    website     TEXT DEFAULT '',
    careers_url TEXT DEFAULT '',
    hub         TEXT DEFAULT '',
    ats         TEXT DEFAULT '',
    ats_token   TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
"""

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_db_path: str | None = None


def set_db_path(path: str) -> None:
    """Set the database file path (called during startup)."""
    global _db_path
    _db_path = path
    Path(path).parent.mkdir(parents=True, exist_ok=True)


async def get_connection() -> aiosqlite.Connection:
    """Open a new connection to the database."""
    if _db_path is None:
        raise RuntimeError("Database path not set. Call set_db_path() first.")
    conn = await aiosqlite.connect(_db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def clean_existing_database_jobs() -> None:
    """Clean company names and titles for existing job rows in database."""
    from vellum.utils.job_cleaner import clean_job_title_and_company
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, company, role, jd_text, apply_url, validation_json FROM jobs")
        rows = await cursor.fetchall()
        for row in rows:
            job_id = row["id"]
            co = row["company"]
            ro = row["role"]
            vj = row["validation_json"]
            v_dict = {}
            if vj and isinstance(vj, str):
                try:
                    v_dict = json.loads(vj)
                except Exception:
                    log.warning("invalid_validation_json", job_id=job_id, exc_info=True)

            val_co = v_dict.get("company_name") if isinstance(v_dict, dict) else ""
            val_ro = v_dict.get("job_role") if isinstance(v_dict, dict) else ""

            clean_co, clean_ro = clean_job_title_and_company(
                raw_title=val_ro or ro,
                raw_company=val_co or co,
                snippet=row["jd_text"] or "",
                apply_url=row["apply_url"] or "",
            )
            if clean_co != co or clean_ro != ro:
                await db.execute(
                    "UPDATE jobs SET company = ?, role = ? WHERE id = ?",
                    (clean_co, clean_ro, job_id),
                )
        await db.commit()


async def init_db() -> None:
    """Create tables and indexes if they don't already exist."""
    log.info("initialising_database", path=_db_path)
    conn = await get_connection()
    try:
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
        log.info("database_ready")
    finally:
        await conn.close()
    try:
        await clean_existing_database_jobs()
    except Exception as exc:
        log.warning("clean_database_jobs_failed", error=str(exc))


# ---------------------------------------------------------------------------
# CRUD Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _new_id() -> str:
    return str(uuid.uuid4())


async def insert_profile(data: dict) -> str:
    """Insert a candidate profile and return its id."""
    profile_id = _new_id()
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO profiles (id, data_json, created_at) VALUES (?, ?, ?)",
            (profile_id, json.dumps(data), _now_iso()),
        )
        await db.commit()
    return profile_id


async def get_latest_profile() -> Optional[dict]:
    """Return the most recently stored profile or None."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT data_json FROM profiles ORDER BY created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["data_json"])
    return None


async def _update_existing_job(db, job_id: str, job_data: dict) -> None:
    """Refresh an existing job row with fresh discovered data."""
    await db.execute(
        """UPDATE jobs SET company = ?, role = ?, jd_text = ?, 
           source = ?, updated_at = ? WHERE id = ?""",
        (
            job_data.get("company", ""),
            job_data.get("role"),
            job_data.get("jd_text"),
            job_data.get("source"),
            _now_iso(),
            job_id,
        ),
    )


async def insert_job(job_data: dict) -> str:
    """Insert a discovered job. Returns job id.

    If a job with the same apply_url already exists, updates its data
    and returns the existing id (instead of creating a duplicate).
    """
    import hashlib

    job_id = job_data.get("id") or _new_id()
    apply_url = job_data.get("apply_url") or job_data.get("career_page_url", "")
    url_hash = hashlib.sha256(apply_url.encode()).hexdigest() if apply_url else None
    if not url_hash:
        log.warning("job_insert_without_url", job_id=job_id, company=job_data.get("company", ""))

    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        # Check for existing job with same URL
        if url_hash:
            cursor = await db.execute(
                "SELECT id FROM jobs WHERE apply_url_hash = ?", (url_hash,)
            )
            row = await cursor.fetchone()
            if row:
                existing_id = row["id"]
                # Update existing job with fresh data instead of returning stale data
                await _update_existing_job(db, existing_id, job_data)
                await db.commit()
                return existing_id

        try:
            await db.execute(
                """INSERT INTO jobs
                   (id, company, role, career_page_url, apply_url, apply_url_hash,
                    jd_text, source, discovery_confidence, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    job_data.get("company", ""),
                    job_data.get("role"),
                    job_data.get("career_page_url"),
                    apply_url,
                    url_hash,
                    job_data.get("jd_text"),
                    job_data.get("source"),
                    job_data.get("discovery_confidence", 0.0),
                    job_data.get("status", "discovered"),
                    _now_iso(),
                    _now_iso(),
                ),
            )
            await db.commit()
        except sqlite3.IntegrityError:
            # Race: another task inserted the same URL between our SELECT and INSERT.
            if url_hash:
                cursor = await db.execute(
                    "SELECT id FROM jobs WHERE apply_url_hash = ?", (url_hash,)
                )
                row = await cursor.fetchone()
                if row:
                    await _update_existing_job(db, row["id"], job_data)
                    await db.commit()
                    return row["id"]
            raise
    return job_id


_JOB_UPDATEABLE_COLUMNS = frozenset({
    "company", "role", "career_page_url", "apply_url", "apply_url_hash",
    "jd_text", "source", "discovery_confidence", "freshness_json",
    "validation_json", "match_score", "status", "tailored_pdf",
})


async def update_job(job_id: str, **fields: Any) -> None:
    """Update specific fields on a job row."""
    fields = {k: v for k, v in fields.items() if k in _JOB_UPDATEABLE_COLUMNS}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [_now_iso(), job_id]
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            f"UPDATE jobs SET {set_clause}, updated_at = ? WHERE id = ?", values
        )
        await db.commit()


async def get_jobs(status: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Return jobs, optionally filtered by status."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_job(job_id: str) -> Optional[dict]:
    """Return a single job by id."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def _reconcile_fts(conn) -> None:
    """Belt-and-braces FTS consistency check.

    `jobs_fts` is an FTS5 EXTERNAL-CONTENT table (content='jobs') — direct
    DELETE statements against it are illegal and corrupt the database, so
    cleanup must go through the AFTER DELETE trigger. For legacy databases
    created without triggers, reconcile by rebuilding the index from
    content, which drops any phantom FTS rows safely.
    """
    cur = await conn.execute(
        "SELECT (SELECT count(*) FROM jobs) AS n_jobs, (SELECT count(*) FROM jobs_fts) AS n_fts"
    )
    row = await cur.fetchone()
    if row["n_jobs"] != row["n_fts"]:
        await conn.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('rebuild')")
        log.warning(
            "fts_reconciled",
            n_jobs=row["n_jobs"],
            n_fts=row["n_fts"],
        )


async def delete_job(job_id: str) -> bool:
    """Delete a single job by id, along with its associated outreach drafts & interventions.

    FTS index cleanup is handled by the AFTER DELETE trigger; for legacy
    databases without triggers, `_reconcile_fts` rebuilds the index so
    `jobs_fts` never retains ghost entries.
    """
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM outreach_drafts WHERE job_id = ?", (job_id,))
        await db.execute("DELETE FROM intervention_sessions WHERE job_id = ?", (job_id,))
        cursor = await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        await _reconcile_fts(db)
        await db.commit()
        return cursor.rowcount > 0


async def clear_jobs(status: Optional[str] = None) -> int:
    """Delete all jobs (or jobs with specified status) from database.

    FTS index cleanup is handled by the AFTER DELETE trigger; for legacy
    databases without triggers, `_reconcile_fts` rebuilds the index so
    `jobs_fts_data` never keeps stale rows.
    """
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        if status:
            await db.execute("DELETE FROM outreach_drafts WHERE job_id IN (SELECT id FROM jobs WHERE status = ?)", (status,))
            await db.execute("DELETE FROM intervention_sessions WHERE job_id IN (SELECT id FROM jobs WHERE status = ?)", (status,))
            cursor = await db.execute("DELETE FROM jobs WHERE status = ?", (status,))
        else:
            await db.execute("DELETE FROM outreach_drafts")
            await db.execute("DELETE FROM intervention_sessions")
            cursor = await db.execute("DELETE FROM jobs")
        await _reconcile_fts(db)
        await db.commit()
        return cursor.rowcount


async def insert_outreach(draft: dict) -> str:
    """Insert an outreach draft."""
    draft_id = draft.get("id") or _new_id()
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """INSERT INTO outreach_drafts
               (id, job_id, company, contact_name, contact_role, email_guesses,
                subject, body, mailto_uri, confidence, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                draft_id,
                draft.get("job_id"),
                draft.get("company", ""),
                draft.get("contact_name"),
                draft.get("contact_role"),
                json.dumps(draft.get("email_guesses", [])),
                draft.get("subject"),
                draft.get("body"),
                draft.get("mailto_uri"),
                draft.get("confidence", 0.0),
                draft.get("status", "drafted"),
                _now_iso(),
            ),
        )
        await db.commit()
    return draft_id


async def get_outreach_drafts(limit: int = 100) -> list[dict]:
    """Return active outreach drafts for existing jobs."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.* FROM outreach_drafts o
               JOIN jobs j ON o.job_id = j.id
               WHERE o.status != 'discarded'
               ORDER BY o.created_at DESC
               LIMIT ?""", (limit,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("email_guesses"):
                d["email_guesses"] = json.loads(d["email_guesses"])
            result.append(d)
        return result


async def log_agent_event(
    run_id: str,
    agent_name: str,
    event_type: str,
    message: str = "",
    job_id: str | None = None,
    data: dict | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    model: str | None = None,
    latency_ms: float | None = None,
) -> None:
    """Persist an agent run event for observability."""
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """INSERT INTO agent_runs
               (run_id, agent_name, job_id, event_type, message, data_json,
                tokens_in, tokens_out, model, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                agent_name,
                job_id,
                event_type,
                message,
                json.dumps(data) if data else None,
                tokens_in,
                tokens_out,
                model,
                latency_ms,
                _now_iso(),
            ),
        )
        await db.commit()


async def get_token_usage_summary() -> dict:
    """Aggregate token usage by model across all runs."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT model,
                      SUM(tokens_in) as total_in,
                      SUM(tokens_out) as total_out,
                      COUNT(*) as call_count
               FROM agent_runs
               WHERE model IS NOT NULL
               GROUP BY model"""
        )
        rows = await cursor.fetchall()
        return {
            row["model"]: {
                "tokens_in": row["total_in"] or 0,
                "tokens_out": row["total_out"] or 0,
                "calls": row["call_count"],
            }
            for row in rows
        }


async def clear_database() -> None:
    """Nuclear reset: destroy ALL tables, database files, cache, screenshots, and browser profiles.
    Rebuilds schema from scratch.
    """
    log.info("nuclear_reset_started")
    
    # 1. Stop active browsers
    try:
        from vellum.agents.browser_agent import stop_all_active_browsers
        await stop_all_active_browsers()
    except Exception as exc:
        log.warning("failed_to_stop_browsers_during_clear", error=str(exc))

    # Let loop processes finish and run garbage collection to release file descriptors
    await asyncio.sleep(0.5)
    import gc
    gc.collect()

    import shutil
    import os
    from vellum.config.settings import get_settings
    
    settings = get_settings()
    
    # Directories to delete
    dirs_to_delete = [
        Path("./data/browser_profile"),
        Path("./data/browser_profile_test"),
        Path(settings.cache_dir),
        Path(settings.screenshots_dir),
    ]
    
    for dir_path in dirs_to_delete:
        if dir_path.exists():
            for i in range(5):
                try:
                    shutil.rmtree(dir_path)
                    log.info("deleted_directory", path=str(dir_path))
                    break
                except Exception as exc:
                    if i == 4:
                         log.warning("failed_to_delete_dir", path=str(dir_path), error=str(exc))
                    await asyncio.sleep(0.5)

    # 2. Delete database files with retries
    if _db_path:
        db_file = Path(_db_path)
        db_files = [
            db_file,
            Path(str(db_file) + "-wal"),
            Path(str(db_file) + "-shm")
        ]
        for f_path in db_files:
            if f_path.exists():
                for i in range(5):
                    try:
                        os.remove(f_path)
                        log.info("deleted_db_file", path=str(f_path))
                        break
                    except Exception as exc:
                        if i == 4:
                            log.warning("failed_to_delete_db_file", path=str(f_path), error=str(exc))
                        await asyncio.sleep(0.5)

    # 3. Re-initialize database schema
    await init_db()
    log.info("nuclear_reset_complete")


# ---------------------------------------------------------------------------
# Intervention Sessions
# ---------------------------------------------------------------------------

async def create_intervention_session(
    job_id: str,
    hitl_type: str,
    url: str,
    company: str = "",
    role: str = "",
) -> int:
    """Insert a new intervention session and return its id."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """INSERT INTO intervention_sessions
               (job_id, hitl_type, url, company, role, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (job_id, hitl_type, url, company, role, _now_iso()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_interventions() -> list[dict]:
    """Return all pending intervention sessions."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, job_id, hitl_type, url, company, role, status, created_at
               FROM intervention_sessions
               WHERE status = 'pending'
               ORDER BY created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def resolve_intervention(session_id: int, status: str = "resolved") -> None:
    """Mark an intervention session as resolved."""
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """UPDATE intervention_sessions
               SET status = ?, resolved_at = ?
               WHERE id = ?""",
            (status, _now_iso(), session_id),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Companies (board-first discovery)
# ---------------------------------------------------------------------------

async def insert_company(data: dict) -> str:
    """Insert a company; returns id. If name exists, refresh ATS fields.

    data keys: name, website, careers_url, hub, ats, ats_token.
    """
    cid = data.get("id") or _new_id()
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Company name required")
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM companies WHERE name = ?", (name,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                """UPDATE companies SET website = ?, careers_url = ?, hub = ?, ats = ?,
                   ats_token = ?, updated_at = ? WHERE id = ?""",
                (data.get("website", ""), data.get("careers_url", ""),
                 data.get("hub", ""), data.get("ats", ""),
                 data.get("ats_token", ""), _now_iso(), row["id"]),
            )
            await db.commit()
            return row["id"]
        await db.execute(
            """INSERT INTO companies (id, name, website, careers_url, hub, ats, ats_token, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, name, data.get("website", ""), data.get("careers_url", ""),
             data.get("hub", ""), data.get("ats", ""), data.get("ats_token", ""),
             _now_iso(), _now_iso()),
        )
        await db.commit()
        return cid


async def get_companies() -> list[dict]:
    """All tracked companies."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, name, website, careers_url, hub, ats, ats_token, created_at FROM companies ORDER BY name"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def delete_company(company_id: str) -> bool:
    """Remove a tracked company by id."""
    async with aiosqlite.connect(_db_path) as db:
        cur = await db.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        await db.commit()
        return cur.rowcount > 0


async def update_company_ats(company_id: str, ats: str, ats_token: str, careers_url: str = "") -> None:
    """Persist detected ATS board info after a probe."""
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """UPDATE companies SET ats = ?, ats_token = ?, careers_url = CASE
               WHEN ? != '' THEN ? ELSE careers_url END, updated_at = ? WHERE id = ?""",
            (ats, ats_token, careers_url, careers_url, _now_iso(), company_id),
        )
        await db.commit()


async def get_company_by_name(name: str) -> Optional[dict]:
    """Look up a company by exact name."""
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM companies WHERE name = ?", (name,))
        row = await cur.fetchone()
        return dict(row) if row else None
