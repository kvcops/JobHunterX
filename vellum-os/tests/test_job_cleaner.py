"""
Unit tests for vellum.utils.job_cleaner.clean_job_title_and_company
"""

from vellum.utils.job_cleaner import clean_job_title_and_company


def test_clean_company_and_role_from_bayt_portal():
    title = "Engineer - Digital & AI Solutions at IQEQ - Hyderabad - Bayt.com"
    company = "Bayt.Com"
    snippet = "Job Description. Responsibilities..."
    url = "https://www.bayt.com/en/india/jobs/engineer-digital-ai-solutions-at-iqeq-12345/"

    cleaned_company, cleaned_role = clean_job_title_and_company(title, company, snippet, url)
    assert cleaned_company == "Iqeq"
    assert "Digital & AI Solutions" in cleaned_role or "Engineer" in cleaned_role


def test_clean_company_and_role_from_ghx_title():
    title = "Job Application for Senior AI Engineer at GHX"
    company = "Unknown"
    snippet = "Senior AI Engineer Location: Hyderabad..."
    url = "https://job-boards.greenhouse.io/globalhealthcareexchangeinc/jobs/4694489005"

    cleaned_company, cleaned_role = clean_job_title_and_company(title, company, snippet, url)
    assert cleaned_company in ("Ghx", "Globalhealthcareexchangeinc")
    assert cleaned_role == "Senior AI Engineer"


def test_clean_company_and_role_from_attach_resume_noise():
    title = "ATTACH RESUME/CV"
    company = "Unknown"
    snippet = "India / Hyderabad. We may use artificial intelligence. Role: AI Engineer"
    url = "https://jobs.lever.co/company-x/12345"

    cleaned_company, cleaned_role = clean_job_title_and_company(title, company, snippet, url)
    assert cleaned_role == "Ai Engineer"
    assert cleaned_company == "Company X"


def test_clean_company_and_role_from_smart_working_solutions():
    title = "Smart Working Solutions - AI Engineer - ElevenLabs (Remote,..."
    company = "Unknown"
    snippet = "We are seeking a Senior ElevenLabs Solutions Engineer..."
    url = "https://jobs.lever.co/smart-working-solutions/c11e12f3-a700-4504"

    cleaned_company, cleaned_role = clean_job_title_and_company(title, company, snippet, url)
    assert cleaned_company in ("Smart Working Solutions", "Elevenlabs")
    assert "AI Engineer" in cleaned_role


def test_clean_company_and_role_from_weekday_client():
    title = "Weekday - AI Engineer Lead"
    company = "Ai Engineer Lead"
    snippet = "This role is for one of our clients Company Name: Incepteo Industry: Information Technology..."
    url = "https://jobs.lever.co/weekdayworks/ef3ebe6c-a72a-4876-9413"

    cleaned_company, cleaned_role = clean_job_title_and_company(title, company, snippet, url)
    assert cleaned_company == "Incepteo"
    assert cleaned_role == "AI Engineer Lead"
