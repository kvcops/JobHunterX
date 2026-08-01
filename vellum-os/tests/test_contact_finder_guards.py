"""Tests for contact_finder.py email-guard overhaul:
- placeholder / fake email rejection
- dedup keeps highest confidence
- ranking: real found emails > permutations > generic fallbacks
- job-page email scraping method exists
"""

import pytest

from vellum.agents.contact_finder import (
    PLACEHOLDER_DOMAINS,
    _is_placeholder_email,
    _dedupe_emails,
    _keep_personal_only,
    rank_email_guesses,
    scrape_job_page_for_emails,
    extract_github_emails,
)


class TestPlaceholderDetection:
    def test_empty_rejected(self):
        assert _is_placeholder_email("") is True

    def test_no_at_sign(self):
        assert _is_placeholder_email("notanemail") is True

    def test_example_dot_com_rejected(self):
        assert _is_placeholder_email("contact@example.com") is True

    def test_acme_dot_com_rejected(self):
        assert _is_placeholder_email("hello@acme.com") is True

    def test_yourcompany_dot_com_rejected(self):
        assert _is_placeholder_email("hr@yourcompany.com") is True

    def test_mailinator_rejected(self):
        assert _is_placeholder_email("bob@mailinator.com") is True

    def test_legit_email_accepted(self):
        assert _is_placeholder_email("priya@stripe.com") is False

    def test_single_char_domain_rejected(self):
        assert _is_placeholder_email("a@b") is True

    def test_yourname_localpart_rejected(self):
        assert _is_placeholder_email("yourname@acme.com") is True

    def test_hello_localpart_accepted(self):
        assert _is_placeholder_email("hello@stripe.com") is False

    def test_rfc_reserved_tld_rejected(self):
        assert _is_placeholder_email("x@company.invalid") is True
        assert _is_placeholder_email("x@company.localhost") is True

    def test_example_subdomain_rejected(self):
        assert _is_placeholder_email("careers@acme.example.com") is True


class TestDedupe:
    def test_dedupe_keeps_highest_confidence(self):
        items = [
            {"address": "a@b.com", "confidence": 0.5, "pattern": "contact_page"},
            {"address": "A@B.COM", "confidence": 0.8, "pattern": "job_page"},
        ]
        result = _dedupe_emails(items)
        assert len(result) == 1
        assert result[0]["pattern"] == "job_page"

    def test_placeholder_dropped_during_dedupe(self):
        result = _dedupe_emails([{"address": "x@example.com", "confidence": 0.9}])
        assert result == []

    def test_empty_input(self):
        assert _dedupe_emails([]) == []


class TestRanking:
    def _item(self, pattern, confidence, mx=None):
        return {
            "address": f"x{pattern}@b.com",
            "pattern": pattern,
            "confidence": confidence,
            "mx_valid": mx,
        }

    def test_found_beats_permutation_beats_generic(self):
        items = [
            self._item("generic_fallback", 0.2, mx=True),
            self._item("permutation", 0.6),
            self._item("job_page", 0.5, mx=True),
        ]
        ranked = rank_email_guesses(items)
        assert [i["pattern"] for i in ranked] == ["job_page", "permutation", "generic_fallback"]

    def test_mx_valid_found_leads_within_tier(self):
        items = [
            self._item("contact_page", 0.6),
            self._item("contact_page", 0.7, mx=True),
        ]
        ranked = rank_email_guesses(items)
        assert ranked[0]["mx_valid"] is True

    def test_empty(self):
        assert rank_email_guesses([]) == []


class TestKeepPersonalOnly:
    def _item(self, pattern, addr):
        return {"address": addr, "pattern": pattern, "confidence": 0.5}

    def test_drops_company_role_inboxes(self):
        items = [
            self._item("site_crawl", "connect@gyandata.com"),
            self._item("site_crawl", "careers@gyandata.com"),
            self._item("site_crawl", "admin@gyandata.com"),
            self._item("site_crawl", "priya.sharma@gyandata.com"),
        ]
        kept = _keep_personal_only(items)
        assert [e["address"] for e in kept] == ["priya.sharma@gyandata.com"]

    def test_keeps_permutations(self):
        items = [self._item("permutation", "psharma@gyandata.com")]
        assert _keep_personal_only(items) == items

    def test_keeps_personal_gmail(self):
        items = [self._item("site_crawl", "priyasharma@gmail.com")]
        assert len(_keep_personal_only(items)) == 1

    def test_drops_noreply(self):
        items = [self._item("site_crawl", "noreply@gyandata.com")]
        assert _keep_personal_only(items) == []

    def test_empty(self):
        assert _keep_personal_only([]) == []


class TestModuleSurface:
    def test_scrape_job_page_for_emails_exists(self):
        assert callable(scrape_job_page_for_emails)

    def test_extract_github_emails_exists(self):
        assert callable(extract_github_emails)

    def test_placeholder_domains_covered(self):
        # All the classic placeholder domains must be blocked
        for d in ["example.com", "acme.com", "test.com", "yourdomain.com", "domain.com"]:
            assert d in PLACEHOLDER_DOMAINS
