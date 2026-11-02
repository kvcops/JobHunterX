"""Requirements judged against the whole profile (degree, jobs, projects), clear have / related / missing states,
sign-in-only job sites, and the resume's Skills section built from the candidate's own skills list."""

import asyncio

from jobhunterx.intelligence import account_wall, skill_links
from jobhunterx.intelligence.matching import assess, candidate_evidence
from tests.fixtures import scenario
from tests.test_api_v2 import _no_lifespan_db, _wait_snapshot, client  # noqa: F401  (fixtures)
from tests.test_intelligence import FIT, job, snap

DEGREE = "Bachelor's degree in Computer Science or a related technical field"
EVIDENCE = ["education: B.Tech, Computer Science & Engineering, Gayatri Vidya Parishad College of Engineering",
            "experience: Junior Data Scientist @ SciTech Patent Art", "project: ReferentWeave (Python, Rust, FastAPI)"]


def test_a_degree_requirement_is_met_by_the_candidates_education():
    req = {"required_skills": ["Python", DEGREE],
           "skill_links": {DEGREE: {"relation": "same", "via": EVIDENCE[0], "why": "B.Tech CSE"}}}
    m = assess(snap(), job(req=req), role_fit=FIT)
    assert DEGREE in m.matched_required and DEGREE not in m.missing_required


def test_related_experience_is_its_own_state_not_missing():
    req = {"required_skills": ["Python", "CrewAI"], "preferred_skills": ["Kubernetes"],
           "skill_links": {"CrewAI": {"relation": "related", "via": "experience: Junior Data Scientist @ SciTech Patent Art"}}}
    m = assess(snap(), job(req=req), role_fit=FIT)
    assert [r["skill"] for r in m.related_required] == ["CrewAI"] and "CrewAI" not in m.missing_required
    assert [r["skill"] for r in m.related_preferred] == ["Kubernetes"]          # Docker is listed as adjacent
    assert m.related_preferred[0]["via"] == "Docker"


def test_the_linker_sees_education_and_work_and_can_point_at_them(monkeypatch):
    seen = {}

    async def fake_call(**kw):
        seen["user"] = kw["user"]
        return skill_links._Links(links=[
            skill_links._Link(skill=DEGREE, relation="same", via="education: B.Tech, Computer Science & Engineering"),
            skill_links._Link(skill="Built and deployed a RAG pipeline", relation="same", via="project: ReferentWeave"),
            skill_links._Link(skill="C# and .NET", relation="none", via=""),
        ]), "fake"

    monkeypatch.setattr(skill_links, "call_structured", fake_call)
    class _Mem(dict):
        def set(self, k, v, expire=None):
            self[k] = v
    mem = _Mem()
    monkeypatch.setattr(skill_links, "_cache", lambda: mem)

    async def no_lookup(skill):
        return ""
    monkeypatch.setattr(skill_links, "_describe", no_lookup)
    j = job(req={"required_skills": [DEGREE, "C# and .NET"], "preferred_skills": ["Built and deployed a RAG pipeline"]})
    n = asyncio.new_event_loop().run_until_complete(
        skill_links.resolve(snap(), [j], "Built a production RAG system with FastAPI.", EVIDENCE))
    assert "EVIDENCE:" in seen["user"] and "B.Tech" in seen["user"] and "production RAG" in seen["user"]
    links = j.requirements.skill_links
    assert n == 2 and links[DEGREE]["via"] == EVIDENCE[0] and links["Built and deployed a RAG pipeline"]["via"] == EVIDENCE[2]
    assert "C# and .NET" not in links and j.requirements.links_version == skill_links.VERSION
    m = assess(snap(), j, role_fit=FIT)
    assert DEGREE in m.matched_required and "Built and deployed a RAG pipeline" in m.matched_preferred
    assert m.missing_required == ["C# and .NET"]


def test_candidate_evidence_lists_degrees_jobs_projects():
    ev = candidate_evidence({"education": [{"degree": "B.Tech, CSE", "institution": "GVP College"}],
                             "experience": [{"role": "AI Engineer", "company": "Acme"}],
                             "projects": [{"title": "Bot", "technologies": ["Python"]}], "certifications": ["GCP"]})
    assert ev == ["education: B.Tech, CSE, GVP College", "experience: AI Engineer @ Acme", "project: Bot (Python)",
                  "certification: GCP"]


def test_sign_in_sites_are_flagged_and_auto_apply_is_refused(client, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setattr(account_wall, "_FILE", tmp_path / "walls.json")
    client.put("/api/profile", json=scenario.PROFILE)
    _wait_snapshot(client)
    from jobhunterx import storage
    from jobhunterx.domain.job import JobPosting
    p = JobPosting(title="ML Engineer", company="Bigcorp", canonical_url="https://bigcorp.wd5.myworkdayjobs.com/x/job/1",
                   apply_url="https://bigcorp.wd5.myworkdayjobs.com/x/job/1/apply", description="ML job")
    jid = asyncio.new_event_loop().run_until_complete(storage.save_job(p, None, None))
    assert client.get(f"/api/jobs/{jid}").json()["job"]["needs_account"] is False
    account_wall.learn("https://bigcorp.wd5.myworkdayjobs.com/x/job/9")       # the agent met a login wall there once
    assert client.get(f"/api/jobs/{jid}").json()["job"]["needs_account"] is True
    r = client.post(f"/api/jobs/{jid}/apply")
    assert r.status_code == 409 and "sign in" in r.text
    assert not account_wall.learned("https://other.example.com/job")


def test_resume_skills_section_is_the_candidates_own_list():
    from jobhunterx.domain.candidate import CandidateProfile, SkillEvidence
    from jobhunterx.generation.skills import group_skills
    prof = CandidateProfile.model_validate({"name": "A", "skills": ["Python", "SQL", "C++"],
                                            "projects": [{"title": "RW", "technologies": ["Python", "Rust"]}]})
    s = snap(skills=[SkillEvidence(name=n, key=n.lower(), strength=0.8) for n in ("Python", "SQL", "C++", "Rust")])
    groups, _ = asyncio.new_event_loop().run_until_complete(group_skills(prof, s, use_llm=False))
    items = [i for g in groups for i in g.items]
    assert items == ["Python", "SQL", "C++"]                 # Rust only in one project's stack: not promoted
