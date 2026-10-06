"""
Safe outbound HTTP for untrusted URLs (search results, job pages).

* Only http/https.
* SSRF guard: the hostname must resolve exclusively to public addresses
  (no loopback, private, link-local, multicast, reserved) — checked on every
  redirect hop, since redirects are followed manually.
* Response size cap and timeouts.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings

log = get_logger("net")

_UA = "Mozilla/5.0 (compatible; JobHunterX/2.0; +local-first job research)"
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 5


class UnsafeURLError(ValueError):
    pass


@dataclass
class FetchResult:
    url: str                       # final URL after redirects
    status: int = 0
    text: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300 and not self.error


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast
                or addr.is_reserved or addr.is_unspecified)


async def assert_safe_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeURLError(f"Unsupported URL: {url[:80]}")
    if get_settings().allow_private_network_fetch:
        return
    host = p.hostname
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80),
                                                             type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed for {host}") from exc
    ips = {i[4][0] for i in infos}
    if not ips or not all(_is_public_ip(ip) for ip in ips):
        raise UnsafeURLError(f"Refusing to fetch non-public address for {host}")


_shared: Optional[tuple[asyncio.AbstractEventLoop, httpx.AsyncClient]] = None


def _client() -> httpx.AsyncClient:
    """One pooled client per event loop: hundreds of board / page requests per search reuse warm connections
    instead of paying a new TCP + TLS handshake each time."""
    global _shared
    loop = asyncio.get_running_loop()
    if _shared is None or _shared[0] is not loop or _shared[1].is_closed:
        _shared = (loop, httpx.AsyncClient(follow_redirects=False,
                                           limits=httpx.Limits(max_connections=48, max_keepalive_connections=24,
                                                               keepalive_expiry=30)))
    return _shared[1]


def _blocked(res: FetchResult) -> bool:
    """A bot wall rather than a real answer: worth one retry that looks like a real Chrome on the wire."""
    if res.status in (403, 429, 503) or (res.status == 202 and not res.text.strip()):
        return True
    head = res.text[:4000].lower() if res.ok else ""
    return bool(res.headers.get("cf-mitigated")) or "<title>just a moment" in head or "cf-browser-verification" in head


async def fetch(url: str, *, method: str = "GET", json_body: Any = None, timeout: Optional[float] = None,
                accept: str = "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                client: Optional[httpx.AsyncClient] = None, headers: Optional[dict[str, str]] = None,
                content: Optional[str] = None) -> FetchResult:
    """Fetch with SSRF checks on every hop. Never raises for HTTP/network errors.

    A page that answers with a bot wall (403 / 429 / 503, a Cloudflare challenge) gets one more try through curl_cffi,
    which sends the same TLS and HTTP/2 fingerprint as a real Chrome — many career sites only block the plain
    Python fingerprint."""
    timeout = timeout or get_settings().fetch_timeout_s
    res = await _fetch_plain(url, method, json_body, timeout, accept, client or _client(), headers, content)
    if method == "GET" and _blocked(res):
        retry = await _fetch_browserlike(url, timeout, accept, headers)
        if retry is not None and retry.ok and not _blocked(retry):
            log.debug("fetch_unblocked", url=url[:80], first=res.status)
            return retry
    return res


async def _fetch_plain(url: str, method: str, json_body: Any, timeout: float, accept: str,
                       client: httpx.AsyncClient, extra: Optional[dict[str, str]] = None,
                       content: Optional[str] = None) -> FetchResult:
    headers = {"User-Agent": _UA, "Accept": accept, **(extra or {})}
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        try:
            await assert_safe_url(current)
        except UnsafeURLError as exc:
            return FetchResult(url=current, error=str(exc))
        try:
            body_kw: dict[str, Any] = {"content": content} if content is not None else {"json": json_body}
            async with client.stream(method, current, headers=headers, timeout=timeout, **body_kw) as resp:
                if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("location"):
                    current = urljoin(current, resp.headers["location"])
                    if resp.status_code == 303:
                        method, json_body, content = "GET", None, None
                    continue
                chunks, size = [], 0
                async for chunk in resp.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        break
                    chunks.append(chunk)
                body = b"".join(chunks)
                enc = resp.encoding or "utf-8"
                return FetchResult(url=str(resp.url), status=resp.status_code,
                                   text=body.decode(enc, errors="replace"),
                                   headers={k.lower(): v for k, v in resp.headers.items()})
        except (httpx.HTTPError, OSError) as exc:
            return FetchResult(url=current, error=f"{type(exc).__name__}: {str(exc)[:120]}")
    return FetchResult(url=current, error="Too many redirects")


_cffi: Optional[tuple[asyncio.AbstractEventLoop, Any]] = None


async def _fetch_browserlike(url: str, timeout: float, accept: str,
                             extra: Optional[dict[str, str]] = None) -> Optional[FetchResult]:
    """GET through curl_cffi impersonating Chrome; redirects followed by hand so every hop passes the SSRF check."""
    global _cffi
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        return None
    loop = asyncio.get_running_loop()
    if _cffi is None or _cffi[0] is not loop:
        _cffi = (loop, AsyncSession(impersonate="chrome"))
    session = _cffi[1]
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        try:
            await assert_safe_url(current)
        except UnsafeURLError as exc:
            return FetchResult(url=current, error=str(exc))
        try:
            r = await session.get(current, timeout=timeout, allow_redirects=False, headers={"Accept": accept, **(extra or {})},
                                  max_recv_speed=0)
        except Exception as exc:                       # curl errors: treat like any network failure
            return FetchResult(url=current, error=f"{type(exc).__name__}: {str(exc)[:120]}")
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
            current = urljoin(current, r.headers["location"])
            continue
        body = r.content[:MAX_BYTES]
        return FetchResult(url=str(r.url), status=r.status_code, text=body.decode(r.encoding or "utf-8", errors="replace"),
                           headers={k.lower(): v for k, v in r.headers.items()})
    return FetchResult(url=current, error="Too many redirects")


async def fetch_json(url: str, **kw) -> tuple[Any, FetchResult]:
    import json
    res = await fetch(url, accept="application/json", **kw)
    if not res.ok:
        return None, res
    try:
        return json.loads(res.text), res
    except ValueError:
        return None, FetchResult(url=res.url, status=res.status, error="Invalid JSON")
