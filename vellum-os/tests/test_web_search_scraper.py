"""Tests for web_search_scraper.py fixes:
- LLM classification map (regression: was a set comprehension, always empty)
- New Bing HTML fallback + ATS-targeted queries
- Valid job URL patterns
"""

import pytest

from vellum.tools.web_search_scraper import (
    _build_classification_map,
    _build_search_queries,
    _is_valid_job_url,
    search_jobs_via_web,
)


class TestClassificationMap:
    """Regression test for the {…} set-comprehension bug that silently
    produced an EMPTY classification map, making LLM filtering a no-op."""

    def test_builds_map_from_list(self):
        classifications = [
            {"index": 0, "is_direct_job_page": True, "company_name": "Acme"},
            {"index": 1, "is_direct_job_page": False, "company_name": "Unknown"},
        ]
        class_map = _build_classification_map(classifications)
        assert class_map == {
            0: {"index": 0, "is_direct_job_page": True, "company_name": "Acme"},
            1: {"index": 1, "is_direct_job_page": False, "company_name": "Unknown"},
        }

    def test_map_returns_index_lookupable(self):
        """The critical property: class_map.get(idx) must hit the LLM's
        classification for the same result index."""
        classifications = [{"index": 2, "is_direct_job_page": True, "company_name": "Beta"}]
        class_map = _build_classification_map(classifications)
        assert class_map.get(2) is not None
        assert class_map.get(2)["is_direct_job_page"] is True

    def test_accepts_string_indices(self):
        """Some LLMs emit string indices; map must still key by int."""
        class_map = _build_classification_map([{"index": "3", "is_direct_job_page": True}])
        assert class_map.get(3) is not None
        assert class_map.get("3") is None

    def test_ignores_garbage_items(self):
        class_map = _build_classification_map(
            [{"index": None}, "not-a-dict", {"index": 1.5}, 42]
        )
        assert class_map == {}

    def test_empty_and_non_list(self):
        assert _build_classification_map([]) == {}
        assert _build_classification_map({}) == {}
        assert _build_classification_map(None) == {}


class TestSearchQueries:
    def test_queries_cover_workday_ats(self):
        queries = _build_search_queries("Python Developer", "Bangalore")
        joined = " ".join(queries).lower()
        assert "myworkdayjobs.com" in joined

    def test_queries_cover_smartrecruiters(self):
        queries = _build_search_queries("Python Developer", "Bangalore")
        joined = " ".join(queries).lower()
        assert "smartrecruiters.com" in joined

    def test_queries_cover_freshteam(self):
        queries = _build_search_queries("Python Developer", "Bangalore")
        joined = " ".join(queries).lower()
        assert "freshteam.com" in joined

    def test_queries_include_careers_apply(self):
        queries = _build_search_queries("Python Developer", "Bangalore")
        joined = " ".join(queries).lower()
        assert "careers apply" in joined


class TestValidJobUrl:
    def test_workday_url_valid(self):
        assert _is_valid_job_url("https://acme.myworkdayjobs.com/en-US/Careers/job/123")

    def test_position_url_valid(self):
        assert _is_valid_job_url("https://acme.com/careers/position/456")

    def test_join_us_url_valid(self):
        assert _is_valid_job_url("https://acme.com/join-us/engineering")

    def test_recruitee_url_valid(self):
        assert _is_valid_job_url("https://acme.recruitee.com/o/backend-engineer")

    def test_aggregator_url_rejected(self):
        assert not _is_valid_job_url("https://www.linkedin.com/jobs/view/123")

    def test_social_url_rejected(self):
        assert not _is_valid_job_url("https://twitter.com/acme/status/123")


class TestModuleSurface:
    def test_bing_fallback_exists(self):
        import inspect
        from vellum.tools import web_search_scraper

        assert hasattr(web_search_scraper, "_search_bing_html")
        assert inspect.iscoroutinefunction(web_search_scraper._search_bing_html)

    def test_search_jobs_via_web_exists(self):
        assert callable(search_jobs_via_web)
