"""
Tests for Parallel AI Search & Direct Job Posting URL unblocking.
"""

import pytest
from jobhunterx.tools.job_discovery import _is_aggregator, _is_direct_job_url, _looks_like_job_url
from jobhunterx.tools import parallel_search


def test_direct_job_urls_recognized():
    assert _is_direct_job_url("https://www.linkedin.com/jobs/view/123456789") is True
    assert _is_direct_job_url("https://www.indeed.com/viewjob?jk=abcdef123456") is True
    assert _is_direct_job_url("https://www.foundit.in/job/software-engineer-hyderabad-123") is True
    assert _is_direct_job_url("https://www.naukri.com/job-listings-software-engineer-hyderabad-12345") is True
    assert _is_direct_job_url("https://boards.greenhouse.io/acme/jobs/98765") is True
    assert _is_direct_job_url("https://jobs.lever.co/acme/12345-67890") is True


def test_waste_aggregators_never_direct():
    # Instahyre & AIJobs require login / are login-gated aggregators — must be filtered out everywhere
    assert _is_direct_job_url("https://www.instahyre.com/job/12345-backend-engineer") is False
    assert _is_aggregator("https://www.instahyre.com/job/12345-backend-engineer") is True
    assert _is_direct_job_url("https://aijobs.net/job/senior-ml-engineer") is False
    assert _is_aggregator("https://aijobs.net/job/senior-ml-engineer") is True


def test_aggregator_filter_permits_direct_job_urls():
    # Direct job posting URLs on LinkedIn, Indeed, FoundIt, Naukri must NOT be treated as aggregator noise
    assert _is_aggregator("https://www.linkedin.com/jobs/view/123456789") is False
    assert _is_aggregator("https://www.indeed.com/viewjob?jk=abcdef123456") is False
    assert _is_aggregator("https://www.foundit.in/job/software-engineer-123") is False
    assert _is_aggregator("https://www.naukri.com/job-listings-software-engineer-123") is False

    # Generic search result pages MUST be treated as aggregators
    assert _is_aggregator("https://www.linkedin.com/jobs/search?keywords=python") is True
    assert _is_aggregator("https://www.google.com/search?q=jobs") is True
    assert _is_aggregator("https://www.quora.com/how-to-find-jobs") is True


def test_looks_like_job_url_with_direct_links():
    assert _looks_like_job_url("https://www.linkedin.com/jobs/view/123456789") is True
    assert _looks_like_job_url("https://www.naukri.com/job-listings-software-engineer-12345") is True
    assert _looks_like_job_url("https://jobs.lever.co/acme/12345") is True


@pytest.mark.asyncio
async def test_parallel_search_execution():
    results = await parallel_search.execute_parallel_search(["software engineer hyderabad"], max_results_per_query=2)
    assert isinstance(results, list)
