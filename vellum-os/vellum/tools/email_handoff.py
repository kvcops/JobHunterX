"""
Vellum OS — Email Handoff Tool

Generates email permutations (explicitly labeled as unverified guesses),
performs MX record checks, and creates mailto: URIs.
Never auto-sends — user clicks "Open in Mail App" to hand off.
"""

from __future__ import annotations

import re
import urllib.parse
import webbrowser
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("email_handoff")


# ---------------------------------------------------------------------------
# Email permutation (all guesses, never assumed valid)
# ---------------------------------------------------------------------------

def generate_email_permutations(
    first_name: str, last_name: str, domain: str
) -> list[dict]:
    """Generate common email permutations for a contact.

    ALL results are labeled `unverified_guess: True`.
    Returns list of EmailGuess-compatible dicts.
    """
    first = re.sub(r"[^a-z]", "", first_name.lower().strip())
    last = re.sub(r"[^a-z]", "", last_name.lower().strip())
    domain = domain.lower().strip()

    if not first or not domain:
        return []

    permutations = []

    patterns = [
        (f"{first}@{domain}", "first@domain", 0.4),
        (f"{first}.{last}@{domain}", "first.last@domain", 0.5) if last else None,
        (f"{first}{last}@{domain}", "firstlast@domain", 0.3) if last else None,
        (f"{first[0]}{last}@{domain}", "flast@domain", 0.35) if last else None,
        (f"{first}{last[0]}@{domain}", "firstl@domain", 0.3) if last else None,
        (f"{first}_{last}@{domain}", "first_last@domain", 0.25) if last else None,
    ]

    for p in patterns:
        if p is None:
            continue
        address, pattern, confidence = p
        permutations.append({
            "address": address,
            "pattern": pattern,
            "confidence": confidence,
            "mx_valid": None,
            "unverified_guess": True,
        })

    log.info(
        "email_permutations_generated",
        first=first,
        last=last,
        domain=domain,
        count=len(permutations),
    )
    return permutations


# ---------------------------------------------------------------------------
# MX record check (does the domain accept email?)
# ---------------------------------------------------------------------------

async def check_mx_record(domain: str) -> Optional[bool]:
    """Check if a domain has MX records (can receive email).

    Returns True if MX found, False if not, None on error.
    """
    import asyncio

    def _check():
        try:
            import dns.resolver

            answers = dns.resolver.resolve(domain, "MX")
            return len(list(answers)) > 0
        except dns.resolver.NoAnswer:
            return False
        except dns.resolver.NXDOMAIN:
            return False
        except Exception as exc:
            log.warning("mx_check_error", domain=domain, error=str(exc))
            return None

    return await asyncio.to_thread(_check)


async def enrich_with_mx(permutations: list[dict]) -> list[dict]:
    """Add MX validation to email permutations.

    All emails for the same domain share one MX check.
    """
    if not permutations:
        return permutations

    # Extract unique domains
    domains = set()
    for p in permutations:
        addr = p.get("address", "")
        if "@" in addr:
            domains.add(addr.split("@")[1])

    # Check MX for each domain
    mx_results = {}
    for domain in domains:
        mx_results[domain] = await check_mx_record(domain)

    # Apply results
    for p in permutations:
        addr = p.get("address", "")
        if "@" in addr:
            domain = addr.split("@")[1]
            p["mx_valid"] = mx_results.get(domain)

    return permutations


# ---------------------------------------------------------------------------
# Mailto URI creation and handoff
# ---------------------------------------------------------------------------

def create_mailto_uri(to: str, subject: str = "", body: str = "") -> str:
    """Create a properly encoded mailto: URI.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body text.

    Returns: Encoded mailto: URI string.
    """
    params = {}
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body

    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    uri = f"mailto:{urllib.parse.quote(to)}"
    if query:
        uri += f"?{query}"
    return uri


def open_mail_client(mailto_uri: str) -> bool:
    """Open the user's default mail client with the mailto URI.

    Returns True if the command succeeded, False otherwise.
    Zero credential handling — user clicks "Send" themselves.
    """
    try:
        webbrowser.open(mailto_uri)
        log.info("mail_client_opened", uri_length=len(mailto_uri))
        return True
    except Exception as exc:
        log.error("mail_client_error", error=str(exc))
        return False
