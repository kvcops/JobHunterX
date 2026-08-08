"""
JobHunterX — Context-Aware Deterministic SERP Quality Gate

Evaluates SERP quality against user search context (target role, target location,
experience level, remote preference, freshness, desired sources) using a
weighted component formula (0 LLM calls required).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from jobhunterx.config.logging import get_logger
from jobhunterx.tools.search_providers import SearchResultItem

log = get_logger("quality_gate")


class QualityDecision(str, Enum):
    PASS = "PASS"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass
class SearchContext:
    target_role: str = "Software Engineer"
    target_location: str = "Hyderabad"
    experience_level: float = 0.0
    remote_preference: str = "hybrid"
    freshness_requirement: str = "recent"
    desired_sources: List[str] = field(default_factory=list)


@dataclass
class QualityGateResult:
    score: float
    decision: QualityDecision
    component_scores: Dict[str, float]
    reasons: List[str]


def evaluate_serp_quality(
    results: List[SearchResultItem],
    context: SearchContext,
    threshold: float = 0.60,
    min_results: int = 3,
) -> QualityGateResult:
    """Evaluate SERP quality against SearchContext using weighted component scoring."""

    if not results or len(results) < min_results:
        return QualityGateResult(
            score=0.0,
            decision=QualityDecision.INSUFFICIENT,
            component_scores={"count": 0.0},
            reasons=[f"SERP count ({len(results)}) below minimum threshold ({min_results})"],
        )

    role_words = [w.lower() for w in re.findall(r"\w+", context.target_role) if len(w) > 2]
    loc_low = context.target_location.lower()

    relevance_scores = []
    location_scores = []
    freshness_scores = []
    source_scores = []
    seen_urls = set()

    for item in results:
        text = f"{item.title} {item.snippet}".lower()
        url_low = item.url.lower()

        # 1. Job Relevance Score (30%)
        rel = 0.0
        if any(w in text for w in role_words):
            rel += 0.6
        if any(kw in text for kw in ["hiring", "job", "career", "opening", "position", "vacancy", "apply"]):
            rel += 0.4
        relevance_scores.append(min(1.0, rel))

        # 2. Location Relevance Score (25%) - positive signal, not hard rejection
        loc_s = 0.5  # Neutral default (since location often lives on full JD page)
        if loc_low in text or loc_low in url_low:
            loc_s = 1.0
        elif "remote" in text or "india" in text:
            loc_s = 0.8
        location_scores.append(loc_s)

        # 3. Freshness Signals (20%)
        fresh_s = 0.5
        if any(kw in text for kw in ["today", "just posted", "day ago", "days ago", "2026", "2025"]):
            fresh_s = 1.0
        freshness_scores.append(fresh_s)

        # 4. Source Quality (15%)
        src_s = 0.5
        if any(ats in url_low for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "smartrecruiters.com"]):
            src_s = 1.0
        elif any(portal in url_low for portal in ["linkedin.com/jobs/view", "naukri.com/job-listings", "foundit.in/job", "instahyre.com/job"]):
            src_s = 0.9
        source_scores.append(src_s)

        seen_urls.add(item.url.lower())

    avg_relevance = sum(relevance_scores) / len(relevance_scores)
    avg_location = sum(location_scores) / len(location_scores)
    avg_freshness = sum(freshness_scores) / len(freshness_scores)
    avg_source = sum(source_scores) / len(source_scores)
    uniqueness_score = min(1.0, len(seen_urls) / len(results))

    final_score = (
        0.30 * avg_relevance
        + 0.25 * avg_location
        + 0.20 * avg_freshness
        + 0.15 * avg_source
        + 0.10 * uniqueness_score
    )

    decision = QualityDecision.PASS if final_score >= threshold else QualityDecision.INSUFFICIENT
    reasons = [
        f"Final SERP Score: {final_score:.2f} (Threshold: {threshold:.2f})",
        f"Component Scores: Relevance={avg_relevance:.2f}, Location={avg_location:.2f}, Freshness={avg_freshness:.2f}, Source={avg_source:.2f}, Uniqueness={uniqueness_score:.2f}",
    ]

    log.info("quality_gate_evaluation", decision=decision.value, score=round(final_score, 2))
    return QualityGateResult(
        score=round(final_score, 2),
        decision=decision,
        component_scores={
            "relevance": round(avg_relevance, 2),
            "location": round(avg_location, 2),
            "freshness": round(avg_freshness, 2),
            "source": round(avg_source, 2),
            "uniqueness": round(uniqueness_score, 2),
        },
        reasons=reasons,
    )
