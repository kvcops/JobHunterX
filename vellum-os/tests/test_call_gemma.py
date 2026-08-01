"""
Unit tests for vellum.agents.job_llm_validator.call_gemma (Gemma 4 email LLM helper)
"""

import json

import pytest
from vellum.agents import job_llm_validator as jlv


def _messages():
    return [
        {"role": "system", "content": "You are a professional email writer."},
        {"role": "user", "content": "Write an outreach email."},
    ]


def test_messages_to_prompt_flattens_roles(monkeypatch):
    prompt = jlv._messages_to_prompt(_messages())
    assert "SYSTEM: You are a professional email writer." in prompt
    assert "USER: Write an outreach email." in prompt


@pytest.mark.asyncio
async def test_call_gemma_returns_gemma_shape(monkeypatch):
    async def fake_fallback(chain, msgs):
        raise AssertionError("should not fall back")

    monkeypatch.setattr(jlv, "_call_gemma_sync", lambda prompt: {"subject": "S", "body": "B"})
    monkeypatch.setattr(
        "vellum.config.llm_router.call_llm_with_fallback", fake_fallback
    )
    result = await jlv.call_gemma(_messages(), require_keys=["subject", "body"])
    assert result["model"] == jlv.GEMMA_MODEL
    assert json.loads(result["content"]) == {"subject": "S", "body": "B"}


@pytest.mark.asyncio
async def test_call_gemma_falls_back_on_error(monkeypatch):
    async def fake_fallback(chain, msgs):
        return {"content": "{}", "model": "fallback-model"}

    def boom(prompt):
        raise RuntimeError("gemma down")

    monkeypatch.setattr(jlv, "_call_gemma_sync", boom)
    monkeypatch.setattr(
        "vellum.config.llm_router.call_llm_with_fallback", fake_fallback
    )
    result = await jlv.call_gemma(_messages())
    assert result["model"] == "fallback-model"


@pytest.mark.asyncio
async def test_call_gemma_falls_back_on_missing_keys(monkeypatch):
    async def fake_fallback(chain, msgs):
        return {"content": "{}", "model": "fallback-model"}

    monkeypatch.setattr(jlv, "_call_gemma_sync", lambda prompt: {"wrong_key": 1})
    monkeypatch.setattr(
        "vellum.config.llm_router.call_llm_with_fallback", fake_fallback
    )
    result = await jlv.call_gemma(_messages(), require_keys=["subject", "body"])
    assert result["model"] == "fallback-model"


@pytest.mark.asyncio
async def test_call_gemma_falls_back_on_empty_output(monkeypatch):
    async def fake_fallback(chain, msgs):
        return {"content": "{}", "model": "fallback-model"}

    monkeypatch.setattr(jlv, "_call_gemma_sync", lambda prompt: {})
    monkeypatch.setattr(
        "vellum.config.llm_router.call_llm_with_fallback", fake_fallback
    )
    result = await jlv.call_gemma(_messages())
    assert result["model"] == "fallback-model"
