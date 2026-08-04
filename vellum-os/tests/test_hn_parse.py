"""
Tests for the HN "Who's Hiring" comment parser — the free-form header
format is the #1 source of junk roles, so lock the good behaviours down.
"""

from vellum.tools.hn_hiring import _parse_comment, _is_type_or_loc, _find_latest_thread


def parse(comment):
    return _parse_comment(comment)


# --- Core: role/location extraction ---------------------------------------


def test_company_role_location():
    jobs = parse("Acme | Backend Engineer | Bengaluru, India")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "Backend Engineer"
    assert jobs[0]["location"] == "Bengaluru, India"
    assert jobs[0]["company"] == "Acme"


def test_role_only():
    jobs = parse("Acme | Frontend Engineer")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "Frontend Engineer"


def test_type_token_before_role():
    # "Company | Full-Time | Remote | Role"
    jobs = parse("Acme | Full-Time | Remote | SWE")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "SWE"
    assert jobs[0]["location"] == "Full-Time Remote"


def test_location_token_before_role():
    jobs = parse("Acme | Remote | Backend Engineer | $120k | equity")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "Backend Engineer"
    assert jobs[0]["location"] == "Remote"
    assert jobs[0]["note"] == "$120k | equity"


def test_onsite_token_before_role():
    jobs = parse("Acme | On-site | Lathe Operator | no remote")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "Lathe Operator"
    assert jobs[0]["location"] == "On-site"


# --- Junk rejection: no real role advertised ------------------------------


def test_no_role_line_is_dropped():
    # "G-Research | London, UK | On-site" — location + type, no role at all.
    assert parse("G-Research | London, UK | On-site") == []


def test_no_role_all_type_tokens_dropped():
    assert parse("Strictly | Remote | Remote | Remote") == []


def test_location_only_line_dropped():
    assert parse("Preferred Networks | Tokyo or Remote in Japan | Full-time") == []


# --- Junk roles must not slip through -------------------------------------


def test_salary_as_role_rejected():
    jobs = parse("Acme | 150-250k+ | SWE")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "SWE"


def test_url_as_role_rejected():
    jobs = parse("Acme | https://acme.com/jobs | SWE")
    assert len(jobs) == 1
    assert jobs[0]["role"] == "SWE"


def test_role_looks_ok_helpers():
    assert _is_type_or_loc("Remote")
    assert _is_type_or_loc("Full-Time")
    assert _is_type_or_loc("London, UK")
    assert _is_type_or_loc("SWE") is False


# --- Thread lookup must target the real monthly thread --------------------


def test_thread_matcher_rejects_reaaged_discussion():
    import re

    from vellum.tools import hn_hiring

    discussion = {
        "objectID": "1",
        "title": "Ask HN: Why is the \"Who is hiring?\" post being re-aged?",
    }
    real_thread = {"objectID": "2", "title": "Ask HN: Who is hiring? (August 2026)"}
    for hit in (discussion, real_thread):
        title = hit["title"]
        m = re.match(hn_hiring._THREAD_TITLE_RE, title, re.I)
        if m:
            assert hit["objectID"] == "2", (
                f"matcher wrongly accepted discussion title: {title!r}"
            )
        else:
            assert hit["objectID"] == "1", (
                f"matcher rejected the real thread title: {title!r}"
            )
