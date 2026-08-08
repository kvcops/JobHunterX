"""
JobHunterX — Unit-Specific Usage Ledger & Local Spending Tracker

Maintains SQLite usage ledger for recording search and fetch attempts,
request counts, native billing unit tracking, and provider quotas.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

import aiosqlite
from jobhunterx.config.database import get_db_path
from jobhunterx.config.logging import get_logger

log = get_logger("usage_ledger")


async def init_ledger_db():
    """Ensure search_usage_ledger table exists in database."""
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS search_usage_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                request_type TEXT NOT NULL,
                search_query_hash TEXT DEFAULT '',
                url_hash TEXT DEFAULT '',
                http_status INTEGER DEFAULT 0,
                verdict TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                native_billing_units REAL DEFAULT 0.0,
                estimated_cost_native REAL DEFAULT 0.0,
                actual_known_cost_native REAL DEFAULT 0.0,
                unit_type TEXT NOT NULL,
                blocked_reason TEXT DEFAULT ''
            );
            """
        )
        await db.commit()


def hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:16]


async def record_ledger_attempt(
    provider: str,
    request_type: str,  # 'search' or 'fetch'
    verdict: str,
    search_query: str = "",
    url: str = "",
    http_status: int = 0,
    retry_count: int = 0,
    native_billing_units: float = 0.0,
    estimated_cost_native: float = 0.0,
    actual_known_cost_native: float = 0.0,
    unit_type: str = "credits",
    blocked_reason: str = "",
):
    """Record a search or fetch attempt in SQLite ledger."""
    await init_ledger_db()
    db_path = get_db_path()
    q_hash = hash_text(search_query) if search_query else ""
    u_hash = hash_text(url) if url else ""

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO search_usage_ledger (
                provider, request_type, search_query_hash, url_hash,
                http_status, verdict, retry_count, native_billing_units,
                estimated_cost_native, actual_known_cost_native, unit_type, blocked_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                request_type,
                q_hash,
                u_hash,
                http_status,
                verdict,
                retry_count,
                native_billing_units,
                estimated_cost_native,
                actual_known_cost_native,
                unit_type,
                blocked_reason,
            ),
        )
        await db.commit()


async def get_monthly_usage_native(provider: str) -> float:
    """Sum native billing units used by provider in current calendar month."""
    await init_ledger_db()
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT SUM(native_billing_units) FROM search_usage_ledger
            WHERE provider = ?
            AND timestamp >= datetime('now', 'start of month')
            """,
            (provider,),
        ) as cursor:
            row = await cursor.fetchone()
            return float(row[0] or 0.0) if row else 0.0


async def get_usage_report() -> dict:
    """Aggregate per-provider usage stats from the ledger for the Usage dashboard.

    Returns {provider: {calls, calls_this_month, native_units_this_month,
    estimated_cost, actual_cost, last_used, verdicts: {verdict: count}}}
    """
    await init_ledger_db()
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT provider,
                   COUNT(*) as calls,
                   SUM(CASE WHEN timestamp >= datetime('now', 'start of month')
                       THEN 1 ELSE 0 END) as calls_month,
                   SUM(CASE WHEN timestamp >= datetime('now', 'start of month')
                       THEN native_billing_units ELSE 0 END) as units_month,
                   COALESCE(SUM(estimated_cost_native), 0) as est_cost,
                   COALESCE(SUM(actual_known_cost_native), 0) as actual_cost,
                   MAX(timestamp) as last_used
            FROM search_usage_ledger
            GROUP BY provider
            """
        ) as cursor:
            rows = await cursor.fetchall()
        async with db.execute(
            "SELECT provider, verdict, COUNT(*) AS n FROM search_usage_ledger GROUP BY provider, verdict"
        ) as cursor:
            verdict_rows = await cursor.fetchall()

    verdicts_by_provider: dict[str, dict[str, int]] = {}
    for vr in verdict_rows:
        verdicts_by_provider.setdefault(vr["provider"], {})[vr["verdict"]] = vr["n"]

    report: dict[str, dict] = {}
    for r in rows:
        report[r["provider"]] = {
            "calls": int(r["calls"] or 0),
            "calls_this_month": int(r["calls_month"] or 0),
            "units_this_month": float(r["units_month"] or 0.0),
            "est_cost_total": float(r["est_cost"] or 0.0),
            "actual_cost_total": float(r["actual_cost"] or 0.0),
            "last_used": r["last_used"] or "",
            "verdicts": verdicts_by_provider.get(r["provider"], {}),
        }
    return report
