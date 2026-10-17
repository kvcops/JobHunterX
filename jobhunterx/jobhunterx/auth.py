"""
Login for production mode (APP_ENV=prod). Without it this module does nothing and the app has no login.

* Users live in the same SQLite database. Passwords are stored only as scrypt hashes.
* The admin account comes from ADMIN_USERNAME / ADMIN_PASSWORD and is refreshed on every start.
  Only the admin creates other users (Users page). Other users bring their own AI keys, saved
  encrypted (SECRET_KEY); the IP-limited free pools (Kilo, LLM7) stay with the admin.
* A login is a random token in an HttpOnly cookie; the server keeps only its SHA-256, so logging
  out (or an admin disabling the user) ends it at once — also for open WebSockets.
* AuthGate (ASGI middleware) runs before everything: without a valid login, pages redirect to
  /login, API calls get 401 and WebSockets are closed. It also tells every layer below who the
  user is (config/auth_ctx.py), which is how each user only ever sees their own profiles.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from jobhunterx.config import auth_ctx
from jobhunterx.config import database as legacy
from jobhunterx.config.auth_ctx import CurrentUser
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import is_real_key, server_settings

log = get_logger("auth")

COOKIE = "jhx_session"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0, disabled INTEGER NOT NULL DEFAULT 0, active_person TEXT,
    keys_enc TEXT, created_at TEXT NOT NULL, last_login TEXT
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL, expires_at REAL NOT NULL,
    ip TEXT, user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
"""
_USERNAME_RE = re.compile(r"[A-Za-z0-9_.@-]{3,40}")
_KEY_RE = re.compile(r"[A-Za-z0-9_\-.:]{12,256}")


def enabled() -> bool:
    return server_settings().prod


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    return legacy.pooled()


# ---------------------------------------------------------------------------- passwords (scrypt, stdlib only)

_N, _R, _P = 2 ** 14, 8, 1          # ~16 MB and ~50 ms per hash: slow for guessing, fine on a 512 MB server


def _hash_sync(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def _verify_sync(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(base64.b64decode(dk)))
        return hmac.compare_digest(got, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_sync, password)


async def verify_password(password: str, stored: str) -> bool:
    return await asyncio.to_thread(_verify_sync, password, stored)


_dummy_hash: Optional[str] = None     # an unknown username costs the same time as a wrong password


def _dummy() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _hash_sync(secrets.token_urlsafe(12))
    return _dummy_hash


# ---------------------------------------------------------------------------- users' own API keys, encrypted

_fernet = None


def _cipher():
    global _fernet
    if _fernet is None:
        from cryptography.fernet import Fernet
        secret = server_settings().secret_key.strip()
        if not secret:
            path = Path(legacy.get_db_path()).parent / ".secret_key"
            if not path.exists():
                path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
                try:
                    path.chmod(0o600)
                except OSError:
                    pass
            secret = path.read_text(encoding="utf-8").strip()
        _fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
    return _fernet


def _decrypt_keys(blob: Optional[str]) -> dict[str, str]:
    if not blob:
        return {}
    try:
        data = json.loads(_cipher().decrypt(blob.encode()).decode())
        return {k: v for k, v in data.items() if k in auth_ctx.USER_KEY_PROVIDERS and isinstance(v, str)}
    except Exception:                 # SECRET_KEY changed: the old keys can't be read, the user pastes them again
        log.warning("user_keys_unreadable")
        return {}


async def user_keys(user_id: str) -> dict[str, str]:
    async with _conn() as db:
        row = await (await db.execute("SELECT keys_enc FROM users WHERE id = ?", (user_id,))).fetchone()
    return _decrypt_keys(row[0] if row else None)


async def save_user_keys(user_id: str, updates: dict[str, str]) -> dict[str, str]:
    """Set ("" removes) some of a user's own keys. Returns the full set."""
    keys = await user_keys(user_id)
    for provider, key in updates.items():
        if provider not in auth_ctx.USER_KEY_PROVIDERS:
            continue
        key = (key or "").strip()
        if key and not (is_real_key(key) and _KEY_RE.fullmatch(key)):
            raise HTTPException(422, f"The {provider} key does not look right — copy the whole key again.")
        if key:
            keys[provider] = key
        else:
            keys.pop(provider, None)
    blob = _cipher().encrypt(json.dumps(keys).encode()).decode() if keys else None
    async with _conn() as db:
        await db.execute("UPDATE users SET keys_enc = ? WHERE id = ?", (blob, user_id))
        await db.commit()
    _row_cache.clear()
    return keys


# ---------------------------------------------------------------------------- startup

async def init() -> None:
    """Create the tables, make sure the admin from .env exists (password refreshed) and give it the profiles that
    were made before login existed. Refuses to start in prod mode without admin credentials."""
    st = server_settings()
    if not st.prod:
        return
    username, password = st.admin_username.strip(), st.admin_password
    if not _USERNAME_RE.fullmatch(username) or len(password) < 8:
        raise RuntimeError("APP_ENV=prod needs ADMIN_USERNAME (3-40 letters, digits or _.@-) and ADMIN_PASSWORD "
                           "(at least 8 characters) in the .env file.")
    async with _conn() as db:
        await db.executescript(_SCHEMA)
        cur = await db.execute("PRAGMA table_info(users)")
        if "signup" not in {r[1] for r in await cur.fetchall()}:     # 1 = made their own account on /signup
            await db.execute("ALTER TABLE users ADD COLUMN signup INTEGER NOT NULL DEFAULT 0")
        await db.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (time.time(),))
        row = await (await db.execute("SELECT id, password_hash FROM users WHERE is_admin = 1 ORDER BY created_at LIMIT 1")).fetchone()
        same = await (await db.execute("SELECT id, is_admin FROM users WHERE username = ?", (username,))).fetchone()
        if same and not same[1]:
            raise RuntimeError(f"ADMIN_USERNAME '{username}' is already a normal user. Choose another admin name.")
        if row is None:
            admin_id = str(uuid.uuid4())
            await db.execute("INSERT INTO users (id, username, password_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)",
                             (admin_id, username, await hash_password(password), _now()))
            log.info("admin_created", username=username)
        else:
            admin_id = row[0]
            changes: dict[str, Any] = {"username": username}
            if not await verify_password(password, row[1]):
                changes["password_hash"] = await hash_password(password)
                await db.execute("DELETE FROM auth_sessions WHERE user_id = ?", (admin_id,))   # old password: sign out
                log.info("admin_password_updated")
            await db.execute(f"UPDATE users SET {', '.join(f'{k} = ?' for k in changes)}, disabled = 0 WHERE id = ?",
                             (*changes.values(), admin_id))
        # profiles from before login existed belong to the admin
        claimed = (await db.execute("UPDATE people SET user_id = ? WHERE user_id IS NULL", (admin_id,))).rowcount
        if claimed:
            from jobhunterx.config import app_state
            active = app_state.get("people.active")
            await db.execute("UPDATE users SET active_person = COALESCE(active_person, ?) WHERE id = ?", (active, admin_id))
            log.info("profiles_given_to_admin", count=claimed)
        await db.commit()


async def admin_user() -> Optional[CurrentUser]:
    """The admin as a CurrentUser (for background work in prod mode: the watchlist checker)."""
    async with _conn() as db:
        row = await (await db.execute("SELECT id, username, active_person FROM users WHERE is_admin = 1 "
                                      "ORDER BY created_at LIMIT 1")).fetchone()
    return CurrentUser(id=row[0], username=row[1], is_admin=True, active_person=row[2]) if row else None


# ---------------------------------------------------------------------------- sessions

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_row_cache: dict[str, tuple[float, Optional[dict]]] = {}     # token hash -> (cached at, row); a few seconds only
_ROW_TTL_S = 5.0


def forget_user(user_id: str) -> None:
    """Drop this user's cached login rows (after they switch profile, so every tab and request sees the new one)."""
    for th, (_, row) in list(_row_cache.items()):
        if row and row.get("id") == user_id:
            _row_cache.pop(th, None)


async def _session_row(th: str) -> Optional[dict]:
    hit = _row_cache.get(th)
    now = time.time()
    if hit and now - hit[0] < _ROW_TTL_S:
        return hit[1]
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT u.id, u.username, u.is_admin, u.signup, u.active_person, u.keys_enc, s.expires_at, p.id AS person_ok "
            "FROM auth_sessions s JOIN users u ON u.id = s.user_id "
            "LEFT JOIN people p ON p.id = u.active_person AND p.user_id = u.id "
            "WHERE s.token_hash = ? AND s.expires_at > ? AND u.disabled = 0", (th, now))).fetchone()
    data = dict(row) if row else None
    if len(_row_cache) > 2000:
        _row_cache.clear()
    _row_cache[th] = (now, data)
    return data


async def user_for_token(token: Optional[str]) -> tuple[Optional[CurrentUser], Optional[str], float]:
    """(user, token hash, expires at) for a cookie value; (None, None, 0) when it is not a valid login."""
    if not token or len(token) > 200:
        return None, None, 0.0
    th = _token_hash(token)
    row = await _session_row(th)
    if not row:
        return None, None, 0.0
    user = CurrentUser(id=row["id"], username=row["username"], is_admin=bool(row["is_admin"]),
                       self_signup=bool(row["signup"]) and not row["is_admin"], active_person=row["person_ok"], keys={} if row["is_admin"] else _decrypt_keys(row["keys_enc"]))
    if user.active_person is None:   # never opened one, or it was deleted: open their most recent profile
        from jobhunterx import storage
        mine = await storage.people_of_user(user.id)
        if mine:
            user.active_person = mine[0]
            async with _conn() as db:
                await db.execute("UPDATE users SET active_person = ? WHERE id = ?", (mine[0], user.id))
                await db.commit()
            _row_cache.pop(th, None)
    return user, th, float(row["expires_at"])


async def _new_session(user_id: str, request: Request) -> tuple[str, float]:
    token = secrets.token_urlsafe(32)
    expires = time.time() + max(0.25, server_settings().session_hours) * 3600
    async with _conn() as db:
        await db.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (time.time(),))
        await db.execute("INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at, ip, user_agent) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (_token_hash(token), user_id, _now(), expires, _client_ip(request),
                                                       (request.headers.get("user-agent") or "")[:200]))
        await db.execute("UPDATE users SET last_login = ? WHERE id = ?", (_now(), user_id))
        await db.commit()
    return token, expires


async def end_sessions(user_id: Optional[str] = None, token_hash: Optional[str] = None, keep: Optional[str] = None) -> None:
    """Sign out one login, or every login of a user (except `keep`), and close their live connections."""
    async with _conn() as db:
        if token_hash:
            await db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
        elif user_id:
            await db.execute("DELETE FROM auth_sessions WHERE user_id = ? AND token_hash != ?", (user_id, keep or ""))
        await db.commit()
    _row_cache.clear()
    from jobhunterx.agents import live_view
    from jobhunterx.api.ws import manager
    await manager.close_for(user_id=None if token_hash else user_id, token_hash=token_hash, keep=keep)
    await live_view.close_for(user_id=None if token_hash else user_id, token_hash=token_hash, keep=keep)


def _cookie_secure(request_scope: dict) -> bool:
    mode = server_settings().cookie_secure.strip().lower()
    if mode in ("true", "1", "yes"):
        return True
    if mode in ("false", "0", "no"):
        return False
    headers = dict(request_scope.get("headers") or [])
    proto = headers.get(b"x-forwarded-proto", b"").decode().split(",")[0].strip()
    return request_scope.get("scheme") == "https" or proto == "https"


def _samesite() -> str:
    v = server_settings().cookie_samesite.strip().lower()
    return v if v in ("strict", "lax", "none") else "strict"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")) or "?"


# ---------------------------------------------------------------------------- guessing protection

_fails: dict[str, list[float]] = {}
_FAIL_WINDOW_S, _FAIL_LIMIT, _LOCK_S = 900.0, 5, 900.0


def _locked(keys: list[str]) -> Optional[int]:
    now = time.time()
    worst = 0.0
    for k in keys:
        recent = [t for t in _fails.get(k, []) if now - t < _FAIL_WINDOW_S]
        _fails[k] = recent
        if len(recent) >= _FAIL_LIMIT:
            worst = max(worst, recent[-1] + _LOCK_S - now)
    return int(worst) + 1 if worst > 0 else None


def _failed(keys: list[str]) -> None:
    now = time.time()
    if len(_fails) > 5000:
        _fails.clear()
    for k in keys:
        _fails.setdefault(k, []).append(now)


# ---------------------------------------------------------------------------- the gate (ASGI middleware)

_PUBLIC = {"/login", "/login.html", "/js/login.js", "/signup", "/signup.html", "/js/signup.js", "/styles.css", "/favicon.ico",
           "/healthz", "/api/auth/login", "/api/auth/signup", "/api/auth/me", "/sw.js", "/service-worker.js"}
_PUBLIC_PREFIX = ("/assets/", "/vendor/fonts/")
_SECURITY_HEADERS = [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                     (b"referrer-policy", b"same-origin"), (b"cross-origin-opener-policy", b"same-origin"),
                     (b"cross-origin-resource-policy", b"same-origin"),
                     (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=(), usb=()")]


def _inline_script_hashes() -> str:
    """CSP hashes of the small inline scripts in our own pages (read from the files, so an edit can't break them)."""
    web = Path(__file__).resolve().parent / "web"
    out = []
    for name in ("index.html", "login.html"):
        try:
            html_text = (web / name).read_text(encoding="utf-8")
        except OSError:
            continue
        for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script>", html_text, re.S):
            if "src=" in attrs or not body.strip():
                continue
            out.append("'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'")
    return " ".join(dict.fromkeys(out))


_SCRIPT_HASHES = _inline_script_hashes()


def _csp(host: str, https: bool) -> bytes:
    """Only this site's own code runs; pages talk only to this server (also over WebSockets); no framing, no plugins."""
    ws = f"wss://{host}" + ("" if https else f" ws://{host}")
    parts = [
        "default-src 'self'", f"script-src 'self' {_SCRIPT_HASHES}".strip(),
        "style-src 'self' 'unsafe-inline'",              # Preact style attributes
        "img-src 'self' data: blob:", "font-src 'self'", f"connect-src 'self' {ws}", "worker-src 'self' blob:",
        "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'",
    ]
    if https:
        parts.append("upgrade-insecure-requests")
    return "; ".join(parts).encode()


def _is_https(scope: dict) -> bool:
    if scope.get("scheme") in ("https", "wss"):
        return True
    headers = dict(scope.get("headers") or [])
    return headers.get(b"x-forwarded-proto", b"").decode().split(",")[0].strip() == "https"


def _must_upgrade(scope: dict) -> bool:
    """Plain http that should be https (FORCE_HTTPS). auto: only when a proxy in front reports the visit was http —
    then https exists for this address; without a proxy or TLS nothing could answer on https."""
    mode = server_settings().force_https.strip().lower()
    if mode in ("false", "0", "no") or _is_https(scope) or scope.get("path") == "/healthz":
        return False
    if mode in ("true", "1", "yes"):
        return True
    headers = dict(scope.get("headers") or [])
    return headers.get(b"x-forwarded-proto", b"").decode().split(",")[0].strip() == "http"


def _cookie_token(scope: dict) -> Optional[str]:
    for name, value in scope.get("headers") or []:
        if name == b"cookie":
            try:
                c = SimpleCookie()
                c.load(value.decode("latin-1"))
                if COOKIE in c:
                    return c[COOKIE].value
            except Exception:
                return None
    return None


class AuthGate:
    """Every request and WebSocket passes here first in prod mode (a no-op otherwise)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not enabled():
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or "/"
        if scope["type"] == "http" and path.startswith(_PUBLIC_PREFIX) and not _must_upgrade(scope):
            await self.app(scope, receive, send)     # logo, fonts, icons: no login lookup needed
            return
        if scope["type"] == "http" and _must_upgrade(scope):
            host = dict(scope.get("headers") or []).get(b"host", b"").decode()
            qs = scope.get("query_string", b"").decode()
            await send({"type": "http.response.start", "status": 308,
                        "headers": [(b"location", f"https://{host}{path}{'?' + qs if qs else ''}".encode()), *_SECURITY_HEADERS]})
            await send({"type": "http.response.body", "body": b""})
            return
        user, th, exp = await user_for_token(_cookie_token(scope))
        if scope["type"] == "websocket":
            if user is None:
                msg = await receive()
                if msg.get("type") == "websocket.connect":
                    await send({"type": "websocket.accept"})
                    await send({"type": "websocket.close", "code": 4401})    # the app sends you to the login page
                return
            scope.setdefault("state", {})["auth"] = {"user_id": user.id, "token_hash": th, "expires": exp}
            token = auth_ctx.set_current(user)
            try:
                await self.app(scope, receive, send)
            finally:
                auth_ctx.reset(token)
            return

        public = path in _PUBLIC or path.startswith(_PUBLIC_PREFIX) or scope.get("method") == "OPTIONS"
        if user is None and not public:
            await self._deny(scope, receive, send, path)
            return
        if user is not None and path in ("/login", "/login.html", "/signup", "/signup.html"):
            await self._redirect(send, "/")
            return
        api_or_page = path.startswith("/api/") or not path.rsplit("/", 1)[-1].count(".") or path.endswith(".html")
        https = _is_https(scope)
        extra = [(b"content-security-policy", _csp(dict(scope.get("headers") or []).get(b"host", b"").decode(), https))]
        hsts = server_settings().hsts_seconds
        if https and hsts > 0:          # browsers only honour HSTS received over https
            extra.append((b"strict-transport-security", f"max-age={hsts}; includeSubDomains".encode()))

        async def send_wrapped(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers += _SECURITY_HEADERS + extra
                if api_or_page:     # data and pages are never kept by the browser (nothing left after logout)
                    headers = [h for h in headers if h[0].lower() not in (b"cache-control", b"etag", b"last-modified")]
                    headers += [(b"cache-control", b"no-store, max-age=0"), (b"pragma", b"no-cache")]
                message = {**message, "headers": headers}
            await send(message)

        token = auth_ctx.set_current(user)
        try:
            scope.setdefault("state", {})["auth"] = {"user_id": user.id if user else None, "token_hash": th, "expires": exp}
            await self.app(scope, receive, send_wrapped)
        finally:
            auth_ctx.reset(token)

    @staticmethod
    async def _redirect(send, location: str) -> None:
        await send({"type": "http.response.start", "status": 303,
                    "headers": [(b"location", location.encode()), (b"cache-control", b"no-store"), *_SECURITY_HEADERS]})
        await send({"type": "http.response.body", "body": b""})

    async def _deny(self, scope, receive, send, path: str) -> None:
        if path.startswith("/api/") or scope.get("method") not in ("GET", "HEAD"):
            body = json.dumps({"error": {"code": "unauthorized", "message": "Please sign in.", "details": None}}).encode()
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store"), *_SECURITY_HEADERS]})
            await send({"type": "http.response.body", "body": body})
            return
        await self._redirect(send, "/login")       # pages, the API docs, any guessed address: only the login page


def require_admin() -> None:
    """Raise 403 unless the request is from the admin (always allowed without login)."""
    if not enabled():
        return
    user = auth_ctx.current()
    if user is None or not user.is_admin:
        raise HTTPException(403, "Only the admin can do this.")


# ---------------------------------------------------------------------------- API

router = APIRouter(prefix="/api/auth")


def _public(user: CurrentUser) -> dict:
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin, "self_signup": user.self_signup}


def signup_open() -> bool:
    return enabled() and server_settings().allow_signup


@router.get("/me")
async def me():
    user = auth_ctx.current()
    return {"enabled": enabled(), "signup": signup_open(), "user": _public(user) if user else None}


def _signed_in(row_id: str, username: str, is_admin: bool, token: str, expires: float, request: Request, status: int = 200,
               self_signup: bool = False) -> JSONResponse:
    resp = JSONResponse({"user": {"id": row_id, "username": username, "is_admin": is_admin, "self_signup": self_signup}},
                        status_code=status, headers={"Cache-Control": "no-store"})
    resp.set_cookie(COOKIE, token, max_age=int(expires - time.time()), httponly=True, samesite=_samesite(),
                    secure=_cookie_secure(request.scope) or _samesite() == "none", path="/")
    return resp


class LoginIn(BaseModel):
    username: str = Field(..., max_length=80)
    password: str = Field(..., max_length=200)


@router.post("/login")
async def login(body: LoginIn, request: Request):
    if not enabled():
        raise HTTPException(404, "Login is off on this server.")
    username = body.username.strip()
    keys = [f"ip:{_client_ip(request)}", f"user:{username.lower()}"]
    wait = _locked(keys)
    if wait:
        raise HTTPException(429, f"Too many wrong tries. Try again in {max(1, wait // 60)} min.")
    async with _conn() as db:
        row = await (await db.execute("SELECT id, username, password_hash, is_admin, disabled FROM users WHERE username = ?",
                                      (username,))).fetchone()
    ok = await verify_password(body.password, row[2] if row else _dummy())
    if not row or not ok or row[4]:
        _failed(keys)
        log.warning("login_failed", username=username[:40], ip=keys[0][3:])
        raise HTTPException(401, "Wrong username or password.")
    _fails.pop(keys[1], None)
    token, expires = await _new_session(row[0], request)
    log.info("login", username=row[1])
    return _signed_in(row[0], row[1], bool(row[3]), token, expires, request)


_signups: dict[str, list[float]] = {}
_SIGNUPS_PER_HOUR = 5


@router.post("/signup", status_code=201)
async def signup(body: LoginIn, request: Request):
    """Anyone can make an account (ALLOW_SIGNUP). They bring their own AI keys, and auto-apply runs only in their own
    Browser Use cloud browser — never on this server's memory."""
    if not signup_open():
        raise HTTPException(404, "Sign-up is closed on this server. Ask the admin for an account.")
    username = body.username.strip()
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Username: 3-40 letters, digits or _ . @ -")
    if len(body.password) < 8:
        raise HTTPException(422, "Password: at least 8 characters.")
    ip = _client_ip(request)
    now = time.time()
    recent = [t for t in _signups.get(ip, []) if now - t < 3600]
    if len(recent) >= _SIGNUPS_PER_HOUR:
        raise HTTPException(429, "Too many new accounts from this address. Try again in an hour.")
    async with _conn() as db:
        if await (await db.execute("SELECT 1 FROM users WHERE username = ?", (username,))).fetchone():
            raise HTTPException(409, "That username is taken. Pick another one.")
        uid = str(uuid.uuid4())
        await db.execute("INSERT INTO users (id, username, password_hash, is_admin, signup, created_at) VALUES (?, ?, ?, 0, 1, ?)",
                         (uid, username, await hash_password(body.password), _now()))
        await db.commit()
    if len(_signups) > 5000:
        _signups.clear()
    _signups[ip] = recent + [now]
    token, expires = await _new_session(uid, request)
    log.info("user_signed_up", username=username)
    return _signed_in(uid, username, False, token, expires, request, status=201, self_signup=True)


@router.post("/logout")
async def logout(request: Request):
    th = ((request.scope.get("state") or {}).get("auth") or {}).get("token_hash")
    if th:
        await end_sessions(token_hash=th)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/", httponly=True, samesite=_samesite(), secure=_cookie_secure(request.scope))
    # the browser drops this site's storage, cookies and cache (secure pages and localhost)
    resp.headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'
    resp.headers["Cache-Control"] = "no-store"
    return resp


class PasswordIn(BaseModel):
    current: str = Field(..., max_length=200)
    new: str = Field(..., min_length=8, max_length=200)


@router.post("/password")
async def change_password(body: PasswordIn, request: Request):
    user = auth_ctx.current()
    if not enabled() or user is None:
        raise HTTPException(404, "Login is off on this server.")
    if user.is_admin:
        raise HTTPException(409, "The admin password is set by ADMIN_PASSWORD in the server's .env file.")
    async with _conn() as db:
        row = await (await db.execute("SELECT password_hash FROM users WHERE id = ?", (user.id,))).fetchone()
    if not row or not await verify_password(body.current, row[0]):
        raise HTTPException(403, "Your current password is not right.")
    async with _conn() as db:
        await db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (await hash_password(body.new), user.id))
        await db.commit()
    th = ((request.scope.get("state") or {}).get("auth") or {}).get("token_hash")
    await end_sessions(user_id=user.id, keep=th)          # other devices sign in again
    return {"ok": True}


# --- admin: users -----------------------------------------------------------

def _users_admin() -> None:
    if not enabled():
        raise HTTPException(404, "Login is off on this server.")
    require_admin()


class UserIn(BaseModel):
    username: str = Field(..., max_length=40)
    password: str = Field(..., min_length=8, max_length=200)


class UserPatch(BaseModel):
    password: Optional[str] = Field(None, min_length=8, max_length=200)
    disabled: Optional[bool] = None


async def _user_rows() -> list[dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        rows = [dict(r) for r in await (await db.execute(
            "SELECT u.id, u.username, u.is_admin, u.disabled, u.signup, u.created_at, u.last_login, u.keys_enc, "
            "(SELECT COUNT(*) FROM people p WHERE p.user_id = u.id) AS profiles, "
            "(SELECT COUNT(*) FROM auth_sessions s WHERE s.user_id = u.id AND s.expires_at > ?) AS signed_in "
            "FROM users u ORDER BY u.is_admin DESC, u.created_at", (time.time(),))).fetchall()]
    for r in rows:   # which providers have a key — never the keys themselves
        r["keys"] = sorted(_decrypt_keys(r.pop("keys_enc")))
        r["is_admin"], r["disabled"], r["signup"] = bool(r["is_admin"]), bool(r["disabled"]), bool(r["signup"])
    return rows


async def _stop_work(user_id: str) -> None:
    """A blocked or deleted user's searches stop and their browsers close (a cloud browser bills their key)."""
    from jobhunterx import storage
    from jobhunterx.agents import browser_agent as ba
    from jobhunterx.services.search import manager as search_manager
    for pid in await storage.people_of_user(user_id):
        await search_manager.cancel_person(pid)
    for jid, sess in list(ba._sessions.items()):
        if sess.data.get("user_id") == user_id:
            try:
                await ba.close(jid)
            except Exception as exc:
                log.warning("stop_user_browser_failed", error=str(exc)[:120])


@router.get("/users")
async def list_users():
    _users_admin()
    return {"users": await _user_rows()}


@router.post("/users", status_code=201)
async def create_user(body: UserIn):
    _users_admin()
    username = body.username.strip()
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Username: 3-40 letters, digits or _ . @ -")
    async with _conn() as db:
        if await (await db.execute("SELECT 1 FROM users WHERE username = ?", (username,))).fetchone():
            raise HTTPException(409, "That username is taken.")
        await db.execute("INSERT INTO users (id, username, password_hash, is_admin, created_at) VALUES (?, ?, ?, 0, ?)",
                         (str(uuid.uuid4()), username, await hash_password(body.password), _now()))
        await db.commit()
    log.info("user_created", username=username)
    return {"users": await _user_rows()}


async def _target(user_id: str) -> dict:
    async with _conn() as db:
        row = await (await db.execute("SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,))).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    if row[2]:
        raise HTTPException(409, "The admin account is managed by ADMIN_USERNAME / ADMIN_PASSWORD in .env.")
    return {"id": row[0], "username": row[1]}


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: UserPatch):
    _users_admin()
    target = await _target(user_id)
    async with _conn() as db:
        if body.password is not None:
            await db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (await hash_password(body.password), user_id))
        if body.disabled is not None:
            await db.execute("UPDATE users SET disabled = ? WHERE id = ?", (int(body.disabled), user_id))
        await db.commit()
    if body.password is not None or body.disabled:
        await end_sessions(user_id=user_id)          # new password / disabled: signed out everywhere now
    if body.disabled:
        await _stop_work(user_id)
    log.info("user_updated", username=target["username"], password=body.password is not None, disabled=body.disabled)
    return {"users": await _user_rows()}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user and everything they made (profiles, jobs, documents, searches)."""
    _users_admin()
    target = await _target(user_id)
    await end_sessions(user_id=user_id)
    await _stop_work(user_id)
    from jobhunterx import storage
    from jobhunterx.services.search import manager as search_manager
    token = auth_ctx.set_current(CurrentUser(id=user_id, username=target["username"], is_admin=False))
    try:
        for pid in await storage.people_of_user(user_id):
            await search_manager.cancel_person(pid)
            await storage.delete_person(pid)
    finally:
        auth_ctx.reset(token)
    async with _conn() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
    _row_cache.clear()
    log.info("user_deleted", username=target["username"])
    return {"users": await _user_rows()}
