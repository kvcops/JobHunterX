"""Early-career changes: experience bands, safety-net track, immediate-joiner boost, scam rules, employer
reachability, referral pack and outcome tracking (docs/research/freshers-getting-shortlisted.md)."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from jobhunterx.domain.common import Seniority
from jobhunterx.domain.job import SourceRef
from jobhunterx.intelligence import scam
from jobhunterx.intelligence.matching import assess, experience_band, years_label
from tests.test_intelligence import FIT, job, keys, snap

FRESHER = dict(professional_years=0.0, total_years=0.5, internship_years=0.5, seniority=Seniority.ENTRY, notice_period_days=0)


def fresher(**kw):
    return snap(**{**FRESHER, **kw})


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- experience bands
def test_bands_follow_the_gap_not_the_number():
    assert experience_band(0, 2, 0.5)[0] == "reachable"
    assert experience_band(1, 3, 0.0)[0] == "direct"
    assert experience_band(2, None, 0.0)[0] == "stretch"
    assert experience_band(3, None, 0.0)[0] == "out_of_range"
    assert experience_band(3, None, 1.5)[0] == "stretch"          # 1.5 years on "3+"
    assert years_label(1.33, True) == "1 yr 4 mo (incl. internships)"


def test_fresher_sees_1_to_3_year_roles_instead_of_a_rejection():
    m = assess(fresher(total_years=0.0, internship_years=0.0), job(req={"experience_min": 1, "experience_max": 3}), role_fit=FIT)
    assert m.verdict != "incompatible" and m.experience.band == "direct"
    exp = next(c for c in m.hard_constraints if c.key == "experience")
    assert exp.status == "warn" and not exp.hard and "referral" in exp.detail
    # 6 months of internships count the way recruiters' systems count them: then "1-3 years" is within reach
    with_intern = assess(fresher(), job(req={"experience_min": 1, "experience_max": 3}), role_fit=FIT)
    assert with_intern.experience.band == "reachable" and "incl. internships" in with_intern.experience.candidate_label


def test_fresher_stretch_and_out_of_range():
    two = assess(fresher(), job(req={"experience_min": 2}), role_fit=FIT)
    assert two.verdict != "incompatible" and two.experience.band == "stretch"
    five = assess(fresher(), job(req={"experience_min": 5}, seniority=Seniority.SENIOR), role_fit=FIT)
    assert five.verdict == "incompatible" and five.experience.band == "out_of_range"


def test_mid_label_on_a_reachable_posting_is_not_a_second_rejection():
    m = assess(fresher(), job(req={"experience_min": 1, "experience_max": 3}, seniority=Seniority.MID), role_fit=FIT)
    assert m.verdict != "incompatible" and "seniority" not in keys(m, "fail")


def test_experienced_candidates_keep_the_old_rules():
    m = assess(snap(professional_years=6, seniority=Seniority.SENIOR), job(req={"experience_min": 10}, seniority=Seniority.PRINCIPAL), role_fit=FIT)
    assert m.verdict == "incompatible" and m.experience.band == ""


# ---------------------------------------------------------------- safety-net track
def test_it_services_employer_is_a_safety_net_for_freshers(monkeypatch):
    m = assess(fresher(), job(company="Infosys"), role_fit=FIT)
    assert m.track == "floor" and m.verdict != "incompatible"
    assert m.reach.score > 25                                      # not capped like a bulk pipeline for experienced people
    senior = assess(snap(professional_years=6, seniority=Seniority.SENIOR), job(company="Infosys", seniority=Seniority.SENIOR), role_fit=FIT)
    assert senior.track == "main" and "company" in keys(senior, "fail")
    from jobhunterx.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "fresher_floor_track", False)
    assert "company" in keys(assess(fresher(), job(company="Infosys"), role_fit=FIT), "fail")


# ---------------------------------------------------------------- immediate joiners
def test_immediate_joiner_posts_rank_up_for_someone_with_no_notice():
    post = job(description="Build LLM apps with Python. Immediate joiners preferred.")
    up = assess(fresher(), post, role_fit=FIT).reach
    assert any(s.key == "notice" and s.points > 0 for s in up.signals)
    long = assess(snap(notice_period_days=60), post, role_fit=FIT).reach
    assert any(s.key == "notice" and s.points < 0 for s in long.signals)


def test_no_boost_when_the_post_has_scam_signals():
    post = job(description="Immediate joiners. Contact us on WhatsApp wa.me/919999999999 for the offer.")
    r = assess(fresher(), post, role_fit=FIT).reach
    assert not any(s.key == "notice" and s.points > 0 for s in r.signals)
    assert any(s.key == "scam" for s in r.signals)


# ---------------------------------------------------------------- scam rules
@pytest.mark.parametrize("text, level", [
    ("Pay a registration fee of Rs 2000 to confirm your seat.", "critical"),
    ("Earn by completing tasks: Rs 150 per review, daily payout.", "critical"),
    ("Send your Aadhaar and bank details before the interview. Install AnyDesk.", "critical"),
    ("Selected candidates will be contacted. Apply via WhatsApp only.", "high"),
    ("Direct joining, no interview required!", "high"),
    ("Copy paste work from home job, flexible hours.", "medium"),
])
def test_scam_rules(text, level):
    assert scam.check(job(description=text)).level == level


def test_a_normal_posting_has_no_scam_flags():
    text = ("We are hiring an AI Engineer in Hyderabad. 1-3 years. Python, LangChain. Send your resume to careers@acme.com. "
            "Our interview process: a 30-minute call, a take-home task and a final round. Competitive pay and benefits.")
    assert scam.check(job(description=text)).level == "none"


def test_critical_scam_is_never_recommended():
    m = assess(fresher(), job(description="Training fee of Rs 5000 is refundable after joining."), role_fit=FIT)
    assert m.verdict == "incompatible" and "scam" in keys(m, "fail")


# ---------------------------------------------------------------- employer reachability from the employer-board index
def test_reachability_comes_from_the_employers_own_recent_postings(monkeypatch):
    from jobhunterx.discovery import ats_index
    now = datetime.now(timezone.utc).isoformat()
    rows = [ats_index.Row(url=f"u{i}", company="Zeta Labs", title="Associate Engineer", location="Bengaluru", level="entry",
                          first_seen=now, ats="greenhouse") for i in range(4)]
    rows += [ats_index.Row(url=f"s{i}", company="Omega Corp", title="Engineer", location="Bengaluru", level="senior",
                           first_seen=now, ats="lever") for i in range(12)]
    monkeypatch.setattr(ats_index, "_rows", rows)
    monkeypatch.setattr(ats_index, "_entry_cache", (0, {}))
    assert ats_index.fresher_reachability("Zeta Labs") == (4, 4)
    up = assess(fresher(), job(company="Zeta Labs"), role_fit=FIT).reach
    assert any(s.key == "early_career" and s.points > 0 for s in up.signals)
    down = assess(fresher(), job(company="Omega Corp"), role_fit=FIT).reach
    assert any(s.key == "early_career" and s.points < 0 for s in down.signals)


# ---------------------------------------------------------------- referral pack
def test_referral_pack_uses_only_profile_facts():
    from jobhunterx.domain.candidate import CandidateProfile
    from jobhunterx.intelligence import connect
    from tests.fixtures import scenario
    profile = CandidateProfile.model_validate(scenario.PROFILE)
    j = job(apply_url="https://job-boards.greenhouse.io/acme/jobs/101")
    m = assess(fresher(), j, role_fit=FIT)
    k = _run(connect.build(j, m, profile, fresher(), use_llm=False))
    pack = k.referral
    assert pack.job_url.endswith("/101") and pack.blurb.count("\n") <= 2
    assert profile.name.split()[0] in pack.blurb and "Can join immediately" in pack.blurb
    if pack.proof_link:
        assert pack.proof_link in pack.blurb


# ---------------------------------------------------------------- outcomes
def test_outcome_summary_and_stop_loss():
    from jobhunterx.services import outcomes
    recs = [{"channel": "linkedin", "band": "direct", "track": "main", "human_path": False, "age_days_at_apply": 9,
             "events": []} for _ in range(40)]
    recs += [{"channel": "referral", "band": "direct", "track": "main", "human_path": True, "age_days_at_apply": 1,
              "events": [{"kind": "reply", "at": "x"}, {"kind": "interview", "at": "y"}]}]
    s = outcomes.summarize(recs)
    assert s["by_channel"]["referral"]["interviews_per_10"] == 10.0 and s["by_channel"]["linkedin"]["replies"] == 0
    assert s["interviews_from_unlocked_jobs"] == 1
    assert s["diagnosis"] and any("72 hours" in d for d in s["diagnosis"])


@pytest.fixture
def client(monkeypatch):
    from jobhunterx.api import main
    from jobhunterx.config import database as db
    path = db._db_path
    monkeypatch.setattr(main, "set_db_path", lambda p: db.set_db_path(path))
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


def test_outcome_api_and_safety_net_view(client):
    from jobhunterx import storage
    j = job(id="j1", sources=[SourceRef(name="greenhouse", kind="ats_api", url="https://x", first_party=True)],
            posted_at=datetime.now(timezone.utc) - timedelta(days=1))
    _run(storage.save_job(j, assess(fresher(), j, role_fit=FIT), None))
    f = job(id="j2", company="Wipro", title="Graduate Engineer Trainee")
    _run(storage.save_job(f, assess(fresher(), f, role_fit=FIT), None))
    counts = client.get("/api/jobs", params={"view": "recommended"}).json()["counts"]
    assert counts["safety_net"] == 1
    ids = [x["id"] for x in client.get("/api/jobs", params={"view": "recommended"}).json()["jobs"]]
    assert "j2" not in ids and "j1" in ids
    assert client.patch("/api/jobs/j1", json={"tracking_status": "applied", "channel": "nope"}).status_code == 422
    r = client.patch("/api/jobs/j1", json={"tracking_status": "applied", "human_path": True})
    assert r.status_code == 200 and r.json()["job"]["outcome"]["channel"] == "own_site"
    assert r.json()["job"]["outcome"]["age_days_at_apply"] is not None
    client.patch("/api/jobs/j1", json={"tracking_status": "applied", "event": "reply"})
    client.patch("/api/jobs/j1", json={"tracking_status": "interviewing"})
    out = client.get("/api/outcomes").json()
    assert out["overall"]["applied"] == 1 and out["overall"]["interviews"] == 1 and out["with_person"]["replies"] == 1


def test_jobs_scored_by_the_old_matcher_are_brought_up_to_date():
    from jobhunterx import storage
    from jobhunterx.services import jobs as jobs_svc
    s = fresher(total_years=0.0, internship_years=0.0)
    j = job(id="old1", req={"experience_min": 1, "experience_max": 3})
    old = assess(s, j, role_fit=FIT).model_copy(update={"engine_version": "match-v2", "verdict": "incompatible", "score": 20})
    _run(storage.save_job(j, old, None))
    assert _run(jobs_svc.reassess_outdated(s, {})) == 1
    _, m = storage.row_to_objects(_run(storage.get_row("old1")))
    assert m.verdict != "incompatible" and m.experience.band == "direct"
    assert _run(jobs_svc.reassess_outdated(s, {})) == 0            # already current: nothing to do
