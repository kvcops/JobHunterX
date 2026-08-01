"""Tests for email_handoff.py — email permutations, MX validation, SMTP verification."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestGenerateEmailPermutations:
    def test_basic_permutations(self):
        from vellum.tools.email_handoff import generate_email_permutations
        result = generate_email_permutations("John", "Doe", "company.com")
        assert isinstance(result, list)
        assert len(result) > 0
        addresses = [e["address"] for e in result]
        assert "john.doe@company.com" in addresses
        assert "john@company.com" in addresses
        assert "johndoe@company.com" in addresses

    def test_single_name(self):
        from vellum.tools.email_handoff import generate_email_permutations
        result = generate_email_permutations("John", "", "company.com")
        addresses = [e["address"] for e in result]
        assert any("john" in a for a in addresses)

    def test_empty_name(self):
        from vellum.tools.email_handoff import generate_email_permutations
        result = generate_email_permutations("", "", "company.com")
        assert isinstance(result, list)


class TestEmailHandoffImports:
    def test_generate_email_permutations_exists(self):
        from vellum.tools.email_handoff import generate_email_permutations
        assert callable(generate_email_permutations)

    def test_check_mx_record_exists(self):
        from vellum.tools.email_handoff import check_mx_record
        assert callable(check_mx_record)

    def test_enrich_with_mx_exists(self):
        from vellum.tools.email_handoff import enrich_with_mx
        assert callable(enrich_with_mx)

    def test_verify_email_smtp_exists(self):
        from vellum.tools.email_handoff import verify_email_smtp
        assert callable(verify_email_smtp)

    def test_detect_catch_all_exists(self):
        from vellum.tools.email_handoff import detect_catch_all
        assert callable(detect_catch_all)

    def test_verify_emails_with_smtp_exists(self):
        from vellum.tools.email_handoff import verify_emails_with_smtp
        assert callable(verify_emails_with_smtp)

    def test_create_mailto_uri_exists(self):
        from vellum.tools.email_handoff import create_mailto_uri
        assert callable(create_mailto_uri)

    def test_create_gmail_compose_url_exists(self):
        from vellum.tools.email_handoff import create_gmail_compose_url
        assert callable(create_gmail_compose_url)

    def test_open_mail_client_exists(self):
        from vellum.tools.email_handoff import open_mail_client
        assert callable(open_mail_client)


class TestCreateMailtoUri:
    def test_basic(self):
        from vellum.tools.email_handoff import create_mailto_uri
        uri = create_mailto_uri("hr@company.com", "Application", "Hello")
        assert uri.startswith("mailto:")
        # Email is URL-encoded in mailto URI
        assert "hr%40company.com" in uri or "hr@company.com" in uri

    def test_no_subject(self):
        from vellum.tools.email_handoff import create_mailto_uri
        uri = create_mailto_uri("hr@company.com")
        assert uri.startswith("mailto:")


class TestCreateGmailComposeUrl:
    def test_basic(self):
        from vellum.tools.email_handoff import create_gmail_compose_url
        url = create_gmail_compose_url("hr@company.com", "Application", "Hello")
        assert "mail.google.com" in url
        assert "hr%40company.com" in url or "hr@company.com" in url


class TestProviderRisk:
    def test_gmail(self):
        from vellum.tools.email_handoff import _provider_risk
        assert _provider_risk("alt1.aspmx.l.google.com") == "gmail"

    def test_m365(self):
        from vellum.tools.email_handoff import _provider_risk
        assert _provider_risk("acme-com.mail.protection.outlook.com") == "m365"

    def test_zoho(self):
        from vellum.tools.email_handoff import _provider_risk
        assert _provider_risk("mx.zoho.in") == "zoho"

    def test_unknown(self):
        from vellum.tools.email_handoff import _provider_risk
        assert _provider_risk("mail.acme.com") == "unknown"

    def test_empties(self):
        from vellum.tools.email_handoff import _provider_risk
        assert _provider_risk(None) == "unknown"
        assert _provider_risk("") == "unknown"


class TestVerifyEmailsWithSmtp:
    def _run(self, monkeypatch, mx_host, rcpt_codes):
        """Monkeypatch MX resolution + RCPT responses, run verifier."""
        import asyncio
        from vellum.tools import email_handoff

        code_iter = iter(rcpt_codes)

        def fake_mx(domain):
            return mx_host

        def fake_rcpt(mx_host, rcpt, timeout):
            return next(code_iter)

        monkeypatch.setattr(email_handoff, "_get_mx_host", fake_mx)
        monkeypatch.setattr(email_handoff, "_smtp_rcpt_check", fake_rcpt)
        return email_handoff

    def test_zoho_honest_550_marks_invalid(self, monkeypatch):
        mod = self._run(monkeypatch, "mx.zoho.in", [550, 550])
        emails = asyncio.run(mod.verify_emails_with_smtp(
            [{"address": "priya@acme.com", "confidence": 0.6, "pattern": "site_crawl"}]
        ))
        assert emails[0]["smtp_valid"] is False
        assert emails[0]["provider_risky"] is False
        assert emails[0]["smtp_provider"] == "zoho"

    def test_zoho_250_boosts_confidence(self, monkeypatch):
        mod = self._run(monkeypatch, "mx.zoho.in", [550, 250])
        emails = asyncio.run(mod.verify_emails_with_smtp(
            [{"address": "priya@acme.com", "confidence": 0.6, "pattern": "site_crawl"}]
        ))
        assert emails[0]["smtp_valid"] is True
        assert emails[0]["confidence"] == pytest.approx(0.9)

    def test_gmail_250_unreliable(self, monkeypatch):
        mod = self._run(monkeypatch, "alt1.aspmx.l.google.com", [550, 250])
        emails = asyncio.run(mod.verify_emails_with_smtp(
            [{"address": "priya@acme.com", "confidence": 0.6, "pattern": "site_crawl"}]
        ))
        assert emails[0]["smtp_valid"] is None
        assert emails[0]["provider_risky"] is True
        assert emails[0]["smtp_provider"] == "gmail"

    def test_gmail_550_marks_invalid(self, monkeypatch):
        mod = self._run(monkeypatch, "alt1.aspmx.l.google.com", [550, 550])
        emails = asyncio.run(mod.verify_emails_with_smtp(
            [{"address": "priya@acme.com", "confidence": 0.6, "pattern": "site_crawl"}]
        ))
        assert emails[0]["smtp_valid"] is False
        assert emails[0]["provider_risky"] is True

    def test_catch_all_detected(self, monkeypatch):
        mod = self._run(monkeypatch, "mail.acme.com", [250, 250])
        emails = asyncio.run(mod.verify_emails_with_smtp(
            [{"address": "priya@acme.com", "confidence": 0.6, "pattern": "site_crawl"}]
        ))
        assert emails[0]["catch_all"] is True
        assert emails[0]["smtp_valid"] is None
        assert emails[0]["confidence"] == pytest.approx(0.4)

    def test_empty_list(self, monkeypatch):
        mod = self._run(monkeypatch, "mail.acme.com", [])
        assert asyncio.run(mod.verify_emails_with_smtp([])) == []
