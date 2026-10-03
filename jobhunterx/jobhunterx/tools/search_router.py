"""
JobHunterX — Sequential Search Router & Safety Bounded Dispatcher

Executes queries sequentially across prioritized providers (TinyFish -> Tavily -> Exa -> DDGS),
evaluating local availability, zero-spend safety, rate limits, transport verdicts,
and returns the first provider's non-empty result set.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.tools.search_providers import (
    BaseSearchProvider,
    BraveProvider,
    DDGSProvider,
    DeepSearchProvider,
    ExaProvider,
    ProviderSearchResponse,
    SearchResultItem,
    TavilyProvider,
    TinyFishProvider,
    TransportVerdict,
)
from jobhunterx.tools.usage_ledger import record_ledger_attempt
from jobhunterx.tools.zero_spend import evaluate_zero_spend_safety

log = get_logger("search_router")


class SearchRouter:
    """Sequential Search Router for JobHunterX."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.providers: Dict[str, BaseSearchProvider] = {
            "tinyfish": TinyFishProvider(),
            "tavily": TavilyProvider(),
            "exa": ExaProvider(),
            "brave": BraveProvider(),
            "deep": DeepSearchProvider(),
            "ddgs": DDGSProvider(),
        }
        self.session_disabled: Dict[str, bool] = {}
        self.backoff_until: Dict[str, float] = {}

    def get_priority_order(self) -> List[str]:
        """Configured primary provider first, then the rest; DDGS (free) last."""
        order = ["tinyfish", "tavily", "exa", "brave"]
        primary = str(self.config.get("PRIMARY_SEARCH_PROVIDER") or "").lower()
        if primary in order:
            order.remove(primary)
            order.insert(0, primary)
        return order + ["deep", "ddgs"]

    async def execute_query(
        self, query: str, max_results: int = 10,
        providers: Optional[List[str]] = None,
    ) -> List[SearchResultItem]:
        """Execute a single search query following sequential fallback priority.

        `providers`: optional sub-list of providers to try (useful for per-run
        provider rotation). Defaults to the full priority order.
        """
        priority_list = providers or self.get_priority_order()
        
        for p_name in priority_list:
            provider = self.providers.get(p_name)
            if not provider:
                continue

            # 1. Local availability check (0 network calls)
            if not provider.is_available(self.config, session_disabled=self.session_disabled.get(p_name, False)):
                continue

            # Check rate limiter backoff
            now = time.time()
            if self.backoff_until.get(p_name, 0) > now:
                log.info("search_router_skipping_backoff", provider=p_name)
                continue

            # 2. Worst-case cost & Zero-Spend Safety evaluation
            cost_estimate = provider.calculate_worst_case_cost({"query": query, "max_results": max_results})
            is_safe, blocked_reason = await evaluate_zero_spend_safety(p_name, cost_estimate, self.config)

            if not is_safe:
                log.warning("zero_spend_safety_blocked", provider=p_name, reason=blocked_reason)
                await record_ledger_attempt(
                    provider=p_name,
                    request_type="search",
                    verdict=TransportVerdict.BILLING_SAFETY_BLOCK.value,
                    search_query=query,
                    estimated_cost_native=cost_estimate.estimated_amount_native,
                    unit_type=cost_estimate.unit_type,
                    blocked_reason=blocked_reason,
                )
                continue

            # 3. Transport Execution
            resp: ProviderSearchResponse = await provider.search(query, max_results=max_results, config=self.config)

            # Record attempt in SQLite ledger
            await record_ledger_attempt(
                provider=p_name,
                request_type="search",
                verdict=resp.verdict.value,
                search_query=query,
                native_billing_units=resp.cost_estimate.units,
                estimated_cost_native=resp.cost_estimate.estimated_amount_native,
                actual_known_cost_native=resp.cost_estimate.estimated_amount_native if resp.verdict == TransportVerdict.SUCCESS else 0.0,
                unit_type=resp.cost_estimate.unit_type,
                blocked_reason=resp.error_message or "",
            )

            # 4. Handle transport verdicts: first provider that returns results wins.
            if resp.verdict == TransportVerdict.SUCCESS:
                if resp.results:
                    return resp.results
            elif resp.verdict == TransportVerdict.RATE_LIMITED:
                retry_sec = resp.retry_after_seconds or 10.0
                self.backoff_until[p_name] = now + retry_sec
                log.warning("search_router_rate_limited", provider=p_name, backoff_seconds=retry_sec)

            elif resp.verdict == TransportVerdict.AUTH_ERROR:
                self.session_disabled[p_name] = True
                log.error("search_router_auth_error_disabled", provider=p_name)

        return []


async def search_one(router: "SearchRouter", query: str, max_results: int = 10) -> List[SearchResultItem]:
    """Run one query through the configured providers in priority order."""
    return await router.execute_query(query, max_results=max_results)
