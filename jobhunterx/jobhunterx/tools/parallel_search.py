"""
JobHunterX — Parallel AI Web Search & Content Fetching Engine

High-throughput, asynchronous search and content extraction engine that
runs multi-query web searches and concurrent page fetching across ATS systems
and major job portals (LinkedIn, Indeed, FoundIt, Naukri, Instahyre).
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from jobhunterx.config.logging import get_logger

log = get_logger("parallel_search")


@dataclass
class SearchItem:
    query: str
    title: str
    url: str
    snippet: str
    source: str = "parallel_search"


async def execute_parallel_search(
    queries: list[str],
    max_results_per_query: int = 15,
    max_concurrency: int = 5,
) -> list[dict]:
    """Execute multiple search queries concurrently.

    Returns a deduplicated list of search result dicts with url, title, snippet, query.
    """
    from jobhunterx.tools import job_discovery

    sem = asyncio.Semaphore(max_concurrency)
    results: list[dict] = []
    seen_urls: set[str] = set()

    async def _search_one(q: str):
        async with sem:
            try:
                raw_results = await job_discovery.search_ddg(q, max_results=max_results_per_query)
                return q, raw_results
            except Exception as exc:
                log.warning("parallel_search_query_failed", query=q[:50], error=str(exc)[:100])
                return q, []

    tasks = [_search_one(q) for q in queries]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, Exception) or not isinstance(item, tuple):
            continue
        query_str, res_list = item
        for res in res_list:
            url = getattr(res, "url", "").strip()
            if not url:
                continue
            url_norm = url.rstrip("/").lower()
            if url_norm in seen_urls:
                continue
            seen_urls.add(url_norm)

            results.append({
                "url": url,
                "title": getattr(res, "title", ""),
                "snippet": getattr(res, "snippet", ""),
                "company": getattr(res, "company", ""),
                "is_job_posting": getattr(res, "is_job_posting", True),
                "query": query_str,
            })

    log.info("parallel_search_complete", queries_count=len(queries), total_results=len(results))
    return results


async def execute_parallel_fetch(
    urls: list[str],
    max_concurrency: int = 10,
    timeout: float = 12.0,
) -> list[dict]:
    """Concurrently fetch and scrape job page content for a list of URLs.

    Returns structured job data dicts for successfully scraped pages.
    """
    from jobhunterx.tools import job_discovery

    sem = asyncio.Semaphore(max_concurrency)
    scraped_jobs: list[dict] = []

    async def _fetch_one(url: str):
        async with sem:
            try:
                data = await job_discovery.scrape_job_page(url)
                if data and data.get("jd_text"):
                    return data
            except Exception as exc:
                log.debug("parallel_fetch_failed", url=url[:60], error=str(exc)[:100])
            return None

    tasks = [_fetch_one(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, dict) and res.get("jd_text"):
            scraped_jobs.append(res)

    log.info("parallel_fetch_complete", urls_count=len(urls), jobs_extracted=len(scraped_jobs))
    return scraped_jobs
