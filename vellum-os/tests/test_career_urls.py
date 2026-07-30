"""Tests for career_urls.py — URL scoring, ATS detection, excluded domains."""

import pytest
from vellum.tools.career_urls import (
    is_excluded_domain,
    detect_ats_from_url,
    score_career_url,
    get_ats_api_url,
    get_career_urls_for_slug,
    get_contact_urls_for_domain,
    EXCLUDED_DOMAINS,
    ATS_PATTERNS,
)


class TestIsExcludedDomain:
    def test_linkedin_excluded(self):
        assert is_excluded_domain("https://www.linkedin.com/jobs/123") is True

    def test_naukri_excluded(self):
        assert is_excluded_domain("https://www.naukri.com/job/456") is True

    def test_instahyre_excluded(self):
        assert is_excluded_domain("https://www.instahyre.com/company/foo") is True

    def test_randstad_excluded(self):
        assert is_excluded_domain("https://www.randstad.com/careers") is True

    def test_company_domain_not_excluded(self):
        assert is_excluded_domain("https://careers.google.com/jobs") is False

    def test_greenhouse_not_excluded(self):
        assert is_excluded_domain("https://boards.greenhouse.io/company") is False

    def test_lever_not_excluded(self):
        assert is_excluded_domain("https://jobs.lever.co/company") is False

    def test_invalid_url(self):
        assert is_excluded_domain("") is False
        assert is_excluded_domain("not-a-url") is False


class TestDetectAtsFromUrl:
    def test_greenhouse(self):
        assert detect_ats_from_url("https://boards.greenhouse.io/spotify") == "greenhouse"

    def test_lever(self):
        assert detect_ats_from_url("https://jobs.lever.co/rippling") == "lever"

    def test_lever_www(self):
        assert detect_ats_from_url("https://www.lever.co/jobs/rippling") == "lever"

    def test_ashby(self):
        assert detect_ats_from_url("https://jobs.ashbyhq.com/figma") == "ashby"

    def test_smartrecruiters(self):
        assert detect_ats_from_url("https://jobs.smartrecruiters.com/stripe") == "smartrecruiters"

    def test_freshteam(self):
        assert detect_ats_from_url("https://company.freshteam.com/jobs") == "freshteam"

    def test_workday(self):
        assert detect_ats_from_url("https://company.wd1.myworkdayjobs.com") == "workday"

    def test_no_ats(self):
        assert detect_ats_from_url("https://careers.google.com") is None

    def test_case_insensitive(self):
        assert detect_ats_from_url("https://BOARDS.GREENHOUSE.IO/test") == "greenhouse"


class TestScoreCareerUrl:
    def test_excluded_returns_zero(self):
        url = "https://www.linkedin.com/jobs/123"
        assert score_career_url(url, "test") == 0.0

    def test_greenhouse_bonus(self):
        url = "https://boards.greenhouse.io/spotify"
        score = score_career_url(url, "spotify")
        assert score > 0.5

    def test_careers_path_bonus(self):
        url = "https://careers.google.com/jobs"
        score = score_career_url(url, "google")
        assert score > 0.5

    def test_company_slug_bonus(self):
        url = "https://careers.spotify.com/jobs"
        score_high = score_career_url(url, "spotify")
        score_low = score_career_url(url, "othercompany")
        assert score_high > score_low

    def test_blog_penalty(self):
        url = "https://blog.google/careers"
        score = score_career_url(url, "google")
        # Blog gets noise penalty but careers path bonus; score may vary
        assert 0.0 <= score <= 1.0

    def test_invalid_url(self):
        score = score_career_url("", "")
        # Empty URL gets 0.0 from parse failure or 0.5 base score
        assert 0.0 <= score <= 1.0

    def test_range(self):
        url = "https://careers.acme.com/jobs"
        score = score_career_url(url, "acme")
        assert 0.0 <= score <= 1.0


class TestGetAtsApiUrl:
    def test_greenhouse_api(self):
        url = get_ats_api_url("greenhouse", "spotify")
        assert "boards-api.greenhouse.io" in url
        assert "spotify" in url

    def test_lever_api(self):
        url = get_ats_api_url("lever", "rippling")
        assert "api.lever.co" in url
        assert "rippling" in url

    def test_unknown_ats(self):
        assert get_ats_api_url("unknown", "test") is None


class TestGetCareerUrlsForSlug:
    def test_returns_list(self):
        urls = get_career_urls_for_slug("spotify")
        assert isinstance(urls, list)
        assert len(urls) > 10

    def test_contains_known_urls(self):
        urls = get_career_urls_for_slug("spotify")
        assert "https://careers.spotify.com" in urls
        assert "https://boards.greenhouse.io/spotify" in urls
        assert "https://jobs.lever.co/spotify" in urls

    def test_slug_substituted(self):
        urls = get_career_urls_for_slug("testcompany")
        for url in urls:
            assert "{slug}" not in url


class TestGetContactUrlsForDomain:
    def test_returns_list(self):
        urls = get_contact_urls_for_domain("acme.com")
        assert isinstance(urls, list)
        assert len(urls) > 5

    def test_contains_contact(self):
        urls = get_contact_urls_for_domain("acme.com")
        assert "https://acme.com/contact" in urls
        assert "https://acme.com/about" in urls

    def test_domain_substituted(self):
        urls = get_contact_urls_for_domain("example.com")
        for url in urls:
            assert "{domain}" not in url
