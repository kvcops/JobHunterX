"""
Unit tests for kuro.utils.json_helper.parse_llm_json
"""

import pytest
from kuro.utils.json_helper import parse_llm_json


def test_parse_valid_json_object():
    raw = '{"match_score": 0.85, "reasoning": "Great fit"}'
    res = parse_llm_json(raw)
    assert res == {"match_score": 0.85, "reasoning": "Great fit"}


def test_parse_markdown_json():
    raw = """```json
[
  {"job_index": 0, "match_score": 0.75, "reasoning": "Strong match"}
]
```"""
    res = parse_llm_json(raw)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["match_score"] == 0.75


def test_parse_json_with_raw_newlines_and_trailing_comma():
    # Simulated broken LLM string output like the user reported
    raw = """[
  {
    "job_index": 0,
    "match_score": 0.8,
    "matching_skills": ["Python", "FastAPI"],
    "reasoning": "Line 1
Line 2 with quotes \\"inside\\"",
  },
]"""
    res = parse_llm_json(raw)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["job_index"] == 0


def test_parse_truncated_json_array():
    raw = '[{"match_score": 0.9, "reasoning": "Truncated string'
    res = parse_llm_json(raw)
    assert isinstance(res, list)
    assert res[0]["match_score"] == 0.9
