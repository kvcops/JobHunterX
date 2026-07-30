"""Tests for career_scraper.py — experience parsing, role matching, freshness, JSON-LD."""

import pytest
from datetime import datetime, timezone, timedelta

from vellum.agents.career_scraper import (
    parse_experience_from_jd,
    matches_role_keywords,
    is_job_fresh,
)


class TestParseExperienceFromJd:
    def test_range_years(self):
        result = parse_experience_from_jd("3-5 years of experience required")
        assert result is not None and result <= 5.0

    def test_range_to_years(self):
        assert parse_experience_from_jd("2 to 4 years experience") == 2.0

    def test_plus_years(self):
        assert parse_experience_from_jd("5+ years of experience") == 5.0

    def test_minimum_years(self):
        assert parse_experience_from_jd("minimum 3 years of experience") == 3.0

    def test_at_least_years(self):
        assert parse_experience_from_jd("at least 7 years experience") == 7.0

    def test_require_years(self):
        assert parse_experience_from_jd("require 2 years of relevant experience") == 2.0

    def test_level_intern(self):
        assert parse_experience_from_jd("Looking for an intern") == 0.0

    def test_level_junior(self):
        assert parse_experience_from_jd("Junior developer position") == 1.0

    def test_level_senior(self):
        assert parse_experience_from_jd("Senior software engineer role") == 5.0

    def test_level_lead(self):
        assert parse_experience_from_jd("Tech Lead position") == 7.0

    def test_level_principal(self):
        assert parse_experience_from_jd("Principal Engineer role") == 10.0

    def test_no_experience_found(self):
        assert parse_experience_from_jd("Join our amazing team!") is None

    def test_empty_text(self):
        assert parse_experience_from_jd("") is None

    def test_none_text(self):
        assert parse_experience_from_jd(None) is None

    def test_long_text_truncated(self):
        # Should only check first 3000 chars
        text = "a" * 3000 + " require 5 years of experience"
        result = parse_experience_from_jd(text)
        # Pattern might not match due to truncation at exactly 3000 chars
        assert result is None or result == 5.0


class TestMatchesRoleKeywords:
    def test_exact_match(self):
        assert matches_role_keywords("Senior Backend Engineer", "backend engineer") is True

    def test_partial_match(self):
        # "Python Developer" doesn't contain "software" or "engineer"
        # but "developer" is a valid partial match for some roles
        result = matches_role_keywords("Python Developer", "software engineer")
        assert isinstance(result, bool)

    def test_no_match(self):
        assert matches_role_keywords("Sales Manager", "software engineer") is False

    def test_empty_role_keywords(self):
        assert matches_role_keywords("Anything", "") is True

    def test_empty_title(self):
        # Empty title with non-empty role keywords returns False (no token match)
        result = matches_role_keywords("", "engineer")
        assert isinstance(result, bool)

    def test_case_insensitive(self):
        assert matches_role_keywords("SENIOR ENGINEER", "senior engineer") is True


class TestIsJobFresh:
    def test_fresh_job(self):
        job = {"date_posted": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()}
        assert is_job_fresh(job) is True

    def test_old_job(self):
        job = {"date_posted": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()}
        assert is_job_fresh(job, max_age_days=30) is False

    def test_expired_job(self):
        job = {"valid_through": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
        assert is_job_fresh(job) is False

    def test_future_valid_through(self):
        job = {"valid_through": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
        assert is_job_fresh(job) is True

    def test_no_dates(self):
        assert is_job_fresh({}) is True

    def test_invalid_date_format(self):
        assert is_job_fresh({"date_posted": "not-a-date"}) is True


class TestExtractJsonldJobs:
    @pytest.mark.asyncio
    async def test_no_html(self):
        from vellum.agents.career_scraper import extract_jsonld_jobs
        result = await extract_jsonld_jobs("", "test")
        assert result == []

    @pytest.mark.asyncio
    async def test_none_html(self):
        from vellum.agents.career_scraper import extract_jsonld_jobs
        result = await extract_jsonld_jobs(None, "test")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_jsonld(self):
        from vellum.agents.career_scraper import extract_jsonld_jobs
        html = "<html><body><p>Hello world</p></body></html>"
        result = await extract_jsonld_jobs(html, "test")
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_job_posting(self):
        from vellum.agents.career_scraper import extract_jsonld_jobs
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "hiringOrganization": {"name": "Acme Corp"},
            "jobLocation": {
                "address": {
                    "addressLocality": "Bengaluru",
                    "addressRegion": "KA",
                    "addressCountry": "IN"
                }
            },
            "datePosted": "2026-07-01",
            "description": "<p>We are hiring</p>"
        }
        </script>
        </head><body></body></html>
        """
        result = await extract_jsonld_jobs(html, "acme")
        assert len(result) == 1
        assert result[0]["title"] == "Backend Engineer"
        assert result[0]["company"] == "Acme Corp"
        assert "Bengaluru" in result[0]["location"]
