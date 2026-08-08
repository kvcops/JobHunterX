"""
Tests for jobhunterx.config.gemma.call_gemma — the ONLY LLM in the system
(Gemma 4 via Google AI Studio). No network: the genai client is faked.

Covers: budget tracking, exhaust guard, prompt assembly, token accounting,
and the no-API-key guard.
"""

import asyncio

import pytest

from jobhunterx.config import gemma as g


@pytest.fixture(autouse=True)
def reset_state():
    g._tokens_used = 0
    g._requests_today = 0
    yield


def _install_fake_client(monkeypatch, text="hello world", raise_exc=None):
    class FakeResponse:
        pass

    FakeResponse.text = text

    class FakeClient:
        calls = []

        def __init__(self, api_key=None):
            pass

        @property
        def models(self):
            class Models:
                def __init__(self, client):
                    self._client = client

                def generate_content(self, model=None, contents=None, config=None):
                    FakeClient.calls.append((model, contents, config))
                    if raise_exc:
                        raise raise_exc
                    return FakeResponse()

            return Models(self)

    import google.genai as genai_mod

    monkeypatch.setattr(genai_mod, "Client", FakeClient)
    monkeypatch.setattr(g, "get_settings", lambda: _Settings())
    return FakeClient


class _Settings:
    google_api_key = "fake-key"


@pytest.mark.asyncio
async def test_call_gemma_builds_prompt_and_returns_text(monkeypatch):
    FakeClient = _install_fake_client(monkeypatch)
    result = await g.call_gemma("be strict", "rank these jobs")
    assert result == "hello world"
    model, contents, config = FakeClient.calls[-1]
    assert model == g.MODEL
    assert "SYSTEM INSTRUCTIONS:" in contents
    assert "be strict" in contents
    assert "rank these jobs" in contents
    assert config["max_output_tokens"] == 1024


@pytest.mark.asyncio
async def test_budget_tracks_tokens(monkeypatch):
    _install_fake_client(monkeypatch, text="x" * 400)
    await g.call_gemma("s", "u")
    assert g._requests_today == 1
    assert g._tokens_used > 0
    assert g.budget_status()["requests_today"] == 1


@pytest.mark.asyncio
async def test_budget_exhausted_raises(monkeypatch):
    _install_fake_client(monkeypatch)
    g._requests_today = g._daily_cap()  # simulate reaching daily RPD limit (14,400 RPD)
    with pytest.raises(RuntimeError, match="gemma_budget_exhausted"):
        await g.call_gemma("s", "u")


@pytest.mark.asyncio
async def test_no_api_key_raises(monkeypatch):
    class NoKey:
        google_api_key = ""
    monkeypatch.setattr(g, "get_settings", lambda: NoKey())
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(g, "_genai_client", None)
    with pytest.raises(RuntimeError, match="No Google API key"):
        await g.call_gemma("s", "u")


def test_budget_status_shape():
    g._tokens_used = 100
    st = g.budget_status()
    assert st["tokens_used"] == 100
    assert st["tokens_cap"] == g._daily_cap()