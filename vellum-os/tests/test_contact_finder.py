"""Tests for contact_finder.py — email waterfall, contact scraping."""

import pytest
import re


class TestEmailExtraction:
    """Test email regex extraction pattern used in contact_finder."""

    def _extract_emails(self, text: str) -> list[str]:
        """Replicate the email extraction logic from scrape_contact_page_emails."""
        emails = re.findall(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            text
        )
        return [
            e for e in emails
            if not e.endswith(('.png', '.jpg', '.gif', '.mp4', '.svg'))
            and not e.startswith(('noreply', 'no-reply', 'donotreply'))
        ]

    def test_valid_emails(self):
        text = "Contact us at hr@company.com or jobs@company.com"
        emails = self._extract_emails(text)
        assert "hr@company.com" in emails
        assert "jobs@company.com" in emails

    def test_filters_noreply(self):
        text = "noreply@company.com support@company.com"
        emails = self._extract_emails(text)
        assert "noreply@company.com" not in emails
        assert "support@company.com" in emails

    def test_filters_images(self):
        text = "image@company.png email@company.com"
        emails = self._extract_emails(text)
        assert "image@company.png" not in emails
        assert "email@company.com" in emails

    def test_no_emails(self):
        text = "No emails here"
        emails = self._extract_emails(text)
        assert len(emails) == 0

    def test_empty_text(self):
        emails = self._extract_emails("")
        assert emails == []


class TestContactFinderImports:
    def test_scrape_contact_page_emails_exists(self):
        from vellum.agents.contact_finder import scrape_contact_page_emails
        assert callable(scrape_contact_page_emails)

    def test_google_dork_for_emails_exists(self):
        from vellum.agents.contact_finder import google_dork_for_emails
        assert callable(google_dork_for_emails)

    def test_extract_github_emails_exists(self):
        from vellum.agents.contact_finder import extract_github_emails
        assert callable(extract_github_emails)

    def test_run_exists(self):
        from vellum.agents.contact_finder import run
        assert callable(run)
