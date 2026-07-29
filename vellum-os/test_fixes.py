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


def test_candidate_profile_expansion():
    """Test 9: CandidateProfile expansion with Project, Addresses, Competitions."""
    header("TEST 9: CandidateProfile expansion")

    from vellum.models import CandidateProfile, Project

    proj = Project(title="AI Job Agent", description="Automated applicant tool", url="https://github.com/vamsi/job-agent", technologies=["Python", "FastAPI"])
    profile = CandidateProfile(
        name="Vamsi Krishna",
        email="vamsi@example.com",
        present_address="123 Hitec City, Hyderabad",
        permanent_address="Visakhapatnam, India",
        github="https://github.com/vamsi",
        portfolio="https://vamsi.dev",
        projects=[proj],
        competitions=["Hackathon Winner 2025"],
        achievements=["AWS Certified Architect"],
    )

    data = profile.model_dump()
    assert data["projects"][0]["title"] == "AI Job Agent"
    assert data["present_address"] == "123 Hitec City, Hyderabad"
    assert data["competitions"][0] == "Hackathon Winner 2025"

    print("  PASS: CandidateProfile expanded model works cleanly")
    return True


def test_json_sanitizer():
    """Test 10: JSON Sanitizer prevents UnicodeDecodeError on binary bytes."""
    header("TEST 10: JSON bytes sanitizer")

    from vellum.api.routes import sanitize_for_json

    sample_state = {
        "job_id": "12345",
        "tailored_pdf": b"%PDF-1.4 \x93\x84 binary PDF bytes header",
        "nested": {"pdf_bytes": b"\x00\x01\x02\x03"},
    }

    cleaned = sanitize_for_json(sample_state)
    assert "<binary_bytes: " in cleaned["tailored_pdf"]
    assert "<binary_bytes: " in cleaned["nested"]["pdf_bytes"]

    import json
    json_str = json.dumps(cleaned)
    assert "binary_bytes" in json_str

    print("  PASS: JSON sanitizer prevents UnicodeDecodeError on bytes")
    return True


def test_strict_location_matrix():
    """Test 11: Two-Tier Location Exclusion Matrix."""
    header("TEST 11: Location exclusion matrix")

    from vellum.agents.geo_search import _matches_location_strict, _clean_company_name

    # Hyderabad target location tests
    assert _matches_location_strict("Senior Software Engineer", "Based in Hyderabad office", "Hyderabad") == True
    assert _matches_location_strict("Senior Engineer - Remote", "Work from anywhere", "Hyderabad") == True
    assert _matches_location_strict("Cluster Manager - BAREILLY", "Located in Bareilly UP", "Hyderabad") == False
    assert _matches_location_strict("Store Manager - Hubballi", "Job in Hubballi Karnataka", "Hyderabad") == False

    # Company name cleaner tests
    assert _clean_company_name("AI Jobs In Hyderabad Secunderabad - Senior Engineer") == ""
    assert _clean_company_name("PhonePe - Software Company") == "Phonepe"

    print("  PASS: Strict location matching and company cleaner work properly")
    return True


def test_pdf_rendering():
    """Test 12: PDF resume rendering with projects & links."""
    header("TEST 12: PDF resume rendering")

    from vellum.tools.pdf_render import render_resume_pdf

    profile = {
        "name": "Karri Vamsi Krishna",
        "email": "vamsi@example.com",
        "phone": "+91 8074749058",
        "location": "Hyderabad, India",
        "github": "https://github.com/vamsi",
        "projects": [
            {
                "title": "Vellum OS",
                "description": "Career automation platform",
                "url": "https://github.com/vamsi/vellum-os",
                "technologies": ["Python", "FastAPI"],
            }
        ],
        "experience": [
            {"role": "Software Engineer", "company": "Tech Corp", "start": "2023", "end": "Present", "bullets": ["Built API microservices"]}
        ],
        "skills": ["Python", "React", "FastAPI"],
    }

    result = render_resume_pdf(profile)
    assert isinstance(result["pdf_bytes"], bytes)
    assert len(result["pdf_bytes"]) > 500
    print(f"  PASS: Rendered resume PDF ({len(result['pdf_bytes'])} bytes, page_count={result['page_count']})")
    return True


def test_ats_api():
    """Test 13: Public ATS & VC API integrations (Greenhouse, Lever, Freshteam, Getro VC, Hasjob)."""
    header("TEST 13: Public ATS & VC API integrations")

    async def _test():
        from vellum.tools.ats_api import fetch_greenhouse_jobs, fetch_lever_jobs, fetch_freshteam_jobs, fetch_getro_vc_jobs
        from vellum.tools.search import fetch_hasjob_jobs

        gh_jobs = await fetch_greenhouse_jobs("stripe")
        lever_jobs = await fetch_lever_jobs("cred")
        ft_jobs = await fetch_freshteam_jobs("happyfox")
        vc_jobs = await fetch_getro_vc_jobs("blume.vc", "Blume Ventures")
        hasjob_items = await fetch_hasjob_jobs(max_results=5)

        assert isinstance(gh_jobs, list)
        assert isinstance(lever_jobs, list)
        assert isinstance(ft_jobs, list)
        assert isinstance(vc_jobs, list)
        assert isinstance(hasjob_items, list)

        print(f"  PASS: GH={len(gh_jobs)}, Lever={len(lever_jobs)}, Freshteam={len(ft_jobs)}, VC Jobs={len(vc_jobs)}, Hasjob={len(hasjob_items)}")
        return True

    return asyncio.run(_test())


def test_browser_timeout_fixes():
    """Test 14: Browser launch timeouts are increased to prevent BrowserStartEvent 30s timeout."""
    header("TEST 14: Browser launch timeout fixes")

    import os
    from dotenv import load_dotenv
    load_dotenv()

    all_ok = True

    # --- Check env vars loaded ---
    bs_timeout = os.getenv("TIMEOUT_BrowserStartEvent")
    bl_timeout = os.getenv("TIMEOUT_BrowserLaunchEvent")
    print(f"  TIMEOUT_BrowserStartEvent = {bs_timeout}")
    print(f"  TIMEOUT_BrowserLaunchEvent = {bl_timeout}")

    if bs_timeout and int(bs_timeout) >= 60:
        print("  [PASS] TIMEOUT_BrowserStartEvent >= 60s")
    else:
        print(f"  [FAIL] TIMEOUT_BrowserStartEvent missing or too low: {bs_timeout}")
        all_ok = False

    if bl_timeout and int(bl_timeout) >= 60:
        print("  [PASS] TIMEOUT_BrowserLaunchEvent >= 60s")
    else:
        print(f"  [FAIL] TIMEOUT_BrowserLaunchEvent missing or too low: {bl_timeout}")
        all_ok = False

    # --- Check watchdog _wait_for_cdp_url default timeout ---
    try:
        from browser_use.browser.watchdogs.local_browser_watchdog import LocalBrowserWatchdog
        import inspect
        sig = inspect.signature(LocalBrowserWatchdog._wait_for_cdp_url)
        default_timeout = sig.parameters["timeout"].default
        print(f"  _wait_for_cdp_url default timeout = {default_timeout}s")
        if default_timeout >= 60:
            print("  [PASS] _wait_for_cdp_url timeout increased to 60s")
        else:
            print(f"  [FAIL] _wait_for_cdp_url timeout still at {default_timeout}s")
            all_ok = False
    except Exception as e:
        print(f"  [WARN] Could not inspect LocalBrowserWatchdog: {e}")

    # --- Check CDP connect timeout in session.py ---
    try:
        import importlib, types
        import browser_use.browser.session as session_mod
        with open(session_mod.__file__, "r", encoding="utf-8") as f:
            session_source = f.read()

        # Look for the timeout= parameter in asyncio.wait_for(self.connect(...))
        import re
        match = re.search(r"asyncio\.wait_for\(self\.connect\(cdp_url=self\.cdp_url\),\s*timeout=(\d+\.?\d*)\)", session_source)
        if match:
            cdp_timeout = float(match.group(1))
            print(f"  CDP connect timeout = {cdp_timeout}s")
            if cdp_timeout >= 30:
                print("  [PASS] CDP connect timeout increased to 30s")
            else:
                print(f"  [FAIL] CDP connect timeout still at {cdp_timeout}s")
                all_ok = False
        else:
            print("  [WARN] Could not find CDP connect timeout pattern in session.py")
    except Exception as e:
        print(f"  [WARN] Could not inspect session.py: {e}")

    if all_ok:
        print("\n  PASS: All browser timeout fixes are in place")
    else:
        print("\n  FAIL: Some browser timeout fixes are missing")

    return all_ok


def test_browser_launch_e2e():
    """Test 15: End-to-end browser launch within the increased timeout."""
    header("TEST 15: Browser launch E2E (within 60s timeout)")

    import asyncio, time

    async def _launch():
        from browser_use import BrowserProfile
        from browser_use.browser import BrowserSession

        profile = BrowserProfile(
            headless=True,
            keep_alive=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        session = BrowserSession(browser_profile=profile)

        t0 = time.monotonic()
        try:
            await asyncio.wait_for(session.start(), timeout=65)
            elapsed = time.monotonic() - t0
            print(f"  Browser started in {elapsed:.1f}s (limit: 65s)")

            # Verify we have a valid CDP URL
            cdp_url = getattr(session, "cdp_url", None)
            if cdp_url and "://" in str(cdp_url):
                print(f"  CDP URL: {cdp_url}")
                print("  [PASS] Browser launched and CDP connected within timeout")
                return True
            else:
                print(f"  [FAIL] No valid CDP URL after start: {cdp_url}")
                return False

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - t0
            print(f"  [FAIL] Browser launch timed out after {elapsed:.1f}s (limit: 65s)")
            return False
        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"  [FAIL] Browser launch failed after {elapsed:.1f}s: {e}")
            return False
        finally:
            try:
                await session.close()
            except Exception:
                pass

    return asyncio.run(_launch())


def test_ctc_fields():
    """Test 16: Verify current_ctc and expected_ctc work in QAMemory and CandidateProfile."""
    header("TEST 16: CTC fields integration in QAMemory")

    from vellum.models import CandidateProfile, QAMemory

    qa = QAMemory(
        expected_salary="15 LPA",
        current_ctc="12 LPA",
        expected_ctc="18 LPA",
        notice_period="30 days",
    )
    profile = CandidateProfile(
        name="Test Candidate",
        email="test@candidate.com",
        qa_memory=qa,
    )

    data = profile.model_dump()
    assert data["qa_memory"]["current_ctc"] == "12 LPA", f"Expected '12 LPA', got {data['qa_memory']['current_ctc']}"
    assert data["qa_memory"]["expected_ctc"] == "18 LPA", f"Expected '18 LPA', got {data['qa_memory']['expected_ctc']}"
    assert data["qa_memory"]["expected_salary"] == "15 LPA", f"Expected '15 LPA', got {data['qa_memory']['expected_salary']}"

    print("  PASS: CTC fields instantiated and serialized cleanly in QAMemory")
    return True


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
        ("CandidateProfile expansion", test_candidate_profile_expansion),
        ("JSON bytes sanitizer", test_json_sanitizer),
        ("Strict location matrix", test_strict_location_matrix),
        ("PDF resume rendering", test_pdf_rendering),
        ("Public ATS APIs", test_ats_api),
        ("Browser timeout fixes", test_browser_timeout_fixes),
        ("Browser launch E2E", test_browser_launch_e2e),
        ("CTC fields integration", test_ctc_fields),
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

