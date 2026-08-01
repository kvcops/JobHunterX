"""Tests for database.py FTS cleanup on delete_job / clear_jobs.

Uses a fresh temp SQLite DB (never touches data/vellum.db).
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from vellum.config import database as db


@pytest.fixture(scope="module")
def tmp_db():
    tmp = Path(tempfile.mkdtemp()) / "test_fts.db"
    db.set_db_path(str(tmp))
    asyncio.run(db.init_db())
    return tmp


async def _fts_count(conn) -> int:
    cur = await conn.execute("SELECT count(*) c FROM jobs_fts")
    row = await cur.fetchone()
    return row["c"]


async def _insert(company: str, url_suffix: str, status: str = "discovered"):
    await db.insert_job({
        "company": company,
        "role": "Engineer",
        "apply_url": f"https://{company.lower()}.com/job/{url_suffix}",
        "jd_text": f"{company.lower()} job posting text",
        "status": status,
    })


async def _reset():
    """Wipe state so each test starts from a clean DB regardless of order."""
    await db.clear_jobs()


def test_insert_populates_fts(tmp_db):
    async def _t():
        await _reset()
        conn = await db.get_connection()
        try:
            await _insert("Acme", "1")
            assert await _fts_count(conn) == 1
        finally:
            await conn.close()

    asyncio.run(_t())


def test_delete_job_clears_fts(tmp_db):
    async def _t():
        await _reset()
        conn = await db.get_connection()
        try:
            await _insert("Beta", "2")
            cur = await conn.execute("SELECT id FROM jobs WHERE company = 'Beta'")
            row = await cur.fetchone()
            await db.delete_job(row["id"])
            assert await _fts_count(conn) == 0
        finally:
            await conn.close()

    asyncio.run(_t())


def test_clear_jobs_clears_fts(tmp_db):
    async def _t():
        await _reset()
        conn = await db.get_connection()
        try:
            await _insert("Gamma", "3")
            await _insert("Delta", "4")
            assert await _fts_count(conn) == 2
            await db.clear_jobs()
            assert await _fts_count(conn) == 0
        finally:
            await conn.close()

    asyncio.run(_t())


def test_clear_jobs_by_status_clears_fts(tmp_db):
    async def _t():
        await _reset()
        conn = await db.get_connection()
        try:
            await _insert("Epsilon", "5", status="matched")
            await _insert("Zeta", "6", status="discovered")
            assert await _fts_count(conn) == 2
            await db.clear_jobs(status="matched")
            assert await _fts_count(conn) == 1
            await db.clear_jobs()
            assert await _fts_count(conn) == 0
        finally:
            await conn.close()

    asyncio.run(_t())
