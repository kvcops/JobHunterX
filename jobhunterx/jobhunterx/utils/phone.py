"""Phone numbers and country calling codes for every country, from Google's libphonenumber data (the `phonenumbers`
package) — no table of chosen countries. Country names are matched in English, case-insensitive, or as their
two-letter region code."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

try:                                   # the app keeps working without the package (numbers are then used as written)
    import phonenumbers
    from phonenumbers import geocoder
except ImportError:                    # pragma: no cover - only on an install that has not got it yet
    phonenumbers = None
    geocoder = None


@lru_cache(maxsize=1)
def _by_name() -> dict[str, str]:
    out: dict[str, str] = {}
    if phonenumbers is None:
        return out
    for region in phonenumbers.SUPPORTED_REGIONS:
        name = geocoder._region_display_name(region, "en") or ""
        if name:
            out[name.lower()] = region
        out[region.lower()] = region
    return out


def region_of(country: str) -> Optional[str]:
    """'India' / 'india' / 'IN' → 'IN'; None when the name is unknown."""
    c = (country or "").strip().lower()
    return _by_name().get(c) if c else None


def country_name(region: str) -> str:
    return (geocoder._region_display_name((region or "").upper(), "en") or "") if geocoder else ""


def calling_code(country: str) -> str:
    """'India' → '+91'; '' when the country is unknown."""
    r = region_of(country)
    code = phonenumbers.country_code_for_region(r) if r and phonenumbers else 0
    return f"+{code}" if code else ""


def _digits(code: str) -> int:
    try:
        return int(re.sub(r"\D", "", code or "") or 0)
    except ValueError:
        return 0


def country_for_code(code: str) -> str:
    """'+91' → 'India' (the main country using that code); '' if none."""
    if phonenumbers is None:
        return ""
    r = phonenumbers.region_code_for_country_code(_digits(code))
    return country_name(r) if r and r != "ZZ" else ""


def region_for_code(code: str) -> str:
    if phonenumbers is None:
        return ""
    r = phonenumbers.region_code_for_country_code(_digits(code))
    return r.lower() if r and r != "ZZ" else ""


def aliases_for_code(code: str) -> list[str]:
    """Every country name and region code that uses this calling code ('+1' → United States, Canada, …)."""
    regions = phonenumbers.COUNTRY_CODE_TO_REGION_CODE.get(_digits(code), ()) if phonenumbers else ()
    return [x for r in regions if r != "001" for x in (country_name(r).lower(), r.lower()) if x]


def split(phone: str, country: str = "") -> tuple[str, str]:
    """'+91 80747 49058' → ('+91', '8074749058'); a number without '+code' is read as a number of `country`.
    ('', digits) when the number can't be read."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return "", ""
    region = None if raw.startswith(("+", "00")) else region_of(country)
    if phonenumbers is None:
        m = re.match(r"\s*\+(\d{1,3})[\s\-()]+(.+)", raw)
        return ("+" + m.group(1), re.sub(r"\D", "", m.group(2))) if m else ("", digits)
    try:
        n = phonenumbers.parse("+" + digits[2:] if raw.startswith("00") else raw, region)
        return f"+{n.country_code}", phonenumbers.national_significant_number(n)
    except phonenumbers.NumberParseException:
        return calling_code(country) if not raw.startswith("+") else "", digits


def country_from_phone(phone: str) -> str:
    """The country a '+code' number belongs to; '' when it has no code or can't be read."""
    raw = (phone or "").strip()
    if not raw.startswith(("+", "00")):
        return ""
    code, _ = split(raw)
    return country_for_code(code)
