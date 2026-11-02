"""Skills grounded in the resume text, a CV that never times out or loses content, several documents for one job,
long work that outlives the request, and applying to any job link."""

import copy

from jobhunterx.agents.extractor import _ground, written_in
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.generation import render
from tests.fixtures import scenario
from tests.test_api_v2 import _no_lifespan_db, _wait_snapshot, client  # noqa: F401  (fixtures)
from tests.test_custom_resume import JD, _huge

RESUME_TEXT = """Asha Rao — AI Engineer
Skills: Python, HTML, CSS, JS, C++
ReferentWeave | Python, FastAPI, Gemini
RAG framework. Recall@1 63%; R@5 100%; RRF rerank with chunk citations. We trust our users. Built with NodeJS and Go.
"""


def test_only_skills_written_in_the_resume_survive_the_read():
    for name, ok in [("Python", True), ("C++", True), ("JS", True), ("Node.js", True), ("Go", True), ("RRF", True),
                     ("R", False), ("Rust", False), ("C", False), ("TypeScript", False)]:
        assert written_in(name, RESUME_TEXT) is ok, name
    p = CandidateProfile.model_validate({"name": "Asha", "skills": ["Python", "C++", "Rust", "R", "JS"],
                                         "projects": [{"title": "ReferentWeave", "technologies": ["Python", "Rust", "FastAPI"]}]})
    dropped = _ground(p, RESUME_TEXT)
    assert p.skills == ["Python", "C++", "JS"] and p.projects[0].technologies == ["Python", "FastAPI"]
    assert set(dropped) == {"Rust", "R"}


def test_a_long_cv_keeps_everything_and_renders_quickly(monkeypatch):
    calls = []
    real = render._html_to_pdf

    def counting(html):
        calls.append(1)
        return real(html)

    monkeypatch.setattr(render, "_html_to_pdf", counting)
    big = _huge()
    pdf, pages = render.render_cv(big)
    assert pdf.startswith(b"%PDF") and pages >= 2           # a CV may run on; nothing is cut to force one page
    assert len(calls) <= 1 + len(render.SHRINK_PROFILES)     # was every resume trimming step (16 renders)
    html = render._render("cv.html", doc=big, s={"id": "classic", **render.styles.STYLES["classic"]}, **render._CV_LAYOUT)
    assert html.count('class="proj-desc"') == len(big["projects"])   # every project, each set apart


def test_projects_have_room_between_them():
    c = copy.deepcopy(_huge())
    html = render._render("resume.html", doc=c, s={"id": "classic", **render.styles.STYLES["classic"]}, **render.SHRINK_PROFILES[0])
    assert ".proj-desc" in html and "margin-bottom: 6px" in html and 'class="proj-desc"' in html


def test_one_job_gives_resume_cv_and_cover_letter_together(client):  # noqa: F811
    client.put("/api/profile", json=scenario.PROFILE)
    _wait_snapshot(client)
    r = client.post("/api/documents/custom", json={"jd_text": JD + " (bundle)", "company": "Zeta Labs",
                                                    "kinds": ["cover_letter", "resume", "cv"]})
    assert r.status_code == 200, r.text
    body = r.json()
    kinds = [d["kind"] for d in body["documents"]]
    assert kinds == ["resume", "cv", "cover_letter"] and body["document"]["kind"] == "resume"
    assert all(d["job_id"] is None for d in body["documents"])
    assert "Zeta Labs" in body["documents"][2]["title"]
    only = client.post("/api/documents/custom", json={"jd_text": JD + " (letter only)", "kinds": ["cover_letter"]})
    assert only.status_code == 200 and [d["kind"] for d in only.json()["documents"]] == ["cover_letter"]
    assert client.post("/api/documents/custom", json={"jd_text": JD, "kinds": []}).status_code == 422
    assert client.post("/api/documents/custom", json={"jd_text": JD, "kinds": ["poem"]}).status_code == 422


def test_slow_writing_answers_later_instead_of_timing_out(client, monkeypatch):  # noqa: F811
    from jobhunterx.api import routes
    from jobhunterx.intelligence import llm_structured
    client.put("/api/profile", json=scenario.PROFILE)
    _wait_snapshot(client)
    fast = llm_structured.call_llm_with_fallback

    async def slow(chain, messages, **kw):
        import asyncio
        await asyncio.sleep(0.6)
        return await fast(chain, messages, **kw)

    monkeypatch.setattr(llm_structured, "call_llm_with_fallback", slow)
    monkeypatch.setattr(routes, "WAIT_S", 0.1)
    r = client.post("/api/documents/cv", json={"focus": "AI Engineer (slow)"})
    assert r.status_code == 202 and r.json()["pending"]
    done = client.get(f"/api/tasks/{r.json()['pending']}", params={"wait": 25})
    assert done.status_code == 200, done.text
    assert done.json()["document"]["kind"] == "cv"
    assert client.get("/api/tasks/nope").status_code == 404


def test_any_job_link_becomes_a_job_to_apply_to(client, monkeypatch):  # noqa: F811
    import asyncio
    from jobhunterx.services import apply as apply_svc
    from jobhunterx.services import documents as docs_svc
    client.put("/api/profile", json=scenario.PROFILE)
    _wait_snapshot(client)

    async def unreadable(*a, **k):
        raise docs_svc.BadTarget("Couldn't read a job description from that page.")

    started = {}

    async def fake_start(job_id, emit, continuing=False):
        started["id"] = job_id
        return {"job_id": job_id, "status": "preparing"}

    monkeypatch.setattr(docs_svc, "job_from_input", unreadable)
    monkeypatch.setattr(apply_svc, "start", fake_start)
    r = client.post("/api/apply/link", json={"url": "https://jobs.zetalabs.ai/ai-engineer", "title": "AI Engineer"})
    assert r.status_code == 200, r.text
    jid = r.json()["job_id"]
    assert started["id"] == jid
    job = client.get(f"/api/jobs/{jid}").json()
    flat = str(job)
    assert "AI Engineer" in flat and "Zetalabs" in flat and "https://jobs.zetalabs.ai/ai-engineer" in flat
    again = client.post("/api/apply/link", json={"url": "https://jobs.zetalabs.ai/ai-engineer"})
    assert again.json()["job_id"] == jid                       # the same link is the same job
    assert client.post("/api/apply/link", json={"url": "https://www.linkedin.com/jobs/view/1"}).status_code == 409
    assert client.post("/api/apply/link", json={"url": "ftp://x.example/job"}).status_code == 409
    del asyncio


def test_cloud_browser_proxy_country_comes_from_the_person():
    from jobhunterx.agents.browser_agent import _country_code
    assert _country_code("India") == "in" and _country_code("United Kingdom") == "gb"
    assert _country_code("in") == "in" and _country_code("") is None and _country_code("Atlantis") is None
