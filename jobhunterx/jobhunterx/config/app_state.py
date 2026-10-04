"""
Small persistent key/value store for user preferences that are not secrets:
provider on/off switches, search strategy, per-task model choices, active profile.

Values live in the SQLite `app_state` table and are mirrored in memory, so hot
paths (the LLM router, the search router) read them without touching the DB.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import aiosqlite

from jobhunterx.config.logging import get_logger

log = get_logger("app_state")

SEARCH_PROVIDERS = ["tinyfish", "tavily", "exa", "brave", "deep", "ddgs"]   # deep + ddgs need no key
LLM_PROVIDERS = ["google", "kilo", "nvidia", "groq", "mistral"]   # kilo needs no key (free pool)

# Seeded on first start; later releases only ever add keys.
DEFAULTS: dict[str, Any] = {
    "llm.providers": {"google": True, "kilo": True, "nvidia": True, "groq": True, "mistral": True},
    "llm.overrides": {},                       # chain -> preferred first model id
    "search.providers": {p: True for p in SEARCH_PROVIDERS},
    "search.order": list(SEARCH_PROVIDERS),
    # smart:    free Deep Search + one keyed provider per query (rotating), merged and AI-ranked once (best results)
    # fallback: first provider that returns results wins (cheapest)
    # spread:   rotate queries across enabled providers (shares free quotas)
    # combine:  ask two providers per query and merge (widest coverage, uses more quota)
    "search.strategy": "smart",
    "search.strategy_v2": False,               # set once the old "fallback" default has been moved to "smart"
    "people.active": None,
    "setup.free_ok": False,                    # the user chose to start on Kilo's free models without any key
}

_cache: dict[str, Any] = copy.deepcopy(DEFAULTS)
_db_path: str | None = None


async def load(db_path: str) -> None:
    """Create the table, seed missing defaults and load everything into memory."""
    global _db_path
    _db_path = db_path
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)")
        cur = await db.execute("SELECT key, value_json FROM app_state")
        rows = {k: v for k, v in await cur.fetchall()}
        for key, default in DEFAULTS.items():
            if key not in rows:
                await db.execute("INSERT INTO app_state (key, value_json) VALUES (?, ?)", (key, json.dumps(default)))
                _cache[key] = copy.deepcopy(default)
                continue
            try:
                val = json.loads(rows[key])
            except ValueError:
                log.warning("app_state_value_corrupt_reset", key=key)
                val = copy.deepcopy(default)
                await db.execute("UPDATE app_state SET value_json = ? WHERE key = ?", (json.dumps(val), key))
            if isinstance(default, dict) and isinstance(val, dict):   # heal: add keys new releases introduced
                val = {**default, **val} if key != "llm.overrides" else val
            _cache[key] = val
        await db.commit()
    if not _cache.get("search.strategy_v2"):
        # "fallback" was the old default: it let one keyed provider answer alone and never used Deep Search,
        # which measured best for real postings. Move it to "smart" once; a later manual choice is kept.
        if _cache.get("search.strategy") == "fallback":
            _cache["search.strategy"] = "smart"
        _cache["search.strategy_v2"] = True
        async with aiosqlite.connect(db_path) as db:
            for k in ("search.strategy", "search.strategy_v2"):
                await db.execute("INSERT INTO app_state (key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE "
                                 "SET value_json = excluded.value_json", (k, json.dumps(_cache[k])))
            await db.commit()
    order = [p for p in _cache["search.order"] if p in SEARCH_PROVIDERS]
    if "deep" not in order:                      # added later: it belongs right before plain DuckDuckGo
        order.insert(order.index("ddgs") if "ddgs" in order else len(order), "deep")
    _cache["search.order"] = order + [p for p in SEARCH_PROVIDERS if p not in order]


def get(key: str) -> Any:
    return copy.deepcopy(_cache.get(key, DEFAULTS.get(key)))


async def set(key: str, value: Any) -> None:  # noqa: A001 — mirrors dict API
    _cache[key] = copy.deepcopy(value)
    if not _db_path:
        return
    async with aiosqlite.connect(_db_path) as db:
        await db.execute("INSERT INTO app_state (key, value_json) VALUES (?, ?) "
                         "ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json", (key, json.dumps(value)))
        await db.commit()


def llm_provider_enabled(provider: str) -> bool:
    return bool(_cache["llm.providers"].get(provider, True))


def search_plan() -> tuple[list[str], str]:
    """Enabled search providers in the user's order, plus the strategy."""
    enabled = _cache["search.providers"]
    return [p for p in _cache["search.order"] if enabled.get(p, True)], _cache["search.strategy"]
