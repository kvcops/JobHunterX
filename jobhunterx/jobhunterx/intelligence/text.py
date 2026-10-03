"""Generic text and date helpers (no domain vocabularies)."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Iterable, Optional

from jobhunterx.domain.candidate import norm_term

_DATE_FORMATS = ("%b %Y", "%B %Y", "%b, %Y", "%B, %Y", "%m/%Y", "%m-%Y", "%Y-%m", "%Y/%m",
                 "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%Y")


def parse_month(raw: str) -> Optional[date]:
    """Parse a resume-style date ("Jan 2023", "2023-01", "2021") to a date, else None."""
    s = re.sub(r"\s+", " ", (raw or "").strip().replace("’", "'").replace(".", ""))
    if not s:
        return None
    s = re.sub(r"'(\d{2})\b", r"20\1", s)        # Jan '23
    for fmt in _DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt)
            return date(d.year, d.month, 1)
        except ValueError:
            continue
    m = re.search(r"\b(19|20)\d{2}\b", s)
    if m:
        return date(int(m.group(0)), 1, 1)
    return None


def parse_iso_datetime(raw) -> Optional[datetime]:
    """Parse ISO strings / epoch millis / date strings from APIs into aware datetimes."""
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, (int, float)):
        ts = raw / 1000 if raw > 10_000_000_000 else raw
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(raw).strip()
    if s.isdigit():
        return parse_iso_datetime(int(s))
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    d = parse_month(s)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) if d else None


def merged_years(intervals: Iterable[tuple[date, date]]) -> float:
    """Total years covered by possibly-overlapping (start, end) intervals."""
    ivs = sorted((a, b) for a, b in intervals if a and b and b >= a)
    total_days = 0
    cur_s, cur_e = None, None
    for s, e in ivs:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            total_days += (cur_e - cur_s).days
            cur_s, cur_e = s, e
    if cur_s is not None:
        total_days += (cur_e - cur_s).days
    # +1 month: "Jan 2023 – Jan 2023" is one month of work
    return round(total_days / 365.25 + (1 / 12 if ivs else 0), 1)


def term_pattern(term: str) -> Optional[re.Pattern]:
    t = norm_term(term)
    if not t:
        return None
    esc = re.escape(t).replace(r"\ ", r"[\s\-_/]*")
    return re.compile(rf"(?<![A-Za-z0-9+#]){esc}(?![A-Za-z0-9+#])", re.I)


def term_in_text(term: str, text: str) -> bool:
    """Boundary-aware, case-insensitive presence check ("Java" ≠ "JavaScript")."""
    pat = term_pattern(term)
    return bool(pat and text and pat.search(text))


def any_term_in_text(terms: Iterable[str], text: str) -> Optional[str]:
    for t in terms:
        if t and term_in_text(t, text):
            return t
    return None


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9+#.\-]*[a-z0-9+#]|[a-z0-9]", (text or "").lower()) if len(w) > 1]


# Indian pay notation: "12-18 LPA", "₹12L–18L", "8 to 10 lakhs per annum", "₹1.2 Cr", "₹50,000 per month".
_INR_UNITS = {"lpa": 1e5, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5,
              "cr": 1e7, "crore": 1e7, "crores": 1e7}
_INR_NUM = r"(\d+(?:,\d{2,3})*(?:\.\d+)?)"
_INR_UNIT = r"\s*(lpa|lakhs?|lacs?|l|crores?|cr)\b"
_INR_CUR = r"(?:₹|rs\.?|inr)"
_INR_TO = r"\s*(?:-|–|—|to)\s*"
_INR_RANGE = re.compile(rf"({_INR_CUR})?\s*{_INR_NUM}(?:{_INR_UNIT})?{_INR_TO}{_INR_CUR}?\s*{_INR_NUM}(?:{_INR_UNIT})?", re.I)
_INR_SINGLE = re.compile(rf"({_INR_CUR})?\s*{_INR_NUM}(?:{_INR_UNIT})?", re.I)
_PAY_WORDS = re.compile(r"\b(ctc|salary|package|compensation|pay|stipend|per annum|p\.?a\.?|lpa)\b", re.I)
_MONTHLY = re.compile(r"per\s*month|/\s*month|\bp\.?m\.?\b|monthly|/\s*mo\b", re.I)


def parse_inr_salary(text: str, require_context: bool = False) -> Optional[tuple[float, Optional[float], str, str]]:
    """Read Indian pay notation into rupees: (min, max, period, matched text), else None.

    An amount counts only when it carries a lakh/crore unit or a rupee sign —
    a bare number ("12-18") is never treated as pay. With `require_context`,
    the match must also sit next to a pay word (CTC, salary, package …),
    so funding news like "raised ₹100 crore" is not read as a salary.
    """
    s = text or ""
    for pat in (_INR_RANGE, _INR_SINGLE):
        for m in pat.finditer(s):
            g = m.groups()
            if pat is _INR_RANGE:
                cur, a, ua, b, ub = g
            else:
                cur, a, ua = g
                b = ub = None
            unit = (ub or ua or "").lower()
            if not unit and not cur:
                continue
            window = s[max(0, m.start() - 60): m.end() + 40]
            if require_context and not _PAY_WORDS.search(window):
                continue
            mult = _INR_UNITS.get(unit, 1.0)
            lo = float(a.replace(",", "")) * (_INR_UNITS.get(ua.lower(), mult) if ua else mult)
            hi = float(b.replace(",", "")) * mult if b else None
            period = "month" if _MONTHLY.search(s[m.end(): m.end() + 25]) else "year"
            annual = (hi or lo) * (12 if period == "month" else 1)
            if annual < 50_000 or annual > 50_000_000 or (hi is not None and hi < lo):
                continue                           # not a believable yearly pay in rupees
            return lo, hi, period, m.group(0).strip()
    return None


def number_in_text(value: float, text: str) -> bool:
    """Does the number literally appear in the text? (anti-hallucination check)"""
    if value is None:
        return False
    v = int(value) if float(value).is_integer() else value
    return bool(re.search(rf"(?<![\d.]){re.escape(str(v))}(?![\d])", text or ""))
