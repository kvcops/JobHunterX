"""
Tests for the eligibility gate — the strict, zero-token filter.

These lock in the two fixes from the review:
  1. Senior-halo / reject terms are scoped to the ROLE TITLE, not the JD
     prose (JD prose is context, not a requirement).
  2. Explicit year requirements ARE caught (the "needs 7+ yrs" case).
  3. City-alias conflict rejection.
"""

from vellum.agents.eligibility import (
    check_eligibility,
    _extract_required_years,
    _has_senior_halo,
)

FRESHER_PLAN = {
    "target_roles": ["software engineer"],
    "seniority_max": "entry",
    "years_experience": 0.0,
    "locations": ["Bengaluru", "Remote"],
    "must_have": ["Python"],
    "reject_terms": ["senior", "sales", "marketing", "recruiter"],
}


def jd(body: str, role: str = "Software Engineer", loc: str = "Bengaluru") -> dict:
    return {"role": role, "location": loc, "jd_text": body}


# --- Fix 1: senior-halo / reject terms are title-scoped -------------------


def test_senior_in_jd_prose_does_not_reject():
    job = jd(
        "You will work closely with our senior engineering team to build "
        "customer-facing features. We value mentorship.",
        role="Software Engineer",
    )
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_senior_in_role_title_rejects():
    job = jd("Build features end to end.", role="Senior Backend Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_sales_in_role_title_rejects():
    job = jd("Great for freshers!", role="Sales Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_sales_word_in_jd_prose_passes():
    job = jd("Our sales team is friendly. Apply now!", role="Software Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


# --- Fix 2: explicit years requirements are caught ------------------------


def test_explicit_seven_plus_years_rejects_fresher():
    job = jd("We need 7+ years of experience in distributed systems.",
             role="Backend Software Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_explicit_three_years_rejects_fresher():
    job = jd("Minimum 3 years of professional experience required.",
             role="Software Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_no_explicit_years_fresher_passes():
    job = jd("You are early in your career and love shipping.", role="Software Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_range_years_caught():
    job = jd("5-8 years experience building web apps.", role="Software Engineer")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_extract_required_years_variants():
    assert _extract_required_years("We need 7+ years of experience.") == 7.0
    assert _extract_required_years("Minimum 3 years of experience") == 3.0
    assert _extract_required_years("Requires 3 years to 5 years experience") == 3.0
    assert _extract_required_years("5-8 years") == 5.0
    assert _extract_required_years("no years mentioned") is None


# --- City-alias conflict rejection ----------------------------------------


def test_bangalore_alias_matches_bengaluru_plan():
    job = jd("great role", role="Software Engineer", loc="Bangalore")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_pune_only_job_conflicts_with_bengaluru_plan():
    job = jd("great role", role="Software Engineer", loc="Pune")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_remote_job_always_passes_location():
    job = jd("great role", role="Software Engineer", loc="Remote")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_unknown_location_not_rejected():
    job = jd("great role", role="Software Engineer", loc="")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_new_york_usa_job_rejected():
    """Foreign cities must never pass — previously 'New York, USA' had no
    Indian city alias so it slipped through the gate."""
    job = jd("great role", role="Software Engineer", loc="New York, USA")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_london_uk_job_rejected():
    job = jd("great role", role="Software Engineer", loc="London, UK")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_san_francisco_job_rejected():
    job = jd("great role", role="Software Engineer", loc="San Francisco, CA")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


def test_preferred_location_override_reaches_gate():
    """When the user explicitly picks a city, jobs in other Indian cities
    must be rejected even if the resume says Bengaluru."""
    plan = dict(FRESHER_PLAN)
    plan["locations"] = ["Hyderabad", "Remote"]
    job = jd("great role", role="Software Engineer", loc="Bengaluru")
    assert check_eligibility(job, plan)["verdict"] == "reject"


def test_hybrid_suffix_still_matches_plan_city():
    """'Bengaluru (Hybrid)' must match a Bengaluru plan — the raw string
    contains the city, and normalization must not break the match."""
    job = jd("great role", role="Software Engineer", loc="Bengaluru (Hybrid)")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


# --- Junior markers prevent senior-halo rejection -------------------------


def test_junior_marker_overrides_senior_halo():
    job = jd("Junior + senior all welcome!", role="Backend Engineer")
    assert _has_senior_halo("Backend Engineer") is False
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "pass"


def test_senior_role_with_junior_marker_pass_attempt():
    job = jd("Freshers and junior engineers encouraged to apply.",
             role="Software Engineer (Senior track)")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"


# --- Non-dev role families ------------------------------------------------


def test_campus_ambassador_rejected():
    job = jd("Spread the word on campus!", role="Campus Ambassador")
    assert check_eligibility(job, FRESHER_PLAN)["verdict"] == "reject"