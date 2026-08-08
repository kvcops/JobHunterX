"""
Unit tests for Two-Tier Zero-Spend Circuit Breaker.
"""

import pytest
from jobhunterx.tools.search_providers import CostEstimate, CostStatus
from jobhunterx.tools.zero_spend import evaluate_zero_spend_safety


@pytest.mark.asyncio
async def test_zero_spend_unknown_cost_blocking():
    cost_unknown = CostEstimate(
        status=CostStatus.UNKNOWN,
        units=0.0,
        unit_type="credits",
        estimated_amount_native=0.0,
        explanation="Unknown parameters",
    )
    is_safe, reason = await evaluate_zero_spend_safety("tavily", cost_unknown, {"STRICT_ZERO_SPEND_PROTECTION": True})
    assert is_safe is False
    assert "UNKNOWN" in reason


@pytest.mark.asyncio
async def test_zero_spend_free_utility_safe():
    cost_free = CostEstimate(
        status=CostStatus.KNOWN,
        units=0.0,
        unit_type="credits",
        estimated_amount_native=0.0,
        explanation="0-credit search",
    )
    is_safe, reason = await evaluate_zero_spend_safety("tinyfish", cost_free, {"STRICT_ZERO_SPEND_PROTECTION": True})
    assert is_safe is True
    assert reason == ""
