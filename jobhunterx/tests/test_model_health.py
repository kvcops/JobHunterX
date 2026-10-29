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
    M.mark_failure("nim/openai/gpt-oss-20b", '402 {"error":{"message":"Add usage credits"}}')
    assert M.key_rejected("nvidia")


def test_a_timeout_without_message_still_rests_the_model():
    assert M.mark_failure("nim/nvidia/nemotron-3-ultra-550b-a55b", "ReadTimeout") == 120
    assert M.resting("nim/nvidia/nemotron-3-ultra-550b-a55b")


def test_nim_catalog_has_only_models_a_free_key_can_call():
    nim = {m["id"] for m in M.CATALOG if m["provider"] == "nvidia"}
    assert "nim/nvidia/nemotron-3-ultra-550b-a55b" in nim
    assert not nim & {"nim/nvidia/nemotron-3-super-120b-a12b", "nim/nvidia/nemotron-nano-3-30b-a3b", "nim/z-ai/glm-5.3-flash"}
    assert all(m in M.BY_ID for chain in M.CHAINS.values() for m in chain)
    assert not any(m.startswith("nim/") for m in M.CHAINS["editor"])          # the chat editor stays Gemini / Kilo


def test_busy_endpoint_gets_a_short_flat_rest():
    for _ in range(3):
        rest = M.mark_failure("nim/poolside/laguna-xs-2.1", '503 {"error":{"message":"ResourceExhausted: Worker local total request limit reached (16/16)"}}')
    assert rest == 60 and "busy" in M.resting("nim/poolside/laguna-xs-2.1")


def test_retry_after_is_honoured():
    assert M.mark_failure("nim/openai/gpt-oss-20b", '429 {"status":429,"title":"Too Many Requests"} retry after 90') == 90


def test_several_nim_models_429ing_rest_the_whole_provider():
    M._provider_rest.clear(); M._nim_429s.clear()
    M.mark_failure("nim/a/one", "429 Too Many Requests")
    M.mark_failure("nim/b/two", "429 Too Many Requests")
    assert M.resting("nim/c/three") is None                     # two 429s: still just those endpoints
    M.mark_failure("nim/a/one", "429 Too Many Requests")
    assert "rate limiting this key" in M.resting("nim/c/three")   # three from two models: the key is limited
    assert M.resting("kilo/kilo-auto/free") is None
    M._provider_rest.clear(); M._nim_429s.clear()


def test_one_busy_nim_model_does_not_rest_the_others():
    M._provider_rest.clear(); M._nim_429s.clear()
    for _ in range(3):
        M.mark_failure("nim/minimaxai/minimax-m3.1-flash", "429 Too Many Requests")
    assert M.resting("nim/openai/gpt-oss-20b") is None
    M._provider_rest.clear(); M._nim_429s.clear()


def test_nim_account_limiter_keeps_headroom():
    assert M.limits(M.NIM_ACCOUNT)["rpm"] == 36


def test_call_plan_gives_reasoning_room_and_size_based_waits():
    budget, wait, skip = M.call_plan("nim/mistralai/mistral-large-4-1t-a52b", 2000)
    assert budget == 5000 and skip is None                   # 2.5x: its reasoning can't be switched off
    assert M.call_plan("nim/nvidia/nemotron-3.5-lightning-30b-a3b", 400)[1] == M.MIN_CALL_TIMEOUT_S
    short, long = M.call_plan("nim/openai/gpt-oss-20b", 400)[1], M.call_plan("nim/openai/gpt-oss-20b", 2000)[1]
    assert short < long <= M.MAX_CALL_TIMEOUT_S              # the wait grows with the answer asked for
    assert M.call_plan("nim/meta/muse-glimmer-30b", 2500)[2]  # too slow for a CV: skipped for that call
    assert M.call_plan("nim/meta/muse-glimmer-30b", 300)[2] is None
    assert M.call_plan("kilo/kilo-auto/free", 2500) == (2500, None, None)   # no measurements: provider defaults


def test_skipping_a_slow_model_does_not_rest_it():
    assert M.mark_failure("nim/meta/muse-glimmer-30b", "nim/meta/muse-glimmer-30b skipped: too slow for an answer this long (~136 s at 11 tokens/s)") is None
    assert M.resting("nim/meta/muse-glimmer-30b") is None


def test_writing_chain_leads_with_models_that_never_invented_tools():
    write = [m for m in M.CHAINS["tailoring"] if m.startswith("nim/")]
    assert write[:2] == ["nim/mistralai/mistral-large-4-1t-a52b", "nim/nvidia/nemotron-3.5-super-vl-120b-a12b"]
    assert "nim/google/diffusiongemma-26b-a4b-it" not in write and "nim/nvidia/nemotron-3-ultra-550b-a55b" not in write
    assert write[-1] == "nim/minimaxai/minimax-m3.1-flash"
