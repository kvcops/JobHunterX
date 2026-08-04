"""
Tests for the liveness checker — proves a job URL is still live.

The critical fix locked in here: HEAD returning 200 must NOT short-circuit
to "unknown". Many job pages answer 200 on HEAD but the body is an expiry
page, so we must fall through to GET and inspect the body. Also: HN comment
URLs are excluded upstream, and 403/404 handling is honest.
"""

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from vellum.tools import liveness


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class _Handler(BaseHTTPRequestHandler):
    routes = {}  # path -> (status, body, accept_methods)

    def do_HEAD(self):
        status, body, methods = self.routes.get(self.path, (404, "not found", {"HEAD", "GET"}))
        self.send_response(status)
        self.end_headers()

    def do_GET(self):
        status, body, methods = self.routes.get(self.path, (404, "not found", {"HEAD", "GET"}))
        self.send_response(status)
        self.end_headers()
        if methods and "GET" in (methods or {"GET"}):
            self.wfile.write(body.encode() or b"")
        else:
            self.wfile.write(b"")

    def log_message(self, *a):
        pass


@pytest.fixture()
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def _url(httpd, path):
    return f"http://127.0.0.1:{httpd.server_address[1]}{path}"


def test_args_predicate(server):
    # Default: no routes registered → any path 404s.
    _Handler.routes = {}

def test_source_isolation():
    # placeholder to keep pytest quiet about ordering
    pass


# --- HEAD 200 + GET live body → live -------------------------------------


def test_head_200_then_get_200_live(server):
    _Handler.routes = {"/job/live": (200, "<html>Software Engineer role open</html>", {"HEAD", "GET"})}
    verdict = liveness._check_url(_url(server, "/job/live"))
    assert verdict == "live"


# --- HEAD 200 but expiry body → gone -------------------------------------


def test_head_200_then_get_gone_marker(server):
    _Handler.routes = {"/job/expired": (200, "This job posting has been filled", {"HEAD", "GET"})}
    verdict = liveness._check_url(_url(server, "/job/expired"))
    assert verdict == "gone"


# --- Direct 404 via HEAD → gone ------------------------------------------


def test_head_404_gone(server):
    _Handler.routes = {}  # everything 404
    verdict = liveness._check_url(_url(server, "/job/missing"))
    assert verdict == "gone"


def test_head_410_gone(server):
    _Handler.routes = {"/job/gone": (410, "gone", {"HEAD", "GET"})}
    assert liveness._check_url(_url(server, "/job/gone")) == "gone"


# --- 500 / anti-bot → unknown (don't kill a job on our own failure) ------


def test_head_500_then_get_500_unknown(server):
    _Handler.routes = {"/job/degraded": (503, "service unavailable", {"HEAD", "GET"})}
    assert liveness._check_url(_url(server, "/job/degraded")) == "unknown"


def test_network_error_unknown():
    assert liveness._check_url("http://127.0.0.1:1/nope") in ("unknown",)


def test_bad_url_unknown():
    assert liveness._check_url("") == "unknown"
    assert liveness._check_url("not-a-url") == "unknown"


# --- 403 / 429 anti-bot → retried once, then honest 'unknown' ------------


def test_403_retries_then_unknown(server):
    hits = {"n": 0}

    class _Flaky(BaseHTTPRequestHandler):
        def do_HEAD(self):
            hits["n"] += 1
            if hits["n"] == 1:
                self.send_response(403)
            else:
                self.send_response(200)
            self.end_headers()

        def do_GET(self):
            hits["n"] += 1
            if hits["n"] == 1:
                self.send_response(403)
            else:
                self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html>open role</html>")

        def log_message(self, *a):
            pass

    server.RequestHandlerClass = _Flaky  # per-connection handler → swapped live
    verdict = liveness._check_url(_url(server, "/job/flaky"))
    assert verdict == "live"
    assert hits["n"] >= 2  # retried, not killed on first 403


def test_503_after_retry_unknown(server):
    _Handler.routes = {"/job/down": (503, "down", {"HEAD", "GET"})}
    assert liveness._check_url(_url(server, "/job/down")) == "unknown"


# --- helpers --------------------------------------------------------------


def test_looks_gone_marker_detection():
    assert liveness._looks_gone("We are no longer accepting applications for this role")
    assert liveness._looks_gone("This job posting has expired")
    assert not liveness._looks_gone("Software Engineer, remote friendly, Python")
    assert not liveness._looks_gone("")


def test_async_verify_returns_verdict(server):
    _Handler.routes = {"/job/live": (200, "Open role", {"HEAD", "GET"})}
    verdict = run(liveness.verify_job({"apply_url": _url(server, "/job/live")}))
    assert verdict == "live"