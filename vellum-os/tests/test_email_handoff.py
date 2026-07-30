"""Tests for email_handoff.py — email permutations, MX validation, SMTP verification."""

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
