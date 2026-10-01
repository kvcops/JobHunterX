"""
Evidence checks for generated text — the anti-fabrication layer.

A generated line is accepted only if every *checkable fact* in it is
supported by the candidate's own source material:

  * numbers / metrics must appear in the source text it was written from;
  * "technical-looking" tokens (CamelCase, ALLCAPS, tokens with digits or
    + # . characters, capitalized words not at sentence start) must appear
    somewhere in the candidate's profile;
  * job-required skills must not be newly attributed to an experience
    that never mentioned them (no keyword stuffing of unearned skills).

These checks are deliberately vocabulary-free: they compare generated text
with the candidate's own data, not with a list of known technologies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobhunterx.intelligence.text import term_in_text

_NUM_RE = re.compile(r"(?<![A-Za-z])\d[\d,.]*\s*(?:%|x|k|m|\+)?", re.I)


def numbers(text: str) -> set[str]:
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        n = re.sub(r"[,\s]", "", m.group(0)).rstrip(".").lower()
        if n:
            out.add(n)
    return out


def _sentence_starts(text: str) -> set[int]:
    starts = {0}
    for m in re.finditer(r"[.!?;:•\n]\s+", text):
        starts.add(m.end())
    return starts


def notable_terms(text: str) -> set[str]:
    """Tokens that look like proper nouns / technologies / products."""
    out = set()
    starts = _sentence_starts(text)
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9+#./\-]*[A-Za-z0-9+#]|[A-Z]", text or ""):
        tok = m.group(0).strip(".-/")
        if len(tok) < 2:
            continue
        technical = bool(re.search(r"[0-9+#]|[a-z][A-Z]|\.[A-Za-z]", tok)) or (tok.isupper() and len(tok) >= 2)
        proper = tok[0].isupper() and m.start() not in starts
        if technical or proper:
            out.add(tok)
    return out


@dataclass
class CheckResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def check_rewrite(rewritten: str, original: str, profile_text: str, *, forbidden_new_terms: list[str] = ()) -> CheckResult:
    """Validate a rewritten line against the line it came from + the whole profile."""
    problems = []
    orig_nums = numbers(original)
    for n in numbers(rewritten) - orig_nums:
        problems.append(f"new number '{n}' not in the original")
    for term in notable_terms(rewritten):
        if not term_in_text(term, profile_text) and not term_in_text(term, original):
            problems.append(f"'{term}' does not appear anywhere in your profile")
    for term in forbidden_new_terms:
        if term and term_in_text(term, rewritten) and not term_in_text(term, original):
            problems.append(f"adds '{term}', which this experience never mentioned")
    if len(rewritten.strip()) < 15:
        problems.append("too short")
    return CheckResult(ok=not problems, problems=problems[:4])


def check_free_text(text: str, profile_text: str, *, allowed_extra: str = "") -> CheckResult:
    """Validate free text (summary, cover letter) against the whole profile.

    `allowed_extra` is trusted context that may legitimately be named (e.g. the
    target company and job title in a cover letter)."""
    problems = []
    corpus = f"{profile_text}\n{allowed_extra}"
    for n in numbers(text) - numbers(corpus):
        problems.append(f"number '{n}' is not in your profile")
    for term in notable_terms(text):
        if not term_in_text(term, corpus):
            problems.append(f"'{term}' does not appear in your profile")
    return CheckResult(ok=not problems, problems=problems[:5])


def filter_sentences(text: str, profile_text: str, allowed_extra: str = "") -> tuple[str, list[str]]:
    """Drop individual sentences that fail `check_free_text`; return (text, problems)."""
    kept, problems = [], []
    for sent in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        if not sent:
            continue
        r = check_free_text(sent, profile_text, allowed_extra=allowed_extra)
        if r.ok:
            kept.append(sent)
        else:
            problems += r.problems
    return " ".join(kept), problems
