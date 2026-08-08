"""
Unit tests for Context-Aware Deterministic SERP Quality Gate.
"""

from jobhunterx.tools.quality_gate import QualityDecision, SearchContext, evaluate_serp_quality
from jobhunterx.tools.search_providers import SearchResultItem


def test_quality_gate_evaluation():
    ctx = SearchContext(target_role="Python Developer", target_location="Hyderabad")

    good_results = [
        SearchResultItem(
            url="https://boards.greenhouse.io/company/jobs/123",
            title="Senior Python Developer - Hyderabad",
            snippet="We are hiring a Python Engineer in Hyderabad. Posted today.",
            provider="tavily",
        ),
        SearchResultItem(
            url="https://linkedin.com/jobs/view/456",
            title="Backend Engineer (Python)",
            snippet="Remote / India role for Python Developer. Apply now.",
            provider="tavily",
        ),
        SearchResultItem(
            url="https://jobs.lever.co/tech/789",
            title="Python Software Engineer",
            snippet="Hyderabad tech team hiring Python Engineer.",
            provider="tavily",
        ),
    ]

    res = evaluate_serp_quality(good_results, context=ctx, threshold=0.50)
    assert res.decision == QualityDecision.PASS
    assert res.score >= 0.50
    assert "relevance" in res.component_scores
