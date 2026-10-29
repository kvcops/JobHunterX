"""Community / startup sources (YC Work at a Startup, r/developersIndia, founder posts), funding news, and the
website-age scam signal."""

import asyncio
import html
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from jobhunterx.discovery import community, funding, job_apis
from jobhunterx.domain.job import FieldCheck, SourceRef
from jobhunterx.intelligence import domain_age, scam
from jobhunterx.intelligence.reach import assess_reach
from tests.test_intelligence import job, snap

LABELS = ["AI Engineer", "Machine Learning Engineer", "Software Engineer"]
NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeCache(dict):
    def set(self, k, v):
        self[k] = v


def _page(props: dict) -> str:
    return f'<div id="app" data-page="{html.escape(json.dumps({"component": "X", "props": props}))}"></div>'


def _yc(**kw):
    base = {"title": "AI Engineer", "url": "/companies/acme/jobs/abc-ai-engineer", "location": "Bangalore", "type": "Full-time",
            "role": "eng", "roleSpecificType": "Machine learning", "minExperience": "Any (new grads ok)", "companyName": "Acme",
            "companyBatchName": "S24", "companyOneLiner": "AI for clinics", "createdAt": "7 days", "salaryRange": "₹10L - ₹20L"}
    return {**base, **kw}


# ---------------------------------------------------------------- YC Work at a Startup
def test_yc_listing_keeps_india_and_open_remote_roles_with_min_experience():
    props = community._data_page(_page({"jobPostings": [
        _yc(),
        _yc(title="Senior AI Engineer", url="/companies/b/jobs/x", location="Remote (US)", companyName="B"),
        _yc(title="ML Engineer", url="/companies/c/jobs/y", location="Remote", companyName="C", minExperience="3+ years"),
        _yc(title="Account Executive", url="/companies/d/jobs/z", role="sales", companyName="D"),
    ]}))
    jobs = community.parse_yc_listing(props, LABELS, include_remote=True, now=NOW)
    assert [j.company for j in jobs] == ["Acme", "C"]                 # US-only remote and sales dropped
    a = jobs[0]
    assert a.canonical_url == "https://www.ycombinator.com/companies/acme/jobs/abc-ai-engineer"
    assert "Minimum experience: Any (new grads ok)" in a.description
    assert a.validation.checks["experience"].value == "Any (new grads ok)"
    assert a.posted_at == NOW - timedelta(days=7)
    assert community.yc_years("Any (new grads ok)") == 0 and community.yc_years("3+ years") == 3
    assert not community.parse_yc_listing(props, LABELS, include_remote=False, now=NOW)[1:]   # remote off → only Bangalore


def test_yc_detail_adds_founder_and_description():
    p = community.parse_yc_listing({"jobPostings": [_yc()]}, LABELS, True, NOW)[0]
    community.enrich_yc(p, {"job": {"description": "Build RAG pipelines.", "hiringManager": {"first_name": "Asha", "last_name": "R"}},
                            "company": {"website": "https://acme.ai", "team_size": 8}})
    assert "Hiring manager: Asha R" in p.description and "Build RAG pipelines." in p.description
    assert "Company website: https://acme.ai" in p.description


def test_relative_age():
    assert community.relative_age("about 2 months", NOW) == NOW - timedelta(days=60)
    assert community.relative_age("a day", NOW) == NOW - timedelta(days=1)
    assert community.relative_age("", NOW) is None


# ---------------------------------------------------------------- Reddit
FIXTURE = "tests/fixtures/reddit_megathread.xml"      # real r/developersIndia "Who's hiring?" thread (Oct 2026), trimmed


def _megathread_jobs(labels=LABELS + ["Python Developer"], **kw):
    rows = community.parse_reddit_rss(open(FIXTURE, encoding="utf-8").read())
    return rows, [p for p in (community.parse_megathread_comment(c, labels, now=NOW, **kw) for c in rows) if p]


def test_megathread_template_posts_become_postings():
    rows, jobs = _megathread_jobs()
    assert len(rows) == 8
    by = {p.company: p for p in jobs}
    e = by["EmployLabs"]
    assert e.title == "Founding Engineer" and e.location_raw == "Remote (India)"
    assert e.apply_url.startswith("https://itszia.ai/roles/founding-engineer")
    assert e.validation.checks["experience"].value == "2+ years"
    assert by["TSIT"].location_raw == "Bengaluru"                      # all fields on one line still parse
    assert "Link:" not in by and "" not in by                          # the thread's own blank template is not a job
    assert all(p.sources[0].kind == "community" for p in jobs)


def test_megathread_skips_questions_bots_and_other_countries():
    rows, jobs = _megathread_jobs()
    assert not any("freshers roles for python" in p.description.lower() or "AutoModerator" in p.company for p in jobs)
    us = {"body": "<p>Company Name: Zeta</p><p>Location: Remote (US)</p><p>Role/Position: AI Engineer</p>", "permalink": "/r/x/comments/a/b/c/"}
    assert community.parse_megathread_comment(us, LABELS, now=NOW) is None
    md = {"body": "**Company Name:** Medly\n**Location:** Hyderabad\n**Role/Position:** AI Engineer Intern\n**Experience Required:** Freshers",
          "permalink": "/r/developersIndia/comments/a/b/c1/", "created_utc": (NOW - timedelta(days=2)).timestamp()}
    p = community.parse_megathread_comment(md, LABELS, now=NOW)      # JSON bodies are markdown
    assert p and p.company == "Medly" and p.employment_type == "internship"
    assert community._short("Remote (India) Overview We are an early-stage US startup", 80) == "Remote (India)"


# ---------------------------------------------------------------- founder posts
def test_founder_posts_come_only_from_search_results():
    qs = community.founder_queries(["AI Engineer"], ["Hyderabad"], fresher=True)
    assert any(q.startswith("site:x.com") for q in qs) and all("Hyderabad" in q for q in qs)
    assert any(q.startswith("site:linkedin.com/posts") and q.endswith("fresher") for q in qs)
    p = community.parse_founder_lead("https://x.com/asha_builds/status/123", "Asha on X: \"We're hiring an AI Engineer in Hyderabad\"",
                                     "We're hiring an AI Engineer (0-1 yrs) at Medly. DM me your GitHub.", LABELS)
    assert p and p.company.startswith("Medly") and p.apply_url == "https://x.com/asha_builds/status/123"
    li = community.parse_founder_lead("https://www.linkedin.com/posts/ravi-kumar_hiring-ai-activity-1", "Ravi Kumar on LinkedIn",
                                      "I'm hiring a machine learning engineer for my team in Bengaluru", LABELS)
    assert li and "LinkedIn hiring post" in li.company
    assert community.parse_founder_lead("https://x.com/a/status/1", "AI Engineer tips", "10 tips to learn AI", LABELS) is None
    assert community.parse_founder_lead("https://example.com/blog", "We're hiring an AI Engineer", "", LABELS) is None


def test_post_ids_carry_their_date():
    d = community.post_date("https://www.linkedin.com/posts/x_were-hiring-activity-7373363717444464641-MZd-")
    assert d and d.date().isoformat() == "2025-09-15"
    recent_ms = int((datetime.now(timezone.utc) - timedelta(days=3)).timestamp() * 1000)
    x_id = (recent_ms - community._X_EPOCH_MS) << 22
    assert (datetime.now(timezone.utc) - community.post_date(f"https://x.com/a/status/{x_id}")).days == 3
    old = "https://www.linkedin.com/posts/x_were-hiring-activity-7373363717444464641-MZd-"      # a year old: skipped
    assert community.parse_founder_lead(old, "We're hiring an AI Engineer", "We're hiring an AI Engineer in Pune", LABELS) is None
    fresh = community.parse_founder_lead(f"https://x.com/a/status/{x_id}", "We're hiring", "We're hiring an AI Engineer in Pune", LABELS)
    assert fresh and fresh.posted_at and "Pune" in fresh.location_raw


def test_founder_posts_are_never_opened():
    from jobhunterx.discovery import validate
    p = job(sources=[SourceRef(name="founder_post", kind="community", url="https://www.linkedin.com/posts/x_1")],
            apply_url="https://www.linkedin.com/posts/x_1")
    state, why = _run(validate.check_liveness(p))
    assert state == "unknown" and "does not open" in why


def test_discover_runs_the_new_sources_and_survives_a_blocked_one(monkeypatch):
    s = SimpleNamespace(adzuna_api_key=None, enable_hn_source=False, enable_yc_source=True, enable_reddit_source=True,
                        enable_founder_posts=True)
    yc = community.parse_yc_listing({"jobPostings": [_yc()]}, LABELS, True, NOW)
    founder = [community.parse_founder_lead("https://x.com/a/status/9", "We're hiring", "We're hiring an AI Engineer at Medly", LABELS)]

    async def yc_search(*a, **k): return yc
    async def blocked(*a, **k): raise RuntimeError("403 from Reddit")       # noqa: E704
    async def founders(*a, **k): return founder
    monkeypatch.setattr(community, "yc_search", yc_search)
    monkeypatch.setattr(community, "reddit_search", blocked)
    monkeypatch.setattr(community, "founder_posts", founders)
    posts, st = _run(job_apis.discover(s, ["AI Engineer"], ["Bengaluru"], labels=LABELS, max_postings=10))
    assert {p.company for p in posts} == {"Acme", "Medly (X hiring post)"}
    assert st["yc"] == 1 and st["reddit"] == 0 and st["founders"] == 1


# ---------------------------------------------------------------- funding news
def test_funding_headlines():
    assert funding.parse_headline("Maasi Raises ₹6 Crore in Pre-Seed Funding Led by Better Capital - Indian Startup Times") == ("Maasi", "₹6 Crore")
    assert funding.parse_headline("Physical AI vision company Nova Spectral AI raises Rs 21.15 Cr led by Shastra VC")[0] == "Nova Spectral AI"
    assert funding.parse_headline("India’s InspeCity Raises $10.5M in Pre-Series A round")[0] == "InspeCity"
    assert funding.parse_headline("Bijnis rebrands as Zorit, raises Rs 27 Cr led by Sparrow Capital")[0] == "Zorit"
    for skip in ("Sarvam AI in talks to raise up to $300 million", "Accel raises $550 million for ninth India fund",
                 "From Boldfit To Origin — Indian Startups Raised About $236 Mn This Week - Inc42",
                 "Google-backed Indian space startup raises $100 million", "Thyrocare Q2 Profit Slips 68% YoY To ₹15 Cr"):
        assert funding.parse_headline(skip) is None, skip
    assert funding.company_key("Nova Spectral AI") == funding.company_key("Nova Spectral Technologies Pvt Ltd")


def test_funding_feed_merge_and_reach_signal(monkeypatch):
    monkeypatch.setattr(funding, "_store", FakeCache())
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    xml = (f"<rss><channel><item><title>Medly raises $3 Mn to build AI clinic software</title><link>https://inc42.com/x</link>"
           f"<pubDate>{today}</pubDate></item><item><title>Old Co raises $1 Mn</title><link>https://inc42.com/y</link>"
           f"<pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate></item></channel></rss>")
    events = funding._merge([], funding.parse_feed(xml, "inc42.com"))
    assert [e["company"] for e in events] == ["Medly"]                 # older than six months dropped
    funding._store.set(funding.KEY, events)
    assert funding.lookup("Medly Technologies")["amount"] == "$3 Mn"
    r = assess_reach(job(company="Medly"), snap())
    assert any(s.key == "funded" and s.points > 0 for s in r.signals)
    assert not any(s.key == "funded" for s in assess_reach(job(company="Acme"), snap()).signals)


# ---------------------------------------------------------------- website age
def test_registrable_domain_and_skipped_platforms():
    assert domain_age.registrable("careers.acme.co.in") == "acme.co.in"
    assert domain_age.registrable("www.jobs.acme.com") == "acme.com"
    p = job(apply_url="https://apply.fastjobs-hiring.com/form", description="Send your CV to hr@fastjobs-hiring.com to apply.")
    assert domain_age.domains_of(p) == ["fastjobs-hiring.com"]
    assert domain_age.domains_of(job(apply_url="https://jobs.lever.co/acme/1", description="Apply via careers@gmail.com")) == []
    assert domain_age.domains_of(job(apply_url="https://inbox.com/x")) == ["inbox.com"]          # 'x.com' is not a substring match


def test_domain_age_lookup_is_cached_and_recorded(monkeypatch):
    from jobhunterx.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "enable_domain_age_check", True)
    monkeypatch.setattr(domain_age, "_store", FakeCache())
    calls = []

    async def fake_json(url, **k):
        calls.append(url)
        return {"events": [{"eventAction": "registration", "eventDate": (datetime.now(timezone.utc) - timedelta(days=12, hours=6)).isoformat()}]}
    monkeypatch.setattr(job_apis, "fetch_json", fake_json)
    p = job(apply_url="https://apply.fastjobs-hiring.com/form")
    assert _run(domain_age.annotate(p)) == 12
    assert p.validation.checks["domain_age"].value == "12"
    _run(domain_age.annotate(job(apply_url="https://fastjobs-hiring.com/b")))
    assert len(calls) == 1                                              # cached


def test_new_domain_scam_levels():
    def with_age(days, text="Build LLM apps with Python."):
        p = job(description=text)
        p.validation.checks["domain_age"] = FieldCheck(status="verified", value=str(days), evidence="x.in was registered on …")
        return scam.check(p)
    assert with_age(900).level == "none"
    assert with_age(120).level == "medium"
    assert with_age(10).level == "high"
    combo = with_age(10, "Pay a refundable deposit of Rs 2000 and message us on WhatsApp")
    assert combo.level == "critical" and any(f.rule == "new_domain" and f.severity == "critical" for f in combo.flags)
