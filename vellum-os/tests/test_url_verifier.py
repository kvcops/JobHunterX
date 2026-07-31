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
