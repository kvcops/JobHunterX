"""Sites where applying needs an account (sign in / create an account first).

Two sources, no fixed list of sites: the job reader (the AI judges it from the posting and its address), and the
browser agent — when it meets a login wall on a site, that site is remembered and every later job there is marked
too. Auto-apply can't get past a login; the app says so up front and offers the documents instead.
"""

from __future__ import annotations

import json
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.config.settings import _BASE_DIR

_FILE = _BASE_DIR / "data" / "account_walls.json"


def site_of(url: str) -> str:
    """The site a job belongs to: its host without "www." (acme.wd5.myworkdayjobs.com stays itself — each employer's
    portal is learned on its own; the reader covers the first job on a new one)."""
    try:
        host = (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""
    return host.removeprefix("www.")


def _load() -> dict:
    try:
        return json.loads(_FILE.read_text())
    except Exception:
        return {}


def learned(url: str) -> bool:
    s = site_of(url)
    return bool(s) and s in _load()


def learn(url: str, why: str = "login") -> None:
    s = site_of(url)
    if not s:
        return
    data = _load()
    if s in data:
        return
    data[s] = why
    try:
        _FILE.parent.mkdir(parents=True, exist_ok=True)
        _FILE.write_text(json.dumps(data))
    except OSError:
        pass


def needs_account(job) -> bool:
    url: Optional[str] = getattr(job, "apply_url", "") or getattr(job, "canonical_url", "")
    return bool(job.requirements.apply_needs_account or learned(url))
