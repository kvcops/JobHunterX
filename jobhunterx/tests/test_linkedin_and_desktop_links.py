"""LinkedIn-hosted postings are never shown; the desktop app opens outside links in the default browser."""

import asyncio

from fastapi.testclient import TestClient

from jobhunterx import storage
from jobhunterx.discovery import community, dedupe
from jobhunterx.domain.job import SourceRef
from jobhunterx.services import jobs as jobs_svc
from tests.test_intelligence import FIT, job, snap
from jobhunterx.intelligence.matching import assess


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _li(id_="li", url="https://www.linkedin.com/jobs/view/123"):
    return job(id=id_, apply_url=url, canonical_url=url, sources=[SourceRef(name="linkedin", kind="job_board", url=url)])


def test_linkedin_only_postings_are_dropped():
    kept, dropped = dedupe.drop_linkedin([_li(), _li("short", "https://lnkd.in/abc"), job(id="ok", apply_url="https://jobs.lever.co/acme/1")])
    assert [p.id for p in kept] == ["ok"] and dropped == 2


def test_merged_posting_opens_the_employer_page_instead():
    p = _li()
    p.sources.append(SourceRef(name="greenhouse", kind="ats_api", url="https://job-boards.greenhouse.io/acme/jobs/9", first_party=True))
    kept, dropped = dedupe.drop_linkedin([p])
    assert dropped == 0 and kept[0].apply_url == "https://job-boards.greenhouse.io/acme/jobs/9"
    assert not any("linkedin" in s.url for s in kept[0].sources)


def test_linkedin_search_results_are_never_read_and_founder_posts_skip_linkedin():
    from jobhunterx.discovery.search import Lead
    from jobhunterx.services.search import _lead_worth_reading
    lead = Lead(url="https://in.linkedin.com/jobs/view/ai-engineer-at-acme-1", title="AI Engineer - Acme", snippet="", provider="x", query="q")
    assert not _lead_worth_reading(lead, snap())
    assert not any("linkedin" in q for q in community.founder_queries(["AI Engineer"], ["Hyderabad"], fresher=True))


def test_saved_linkedin_jobs_leave_discovery_views_but_stay_in_saved():
    async def go():
        s = snap()
        await storage.save_job(_li(), assess(s, _li(), role_fit=FIT), None)
        ok = job(id="ok", apply_url="https://jobs.lever.co/acme/1")
        await storage.save_job(ok, assess(s, ok, role_fit=FIT), None)
        assert await storage.set_saved("li", True)
        listed, counts = await jobs_svc.list_jobs("all", None)
        saved, _ = await jobs_svc.list_jobs("saved", None)
        return [j["id"] for j in listed], counts, [j["id"] for j in saved]
    ids, counts, saved = _run(go())
    assert ids == ["ok"] and counts["all"] == 1
    assert saved == ["li"]                    # your own saved / applied jobs are never hidden


def test_desktop_open_only_in_desktop_mode_and_only_web_or_mail_links(monkeypatch):
    from jobhunterx.api import routes
    from jobhunterx.api.main import app
    from jobhunterx.config.settings import get_settings
    opened = []
    monkeypatch.setattr(routes, "_open_outside", opened.append)
    with TestClient(app, base_url="http://127.0.0.1:47821") as c:
        monkeypatch.setattr(get_settings(), "desktop", False)
        assert c.post("/api/desktop/open", json={"url": "https://example.com"}).status_code == 404
        monkeypatch.setattr(get_settings(), "desktop", True)
        assert c.post("/api/desktop/open", json={"url": "https://jobs.lever.co/acme/1"}).status_code == 200
        assert c.post("/api/desktop/open", json={"url": "mailto:hr@acme.com?subject=Hi"}).status_code == 200
        for bad in ("javascript:alert(1)", "file:///etc/passwd", "https://", "https://a.com/\nx", "C:\\\\Windows\\\\calc.exe"):
            assert c.post("/api/desktop/open", json={"url": bad}).status_code == 422, bad
        assert c.post("/api/desktop/open", json={"url": "https://x.com"}, headers={"origin": "https://evil.example"}).status_code == 403
    assert opened == ["https://jobs.lever.co/acme/1", "mailto:hr@acme.com?subject=Hi"]
