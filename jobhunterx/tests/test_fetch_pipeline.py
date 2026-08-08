"""
Unit tests for Safe URL Normalization & Hybrid Fetch Pipeline.
"""

from jobhunterx.tools.fetch_pipeline import normalize_url_safely


def test_url_normalization_tracking_strip():
    raw = "https://www.linkedin.com/jobs/view/12345/?utm_source=google&utm_medium=cpc&ref=123&job_id=99"
    norm = normalize_url_safely(raw)
    assert "utm_source" not in norm
    assert "utm_medium" not in norm
    assert "ref=" not in norm
    assert "job_id=99" in norm
    assert "linkedin.com/jobs/view/12345" in norm
