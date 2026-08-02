"""
Unit tests for vellum.tools.url_verifier
"""

import pytest
from vellum.tools.url_verifier import verify_job_url, filter_active_jobs


@pytest.mark.asyncio
async def test_verify_invalid_url_format():
    is_active, reason, _ = await verify_job_url("invalid_url_str")
    assert not is_active
    assert "Invalid URL" in reason


@pytest.mark.asyncio
async def test_verify_unreachable_url():
    is_active, reason, _ = await verify_job_url("https://invalid-domain-that-does-not-exist-12345.com/job")
    assert not is_active


@pytest.mark.asyncio
async def test_filter_active_jobs_empty():
    res = await filter_active_jobs([])
    assert res == []


def test_verify_job_text_local():
    from vellum.tools.url_verifier import verify_job_text_local
    
    # Success case
    jd_ok = "This is a great software engineer role. We require skills in Python, FastAPI, and general backend development. Location is Bengaluru. Apply today!"
    is_active, reason = verify_job_text_local(jd_ok)
    assert is_active
    assert reason == "Active"
    
    # Too short case
    jd_short = "Short text"
    is_active, reason = verify_job_text_local(jd_short)
    assert not is_active
    assert "Insufficient text" in reason
    
    # Closed case
    jd_closed = "This position has been filled. We are no longer accepting applications."
    is_active, reason = verify_job_text_local(jd_closed)
    assert not is_active
    assert "expired/closed" in reason
