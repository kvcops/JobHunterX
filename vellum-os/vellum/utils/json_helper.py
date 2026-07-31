"""
Vellum OS — Robust LLM JSON Repair & Parsing Helper

Handles common LLM JSON output flaws (markdown wrappers, unescaped quotes,
unescaped newlines inside strings, trailing commas, truncated output).
"""

from __future__ import annotations

import json
import re
from typing import Any

from vellum.config.logging import get_logger

log = get_logger("json_helper")


def parse_llm_json(raw_text: str | None, default: Any = None) -> Any:
    """Parse JSON string from LLM output with robust fault-tolerant repair.

    Args:
        raw_text: Raw string returned by LLM.
        default: Fallback return value if parsing fails completely.

    Returns:
        Parsed JSON data (list, dict, etc.) or default.
    """
    if not raw_text or not isinstance(raw_text, str):
        return default if default is not None else {}

    text = raw_text.strip()

    # Step 1: Strip Markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Fast path: try standard json.loads
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 2: Attempt standard string repairs
    repaired = _repair_json_string(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Step 3: Regex fallback extraction for array [...] or object {...}
    array_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if array_match:
        try:
            return json.loads(_repair_json_string(array_match.group(0)))
        except json.JSONDecodeError:
            pass

    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        try:
            return json.loads(_repair_json_string(obj_match.group(0)))
        except json.JSONDecodeError:
            pass

    # Step 4: Line-by-line / partial array repair for unterminated strings
    repaired_partial = _repair_truncated_json(text)
    if repaired_partial:
        try:
            return json.loads(repaired_partial)
        except json.JSONDecodeError:
            pass

    log.warning("parse_llm_json_failed", raw_sample=raw_text[:200])
    return default if default is not None else {}


def _repair_json_string(text: str) -> str:
    """Apply common formatting repairs to malformed JSON text."""
    # Replace literal unescaped newlines/tabs inside string values
    # We do a character walk or safe replacement
    s = text

    # Remove trailing commas in objects and arrays: , \s* [}] or , \s* ]
    s = re.sub(r",\s*([\}\]])", r"\1", s)

    # Fix unescaped double quotes inside string fields (heuristic)
    # Match patterns like `"key": "some "inner quote" text"`
    # Replace single backslashes if improperly escaped
    s = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r"\\\\", s)

    # Fix unescaped newlines inside quotes
    def replace_newlines_in_strings(match: re.Match) -> str:
        content = match.group(0)
        # replace raw newlines inside string literal
        return content.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

    # Match string literals in JSON
    s = re.sub(r'"([^"\\]|\\.)*"', replace_newlines_in_strings, s, flags=re.DOTALL)

    return s


def _repair_truncated_json(text: str) -> str | None:
    """Attempt to close open strings, objects, or arrays in truncated LLM outputs."""
    s = text.strip()

    # Count brackets
    open_brackets = s.count("[") - s.count("]")
    open_braces = s.count("{") - s.count("}")

    # Check if inside an unclosed string
    # If odd number of unescaped quotes, add a closing quote
    quote_count = len(re.findall(r'(?<!\\)"', s))
    if quote_count % 2 != 0:
        s += '"'

    # Remove trailing comma if present
    s = re.sub(r",\s*$", "", s.strip())

    # Close missing braces and brackets in order
    if open_braces > 0:
        s += "}" * open_braces
    if open_brackets > 0:
        s += "]" * open_brackets

    return s
