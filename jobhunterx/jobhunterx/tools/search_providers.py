"""
JobHunterX — Web Search Provider Adapters & Transport Layer

Implements individual search provider adapters for TinyFish, Tavily, Exa,
Brave Search, and DuckDuckGo (DDGS). Each adapter exposes transport-level execution,
provider-native cost calculation, and local availability checks.
"""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from jobhunterx.config.logging import get_logger

log = get_logger("search_providers")


class TransportVerdict(str, Enum):
    SUCCESS = "SUCCESS"
    RATE_LIMITED = "RATE_LIMITED"
    TEMPORARY_PROVIDER_ERROR = "TEMPORARY_PROVIDER_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    BILLING_SAFETY_BLOCK = "BILLING_SAFETY_BLOCK"


class CostStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class CostEstimate:
    status: CostStatus
    units: float
    unit_type: str  # e.g., "credits", "USD", "NOT_APPLICABLE"
    estimated_amount_native: float
    explanation: str


@dataclass
class SearchResultItem:
    url: str
    title: str
    snippet: str
    provider: str
    canonical_url: str = ""
    job_id: str = ""


@dataclass
class ProviderSearchResponse:
    provider_name: str
    verdict: TransportVerdict
    results: List[SearchResultItem]
    cost_estimate: CostEstimate
    error_message: Optional[str] = None
    retry_after_seconds: Optional[float] = None


class BaseSearchProvider(ABC):
    """Abstract Base Class for Web Search Providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        """Perform local availability check without network calls."""
        pass

    @abstractmethod
    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        """Calculate worst-case cost BEFORE sending request."""
        pass

    @abstractmethod
    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        """Execute HTTP search request and return transport verdict."""
        pass


class TinyFishProvider(BaseSearchProvider):
    """TinyFish Search API Adapter (GET https://api.search.tinyfish.ai)."""

    @property
    def name(self) -> str:
        return "tinyfish"

    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        if session_disabled:
            return False
        api_key = config.get("TINYFISH_API_KEY") or ""
        return bool(api_key.strip())

    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        # Official docs: Search API consumes 0 credits on all plans (free utility)
        return CostEstimate(
            status=CostStatus.KNOWN,
            units=0.0,
            unit_type="credits",
            estimated_amount_native=0.0,
            explanation="TinyFish Search API is a 0-credit free utility (docs.tinyfish.ai/rate-limits)",
        )

    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        cfg = config or {}
        api_key = cfg.get("TINYFISH_API_KEY", "")
        cost = self.calculate_worst_case_cost({"query": query, "max_results": max_results})

        if not api_key:
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.AUTH_ERROR,
                results=[],
                cost_estimate=cost,
                error_message="Missing TINYFISH_API_KEY",
            )

        endpoint = cfg.get("TINYFISH_SEARCH_ENDPOINT", "https://api.search.tinyfish.ai")
        headers = {"X-API-Key": api_key}
        params = {"query": query}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers, params=params)

            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results") or data.get("data") or []
                items = []
                for r in raw_results[:max_results]:
                    url = r.get("url") or r.get("link") or ""
                    if url:
                        items.append(SearchResultItem(
                            url=url,
                            title=r.get("title", ""),
                            snippet=r.get("snippet", "") or r.get("description", ""),
                            provider=self.name,
                        ))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.SUCCESS,
                    results=items,
                    cost_estimate=cost,
                )
            elif resp.status_code == 429:
                retry_sec = float(resp.headers.get("retry-after", "10"))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.RATE_LIMITED,
                    results=[],
                    cost_estimate=cost,
                    error_message="TinyFish HTTP 429 Rate Limit Exceeded",
                    retry_after_seconds=retry_sec,
                )
            elif resp.status_code in (401, 403):
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.AUTH_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"TinyFish HTTP {resp.status_code} Auth Error",
                )
            else:
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"TinyFish HTTP {resp.status_code}",
                )
        except Exception as exc:
            log.warning("tinyfish_search_failed", error=str(exc)[:100])
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                results=[],
                cost_estimate=cost,
                error_message=str(exc)[:120],
            )


class TavilyProvider(BaseSearchProvider):
    """Tavily Search API Adapter (POST https://api.tavily.com/search)."""

    @property
    def name(self) -> str:
        return "tavily"

    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        if session_disabled:
            return False
        api_key = config.get("TAVILY_API_KEY") or ""
        return bool(api_key.strip())

    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        depth = request_params.get("search_depth", "basic")
        auto_params = request_params.get("auto_parameters", False)

        if auto_params:
            return CostEstimate(
                status=CostStatus.UNKNOWN,
                units=0.0,
                unit_type="credits",
                estimated_amount_native=0.0,
                explanation="Tavily auto_parameters can increase depth/cost dynamically; UNKNOWN cost under zero-spend rule",
            )

        credits = 1.0 if depth == "basic" else 2.0
        return CostEstimate(
            status=CostStatus.KNOWN,
            units=credits,
            unit_type="credits",
            estimated_amount_native=credits,
            explanation=f"Tavily search ({depth}) costs {credits} credit(s) per request",
        )

    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        cfg = config or {}
        api_key = cfg.get("TAVILY_API_KEY", "")
        depth = cfg.get("TAVILY_SEARCH_DEPTH", "basic")
        cost = self.calculate_worst_case_cost({"search_depth": depth, "auto_parameters": False})

        if not api_key:
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.AUTH_ERROR,
                results=[],
                cost_estimate=cost,
                error_message="Missing TAVILY_API_KEY",
            )

        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": depth,
            "max_results": max_results,
            "auto_parameters": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.tavily.com/search", json=payload)

            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results") or []
                items = []
                for r in raw_results[:max_results]:
                    url = r.get("url") or ""
                    if url:
                        items.append(SearchResultItem(
                            url=url,
                            title=r.get("title", ""),
                            snippet=r.get("content") or r.get("snippet", ""),
                            provider=self.name,
                        ))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.SUCCESS,
                    results=items,
                    cost_estimate=cost,
                )
            elif resp.status_code == 429:
                retry_sec = float(resp.headers.get("retry-after", "10"))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.RATE_LIMITED,
                    results=[],
                    cost_estimate=cost,
                    error_message="Tavily HTTP 429 Rate Limit Exceeded",
                    retry_after_seconds=retry_sec,
                )
            elif resp.status_code in (401, 403):
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.AUTH_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Tavily HTTP {resp.status_code} Auth Error",
                )
            else:
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Tavily HTTP {resp.status_code}",
                )
        except Exception as exc:
            log.warning("tavily_search_failed", error=str(exc)[:100])
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                results=[],
                cost_estimate=cost,
                error_message=str(exc)[:120],
            )


class ExaProvider(BaseSearchProvider):
    """Exa AI Search API Adapter (POST https://api.exa.ai/search)."""

    @property
    def name(self) -> str:
        return "exa"

    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        if session_disabled:
            return False
        api_key = config.get("EXA_API_KEY") or ""
        return bool(api_key.strip())

    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        num_results = request_params.get("numResults", 10)
        has_summary = request_params.get("summary") is not None
        contents_val = request_params.get("contents")
        has_full_contents = contents_val is True or (isinstance(contents_val, dict) and (contents_val.get("text") or contents_val.get("summary")))

        if has_summary or has_full_contents or request_params.get("subpages"):
            return CostEstimate(
                status=CostStatus.UNKNOWN,
                units=0.0,
                unit_type="USD",
                estimated_amount_native=0.0,
                explanation="Exa full text/summaries/subpages incur variable extra charges; UNKNOWN cost under zero-spend rule",
            )

        base_usd = 0.007  # $7 per 1,000 requests for numResults <= 10
        if num_results > 10:
            extra_results = num_results - 10
            base_usd += extra_results * 0.001

        return CostEstimate(
            status=CostStatus.KNOWN,
            units=base_usd,
            unit_type="USD",
            estimated_amount_native=base_usd,
            explanation=f"Exa search ({num_results} results max) costs worst-case ${base_usd:.4f}",
        )

    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        cfg = config or {}
        api_key = cfg.get("EXA_API_KEY", "")
        num_res = min(max_results, cfg.get("EXA_SEARCH_NUM_RESULTS", 10))
        cost = self.calculate_worst_case_cost({"numResults": num_res})

        if not api_key:
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.AUTH_ERROR,
                results=[],
                cost_estimate=cost,
                error_message="Missing EXA_API_KEY",
            )

        payload = {
            "query": query,
            "numResults": num_res,
            "type": "auto",
            "contents": {
                "highlights": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": api_key, "Content-Type": "application/json"},
                    json=payload,
                )

            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results") or []
                items = []
                for r in raw_results[:num_res]:
                    url = r.get("url") or ""
                    if url:
                        highlights = r.get("highlights") or []
                        snippet_text = " ".join(highlights) if isinstance(highlights, list) and highlights else (r.get("text", "") or r.get("snippet", ""))
                        items.append(SearchResultItem(
                            url=url,
                            title=r.get("title", ""),
                            snippet=snippet_text,
                            provider=self.name,
                        ))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.SUCCESS,
                    results=items,
                    cost_estimate=cost,
                )
            elif resp.status_code == 429:
                retry_sec = float(resp.headers.get("retry-after", "10"))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.RATE_LIMITED,
                    results=[],
                    cost_estimate=cost,
                    error_message="Exa HTTP 429 Rate Limit Exceeded",
                    retry_after_seconds=retry_sec,
                )
            elif resp.status_code in (401, 403):
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.AUTH_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Exa HTTP {resp.status_code} Auth Error",
                )
            else:
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Exa HTTP {resp.status_code}",
                )
        except Exception as exc:
            log.warning("exa_search_failed", error=str(exc)[:100])
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                results=[],
                cost_estimate=cost,
                error_message=str(exc)[:120],
            )


class BraveProvider(BaseSearchProvider):
    """Brave Web Search API Adapter (GET https://api.search.brave.com/res/v1/web/search)."""

    @property
    def name(self) -> str:
        return "brave"

    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        if session_disabled:
            return False
        if not config.get("BRAVE_ENABLED", False):
            return False
        api_key = config.get("BRAVE_API_KEY") or ""
        return bool(api_key.strip())

    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        usd_cost = 0.005  # $5.00 per 1,000 requests
        return CostEstimate(
            status=CostStatus.KNOWN,
            units=usd_cost,
            unit_type="USD",
            estimated_amount_native=usd_cost,
            explanation="Brave Web Search costs $0.005 USD per request",
        )

    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        cfg = config or {}
        api_key = cfg.get("BRAVE_API_KEY", "")
        cost = self.calculate_worst_case_cost({"max_results": max_results})

        if not cfg.get("BRAVE_ENABLED", False) or not api_key:
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.AUTH_ERROR,
                results=[],
                cost_estimate=cost,
                error_message="Brave is disabled or missing BRAVE_API_KEY",
            )

        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
        params = {"q": query, "count": max_results}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params,
                )

            if resp.status_code == 200:
                data = resp.json()
                web_data = data.get("web") or {}
                raw_results = web_data.get("results") or []
                items = []
                for r in raw_results[:max_results]:
                    url = r.get("url") or ""
                    if url:
                        items.append(SearchResultItem(
                            url=url,
                            title=r.get("title", ""),
                            snippet=r.get("description", ""),
                            provider=self.name,
                        ))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.SUCCESS,
                    results=items,
                    cost_estimate=cost,
                )
            elif resp.status_code == 429:
                retry_sec = float(resp.headers.get("retry-after", "10"))
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.RATE_LIMITED,
                    results=[],
                    cost_estimate=cost,
                    error_message="Brave HTTP 429 Rate Limit Exceeded",
                    retry_after_seconds=retry_sec,
                )
            elif resp.status_code in (401, 403):
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.AUTH_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Brave HTTP {resp.status_code} Auth Error",
                )
            else:
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                    results=[],
                    cost_estimate=cost,
                    error_message=f"Brave HTTP {resp.status_code}",
                )
        except Exception as exc:
            log.warning("brave_search_failed", error=str(exc)[:100])
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                results=[],
                cost_estimate=cost,
                error_message=str(exc)[:120],
            )


class DDGSProvider(BaseSearchProvider):
    """DuckDuckGo Third-Party Scraper Adapter (UNOFFICIAL / SCRAPER-BASED)."""

    @property
    def name(self) -> str:
        return "ddgs"

    def is_available(self, config: Dict[str, Any], session_disabled: bool = False) -> bool:
        return not session_disabled

    def calculate_worst_case_cost(self, request_params: Dict[str, Any]) -> CostEstimate:
        return CostEstimate(
            status=CostStatus.NOT_APPLICABLE,
            units=0.0,
            unit_type="NOT_APPLICABLE",
            estimated_amount_native=0.0,
            explanation="DuckDuckGo is an unofficial web scraping fallback with no API cost",
        )

    async def _search_sync(self, query: str, max_results: int) -> list[dict]:
        def _exec():
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results, region="in-en"))
            except Exception as exc:
                log.debug("ddgs_sync_exception", error=str(exc)[:100])
                raise exc

        return await asyncio.to_thread(_exec)

    async def search(
        self, query: str, max_results: int = 10, config: Optional[Dict[str, Any]] = None
    ) -> ProviderSearchResponse:
        cost = self.calculate_worst_case_cost({"query": query})
        try:
            raw = await self._search_sync(query, max_results)
            items = []
            for r in raw:
                url = r.get("href") or r.get("url") or ""
                if url:
                    items.append(SearchResultItem(
                        url=url,
                        title=r.get("title", ""),
                        snippet=r.get("body") or r.get("snippet", ""),
                        provider=self.name,
                    ))
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.SUCCESS,
                results=items,
                cost_estimate=cost,
            )
        except Exception as exc:
            err_str = str(exc).lower()
            if "ratelimit" in err_str or "429" in err_str or "202" in err_str or "403" in err_str:
                return ProviderSearchResponse(
                    provider_name=self.name,
                    verdict=TransportVerdict.RATE_LIMITED,
                    results=[],
                    cost_estimate=cost,
                    error_message="DDGS rate limited / blocked by DuckDuckGo",
                    retry_after_seconds=15.0,
                )
            return ProviderSearchResponse(
                provider_name=self.name,
                verdict=TransportVerdict.TEMPORARY_PROVIDER_ERROR,
                results=[],
                cost_estimate=cost,
                error_message=str(exc)[:120],
            )
