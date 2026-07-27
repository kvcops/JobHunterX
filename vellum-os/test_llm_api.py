"""
LLM API Test — verify all 3 providers work with a simple prompt.
Run: python test_llm_api.py
"""
import sys
import os
import time

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Set API keys from .env
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")
if os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
if os.getenv("MISTRAL_API_KEY"):
    os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY")

import litellm

# Suppress noisy LiteLLM logs
litellm.suppress_debug_info = True

MODELS = [
    ("Gemini",  "gemini/gemini-3.1-flash-lite"),
    ("Groq",    "groq/openai/gpt-oss-120b"),
    ("Mistral", "mistral/mistral-large-2512"),
]

PROMPT = "Say exactly: HELLO_TEST_OK"
EXPECTED = "HELLO_TEST_OK"


def test_model(provider_name, model):
    print(f"\n{'---'*20}")
    print(f"  Testing: {provider_name} ({model})")
    print(f"{'---'*20}")

    try:
        # Groq reasoning models (gpt-oss) need larger max_tokens + check reasoning field
        if "gpt-oss" in model or "reasoning" in model:
            max_tokens = 100
        else:
            max_tokens = 20

        t0 = time.monotonic()
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=max_tokens,
            temperature=0,
        )
        latency = (time.monotonic() - t0) * 1000

        content = response.choices[0].message.content or ""
        # Reasoning models (Groq gpt-oss) put thinking in 'reasoning' field
        reasoning = ""
        if hasattr(response.choices[0].message, 'reasoning') and response.choices[0].message.reasoning:
            reasoning = response.choices[0].message.reasoning or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        ok = EXPECTED.lower() in content.lower() or EXPECTED.lower() in reasoning.lower()

        print(f"  Response : '{content}'")
        if reasoning:
            print(f"  Reasoning: '{reasoning[:80]}...'")
        print(f"  Tokens   : {tokens_in} in / {tokens_out} out")
        print(f"  Latency  : {latency:.0f}ms")
        print(f"  Status   : {'PASS' if ok else 'FAIL (unexpected response)'}")
        return ok, latency

    except litellm.RateLimitError as e:
        print(f"  Status   : RATE_LIMITED")
        print(f"  Error    : {str(e)[:120]}")
        return False, 0
    except litellm.AuthenticationError as e:
        print(f"  Status   : AUTH_ERROR (bad API key?)")
        print(f"  Error    : {str(e)[:120]}")
        return False, 0
    except Exception as e:
        print(f"  Status   : ERROR")
        print(f"  Error    : {type(e).__name__}: {str(e)[:120]}")
        return False, 0


def main():
    print(f"Python: {sys.version}")
    print(f"LiteLLM: {getattr(litellm, 'version', 'unknown')}")
    print(f"API keys configured: Gemini={'YES' if os.getenv('GEMINI_API_KEY') else 'NO'}, "
          f"Groq={'YES' if os.getenv('GROQ_API_KEY') else 'NO'}, "
          f"Mistral={'YES' if os.getenv('MISTRAL_API_KEY') else 'NO'}")

    results = {}
    total_latency = 0

    for provider, model in MODELS:
        ok, latency = test_model(provider, model)
        results[provider] = ok
        total_latency += latency

    # Summary
    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    for provider, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {provider}")

    passed = sum(results.values())
    total = len(results)
    print(f"\n  {passed}/{total} providers working")
    print(f"  Total latency: {total_latency:.0f}ms")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
