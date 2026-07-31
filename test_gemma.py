"""
Test script: Verify Gemma works via google GenAI library directly (NOT litellm).

This tests the approach used in job_llm_validator.py — bypassing litellm entirely
for Gemma models since litellm returns 503 errors for them.

Usage:
  cd "C:\\Users\\vamsi\\OneDrive\\Desktop\\Job agent"
  python test_gemma.py

Ensure GOOGLE_API_KEY is set in .env or environment.
"""

import os
import sys
import time

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vellum-os"))


def test_gemma_import():
    """Verify google.genai can be imported."""
    print("[1/4] Testing google.genai import...")
    try:
        from google import genai
        print(f"  OK - google.genai imported (version: {genai.__version__ if hasattr(genai, '__version__') else 'unknown'})")
        return True
    except ImportError as e:
        print(f"  FAIL - Cannot import google.genai: {e}")
        print("  Fix: pip install google-genai")
        return False


def test_api_key():
    """Verify GOOGLE_API_KEY is available."""
    print("[2/4] Testing API key...")
    # Try loading from .env first
    env_path = os.path.join(os.path.dirname(__file__), "vellum-os", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "GOOGLE_API_KEY" and v:
                        os.environ.setdefault(k, v)

    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        print(f"  OK - API key found: {masked}")
        return True
    print("  FAIL - GOOGLE_API_KEY not found in environment or .env")
    print("  Fix: Set GOOGLE_API_KEY in vellum-os/.env or environment")
    return False


def test_gemma_sync():
    """Test synchronous Gemma call via google.genai (same as job_llm_validator)."""
    print("[3/4] Testing synchronous Gemma call (gemma-4-26b-a4b-it)...")

    from google import genai

    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=key)

    prompt = "What is 2+2? Reply with just the number."

    t0 = time.monotonic()
    try:
        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt,
            config={
                "thinkingConfig": {
                    "thinkingLevel": "minimal",
                },
            },
        )
        elapsed = time.monotonic() - t0
        text = response.text if hasattr(response, "text") else str(response)
        print(f"  OK - Response ({elapsed:.2f}s): {text.strip()[:200]}")
        return True
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"  FAIL - Error after {elapsed:.2f}s: {e}")
        return False


def test_gemma_async():
    """Test async Gemma call via thread executor (same as job_llm_validator)."""
    print("[4/4] Testing async Gemma call (thread executor pattern)...")

    from google import genai
    import asyncio

    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=key)

    def _call_sync():
        return client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents="What is the capital of France? Reply with just the city name.",
            config={
                "thinkingConfig": {
                    "thinkingLevel": "minimal",
                },
            },
        )

    async def _call_async():
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_sync)

    t0 = time.monotonic()
    try:
        response = asyncio.run(_call_async())
        elapsed = time.monotonic() - t0
        text = response.text if hasattr(response, "text") else str(response)
        print(f"  OK - Async response ({elapsed:.2f}s): {text.strip()[:200]}")
        return True
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"  FAIL - Error after {elapsed:.2f}s: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Gemma via google.genai - Test Suite")
    print("Model: gemma-4-26b-a4b-it | Thinking: minimal")
    print("=" * 60)
    print()

    results = {}
    results["import"] = test_gemma_import()
    results["api_key"] = test_api_key()
    if results["api_key"]:
        results["sync"] = test_gemma_sync()
        results["async"] = test_gemma_async()
    else:
        results["sync"] = False
        results["async"] = False

    print()
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    if passed == total:
        print(f"ALL {total}/{total} PASSED - Gemma via google.genai is working!")
    else:
        print(f"PASSED {passed}/{total} - Some tests failed (see above)")
    print("=" * 60)
