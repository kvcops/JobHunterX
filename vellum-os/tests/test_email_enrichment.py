"""Tests for email_enrichment.py — keyless employee email finding:
LinkedIn people discovery, site crawl, Wayback recovery, LinkedIn guest
profile emails, obfuscation decoding and pattern learning.
All network calls are mocked.
"""

import asyncio

import pytest

from vellum.tools import email_enrichment as ee
from vellum.tools.email_handoff import generate_email_permutations_with_pattern


class FakeResponse:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


class FakeClient:
    _resp = FakeResponse({})

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kwargs):
        return self._resp

    async def post(self, url, **kwargs):
        return self._resp


class TestNameFromHandle:
    def test_simple_handle(self):
        assert ee._name_from_linkedin_handle("priya-sharma") == "Priya Sharma"

    def test_multi_word_handle(self):
        assert ee._name_from_linkedin_handle("arjun-reddy-kumar") == "Arjun Reddy Kumar"

    def test_stopword_only_handle(self):
        assert ee._name_from_linkedin_handle("hr") is None
        assert ee._name_from_linkedin_handle("company") is None
        assert ee._name_from_linkedin_handle("people") is None

    def test_handle_with_role_suffix(self):
        # trailing job-role words in the handle are dropped
        assert ee._name_from_linkedin_handle("priya-sharma-hr") == "Priya Sharma"

    def test_entity_style_handle_rejected(self):
        assert ee._name_from_linkedin_handle("acme-renewables-solutions") is None
        assert ee._name_from_linkedin_handle("global-software-solutions") is None

    def test_trailing_id_junk_stripped(self):
        assert ee._name_from_linkedin_handle("ranjan-sir-data-gyan-51611a123") == "Ranjan Sir Data Gyan"

    def test_empty(self):
        assert ee._name_from_linkedin_handle("") is None


class TestCompanyAffinity:
    def test_contiguous_company_name(self):
        blob = "Shankar Narasimhan - CEO - Gyan Data | LinkedIn"
        assert ee._company_affinity("Gyan Data", blob)

    def test_name_coincidence_rejected(self):
        blob = "Isaac Gyan | Data Analytics professional skilled in Microsoft"
        assert not ee._company_affinity("Gyan Data", blob)

    def test_reversed_tokens_rejected(self):
        blob = "Ranjan Sir Data Gyan | LinkedIn"
        assert not ee._company_affinity("Gyan Data", blob)

    def test_single_word_company_token_match(self):
        assert ee._company_affinity("Tata", "Engineer at Tata Motors | LinkedIn")
        assert not ee._company_affinity("Tata", "Infosys careers page")

    def test_company_with_suffix_words(self):
        blob = "Arjun Ravichandran - Gyan Data Technologies | LinkedIn"
        assert ee._company_affinity("Gyan Data Pvt Ltd", blob)


class TestLinkedinPeopleDiscovery:
    def _fake_search(self, monkeypatch):
        from vellum.tools import search as search_mod

        results = [
            {
                "title": "Priya Sharma - Talent Acquisition - Acme | LinkedIn",
                "href": "https://www.linkedin.com/in/priya-sharma/",
                "body": "Talent Acquisition at Acme",
            },
            {
                "title": "Arjun Reddy - Software Engineer - Acme | LinkedIn",
                "href": "https://www.linkedin.com/in/arjun-reddy/",
                "body": "Software Engineer at Acme",
            },
            {
                "title": "Acme | LinkedIn",
                "href": "https://www.linkedin.com/company/acme/",
                "body": "Acme company page",
            },
        ]

        async def fake(q, max_results=10):
            return results

        monkeypatch.setattr(search_mod, "search_multi_engine", fake)

    def test_extracts_real_names(self, monkeypatch):
        self._fake_search(monkeypatch)
        people = asyncio.run(ee.linkedin_company_people("Acme", "Engineer", max_names=6))
        names = {p["name"] for p in people}
        assert names == {"Priya Sharma", "Arjun Reddy"}
        assert all(p["linkedin_url"] for p in people)
        assert all(p["pattern"] == "linkedin_people" for p in people)

    def test_company_page_not_treated_as_person(self, monkeypatch):
        self._fake_search(monkeypatch)
        people = asyncio.run(ee.linkedin_company_people("Acme"))
        assert not any("company" in p["name"].lower() for p in people)

    def test_no_results(self, monkeypatch):
        from vellum.tools import search as search_mod

        async def fake(q, max_results=10):
            return []

        monkeypatch.setattr(search_mod, "search_multi_engine", fake)
        assert asyncio.run(ee.linkedin_company_people("Acme")) == []

    def test_empty_company(self):
        assert asyncio.run(ee.linkedin_company_people("")) == []


class TestLinkedinCompanyUrl:
    def test_finds_company_page(self, monkeypatch):
        from vellum.tools import search as search_mod

        async def fake(q, max_results=10):
            return [
                {"title": "Acme | LinkedIn", "href": "https://www.linkedin.com/company/acme/"},
            ]

        monkeypatch.setattr(search_mod, "search_multi_engine", fake)
        assert asyncio.run(ee.linkedin_company_url("Acme")) == "https://www.linkedin.com/company/acme/"

    def test_no_result(self, monkeypatch):
        from vellum.tools import search as search_mod

        async def fake(q, max_results=10):
            return []

        monkeypatch.setattr(search_mod, "search_multi_engine", fake)
        assert asyncio.run(ee.linkedin_company_url("Acme")) == ""


class TestPatternPermutations:
    def test_pattern_informed_generation(self):
        perms = generate_email_permutations_with_pattern(
            "Priya", "Sharma", "acme.com", "{first}.{last}@acme.com"
        )
        assert len(perms) == 1
        assert perms[0]["address"] == "priya.sharma@acme.com"
        assert perms[0]["unverified_guess"] is True
        assert perms[0]["pattern_informed"] is True

    def test_f_initial_pattern(self):
        perms = generate_email_permutations_with_pattern(
            "Priya", "Sharma", "acme.com", "{f}{last}@acme.com"
        )
        assert perms[0]["address"] == "psharma@acme.com"

    def test_bad_pattern_returns_empty(self):
        assert generate_email_permutations_with_pattern("Priya", "Sharma", "acme.com", "") == []
        assert generate_email_permutations_with_pattern("Priya", "Sharma", "acme.com", "no-tokens") == []


class TestObfuscationDecode:
    def test_parenthesized_at_dot(self):
        assert ee._decode_obfuscated_emails("reach priya (at) acme (dot) com") == ["priya@acme.com"]

    def test_bracket_style(self):
        assert ee._decode_obfuscated_emails("mail: priya[at]acme[dot]com") == ["priya@acme.com"]

    def test_plain_text_untouched(self):
        assert ee._decode_obfuscated_emails("priya@acme.com") == []


class TestExtractEmailsFromHtml:
    def test_mailto_links(self):
        html = '<a href="mailto:jobs@acme.io">Apply</a>'
        found = ee._extract_emails_from_html(html, "https://acme.com/contact", "site_crawl")
        assert any(e["address"] == "jobs@acme.io" for e in found)

    def test_json_ld_email(self):
        html = '{"email": "privacy@acme.io"}'
        found = ee._extract_emails_from_html(html, "https://acme.com/privacy", "site_crawl")
        assert any(e["address"] == "privacy@acme.io" for e in found)

    def test_filters_noreply(self):
        html = "noreply@acme.com press@acme.io"
        found = ee._extract_emails_from_html(html, "https://acme.com/contact", "site_crawl")
        assert not any(e["address"] == "noreply@acme.com" for e in found)
        assert any(e["address"] == "press@acme.io" for e in found)

    def test_filters_image_assets(self):
        html = "logo@acme.png support@acme.io"
        found = ee._extract_emails_from_html(html, "https://acme.com/contact", "site_crawl")
        assert not any(e["address"] == "logo@acme.png" for e in found)
        assert any(e["address"] == "support@acme.io" for e in found)

    def test_filters_placeholders(self):
        html = "yourname@acme.io hello@acme.io"
        found = ee._extract_emails_from_html(html, "https://acme.com/contact", "site_crawl")
        assert not any(e["address"] == "yourname@acme.io" for e in found)
        assert any(e["address"] == "hello@acme.io" for e in found)


class TestScrapeCompanyEmailPages:
    def test_fetches_pattern_pages_and_dedupes(self, monkeypatch):
        from vellum.tools import scrape

        async def fake_fetch(url):
            host = url.split("//")[1].split("/")[0]
            return {
                "html": f'<a href="mailto:careers@{host}">apply</a>'
                        f' <script>leak@fake.js</script>',
                "status": 200,
            }

        monkeypatch.setattr(scrape, "fetch_page", fake_fetch)
        found = asyncio.run(ee.scrape_company_email_pages("acme.io", max_pages=3))
        assert len(found) >= 1
        assert all("acme.io" in e["address"] for e in found)
        assert all(e["pattern"] == "site_crawl" for e in found)

    def test_empty_domain(self):
        assert asyncio.run(ee.scrape_company_email_pages("")) == []


class TestRecoverEmailsViaWayback:
    def test_cdx_snapshot_flow(self, monkeypatch):
        class TextResponse(FakeResponse):
            status_code = 200
            text = '<a href="mailto:old-press@acme.io">old</a>'

            def json(self):
                return [
                    ["timestamp", "original", "statuscode"],
                    ["20240101", "acme.com/contact", "200"],
                ]

        class SeqClient(FakeClient):
            async def get(self, url, **kwargs):
                return TextResponse({})

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", SeqClient)
        found = asyncio.run(ee.recover_emails_via_wayback("acme.com"))
        assert any(e["address"] == "old-press@acme.io" for e in found)
        assert any(e["pattern"] == "wayback" for e in found)

    def test_empty_domain(self):
        assert asyncio.run(ee.recover_emails_via_wayback("")) == []


class TestLinkedinGuestEmails:
    def test_company_page_email_and_website(self, monkeypatch):
        class PageResponse:
            status_code = 200
            text = (
                '{"website": "https://acme.io/"}'
                '<a href="mailto:hello@acme.io">email us</a>'
            )

        class PageClient(FakeClient):
            async def get(self, url, **kwargs):
                return PageResponse()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", PageClient)
        found = asyncio.run(ee.linkedin_guest_emails("Acme", "https://www.linkedin.com/company/acme/"))
        assert any(e["address"] == "hello@acme.io" for e in found)
        assert any(e.get("website_url") for e in found)

    def test_empty_company(self):
        assert asyncio.run(ee.linkedin_guest_emails("")) == []


class TestScrapeTeamLinkedinProfiles:
    def test_extracts_employee_profiles(self, monkeypatch):
        from vellum.tools import scrape

        async def fake_fetch(url):
            html = """
            <div class="member">
              <img alt="Shankar Narasimhan" src="photo1.jpg">
              <a href="https://www.linkedin.com/in/shankar-narasimhan-9293934">in</a>
            </div>
            <div class="member">
              <img alt="Raghunathan Rengasamy" src="photo2.jpg">
              <a href="https://www.linkedin.com/in/raghunathan-rengasamy-627a407b">in</a>
            </div>
            <img alt="linkedin icon" src="li.png"><a href="https://www.linkedin.com/in/hiring-manager">in</a>
            """
            return {"html": html, "status": 200}

        monkeypatch.setattr(scrape, "fetch_page", fake_fetch)
        people = asyncio.run(ee.scrape_team_linkedin_profiles("gyandata.com"))
        names = {p["name"] for p in people}
        assert "Shankar Narasimhan" in names
        assert "Raghunathan Rengasamy" in names
        assert all(p["pattern"] == "team_page" for p in people)
        assert all(p["linkedin_url"].startswith("https://www.linkedin.com/in/") for p in people)

    def test_no_team_page(self, monkeypatch):
        from vellum.tools import scrape

        async def fake_fetch(url):
            return {"html": "<p>no team here</p>", "status": 200}

        monkeypatch.setattr(scrape, "fetch_page", fake_fetch)
        assert asyncio.run(ee.scrape_team_linkedin_profiles("acme.io")) == []

    def test_empty_domain(self):
        assert asyncio.run(ee.scrape_team_linkedin_profiles("")) == []


class TestLinkedinProfileEmails:
    def test_fetches_employee_profiles(self, monkeypatch):
        class ProfileResponse:
            status_code = 200
            text = '<a href="mailto:priya.sharma@acme.io">email me</a>'

        class ProfileClient(FakeClient):
            async def get(self, url, **kwargs):
                return ProfileResponse()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", ProfileClient)
        people = [
            {"name": "Priya Sharma", "linkedin_url": "https://www.linkedin.com/in/priya-sharma/"},
            {"name": "Arjun Reddy", "linkedin_url": "https://www.linkedin.com/in/arjun-reddy/"},
        ]
        found = asyncio.run(ee.linkedin_profile_emails(people))
        assert any(e["address"] == "priya.sharma@acme.io" for e in found)
        assert any(e["pattern"] == "linkedin_profile" for e in found)
        assert any(e.get("name") == "Priya Sharma" for e in found)

    def test_no_people(self):
        assert asyncio.run(ee.linkedin_profile_emails([])) == []

    def test_skips_non_profile_urls(self, monkeypatch):
        import httpx

        calls = []

        class TrackingClient(FakeClient):
            async def get(self, url, **kwargs):
                calls.append(url)
                return FakeResponse({})

        monkeypatch.setattr(httpx, "AsyncClient", TrackingClient)
        people = [
            {"name": "Priya Sharma", "linkedin_url": "https://www.linkedin.com/company/acme/"},
            {"name": "No Url", "linkedin_url": ""},
        ]
        assert asyncio.run(ee.linkedin_profile_emails(people)) == []
        assert calls == []


class TestInferEmailPattern:
    def test_first_last(self):
        emails = [{"address": "priya.sharma@acme.com", "confidence": 0.8}]
        assert ee.infer_email_pattern(emails, "acme.com") == "{first}.{last}@acme.com"

    def test_f_last(self):
        emails = [{"address": "psharma@acme.com", "confidence": 0.8}]
        assert ee.infer_email_pattern(emails, "acme.com") == "{f}{last}@acme.com"

    def test_generic_only_no_pattern(self):
        emails = [{"address": "careers@acme.com", "confidence": 0.9}]
        assert ee.infer_email_pattern(emails, "acme.com") is None

    def test_connect_role_inbox_no_pattern(self):
        emails = [{"address": "connect@acme.io", "confidence": 0.9}]
        assert ee.infer_email_pattern(emails, "acme.io") is None

    def test_wrong_domain_ignored(self):
        emails = [{"address": "priya.sharma@other.com", "confidence": 0.8}]
        assert ee.infer_email_pattern(emails, "acme.com") is None

    def test_empty(self):
        assert ee.infer_email_pattern([], "acme.com") is None
        assert ee.infer_email_pattern([{"address": "x@acme.com"}], "") is None
