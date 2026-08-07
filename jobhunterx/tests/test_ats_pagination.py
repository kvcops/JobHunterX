"""
Tests for ATS pagination — Greenhouse loops pages until a short page,
SmartRecruiters loops until offset >= totalFound. Both previously returned
only the first page, silently dropping jobs.

Internet is not touched: the async fetchers are wrapped with a fake
_fetch_json that returns canned page payloads.
"""

import asyncio

import pytest

from jobhunterx.tools import ats_client


def _run(coro):
    return asyncio.run(coro)


class FakeFetcher:
    """Stands in for ats_client._fetch_json, one canned response per page."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def __call__(self, url, timeout=15.0):
        self.calls.append(url)
        page = self.pages.pop(0)
        return page


def test_greenhouse_paginates_all_pages(monkeypatch):
    # Page 1 is FULL (100) → must request page 2; page 2 is short → stop.
    full = {"jobs": [{"title": f"Role {i}", "content": "<p>x</p>",
                      "location": {"name": "Bengaluru"}, "absolute_url": f"/job/{i}",
                      "updated_at": ""} for i in range(100)]}
    short = {"jobs": [{"title": "Role 100", "content": "<p>x</p>",
                       "location": {"name": "Remote"}, "absolute_url": "/job/100",
                       "updated_at": ""}]}
    pages = [full, short]
    fake = FakeFetcher(pages)
    monkeypatch.setattr(ats_client, "_fetch_json", fake)

    jobs = _run(ats_client._greenhouse("acme", "Acme", "https://acme.com/careers", max_pages=5))
    assert len(jobs) == 101
    assert jobs[100].role == "Role 100"
    assert len(fake.calls) == 2  # stopped after the short page


def test_greenhouse_respects_max_pages(monkeypatch):
    # Three full pages but max_pages=2 → stops at 2 pages.
    full = {"jobs": [{"title": f"Role {i}", "content": "x",
                      "location": {"name": ""}, "absolute_url": "", "updated_at": ""}
                     for i in range(100)]}
    pages = [full, full, full]
    fake = FakeFetcher(pages)
    monkeypatch.setattr(ats_client, "_fetch_json", fake)
    jobs = _run(ats_client._greenhouse("acme", "Acme", "", max_pages=2))
    assert len(jobs) == 200
    assert len(fake.calls) == 2


def test_smartrecruiters_uses_totalfound(monkeypatch):
    # totalFound=250, but only 2 pages of 100 are actually present → we stop
    # when offset >= totalFound. First page has 100 items, second 100.
    mk = lambda n: {"content": [
        {"name": f"SR Role {i}", "releasedDate": "", "ref": "",
         "location": {"city": "", "country": "India"}} for i in range(n)],
        "totalFound": 250}
    pages = [mk(100), mk(100), mk(50)]  # third page 50 < 100 → also stops
    fake = FakeFetcher(pages)
    monkeypatch.setattr(ats_client, "_fetch_json", fake)
    jobs = _run(ats_client._smartrecruiters("acme", "Acme", ""))
    assert len(jobs) == 250
    # 3 callbacks: page 3 gives 50 items, offset=250 == totalFound → break
    assert len(fake.calls) == 3


def test_smartrecruiters_stops_on_empty_page(monkeypatch):
    pages = [{"content": [{"name": "A", "ref": ""} for _ in range(100)], "totalFound": 300},
             {"content": [], "totalFound": 300}]
    fake = FakeFetcher(pages)
    monkeypatch.setattr(ats_client, "_fetch_json", fake)
    jobs = _run(ats_client._smartrecruiters("acme", "Acme", ""))
    assert len(jobs) == 100


def test_ashby_single_page(monkeypatch):
    data = {"jobs": [{"title": "Ashby Role", "descriptionHtml": "<p>d</p>",
                      "location": "Bengaluru", "applyUrl": "/a", "publishedAt": "",
                      "department": "Eng"}]}
    fake = FakeFetcher([data])
    monkeypatch.setattr(ats_client, "_fetch_json", fake)
    jobs = _run(ats_client._ashby("acme", "Acme", ""))
    assert len(jobs) == 1
    assert jobs[0].role == "Ashby Role"
    assert jobs[0].location == "Bengaluru"


def test_fetch_jobs_no_ats_returns_empty():
    comp = ats_client.Company(name="Acme", ats="none", ats_token="")
    assert _run(ats_client.fetch_jobs(comp)) == []


def test_detect_ats_from_html_prefers_ashby_over_greenhouse_noise():
    html = ("<script>window.board = 'api.ashbyhq.com/posting-api/job-board/acme'</script>"
            "<a href='boards.greenhouse.io/acme'>legacy</a>")
    ats, token = ats_client.detect_ats_from_html(html)
    assert ats == "ashby"
    assert token == "acme"


def test_probe_company_parallel_candidates(monkeypatch):
    """Candidate URLs are fetched in parallel, so a dead careers page does
    not delay the website-root probe. Verify a board found on the second
    candidate when the first hangs."""
    from jobhunterx.tools import ats_client as ac

    async def slow_fetch(url, timeout=8.0):
        if url.endswith("/careers"):
            await asyncio.sleep(2.0)  # dead, slow
            return ""
        return '<html><body>api.lever.co/v0/postings/acme</body></html>'

    monkeypatch.setattr(ac, "fetch_page", slow_fetch)
    comp = ac.Company(name="Acme", website="https://acme.com", careers_url="https://acme.com/careers")
    result = _run(ac.probe_company(comp))
    assert result.ats == "lever"
    assert result.ats_token == "acme"


def test_probe_company_no_ats_marks_none(monkeypatch):
    from jobhunterx.tools import ats_client as ac

    async def empty_fetch(url, timeout=8.0):
        return "<html>no ATS here</html>"

    monkeypatch.setattr(ac, "fetch_page", empty_fetch)
    comp = ac.Company(name="Empty", website="https://empty.com")
    result = _run(ac.probe_company(comp))
    assert result.ats == "none"


def test_probe_company_no_urls_is_none():
    from jobhunterx.tools import ats_client as ac

    comp = ac.Company(name="NoUrls")
    result = _run(ac.probe_company(comp))
    assert result.ats == "none"