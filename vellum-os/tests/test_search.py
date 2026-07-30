"""Tests for search.py — verify DDGS removal, remaining functions intact."""

import pytest
from vellum.tools import search


class TestDDGSRemoval:
    def test_no_ddgs_import(self):
        """Verify DuckDuckGo search functions were removed."""
        assert not hasattr(search, "search_wellfound_instahyre_jobs")
        assert not hasattr(search, "search_direct_ats_jobs")
        assert not hasattr(search, "search_career_pages")


class TestRemainingFunctions:
    def test_fetch_hasjob_jobs_exists(self):
        assert callable(getattr(search, "fetch_hasjob_jobs", None))

    def test_search_unadvertised_social_posts_exists(self):
        assert callable(getattr(search, "search_unadvertised_social_posts", None))

    def test_search_contacts_exists(self):
        assert callable(getattr(search, "search_contacts", None))

    def test_verify_email_mx_exists(self):
        assert callable(getattr(search, "verify_email_mx", None))

    def test_score_career_url_exists(self):
        assert callable(getattr(search, "score_career_url", None))

    def test_search_multi_engine_exists(self):
        assert callable(getattr(search, "search_multi_engine", None))
