"""Tests for resume tailoring fixes:
- BULLET_TAILORING_PROMPT no longer teaches the fabricated-metric XYZ formula
- placeholder-artifact sanitizer strips "X% / [Y] / by doing Z" tokens
- hard safety check drops bullets that still contain placeholders
"""

import pytest

from jobhunterx.agents.validator_tailor import (
    BULLET_TAILORING_PROMPT,
    _sanitize_metric_placeholders,
    _has_placeholder_artifact,
)


class TestBulletPrompt:
    def test_no_xyz_formula_instruction(self):
        """The prompt must NOT instruct the LLM to use the Google XYZ
        Formula, which caused fabricated 'X% / Y' placeholders."""
        assert "Google XYZ Formula" not in BULLET_TAILORING_PROMPT
        assert "Accomplished [X]" not in BULLET_TAILORING_PROMPT

    def test_explicitly_forbids_fabricated_metrics(self):
        lowered = BULLET_TAILORING_PROMPT.lower()
        assert "no fabricated metrics" in lowered or "must not invent numbers" in lowered

    def test_forbids_placeholder_output_tokens(self):
        lowered = BULLET_TAILORING_PROMPT.lower()
        assert "x%" in lowered and "y%" in lowered  # mentioned as forbidden output

    def test_truthfulness_rule_preserved(self):
        assert "truthfulness" in BULLET_TAILORING_PROMPT.lower()


class TestSanitizePlaceholders:
    def test_strips_bracket_tokens(self):
        out = _sanitize_metric_placeholders("Reduced [Y] by [Z] with caching")
        assert "[" not in out and "]" not in out
        assert "caching" in out

    def test_strips_x_percent(self):
        out = _sanitize_metric_placeholders("Improved X% by adding tests")
        assert "X%" not in out
        assert "tests" in out

    def test_strips_measured_by_y(self):
        out = _sanitize_metric_placeholders("Accomplished X as measured by Y by doing Z")
        assert "measured by" not in out

    def test_keeps_real_metrics(self):
        out = _sanitize_metric_placeholders("Cut API latency by 40% via Redis caching")
        assert "40%" in out

    def test_keeps_normal_text(self):
        out = _sanitize_metric_placeholders("Built a REST API with FastAPI")
        assert out == "Built a REST API with FastAPI"

    def test_empty(self):
        assert _sanitize_metric_placeholders("") == ""


class TestHasPlaceholderArtifact:
    def test_detects_bracket(self):
        assert _has_placeholder_artifact("Reduced [Y] by 30%") is True

    def test_detects_x_percent(self):
        assert _has_placeholder_artifact("Improved X%") is True

    def test_clean_bullet_passes(self):
        assert _has_placeholder_artifact("Shipped GraphQL API in Python") is False

    def test_real_percentage_not_flagged(self):
        assert _has_placeholder_artifact("Reduced latency by 40%") is False

    def test_empty(self):
        assert _has_placeholder_artifact("") is False
