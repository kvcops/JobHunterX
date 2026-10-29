"""Router health rules for errors seen live: NIM models a free key can't call, unpaid providers, silent timeouts."""

from jobhunterx.config import models as M


def setup_function():
    M._health.clear()
    M._bad_keys.clear()


def test_not_found_for_account_rests_only_that_model():
    rest = M.mark_failure("nim/nvidia/nemotron-3-super-120b-a12b", "404 {\"detail\":\"Function 'ac74': Not found for account 'gtv'\"}")
    assert rest == 12 * 3600 and "not available on this account" in M.resting("nim/nvidia/nemotron-3-super-120b-a12b")
    assert M.resting("nim/openai/gpt-oss-20b") is None and not M.key_rejected("nvidia")


def test_402_usage_credits_rests_the_provider(monkeypatch):
    monkeypatch.setattr(M, "provider_key", lambda p: "k" * 20)
    M.mark_failure("ollama/gpt-oss:20b", '402 {"error":{"message":"Add usage credits to use cloud models"}}')
    assert M.key_rejected("ollama")


def test_a_timeout_without_message_still_rests_the_model():
    assert M.mark_failure("nim/nvidia/nemotron-3-ultra-550b-a55b", "ReadTimeout") == 120
    assert M.resting("nim/nvidia/nemotron-3-ultra-550b-a55b")


def test_nim_catalog_has_only_models_a_free_key_can_call():
    nim = {m["id"] for m in M.CATALOG if m["provider"] == "nvidia"}
    assert "nim/nvidia/nemotron-3-ultra-550b-a55b" in nim
    assert not nim & {"nim/nvidia/nemotron-3-super-120b-a12b", "nim/nvidia/nemotron-nano-3-30b-a3b", "nim/z-ai/glm-5.3-flash"}
    assert all(m in M.BY_ID for chain in M.CHAINS.values() for m in chain)
    assert not any(m.startswith("nim/") for m in M.CHAINS["editor"])          # the chat editor stays Gemini / Kilo
