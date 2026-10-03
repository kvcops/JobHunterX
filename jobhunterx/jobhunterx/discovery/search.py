"""
Stages 2–4 — Search planning and multi-source discovery.

Queries are built from the CandidateSnapshot (titles, tracks, locations the
AI derived from the candidate's own profile). The LLM proposes diverse
queries; the code validates and deduplicates them, and always adds
first-party ATS `site:` queries so discovery is anchored on employers' own
hiring systems rather than aggregator snippets.

Search results are *leads*, never jobs: every result is resolved to a real
posting later (ATS API → JSON-LD → page text).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.discovery.ats import ats_site_hints
from jobhunterx.domain.candidate import CandidateSnapshot
from jobhunterx.domain.common import WorkMode
from jobhunterx.intelligence.llm_structured import call_structured
from jobhunterx.intelligence.text import tokens
from jobhunterx.tools.search_router import SearchRouter

log = get_logger("search")

PLAN_VERSION = "plan-v1"
QUERY_CONCURRENCY = 3                   # searches in flight at once (Deep Search fans each out to several engines)


@dataclass
class SearchScope:
    titles: list[str]
    locations: list[str]          # display names of places to search
    include_remote: bool
    country: str


class _Plan(BaseModel):
    queries: list[str] = Field(default_factory=list, description="8-14 distinct web search queries")


_PLAN_SYSTEM = """You design web search queries that surface individual, currently open job postings for one candidate.
Use the candidate's target titles, adjacent titles and locations given to you. Vary the angle: exact titles,
title synonyms employers use, skill-anchored queries for their strongest skills, location variants, and remote variants
(only if remote is accepted). Prefer queries that land on employers' own career pages and applicant-tracking-system job pages.
Do not include seniority levels above the candidate's. Keep each query under 120 characters. No duplicates."""


def scope_from_snapshot(snap: CandidateSnapshot, *, locations: Optional[list[str]] = None,
                        role_focus: Optional[list[str]] = None, work_modes: Optional[list[str]] = None) -> SearchScope:
    titles = list(dict.fromkeys([*(role_focus or []), *snap.target_titles]))
    if not titles:
        titles = [f.label for f in snap.role_families]
    locs = locations or [p.city or p.country for p in snap.locations if (p.city or p.country)]
    modes = set(work_modes or [m.value for m in snap.work_modes])
    return SearchScope(titles=titles[:8], locations=locs[:4], include_remote=WorkMode.REMOTE.value in modes,
                       country=snap.home_country)


def _norm_query(q: str) -> str:
    return " ".join(sorted(set(tokens(q))))


def deterministic_queries(scope: SearchScope, limit: int) -> list[str]:
    """ATS-anchored queries from titles × places; no extra vocabulary."""
    hosts = ats_site_hints()
    places = list(scope.locations)
    if scope.include_remote:
        places.append(f"remote {scope.country}".strip())
    places = places or [scope.country]
    out = []
    for ti, title in enumerate(scope.titles[:4]):
        for pi, place in enumerate(places[:3]):
            host = hosts[(ti * 3 + pi) % len(hosts)]
            out.append(f'site:{host} "{title}" {place}'.strip())
            out.append(f'"{title}" {place}'.strip())
    return out[:limit]


async def plan_queries(snap: CandidateSnapshot, scope: SearchScope, max_queries: int) -> tuple[list[str], str]:
    """Return (queries, method)."""
    base = deterministic_queries(scope, max_queries)
    user = (
        f"Target titles: {', '.join(scope.titles)}\n"
        f"Adjacent titles: {', '.join(snap.adjacent_titles[:6])}\n"
        f"Strongest skills: {', '.join(s.name for s in snap.skills[:8])}\n"
        f"Candidate level: {snap.seniority.value}, ~{snap.professional_years:g} years\n"
        f"Locations: {', '.join(scope.locations) or scope.country}; remote accepted: {scope.include_remote}; country: {scope.country}\n"
        f"Applicant-tracking-system job hosts you may target with site: {', '.join(ats_site_hints())}"
    )
    plan, _ = await call_structured(
        task="search_plan", version=PLAN_VERSION, model=_Plan, system=_PLAN_SYSTEM, user=user,
        chain="fast", max_tokens=900, cache_parts=(snap.profile_hash, user),
    )
    method = "llm" if plan else "fallback"
    seen: set[str] = set()
    queries: list[str] = []
    # Interleave ATS-anchored and LLM queries so both kinds survive the cap.
    llm_q = [q.strip() for q in (plan.queries if plan else []) if 5 < len(q.strip()) <= 160]
    for pair in zip(base, llm_q):
        for q in pair:
            k = _norm_query(q)
            if k and k not in seen:
                seen.add(k)
                queries.append(q)
    for q in base[len(llm_q):] + llm_q[len(base):]:
        k = _norm_query(q)
        if k and k not in seen:
            seen.add(k)
            queries.append(q)
    return queries[:max_queries], method


def router_config() -> dict:
    s = get_settings()
    return {
        "PRIMARY_SEARCH_PROVIDER": s.primary_search_provider,
        "STRICT_ZERO_SPEND_PROTECTION": s.strict_zero_spend_protection,
        "TINYFISH_API_KEY": s.tinyfish_api_key,
        "TAVILY_API_KEY": s.tavily_api_key,
        "EXA_API_KEY": s.exa_api_key,
        "BRAVE_API_KEY": s.brave_api_key,
        "BRAVE_ENABLED": s.brave_enabled,
        "TAVILY_SEARCH_DEPTH": s.tavily_search_depth,
        "EXA_SEARCH_NUM_RESULTS": s.exa_search_num_results,
    }


@dataclass
class Lead:
    url: str
    title: str
    snippet: str
    provider: str
    query: str


FREE_PROVIDERS = ("deep", "ddgs")       # keyless: Deep Search (multi-engine + crawl + AI rerank), plain DuckDuckGo


def _provider_lists(router: SearchRouter, n_queries: int) -> tuple[list[list[str]], str]:
    """Per-query provider order from the user's settings (order, on/off, strategy)."""
    from jobhunterx.config import app_state
    order, strategy = app_state.search_plan()
    if not get_settings().enable_web_search_apis:
        order = [p for p in order if p in FREE_PROVIDERS]
    usable = [p for p in order if p in router.providers
              and router.providers[p].is_available(router.config, session_disabled=router.session_disabled.get(p, False))]
    paid, free = [p for p in usable if p not in FREE_PROVIDERS], [p for p in usable if p in FREE_PROVIDERS]
    lists = []
    for i in range(n_queries):
        if strategy in ("spread", "combine") and paid:
            k = i % len(paid)
            rot = paid[k:] + paid[:k]          # each query starts at a different provider: quotas are shared
        else:
            rot = list(paid)
        lists.append(rot + free)
    return lists, strategy


async def run_queries(queries: list[str], per_query: int = 10,
                      on_progress: Optional[Callable[[int, int], Awaitable[None]]] = None) -> list[Lead]:
    """Run planned queries through the enabled search providers.

    fallback — the first provider that returns results answers (fewest calls)
    spread   — queries rotate across providers, sharing their free quotas
    combine  — two providers answer each query and results are merged (widest coverage)
    """
    router = SearchRouter(config=router_config())
    lists, strategy = _provider_lists(router, len(queries))
    sem = asyncio.Semaphore(QUERY_CONCURRENCY)
    done = {"n": 0}

    async def one(q: str, providers: list[str]) -> list:
        batches = []
        if providers:
            async with sem:
                try:
                    batches.append(await router.execute_query(q, max_results=per_query, providers=providers))
                    if strategy == "combine" and len(providers) > 1:
                        answered = batches[0][0].provider if batches[0] else None
                        rest = [p for p in providers if p != answered]
                        batches.append(await router.execute_query(q, max_results=per_query, providers=rest))
                except Exception as exc:
                    log.warning("search_query_failed", query=q[:60], error=str(exc)[:120])
        done["n"] += 1
        if on_progress:
            await on_progress(done["n"], len(queries))
        return [(q, it) for items in batches for it in items]

    if on_progress:
        await on_progress(0, len(queries))
    results = await asyncio.gather(*(one(q, p) for q, p in zip(queries, lists)))
    leads: list[Lead] = []
    seen: set[str] = set()
    for group in results:                      # keep query order, so the planner's best queries lead
        for q, it in group:
            key = re.sub(r"[#?].*$", "", (it.url or "").strip().lower()).rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            leads.append(Lead(url=it.url, title=it.title, snippet=it.snippet, provider=it.provider, query=q))
    return leads
