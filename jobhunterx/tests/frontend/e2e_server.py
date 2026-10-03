"""Run the real app with the fake outside world (tests/fixtures/scenario.py) for browser E2E tests.

Usage: python -m tests.frontend.e2e_server <port> <data_dir>
"""
import asyncio
import os
import sys

port, data_dir = int(sys.argv[1]), sys.argv[2]
os.environ.update(DB_PATH=f"{data_dir}/e2e.db", CACHE_DIR=f"{data_dir}/cache", SCREENSHOTS_DIR=f"{data_dir}/shots",
                  PORT=str(port), GOOGLE_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="")

from _pytest.monkeypatch import MonkeyPatch  # noqa: E402

from tests.fixtures import scenario  # noqa: E402

mp = MonkeyPatch()
scenario.install(mp)

# Slow the fake LLM slightly so streaming/progress states are observable.
from jobhunterx.intelligence import llm_structured  # noqa: E402
_fast = llm_structured.call_llm_with_fallback


async def _slow(chain, messages, **kw):
    await asyncio.sleep(float(os.environ.get("E2E_LLM_DELAY", "0.15")))
    return await _fast(chain, messages, **kw)

mp.setattr(llm_structured, "call_llm_with_fallback", _slow)

# The fake LLM needs no keys: skip the first-run API key screen.
from jobhunterx.api import routes  # noqa: E402
_real_setup = routes._setup_status
mp.setattr(routes, "_setup_status", lambda: {**_real_setup(), "llm_ready": True})

import uvicorn  # noqa: E402
from jobhunterx.api.main import app  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
