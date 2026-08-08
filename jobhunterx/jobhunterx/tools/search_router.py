"""
JobHunterX — Sequential Search Router & Safety Bounded Dispatcher

Executes queries sequentially across prioritized providers (TinyFish -> Tavily -> Exa -> DDGS),
evaluating local availability, zero-spend safety, rate limits, transport verdicts,
and context-aware Quality Gate passing conditions.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from jobhunterx.config.logging import get_logger
from jobhunterx.tools.quality_gate import QualityDecision, QualityGateResult, SearchContext, evaluate_serp_quality
from jobhunterx.tools.search_providers import (
    BaseSearchProvider,
    BraveProvider,
    CostStatus,
    DDGSProvider,
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
            "ddgs": DDGSProvider(),
        }
        self.session_disabled: Dict[str, bool] = {}
        self.backoff_until: Dict[str, float] = {}

    def get_priority_order(self) -> List[str]:
        return ["tinyfish", "tavily", "exa", "ddgs"]

    async def execute_query(
        self, query: str, context: SearchContext, max_results: int = 10,
        providers: Optional[List[str]] = None,
    ) -> List[SearchResultItem]:
        """Execute a single search query following sequential fallback priority.

        `providers`: optional sub-list of providers to try (useful for per-run
        provider rotation). Defaults to the full priority order.
        """
        priority_list = providers or self.get_priority_order()
        collected_items: List[SearchResultItem] = []

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
            start_t = time.time()
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

            # 4. Handle Transport Verdicts
            if resp.verdict == TransportVerdict.SUCCESS:
                collected_items.extend(resp.results)
                # 5. Evaluate Deterministic Quality Gate
                quality: QualityGateResult = evaluate_serp_quality(
                    resp.results,
                    context=context,
                    threshold=float(self.config.get("QUALITY_SCORE_THRESHOLD", 0.60)),
                )
                if quality.decision == QualityDecision.PASS:
                    log.info("search_router_quality_gate_passed", provider=p_name, score=quality.score)
                    return resp.results
                else:
                    log.info("search_router_quality_gate_insufficient", provider=p_name, score=quality.score)

            elif resp.verdict == TransportVerdict.RATE_LIMITED:
                retry_sec = resp.retry_after_seconds or 10.0
                self.backoff_until[p_name] = now + retry_sec
                log.warning("search_router_rate_limited", provider=p_name, backoff_seconds=retry_sec)

            elif resp.verdict == TransportVerdict.AUTH_ERROR:
                self.session_disabled[p_name] = True
                log.error("search_router_auth_error_disabled", provider=p_name)

        return collected_items


async def route_search_queries(
    queries: List[str], context: SearchContext, config: Optional[Dict[str, Any]] = None
) -> List[SearchResultItem]:
    """Execute search queries using router with safety bounds.

    Paid/primary providers are ROTATED across queries (never one provider for the
    whole run): every configured provider gets a fair share, capped per run by
    MAX_REQUESTS_PER_PROVIDER_PER_RUN (default 2 for Tavily/Exa/Brave; TinyFish
    and DDGS are unlimited since they cost 0 credits). If a query's provider
    fails or the quality gate rejects its SERP, DDGS runs as the free safety net.
    """
    cfg = config or {}
    router = SearchRouter(config=cfg)

    max_queries = int(cfg.get("MAX_SEARCH_QUERIES_PER_RUN", 5))
    bounded_queries = queries[:max_queries]
    all_results: List[SearchResultItem] = []
    seen_urls: set[str] = set()

    # Which providers actually have keys/are enabled for this run
    available = [
        p for p in router.get_priority_order()
        if p in router.providers
        and router.providers[p].is_available(cfg, session_disabled=False)
    ]
    rotation_pool = [p for p in available if p != "ddgs"]
    ddgs_available = "ddgs" in available

    # Cap usage of paid providers so no single one dominates the run
    max_per_provider = max(1, int(cfg.get("MAX_REQUESTS_PER_PROVIDER_PER_RUN", 2)))
    paid_provider = {"tavily", "exa", "brave"}
    used: Dict[str, int] = {}

    for i, q in enumerate(bounded_queries):
        # Rotate starting provider across queries; skip providers that hit their cap.
        chosen: Optional[str] = None
        if rotation_pool:
            for k in range(len(rotation_pool)):
                cand = rotation_pool[(i + k) % len(rotation_pool)]
                if cand in paid_provider and used.get(cand, 0) >= max_per_provider:
                    continue
                chosen = cand
                break
            # Paid caps exhausted but more queries remain -> fall back to TinyFish/DDG
            if chosen is None:
                chosen = next((p for p in rotation_pool if p not in paid_provider), None)

        if chosen:
            used[chosen] = used.get(chosen, 0) + 1
            log.info("search_router_provider_chosen", query_i=i, provider=chosen)
            if ddgs_available:
                res_items = await router.execute_query(
                    q, context=context, max_results=10, providers=[chosen, "ddgs"]
                )
            else:
                res_items = await router.execute_query(
                    q, context=context, max_results=10, providers=[chosen]
                )
        elif ddgs_available:
            res_items = await router.execute_query(
                q, context=context, max_results=10, providers=["ddgs"]
            )
        else:
            res_items = await router.execute_query(q, context=context, max_results=10)

        for item in res_items:
            url_norm = item.url.strip().rstrip("/").lower()
            if url_norm not in seen_urls:
                seen_urls.add(url_norm)
                all_results.append(item)

    log.info(
        "route_search_queries_complete", queries_count=len(bounded_queries),
        total_unique_results=len(all_results), provider_usage=used,
    )
    return all_results
