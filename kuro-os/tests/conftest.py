"""Shared fixtures: isolated temp DB per test, pointed at by the global db path."""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kuro.config import database as db


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