"""
End-to-end pipeline scenarios (fake network + fake LLM, real logic).

Candidate: ~1.5 years professional AI/ML experience in Hyderabad.
  A  AI Engineer, 0–2 yrs, Python/LLM/RAG, Hyderabad      → recommended
  B  Senior AI Engineer, 6+ yrs                          → incompatible (experience/seniority)
  C  Frontend Engineer, React/TypeScript                 → incompatible (career track)
  D  AI Engineer, 1–3 yrs, Berlin on-site                → incompatible (location)
  E  AI Engineer, mandatory Kubernetes (absent)          → incompatible (mandatory skill)
  +  duplicate of A on a job board (JSON-LD)             → merged into A
  +  dead link (404)                                     → dropped
  +  ML Engineer posted 200 days ago                     → flagged stale
"""

import asyncio

import pytest

from jobhunterx import storage
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.services import documents as docs_svc
from jobhunterx.services import profile as profile_svc
from jobhunterx.services.search import Run, execute, new_run
from tests.fixtures import scenario


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def world(monkeypatch):
    return scenario.install(monkeypatch)


async def _search():
    profile = CandidateProfile.model_validate(scenario.PROFILE)
    await profile_svc.save_profile(profile)
    events = []

    async def emit(e):
        events.append(e)

    r = Run(new_run(profile.content_hash()), emit)
    await execute(r, profile, {})
    rows = await storage.list_rows(order="fit_score DESC")
    jobs = {}
    for row in rows:
        p, m = storage.row_to_objects(row)
        jobs[p.ats.job_id if p.ats else p.canonical_url] = (p, m)
    return r, events, jobs, profile


def test_pipeline_distinguishes_jobs_for_the_right_reasons(world):
    r, events, jobs, _ = run(_search())
    assert r.data["status"] == "completed"
    a, b, c, d, e = (jobs[k] for k in ("101", "102", "103", "104", "105"))

    pa, ma = a
    assert ma.verdict in ("strong", "good"), (ma.score, ma.hard_constraints)
    assert not ma.rejected_reasons
    assert "Rust" not in pa.requirements.required_skills           # hallucinated JD skill dropped
    assert {"Python", "LLMs", "RAG"} <= set(ma.matched_required)

    assert b[1].verdict == "incompatible"
    assert {x.key for x in b[1].hard_constraints if x.status == "fail"} & {"experience", "seniority"}
    assert b[1].score <= 35                                        # keyword overlap cannot lift it

    assert c[1].verdict == "incompatible"
    assert any(x.key == "role" and x.status == "fail" for x in c[1].hard_constraints)

    assert d[1].verdict == "incompatible"
    assert any(x.key == "location" and x.status == "fail" for x in d[1].hard_constraints)

    assert e[1].verdict == "incompatible"
    assert any(x.key == "must_have" and x.status == "fail" and "Kubernetes" in x.detail for x in e[1].hard_constraints)

    # A and B share the same skills; only the explanation of B's seniority gap separates them.
    assert ma.score - b[1].score >= 30


def test_dedupe_dead_links_and_staleness(world):
    r, _, jobs, _ = run(_search())
    a, _ = jobs["101"]
    assert len(a.sources) == 2 and a.primary_source.first_party   # job-board copy merged into ATS posting
    assert r.data["counts"]["duplicates"] >= 1
    assert not any("dead.example" in k for k in jobs)              # 404 lead never becomes a job
    stale, m = jobs["106"]
    assert stale.validation.status == "stale"
    assert any(x.key == "active" and x.status == "warn" for x in m.hard_constraints)


def test_validation_is_honest(world):
    _, _, jobs, _ = run(_search())
    a, _ = jobs["101"]
    checks = a.validation.checks
    assert checks["ats_confirmed"].status == "verified"
    assert checks["salary"].status == "unknown"                    # never stated → unknown, not invented
    assert a.validation.status == "active"


def test_events_are_scoped_to_the_run(world):
    r, events, _, _ = run(_search())
    assert events and all(ev.get("run_id") == r.id for ev in events)
    assert any(ev["type"] == "search.job" for ev in events)


def test_untrusted_jd_text_is_fenced(world, monkeypatch):
    from jobhunterx.intelligence import llm_structured
    seen = []
    original = llm_structured.call_llm_with_fallback

    async def spy(chain, messages, **kw):
        seen.append(messages[-1]["content"])
        return await original(chain, messages, **kw)

    monkeypatch.setattr(llm_structured, "call_llm_with_fallback", spy)
    run(_search())
    jd_prompts = [u for u in seen if scenario.IGNORE_INSTRUCTIONS in u]
    assert jd_prompts
    for u in jd_prompts:
        i = u.index(scenario.IGNORE_INSTRUCTIONS)
        assert u.rfind("<untrusted_data>", 0, i) > u.rfind("</untrusted_data>", 0, i)


def test_snapshot_is_verified_against_profile(world):
    profile = CandidateProfile.model_validate(scenario.PROFILE)
    snap = run(profile_svc.get_snapshot(profile))
    names = {s.name for s in snap.skills}
    assert "Kotlin" not in names                                   # LLM-invented skill rejected
    assert snap.years_source == "dates"
    assert 1.3 <= snap.professional_years <= 1.7                   # internship excluded
    py = next(s for s in snap.skills if s.name == "Python")
    assert any(src.startswith("experience") for src in py.sources)


def test_resume_cv_and_cover_letter_are_distinct_and_evidence_based(world):
    async def go():
        r, _, jobs, profile = await _search()
        snap = await profile_svc.get_snapshot(profile)
        pa, _ = jobs["101"]

        async def emit(e):
            pass

        resume = await docs_svc.generate_for_job(pa.id, "resume", profile, snap, emit)
        cv = await docs_svc.generate_cv_doc(profile, snap, "", emit)
        letter = await docs_svc.generate_for_job(pa.id, "cover_letter", profile, snap, emit)
        return resume, cv, letter, profile, pa.id

    resume, cv, letter, profile, job_id = run(go())
    text = str(resume.content)
    assert "45%" not in text and "40%" not in text                 # fabricated metrics rejected
    assert "Kubernetes" not in text                                # unearned job keyword rejected
    assert "Terraform" not in text                                 # skill grouping limited to real skills
    assert any(not rw.accepted for rw in resume.provenance.rewrites)
    assert resume.job_id == job_id and letter.job_id == job_id
    assert resume.page_count == 1

    assert cv.kind == "cv" and cv.job_id is None
    cv_bullets = sum(len(e["bullets"]) for e in cv.content["experience"])
    resume_bullets = sum(len(e["bullets"]) for e in resume.content["experience"])
    assert cv_bullets == sum(len(e.bullets) for e in profile.experience) >= resume_bullets
    assert len(cv.content["projects"]) == len(profile.projects)
    assert cv.content["certifications"] == profile.certifications
    assert cv.content["summary"] != resume.content["summary"]

    paras = " ".join(letter.content["paragraphs"])
    assert "300%" not in paras and "Kubernetes" not in paras
    assert "RAG" in paras


def test_concurrent_generation_for_same_job_is_rejected(world):
    async def go():
        _, _, jobs, profile = await _search()
        snap = await profile_svc.get_snapshot(profile)
        pa, _ = jobs["101"]

        async def emit(e):
            pass

        results = await asyncio.gather(
            docs_svc.generate_for_job(pa.id, "resume", profile, snap, emit),
            docs_svc.generate_for_job(pa.id, "resume", profile, snap, emit),
            return_exceptions=True)
        return results

    results = run(go())
    assert sum(isinstance(x, docs_svc.AlreadyGenerating) for x in results) == 1
