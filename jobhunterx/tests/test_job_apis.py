"""Adzuna and Hacker News parsers + orchestration (fake network, no keys needed)."""

import asyncio
from types import SimpleNamespace

from jobhunterx.discovery import job_apis

LABELS = ["AI Engineer", "Machine Learning Engineer"]


def test_adzuna_credentials():
    assert job_apis.adzuna_credentials("abc123:def456") == ("abc123", "def456")
    assert job_apis.adzuna_credentials("nocolon") is None
    assert job_apis.adzuna_credentials(":x") is None
    assert job_apis.adzuna_credentials(None) is None


def test_parse_adzuna():
    data = {"results": [
        {"title": "<strong>AI</strong> Engineer", "company": {"display_name": "Acme AI"}, "redirect_url": "https://www.adzuna.in/land/ad/1",
         "location": {"display_name": "Hyderabad, Telangana"}, "created": "2026-10-27T09:00:00Z", "description": "Build LLM apps",
         "salary_min": 1200000, "salary_max": 1800000, "salary_is_predicted": "0", "contract_time": "full_time"},
        {"title": "ML Engineer", "company": {"display_name": "Beta"}, "redirect_url": "https://www.adzuna.in/land/ad/2",
         "location": {"display_name": "Pune"}, "created": "2026-10-20T09:00:00Z", "salary_min": 9, "salary_max": 99, "salary_is_predicted": "1"},
        {"title": "No company", "redirect_url": "https://x"},
    ]}
    a, b = job_apis.parse_adzuna(data)
    assert a.title == "AI Engineer" and a.company == "Acme AI" and a.location_raw.startswith("Hyderabad")
    assert a.salary.min == 1200000 and a.salary.currency == "INR" and a.employment_type == "full_time"
    assert a.posted_at.year == 2026 and a.sources[0].name == "adzuna"
    assert b.salary is None                         # predicted salaries are not shown as facts


def _hit(text, oid="1"):
    return {"objectID": oid, "comment_text": text, "created_at": "2026-10-25T10:00:00Z", "parent_id": 100}


def test_hn_comment_india_and_field():
    ok = _hit("Acme (YC S21) | AI Engineer | Bengaluru, India | ONSITE<p>We build LLM agents. Send CV to jobs@acme.ai")
    p = job_apis.parse_hn_comment(ok, LABELS, ["Bengaluru"], True)
    assert p and p.company == "Acme" and "AI Engineer" in p.title and "jobs@acme.ai" in p.description
    assert p.canonical_url.endswith("id=1")
    us = _hit("Foo | AI Engineer | San Francisco | ONSITE", "2")
    assert job_apis.parse_hn_comment(us, LABELS, ["Bengaluru"], True) is None            # not India
    off_field = _hit("Bar | Sales Manager | Bengaluru, India | ONSITE", "3")
    assert job_apis.parse_hn_comment(off_field, LABELS, ["Bengaluru"], True) is None     # not the candidate's field
    remote = _hit("Baz | ML Engineer | Remote (APAC) | REMOTE", "4")
    assert job_apis.parse_hn_comment(remote, LABELS, ["Bengaluru"], True)
    assert job_apis.parse_hn_comment(remote, LABELS, ["Bengaluru"], False) is None       # remote not wanted


def test_hn_job_story():
    item = {"type": "job", "id": 5, "title": "Quux (YC W22) Is Hiring Machine Learning Engineers in India", "time": 1792000000,
            "url": "https://quux.com/jobs"}
    p = job_apis.parse_hn_job(item, LABELS)
    assert p and p.company == "Quux" and p.apply_url == "https://quux.com/jobs"
    assert job_apis.parse_hn_job({**item, "title": "Quux is hiring a designer in London"}, LABELS) is None


def test_status_flags():
    s = SimpleNamespace(adzuna_api_key="a:b", enable_hn_source=False)
    assert job_apis.status(s) == {"adzuna": True, "hackernews": False}
    assert job_apis.status(SimpleNamespace(adzuna_api_key=None, enable_hn_source=False)) == {"adzuna": False, "hackernews": False}


def test_discover_merges_and_survives_failures(monkeypatch):
    s = SimpleNamespace(adzuna_api_key="a:b", enable_hn_source=True)
    adz = job_apis.parse_adzuna({"results": [
        {"title": "AI Engineer", "company": {"display_name": "Acme AI"}, "redirect_url": "https://www.adzuna.in/land/ad/1",
         "location": {"display_name": "Hyderabad"}, "created": "2026-10-27T09:00:00Z"},
        {"title": "ML Engineer", "company": {"display_name": "Infosys Staffing Recruitment"}, "redirect_url": "https://www.adzuna.in/land/ad/2",
         "location": {"display_name": "Hyderabad"}, "created": "2026-10-27T09:00:00Z"}]})

    async def fake_adzuna(*a, **k): return adz
    async def boom(*a, **k): raise RuntimeError("quota")
    async def first_party(p): return p
    monkeypatch.setattr(job_apis, "adzuna_search", fake_adzuna)
    monkeypatch.setattr(job_apis, "hackernews_search", boom)
    monkeypatch.setattr(job_apis, "_prefer_first_party", first_party)
    posts, st = asyncio.new_event_loop().run_until_complete(
        job_apis.discover(s, ["AI Engineer"], ["Hyderabad"], labels=LABELS, max_postings=10))
    assert [p.company for p in posts] == ["Acme AI"]            # recruiter dropped, failing source skipped
    assert st["agencies"] == 1 and st["adzuna"] >= 1 and st["hackernews"] == 0
