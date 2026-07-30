"""Tests for job_evaluator.py — experience extraction, matching, heuristic scoring."""

import pytest
from vellum.agents.job_evaluator import (
    extract_experience_from_jd,
    is_experience_match,
    _heuristic_match_score,
)


class TestExtractExperienceFromJd:
    def test_range_years(self):
        assert extract_experience_from_jd("3-5 years of experience") == 3.0

    def test_dash_range(self):
        assert extract_experience_from_jd("3–5 years of experience") == 3.0

    def test_plus_years(self):
        assert extract_experience_from_jd("5+ years experience") == 5.0

    def test_minimum_years(self):
        assert extract_experience_from_jd("minimum 3 years") == 3.0

    def test_level_keywords(self):
        assert extract_experience_from_jd("We need a senior engineer") == 5.0

    def test_intern_level(self):
        assert extract_experience_from_jd("Intern position") == 0.0

    def test_no_experience(self):
        assert extract_experience_from_jd("Join our team!") is None

    def test_empty(self):
        assert extract_experience_from_jd("") is None


class TestIsExperienceMatch:
    def test_match(self):
        assert is_experience_match(3.0, 5.0) is True

    def test_exact_match(self):
        assert is_experience_match(5.0, 5.0) is True

    def test_no_match(self):
        assert is_experience_match(7.0, 3.0) is False

    def test_unknown_required(self):
        assert is_experience_match(None, 3.0) is True

    def test_zero_required(self):
        assert is_experience_match(0.0, 0.0) is True


class TestHeuristicMatchScore:
    def test_relevant_job(self):
        job = {
            "title": "Senior Python Developer",
            "jd_text": "Python Django AWS experience required",
        }
        profile = {
            "skills": ["Python", "Django", "AWS"],
            "relevant_experience": "5 years",
        }
        score = _heuristic_match_score(job, profile, "python developer")
        assert score > 0.5

    def test_irrelevant_job(self):
        job = {
            "title": "Sales Manager",
            "jd_text": "Sales experience in B2B",
        }
        profile = {
            "skills": ["Python", "Django"],
            "relevant_experience": "5 years",
        }
        score = _heuristic_match_score(job, profile, "software engineer")
        assert score < 0.6

    def test_empty_profile(self):
        job = {"title": "Engineer", "jd_text": "Python developer"}
        profile = {"skills": [], "relevant_experience": ""}
        score = _heuristic_match_score(job, profile, "engineer")
        assert 0.0 <= score <= 1.0

    def test_score_range(self):
        job = {"title": "Developer", "jd_text": "Coding"}
        profile = {"skills": ["Python"], "relevant_experience": "3 years"}
        score = _heuristic_match_score(job, profile, "developer")
        assert 0.10 <= score <= 0.95
