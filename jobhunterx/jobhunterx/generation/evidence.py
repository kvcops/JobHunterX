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


def _canon(raw: str) -> str:
    """'20k' / '20,000' / '20000' -> '20000'; '30%' -> '30'; '1.50' -> '1.5' (same fact, different spelling)."""
    n = re.sub(r"[,\s]", "", raw).rstrip(".").lower().rstrip("+x%")
    mult = 1
    if n.endswith("k"):
        n, mult = n[:-1], 1000
    elif n.endswith("m"):
        n, mult = n[:-1], 1_000_000
    try:
        value = float(n) * mult
    except ValueError:
        return n
    return f"{value:g}" if value < 1e15 else n


def numbers(text: str) -> set[str]:
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        n = _canon(m.group(0))
        if n:
            out.add(n)
    return out


def snapshot_facts(snapshot) -> str:
    """Facts the app worked out and verified itself (years of experience, verified skills) —
    allowed in generated text even though the profile never spells them out (e.g. '1.6 years')."""
    if snapshot is None:
        return ""
    parts = []
    for attr in ("professional_years", "total_years", "internship_years"):
        v = float(getattr(snapshot, attr, 0) or 0)
        if v:
            parts += [f"{v:g}", f"{round(v, 1):g}", f"{round(v):g}", f"{int(v):g}"]
    for s in getattr(snapshot, "skills", []) or []:
        parts += [s.name, *getattr(s, "aliases", [])]
    # Target titles and career tracks are deliberately NOT allowed: they are jobs to search for, not jobs held.
    return "\n".join(str(x) for x in parts if x)


def keep_tense(original: str, rewritten: str) -> str:
    """If the rewrite only changed the opening verb's form ('Built' -> 'Build'), keep the original verb."""
    o, r = (original or "").split(maxsplit=1), (rewritten or "").split(maxsplit=1)
    if len(o) < 1 or len(r) < 2:
        return rewritten
    ow, rw = o[0].strip(",;:"), r[0].strip(",;:")
    if ow.lower() == rw.lower():
        return rewritten
    a, b = ow.lower(), rw.lower()
    common = 0
    while common < min(len(a), len(b)) and a[common] == b[common]:
        common += 1
    if common >= max(3, min(len(a), len(b)) - 2):          # same verb, different form
        return f"{ow} {r[1]}"
    return rewritten


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
