"""Shared fixtures: isolated temp DB per test, pointed at by the global db path."""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Keyless network sources stay off in tests (their parsers are tested with fixtures in test_sources.py).
for _flag in ("ENABLE_YC_SOURCE", "ENABLE_REDDIT_SOURCE", "ENABLE_FOUNDER_POSTS", "ENABLE_FUNDING_SIGNALS", "ENABLE_DOMAIN_AGE_CHECK"):
    os.environ.setdefault(_flag, "false")

from jobhunterx.config import database as db


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Point the DB layer at a fresh temp SQLite file for every test."""
    old = db._db_path
    db.set_db_path(str(tmp_path / "test.db"))
    _run(db.init_db())
    yield tmp_path
    if old is not None:
        db.set_db_path(old)

class _MemCache(dict):
    def set(self, k, v):
        self[k] = v


@pytest.fixture(autouse=True)
def isolated_caches(monkeypatch):
    """Funding news and website ages come from the real disk cache in the app; tests start with empty ones."""
    from jobhunterx.discovery import funding
    from jobhunterx.intelligence import domain_age
    monkeypatch.setattr(funding, "_store", _MemCache())
    monkeypatch.setattr(domain_age, "_store", _MemCache())
