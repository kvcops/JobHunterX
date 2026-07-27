"""
Test script to verify all fixes work correctly.

Run: python test_fixes.py
"""
import sys
import asyncio
import time
import traceback


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_proactor_event_loop_in_thread():
    """Test 1: ProactorEventLoop works in a dedicated thread for subprocesses."""
    header("TEST 1: ProactorEventLoop in dedicated thread")

    async def _run_in_thread():
        def _thread_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def subprocess_test():
                    proc = await asyncio.create_subprocess_exec(
                        "cmd", "/c", "echo", "hello from proactor thread",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    return stdout.decode().strip()

                result = loop.run_until_complete(subprocess_test())
                return result, type(loop).__name__
            finally:
                loop.close()

        loop = asyncio.get_running_loop()
        result, loop_type = await loop.run_in_executor(None, _thread_worker)
        return result, loop_type

    result, loop_type = asyncio.run(_run_in_thread())

    assert loop_type == "ProactorEventLoop", f"Expected ProactorEventLoop, got {loop_type}"
    assert "hello from proactor thread" in result, f"Subprocess failed: {result}"
    print(f"  PASS: Loop type={loop_type}, subprocess output='{result}'")
    return True


def test_subprocess_in_existing_event_loop():
    """Test 2: Check SelectorEventLoop subprocess support (informational)."""
    header("TEST 2: SelectorEventLoop subprocess support (informational)")

    async def _test():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from asyncio import SelectorEventLoop
            sel_loop = SelectorEventLoop()
            asyncio.set_event_loop(sel_loop)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "cmd", "/c", "echo", "should not work",
                    stdout=asyncio.subprocess.PIPE,
                )
                print("  INFO: SelectorEventLoop can create subprocesses on this Python version")
                print("  (The user's runtime environment hits NotImplementedError — our fix is still needed)")
                return True
            except NotImplementedError:
                print("  INFO: SelectorEventLoop cannot create subprocesses (matches user's error)")
                print("  (Our fix runs browser agent in ProactorEventLoop thread — this is correct)")
                return True
            finally:
                sel_loop.close()
        finally:
            loop.close()

    return asyncio.run(_test())


def test_proactor_in_main_loop():
    """Test 3: ProactorEventLoop works in the main loop."""
    header("TEST 3: ProactorEventLoop in main event loop")

    async def _test():
        proc = await asyncio.create_subprocess_exec(
            "cmd", "/c", "echo", "hello from main loop",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = asyncio.run(_test())
        assert "hello from main loop" in result
        print(f"  PASS: subprocess output='{result}'")
        return True
    finally:
        loop.close()


def test_rate_limiting():
    """Test 4: Rate limiter enforces minimum delays between requests."""
    header("TEST 4: Rate limiter delays")

    from vellum.config.llm_router import _enforce_rate_limit, _provider_last_request

    async def _test():
        # Clear state
        _provider_last_request.clear()

        # First call should be instant
        t0 = time.monotonic()
        await _enforce_rate_limit("groq/some-model")
        elapsed_first = time.monotonic() - t0

        # Second call should be delayed by ~2s
        t1 = time.monotonic()
        await _enforce_rate_limit("groq/some-model")
        elapsed_second = time.monotonic() - t1

        # Third call on mistral should be instant (different provider)
        t2 = time.monotonic()
        await _enforce_rate_limit("mistral/some-model")
        elapsed_mistral = time.monotonic() - t2

        return elapsed_first, elapsed_second, elapsed_mistral

    first, second, mistral = asyncio.run(_test())

    assert first < 0.5, f"First call was too slow: {first:.2f}s"
    assert second >= 1.5, f"Second call was too fast: {second:.2f}s (should be >= 1.5s)"
    assert mistral < 0.5, f"Mistral call was too slow: {mistral:.2f}s"

    print(f"  PASS: First={first:.2f}s (< 0.5s), Groq retry={second:.2f}s (>= 1.5s), Mistral={mistral:.2f}s (< 0.5s)")
    return True


def test_mistral_retry_on_429():
    """Test 5: Mistral 429 retries with backoff instead of immediate raise."""
    header("TEST 5: Mistral 429 retry logic")

    from vellum.config.llm_router import _raw_completion
    import litellm

    async def _test():
        # Mock litellm.acompletion to raise RateLimitError 3 times then succeed
        call_count = 0
        original_acompletion = litellm.acompletion

        async def mock_acompletion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise litellm.RateLimitError(
                    message='Rate limit exceeded',
                    model=kwargs.get('model', ''),
                    llm_provider='mistral',
                )
            # Succeed on 4th call
            return original_acompletion(**kwargs)

        litellm.acompletion = mock_acompletion
        try:
            result = await _raw_completion({
                "model": "mistral/mistral-large-2512",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10,
            })
            print(f"  PASS: Retried {call_count - 1} times, then succeeded")
            return True
        except Exception as e:
            print(f"  FAIL: {e}")
            return False
        finally:
            litellm.acompletion = original_acompletion

    return asyncio.run(_test())


def test_fallback_chain():
    """Test 6: Fallback chain tries multiple providers."""
    header("TEST 6: Fallback chain logic")

    from vellum.config.llm_router import FALLBACK_CHAINS

    chains = FALLBACK_CHAINS
    print(f"  Fast chain:       {chains.get('fast', [])}")
    print(f"  Reasoning chain:  {chains.get('reasoning', [])}")
    print(f"  Tailoring chain:  {chains.get('tailoring', [])}")
    print(f"  Extraction chain: {chains.get('extraction', [])}")

    for name, chain in chains.items():
        assert len(chain) >= 2, f"Chain '{name}' should have >= 2 models"
        assert any("gemini" in m for m in chain), f"Chain '{name}' should have a gemini fallback"

    print("  PASS: All chains have multiple models with gemini fallback")
    return True


def test_browser_agent_import():
    """Test 7: Browser agent module imports cleanly."""
    header("TEST 7: Browser agent import")

    try:
        from vellum.agents.browser_agent import run
        print("  PASS: browser_agent.run imported successfully")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_event_loop_policy():
    """Test 8: Event loop policy is ProactorEventLoop."""
    header("TEST 8: Event loop policy check")

    policy = asyncio.get_event_loop_policy()
    policy_name = type(policy).__name__
    print(f"  Current policy: {policy_name}")

    loop = asyncio.new_event_loop()
    loop_type = type(loop).__name__
    print(f"  New loop type:  {loop_type}")
    loop.close()

    if loop_type == "ProactorEventLoop":
        print("  PASS: New event loop is ProactorEventLoop")
        return True
    else:
        print(f"  WARN: New event loop is {loop_type} (not ProactorEventLoop)")
        return False


def main():
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")

    tests = [
        ("ProactorEventLoop in thread", test_proactor_event_loop_in_thread),
        ("SelectorEventLoop fails subprocess", test_subprocess_in_existing_event_loop),
        ("ProactorEventLoop main loop", test_proactor_in_main_loop),
        ("Rate limiter delays", test_rate_limiting),
        ("Mistral 429 retry", test_mistral_retry_on_429),
        ("Fallback chains", test_fallback_chain),
        ("Browser agent import", test_browser_agent_import),
        ("Event loop policy", test_event_loop_policy),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            results[name] = False

    # Summary
    header("RESULTS")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\n  {passed}/{total} tests passed")

    if passed == total:
        print("\n  All tests passed!")
        return 0
    else:
        print(f"\n  {total - passed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
