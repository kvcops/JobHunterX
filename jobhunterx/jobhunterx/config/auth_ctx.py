"""
Who is making this request (production mode only).

A ContextVar holds the signed-in user for the request and for every task started from it
(asyncio copies context into new tasks, and the browser worker thread gets it through
run_coroutine_threadsafe). Without APP_ENV=prod nothing is ever set here, and every helper
answers exactly as the single-user app always did.

Kept free of heavy imports: settings, the LLM router and storage all read it on hot paths.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Optional

# Providers whose free pools are limited per server IP: one user would use up everyone's share.
SHARED_POOLS = ("kilo", "llm7")
# Keys a non-admin user brings themselves (BYOK). Kilo is not here: its free pool is IP-limited.
USER_KEY_PROVIDERS = ("google", "nvidia", "groq", "mistral", "tinyfish", "tavily", "exa", "brave", "browser_use", "adzuna")


@dataclass
class CurrentUser:
    id: str
    username: str
    is_admin: bool
    active_person: Optional[str] = None
    self_signup: bool = False               # made their own account on /signup: auto-apply only with their own Browser Use key
    keys: dict[str, str] = field(default_factory=dict)      # provider -> key (decrypted; non-admins only)
    _settings: Any = None

    def settings_view(self, base: Any) -> Any:
        """The server settings with this user's own keys in place of the server's (built once per request)."""
        if self._settings is None:
            upd = {f"{p}_api_key": self.keys.get(p) or None for p in USER_KEY_PROVIDERS}
            upd["kilo_api_key"] = None
            upd["browser_cdp_url"] = ""         # the admin's own Chrome (their logins) is never anyone else's
            self._settings = base.model_copy(update=upd)
        return self._settings


_current: ContextVar[Optional[CurrentUser]] = ContextVar("jhx_current_user", default=None)


def current() -> Optional[CurrentUser]:
    return _current.get()


def set_current(user: Optional[CurrentUser]):
    return _current.set(user)


def reset(token) -> None:
    _current.reset(token)


def restricted() -> Optional[CurrentUser]:
    """The signed-in non-admin user (they use only their own keys), or None."""
    u = _current.get()
    return u if u is not None and not u.is_admin else None


def shared_pools_allowed() -> bool:
    return restricted() is None


def scope() -> str:
    """Suffix that keeps per-key limits apart: a user's own key has its own rate limits."""
    u = restricted()
    return f"@{u.id}" if u else ""


def env_key(*names: str) -> Optional[str]:
    """A key from the process environment — never for a non-admin user (those are the server's keys)."""
    if restricted() is not None:
        return None
    return next((v for v in (os.getenv(n) for n in names) if v), None)
