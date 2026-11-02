"""Searches reach new employers: postings already in the list and employers that never fitted are skipped before the
limit, new employers rank first, and every run asks Greenhouse, Lever and Ashby directly."""

from jobhunterx.discovery import ats_index, search
from jobhunterx.services.search import _company_weight


def test_company_weight_learns_from_the_persons_own_list():
    w = _company_weight({"acme": {"total": 4, "good": 0, "poor": 3}, "globex": {"total": 2, "good": 1, "poor": 0}})
    assert w("Acme") == 0                       # kept coming back, never a fit
    assert 0 < w("Globex") < 1                  # covered already: gives way
    assert w("Initech") > 1                     # never seen: first


def test_index_search_skips_known_postings_before_the_limit(monkeypatch):
    rows = [ats_index.Row(url=f"https://jobs.lever.co/c{i}/{i}", company=f"C{i}", title="Data Analyst", location="Pune, India",
                          level="entry", first_seen="2099-01-01T00:00:00Z", ats="lever") for i in range(6)]
    monkeypatch.setattr(ats_index, "_load", lambda: rows)
    monkeypatch.setattr(ats_index, "_common", lambda: set())
    have = {rows[0].url, rows[1].url}
    hits = ats_index.search(["Data Analyst"], ["Pune"], limit=2, skip=lambda u: u in have,
                            weight=lambda c: 0 if c == "C2" else 1)
    assert [r.company for r, _ in hits] == ["C3", "C4"]


def test_board_queries_cover_the_open_boards_and_rotate():
    scope = search.SearchScope(titles=["Data Analyst", "Business Analyst"], locations=["Pune"], include_remote=False, country="India")
    q0, q1 = search.board_queries(scope, 0), search.board_queries(scope, 1)
    assert any("jobs.lever.co" in q for q in q0) and any("jobs.ashbyhq.com" in q for q in q0) \
        and any("greenhouse.io" in q for q in q0)
    assert q0[0] != q1[0]
