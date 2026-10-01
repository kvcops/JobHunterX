"""Unit tests: matching policy edges, evidence checks, dedupe, ATS URL parsing, verification of LLM output."""

from datetime import datetime, timedelta, timezone

from jobhunterx.discovery.ats import parse_ats_url
from jobhunterx.discovery.dedupe import canonical_url, deduplicate
from jobhunterx.domain.candidate import CandidateSnapshot, PlaceRef, RoleFamilyFit, SkillEvidence
from jobhunterx.domain.common import Seniority, WorkMode
from jobhunterx.domain.job import JobPosting, Requirements, SourceRef
from jobhunterx.generation.evidence import check_free_text, check_rewrite
from jobhunterx.intelligence.job import JobUnderstanding, _Skill, apply_understanding
from jobhunterx.intelligence.matching import assess
from jobhunterx.intelligence.text import merged_years, parse_month, term_in_text


def snap(**kw):
    base = dict(
        profile_hash="h", professional_years=1.5, years_source="dates", seniority=Seniority.JUNIOR,
        role_families=[RoleFamilyFit(label="GenAI", closeness=1.0)],
        skills=[SkillEvidence(name="Python", key="python", strength=1.0, sources=["experience: x"]),
                SkillEvidence(name="Docker", key="docker", strength=1.0, adjacent=["Kubernetes"], sources=["experience: x"])],
        education_level="bachelor", locations=[PlaceRef(city="Hyderabad", country="India", aliases=["Secunderabad"])],
        home_country="India", work_modes=[WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ONSITE],
    )
    base.update(kw)
    return CandidateSnapshot(**base)


def job(**kw):
    req = kw.pop("req", {})
    base = dict(id="j", title="AI Engineer", company="Acme", location_raw="Hyderabad, India", locations=["Hyderabad"],
                countries=["India"], seniority=Seniority.JUNIOR, description="Build LLM apps with Python.",
                requirements=Requirements(**{"method": "llm", "required_skills": ["Python"], **req}))
    base.update(kw)
    j = JobPosting(**base)
    j.validation.status = kw.get("status", "active")
    return j


FIT = (0.95, "GenAI", "same work", "llm")


def keys(m, status):
    return {c.key for c in m.hard_constraints if c.status == status}


def test_small_experience_gap_is_a_stretch_not_a_rejection():
    m = assess(snap(), job(req={"experience_min": 3}), role_fit=FIT)
    assert "experience" in keys(m, "warn") and m.verdict != "incompatible"


def test_large_experience_gap_is_incompatible_even_with_perfect_skills():
    m = assess(snap(), job(req={"experience_min": 8}, seniority=Seniority.SENIOR), role_fit=FIT)
    assert m.verdict == "incompatible" and m.score <= 35


def test_mandatory_skill_with_only_related_experience_warns():
    m = assess(snap(), job(req={"required_skills": ["Python", "Kubernetes"], "must_have_skills": ["Kubernetes"]}), role_fit=FIT)
    assert "must_have" in keys(m, "warn") and m.verdict != "incompatible"


def test_remote_restricted_to_other_country_fails():
    m = assess(snap(), job(work_mode=WorkMode.REMOTE, remote_countries=["United States"], locations=[], countries=[]), role_fit=FIT)
    assert "location" in keys(m, "fail")


def test_alias_city_matches_location():
    m = assess(snap(), job(location_raw="Secunderabad, Telangana", locations=[], countries=[]), role_fit=FIT)
    assert "location" in keys(m, "pass")


def test_unknowns_are_reported_not_guessed():
    m = assess(snap(), job(location_raw="", locations=[], countries=[], status="unverified"), role_fit=FIT)
    assert {"location", "experience", "active"} <= keys(m, "unknown")
    assert m.unknowns


def test_fallback_analysis_is_flagged():
    j = job()
    j.requirements.method = "fallback"
    m = assess(snap(), j, role_fit=(0.6, "GenAI", "", "fallback"))
    assert m.method == "fallback" and any("partial" in u for u in m.unknowns)


def test_llm_understanding_is_verified_against_text():
    j = JobPosting(id="x", title="AI Engineer", description="We need 2+ years of experience with Python. Salary not disclosed.")
    u = JobUnderstanding(required_skills=[_Skill(name="Python"), _Skill(name="Golang")], experience_min_years=5,
                         experience_evidence="5+ years of experience", salary=None)
    apply_understanding(j, u, "m")
    assert j.requirements.required_skills == ["Python"]      # Golang not in text
    assert j.requirements.experience_min is None             # fabricated evidence rejected


def test_fact_checker():
    profile = "Built a RAG assistant over 20k documents using LangChain and Python"
    assert check_rewrite("Built a Python RAG assistant with LangChain over 20k documents", profile, profile).ok
    assert not check_rewrite("Built a RAG assistant serving 1M users", profile, profile).ok
    assert not check_rewrite("Built a RAG assistant on Kubernetes", profile, profile + " Kubernetes",
                             forbidden_new_terms=["Kubernetes"]).ok
    assert not check_free_text("Expert in Snowflake and Databricks.", profile).ok


def test_term_matching_respects_boundaries():
    assert term_in_text("Java", "Java and Spring") and not term_in_text("Java", "JavaScript developer")
    assert term_in_text("C++", "Strong C++ skills") and not term_in_text("Go", "a good engineer")


def test_years_from_dates_merge_overlaps():
    a = (parse_month("Jan 2023"), parse_month("Dec 2023"))
    b = (parse_month("Jun 2023"), parse_month("Jun 2024"))
    assert 1.4 <= merged_years([a, b]) <= 1.6


def test_canonical_url_and_dedupe():
    assert canonical_url("https://www.Acme.com/jobs/12/?utm_source=x&gh_jid=99#top") == "https://acme.com/jobs/12?gh_jid=99"
    ats_job = JobPosting(id="1", title="AI Engineer", company="Acme", location_raw="Hyderabad", description="x " * 300,
                         canonical_url="https://job-boards.greenhouse.io/acme/jobs/1",
                         sources=[SourceRef(name="greenhouse", kind="ats_api", url="u1", first_party=True, confidence=.95)])
    board = JobPosting(id="2", title="AI  engineer", company="ACME", location_raw="Hyderabad", description="different text",
                       canonical_url="https://board.example/1",
                       sources=[SourceRef(name="board", kind="job_board", url="u2", confidence=.6)])
    unique, dups = deduplicate([board, ats_job])
    assert dups == 1 and unique[0].id == "1" and len(unique[0].sources) == 2


def test_ats_url_parsing():
    assert parse_ats_url("https://job-boards.greenhouse.io/acme/jobs/123").job_id == "123"
    assert parse_ats_url("https://jobs.lever.co/acme/0b1e2c3d-1111-2222-3333-444455556666/apply").kind == "lever"
    assert parse_ats_url("https://jobs.ashbyhq.com/acme").job_id == ""
    assert parse_ats_url("https://example.com/careers") is None


def test_stale_posting_detection():
    from jobhunterx.discovery.validate import finalize
    j = job(posted_at=datetime.now(timezone.utc) - timedelta(days=400), status="unverified")
    finalize(j, ("live", "HTTP 200"))
    assert j.validation.status == "stale"
    j2 = job(valid_through=datetime.now(timezone.utc) - timedelta(days=1), status="unverified")
    finalize(j2, ("live", "HTTP 200"))
    assert j2.validation.status == "closed"
