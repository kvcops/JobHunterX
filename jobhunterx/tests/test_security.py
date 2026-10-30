"""
Unit tests for API key security and privacy controls.
"""

from jobhunterx.api.routes import _mask


def test_mask():
    assert _mask("") == ""
    assert _mask(None) == ""
    assert _mask("12345") == "******"
    assert _mask("sk_test_123456789") == "********6789"


def test_desktop_mode_answers_only_requests_addressed_to_this_computer(monkeypatch):
    """Desktop app: a page that points its own domain at 127.0.0.1 (DNS rebinding) sends that domain in Host."""
    from fastapi.testclient import TestClient
    from jobhunterx.api.main import app
    from jobhunterx.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "desktop", True)
    with TestClient(app, base_url="http://127.0.0.1:47821") as c:
        assert c.get("/api/settings").status_code == 200
        assert c.get("/api/settings", headers={"host": "localhost:47821"}).status_code == 200
        assert c.get("/api/settings", headers={"host": "evil.example:47821"}).status_code == 403
    monkeypatch.setattr(get_settings(), "desktop", False)          # the normal web app is unchanged
    with TestClient(app, base_url="http://127.0.0.1:9000") as c:
        assert c.get("/api/settings", headers={"host": "my-pc.lan:9000"}).status_code == 200
