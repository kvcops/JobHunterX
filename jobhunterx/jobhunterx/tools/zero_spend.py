"""
JobHunterX — Two-Tier Zero-Spend Circuit Breaker

Enforces hard billing safety (Tier A) and soft reserve caps (Tier B) to guarantee
zero accidental credit card charges or out-of-pocket spend.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
from jobhunterx.config.logging import get_logger
from jobhunterx.tools.search_providers import CostEstimate, CostStatus
from jobhunterx.tools.usage_ledger import get_monthly_usage_native

log = get_logger("zero_spend")

# Primary documented recurring monthly free allowances
KNOWN_FREE_ALLOWANCES_NATIVE = {
    "tavily": (1000.0, "credits"),
    "exa": (10.00, "USD"),
    "brave": (5.00, "USD"),
    "tinyfish": (None, "credits"),  # Uncapped 0-credit utility (no Tier B soft cap)
    "ddgs": (None, "NOT_APPLICABLE"),
}


async def evaluate_zero_spend_safety(
    provider_name: str, cost_estimate: CostEstimate, config: Dict[str, Any]
) -> Tuple[bool, str]:
    """Evaluate whether request is safe to execute under zero-spend protection.

    Returns: (is_safe: bool, blocked_reason: str)
    """
    strict_mode = config.get("STRICT_ZERO_SPEND_PROTECTION", True)

    # Unknown costs strictly block execution under zero-spend protection
    if cost_estimate.status == CostStatus.UNKNOWN:
        if strict_mode:
            return False, f"Provider '{provider_name}' cost estimate is UNKNOWN under STRICT_ZERO_SPEND_PROTECTION"

    # 0-cost or non-applicable providers are always safe
    if cost_estimate.status == CostStatus.NOT_APPLICABLE or cost_estimate.estimated_amount_native == 0.0:
        return True, ""

    allowance_info = KNOWN_FREE_ALLOWANCES_NATIVE.get(provider_name)
    if not allowance_info:
        return True, ""

    known_free_limit, unit_type = allowance_info

    # Fetch current monthly usage from ledger in provider-native units
    monthly_used = await get_monthly_usage_native(provider_name)

    # Tier A: Hard Billing Safety (Mandatory: remaining_free >= worst_case_cost)
    if known_free_limit is not None:
        remaining_free = known_free_limit - monthly_used
        if remaining_free - cost_estimate.estimated_amount_native < 0:
            return False, (
                f"Tier A Hard Billing Safety Block: Provider '{provider_name}' worst-case cost "
                f"({cost_estimate.estimated_amount_native} {unit_type}) exceeds remaining free balance "
                f"({remaining_free:.2f} {unit_type})"
            )

        # Tier B: Soft Reserve Cap (Stop normal usage at 95% of known free allowance)
        soft_cap = known_free_limit * 0.95
        if monthly_used >= soft_cap:
            return False, (
                f"Tier B Soft Reserve Cap Block: Provider '{provider_name}' usage ({monthly_used:.2f} {unit_type}) "
                f"has reached 95% of monthly allowance ({known_free_limit} {unit_type})"
            )

    return True, ""
