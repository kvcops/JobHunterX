"""Search ranking and employer judgement come from the candidate's profile and the AI — no fixed city, role or
company lists."""

from jobhunterx.tools import deep_search as ds


def test_places_come_from_the_candidate_not_a_city_table():
    tok = ds.set_context({"Pune": ["Pune", "Poona"]}, ["India"], ["Data Analyst"])
    try:
        q = ds.understand("data analyst poona jobs")
        assert q.places == ["pune"] and q.role == ["data", "analyst"] and q.india
        assert ds._place_ok("Pune, Maharashtra", [], q) and not ds._place_ok("Hyderabad", [], q)
    finally:
        ds._CTX.reset(tok)
    q = ds.understand("data analyst hyderabad jobs")        # no context: nothing is assumed about cities
    assert q.places == [] and "hyderabad" in q.role


def test_initials_match_both_ways_without_a_synonym_table():
    q = ds.Query(raw="", core="", role=["machine", "learning", "engineer"], places=[], india=False, remote=False)
    assert ds._role_match("ML Engineer", q) == 1.0
    q2 = ds.Query(raw="", core="", role=["ai", "engineer"], places=[], india=False, remote=False)
    assert ds._role_match("Artificial Intelligence Engineer", q2) == 1.0


def test_generic_words_are_learned_from_the_board_itself():
    titles = [f"{x} Engineer" for x in ("Software", "Backend", "Frontend", "Data", "Platform", "QA", "Security", "AI", "DevOps")]
    common = ds._common_words(titles)
    assert "engineer" in common
    q = ds.Query(raw="", core="", role=["ai", "engineer"], places=[], india=False, remote=False)
    assert ds._role_match("Software Engineer", q, common) == 0.0      # shares only the board-wide word
    assert ds._role_match("AI Engineer", q, common) == 1.0


def test_bulk_it_services_is_the_ai_reading_not_a_name_list():
    from tests.test_intelligence import FIT, job, snap
    from jobhunterx.intelligence.matching import assess
    m = assess(snap(), job(company="Infosys"), role_fit=FIT)              # name alone means nothing now
    assert m.track == "main" and "company" not in {c.key for c in m.hard_constraints if c.status == "fail"}
    m = assess(snap(), job(company="Some Firm", employer_kind="it_services_bulk"), role_fit=FIT)
    assert any(c.key == "company" for c in m.hard_constraints)
