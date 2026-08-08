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
