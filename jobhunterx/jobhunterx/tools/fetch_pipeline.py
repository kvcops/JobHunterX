"""
JobHunterX — Safe URL Normalization, Hybrid Fetch & Post-Extraction Deduplication Pipeline

Flow:
  1. Safe URL Normalization (strips only confirmed tracking params: utm_*, ref, source, fbclid, gclid)
  2. Pre-fetch selection (max 8 promising candidate URLs)
  3. Hybrid Fetch Escalation:
     - Direct HTTP + BeautifulSoup (for static pages)
     - TinyFish Fetch API (POST https://api.fetch.tinyfish.ai, max 10 URLs/batch) for JS-heavy/ATS pages
  4. Post-Extraction Semantic Identity Deduplication (job_id -> canonical_url -> company+title+location)
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from jobhunterx.config.logging import get_logger
from jobhunterx.tools.job_discovery import scrape_job_page
from jobhunterx.tools.usage_ledger import record_ledger_attempt

log = get_logger("fetch_pipeline")

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid",
}


def normalize_url_safely(raw_url: str) -> str:
    """Safely normalize URL without removing functional parameters."""
    if not raw_url:
        return ""

    url = raw_url.strip()
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Remove 'www.' prefix for consistency
        netloc = re.sub(r"^www\.", "", netloc)

        path = parsed.path.rstrip("/")

        # Preserve non-tracking query parameters
        qs = parse_qs(parsed.query, keep_blank_values=True)
        clean_qs = {}
        for k, v in qs.items():
            if k.lower() not in TRACKING_PARAMS:
                clean_qs[k] = v

        new_query = urlencode(clean_qs, doseq=True)
        normalized = urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
        return normalized
    except Exception:
        return raw_url


async def fetch_page_hybrid(url: str, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Hybrid fetch strategy: try direct HTTP first; escalate to TinyFish Fetch API if required."""
    cfg = config or {}
    clean_url = normalize_url_safely(url)

    # Step 1: Direct lightweight HTTP attempt
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    html_content = ""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(clean_url, headers=headers)
            if resp.status_code == 200 and len(resp.text) > 400:
                html_content = resp.text
    except Exception as exc:
        log.debug("direct_http_fetch_failed", url=clean_url[:60], error=str(exc)[:100])

    # Check if direct HTTP result contains usable HTML with job details
    if html_content:
        data = await scrape_job_page(clean_url)
        if data and data.get("jd_text") and len(data.get("jd_text", "")) > 150:
            await record_ledger_attempt(
                provider="direct_http",
                request_type="fetch",
                verdict="SUCCESS",
                url=clean_url,
                http_status=200,
            )
            return data

    # Step 2: Escalate to TinyFish Fetch API for JS-heavy/ATS pages if API key is configured
    tf_key = cfg.get("TINYFISH_API_KEY", "")
    if tf_key:
        fetch_endpoint = cfg.get("TINYFISH_FETCH_ENDPOINT", "https://api.fetch.tinyfish.ai")
        tf_headers = {"X-API-Key": tf_key, "Content-Type": "application/json"}
        payload = {"urls": [clean_url]}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(fetch_endpoint, headers=tf_headers, json=payload)

            await record_ledger_attempt(
                provider="tinyfish",
                request_type="fetch",
                verdict="SUCCESS" if resp.status_code == 200 else f"HTTP_{resp.status_code}",
                url=clean_url,
                http_status=resp.status_code,
                unit_type="credits",
            )

            if resp.status_code == 200:
                body = resp.json()
                results = body.get("results") or body.get("data") or []
                if results and isinstance(results, list):
                    item = results[0]
                    return {
                        "title": item.get("title", ""),
                        "company": item.get("company", ""),
                        "location": item.get("location", ""),
                        "jd_text": item.get("markdown") or item.get("text") or item.get("content", ""),
                        "apply_url": clean_url,
                    }
        except Exception as exc:
            log.warning("tinyfish_fetch_failed", url=clean_url[:60], error=str(exc)[:100])

    return None


async def execute_fetch_pipeline(
    urls: List[str], max_fetch: int = 8, config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute multi-stage deduplicated fetch pipeline for a list of candidate URLs."""
    cfg = config or {}

    # 1. Pre-fetch safe URL normalization & deduplication
    normalized_map: Dict[str, str] = {}
    for raw in urls:
        norm = normalize_url_safely(raw)
        if norm and norm not in normalized_map:
            normalized_map[norm] = raw

    candidate_urls = list(normalized_map.keys())[:max_fetch]
    log.info("fetch_pipeline_candidates", count=len(candidate_urls))

    sem = asyncio.Semaphore(5)

    async def _fetch_one(u: str):
        async with sem:
            return await fetch_page_hybrid(u, config=cfg)

    tasks = [_fetch_one(u) for u in candidate_urls]
    raw_jobs = await asyncio.gather(*tasks, return_exceptions=True)

    # 2. Post-extraction semantic identity deduplication
    extracted_jobs: List[Dict[str, Any]] = []
    seen_semantic_keys: set[str] = set()

    for job in raw_jobs:
        if isinstance(job, dict) and job.get("jd_text"):
            comp = (job.get("company") or "").lower().strip()
            title = (job.get("title") or "").lower().strip()
            loc = (job.get("location") or "").lower().strip()
            job_id = job.get("job_id", "")

            if job_id:
                sem_key = f"id:{job_id}"
            else:
                sem_key = f"{comp}:{title}:{loc}"

            if sem_key not in seen_semantic_keys:
                seen_semantic_keys.add(sem_key)
                extracted_jobs.append(job)

    log.info("fetch_pipeline_complete", extracted_jobs=len(extracted_jobs))
    return extracted_jobs
