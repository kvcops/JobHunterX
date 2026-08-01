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


def generate_email_permutations_with_pattern(
    first_name: str, last_name: str, domain: str, pattern: str
) -> list[dict]:
    """Generate email addresses from a REAL, API-reported email pattern.

    Unlike plain permutations (blind guessing), this uses the company's
    actual email format (e.g. Hunter.io Domain Search reports
    '{first}.{last}@acme.com'). The result is still labelled
    `unverified_guess: True` — the pattern is real, but the specific
    mailbox still needs verification before use.
    """
    first = re.sub(r"[^a-z]", "", first_name.lower().strip())
    last = re.sub(r"[^a-z]", "", last_name.lower().strip())
    domain = domain.lower().strip()

    if not first or not domain or not pattern or "{" not in pattern:
        return []

    def _tokens(addr: str) -> str:
        return (
            addr.replace("{first}", first)
            .replace("{last}", last)
            .replace("{f}", first[:1])
            .replace("{l}", last[:1] if last else "")
        )

    address = _tokens(pattern).lower().strip()
    if not address or "@" not in address:
        return []

    log.info(
        "email_pattern_permutation_generated",
        first=first,
        last=last,
        domain=domain,
        pattern=pattern,
    )
    return [{
        "address": address,
        "pattern": "permutation",
        "confidence": 0.55,
        "mx_valid": None,
        "unverified_guess": True,
        "pattern_informed": True,
    }]


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
    """Add MX + SMTP validation to email permutations.

    All emails for the same domain share one MX check.
    Top candidates get SMTP verification.
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

    # SMTP verify top 3 candidates (if MX valid)
    top_candidates = [p for p in permutations if p.get("mx_valid") is True][:3]
    if top_candidates:
        verified = await verify_emails_with_smtp(top_candidates)
        # Update the original list with SMTP results
        verified_map = {v["address"]: v for v in verified}
        for i, p in enumerate(permutations):
            if p["address"] in verified_map:
                permutations[i] = verified_map[p["address"]]

    return permutations


# ---------------------------------------------------------------------------
# SMTP Email Verification (deeper than MX check)
# ---------------------------------------------------------------------------

def _get_mx_host(domain: str) -> Optional[str]:
    """Resolve the domain's primary MX host (or None)."""
    import dns.resolver

    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        return str(mx_records[0].exchange).rstrip(".")
    except Exception:
        return None


def _smtp_rcpt_check(mx_host: str, rcpt: str, timeout: int) -> Optional[int]:
    """Run RCPT TO against the MX host and return the response code.

    Uses the machine's real FQDN for EHLO (many servers reject bare
    'verify.local'), falls back from port 25 to 587 with STARTTLS.
    Never sends DATA. Returns the SMTP response code or None on failure.
    """
    import smtplib
    import socket

    helo = socket.gethostname() or "verify.local"
    for port in (25, 587):
        try:
            with smtplib.SMTP(mx_host, port, timeout=timeout) as smtp:
                try:
                    smtp.ehlo(helo)
                except smtplib.SMTPHeloError:
                    smtp.helo(helo)
                if port == 587:
                    try:
                        smtp.starttls()
                    except Exception:
                        pass
                smtp.mail(f"verify@{helo}")
                code, _ = smtp.rcpt(rcpt)
                return code
        except Exception:
            continue
    return None


def _provider_risk(mx_host: str) -> str:
    """Classify the mail provider by MX host.

    2026 reality: Gmail answers 250 to every RCPT (existence checks broken),
    M365 bounces asynchronously (50-70% unverifiable), Yahoo/AOL answer
    250/252. Zoho (incl. India) still returns honest 550s.
    """
    mx = (mx_host or "").lower()
    if "google" in mx or mx.endswith(".google.com"):
        return "gmail"
    if "outlook" in mx or "protection.outlook.com" in mx:
        return "m365"
    if "yahoo" in mx or "aol" in mx:
        return "yahoo"
    if "zoho" in mx:
        return "zoho"
    return "unknown"


async def verify_email_smtp(email: str, timeout: int = 10) -> bool:
    """Verify if an email exists via SMTP handshake (no email sent).

    Opens a TCP connection to the mail server, runs EHLO → MAIL FROM →
    RCPT TO, reads the response code, then QUIT. Never sends DATA.

    Returns True if the server responds with 250 (mailbox exists).
    NOTE: for Gmail/M365 (which answer 250 to everything) this result is
    meaningless — use verify_emails_with_smtp for provider-aware grading.
    """
    import asyncio

    if not email or "@" not in email:
        return False

    domain = email.split("@")[1]

    def _verify():
        mx_host = _get_mx_host(domain)
        if not mx_host:
            return False
        code = _smtp_rcpt_check(mx_host, email, timeout)
        return code is not None and code == 250

    return await asyncio.to_thread(_verify)


async def detect_catch_all(domain: str) -> bool:
    """Detect if a domain is catch-all (accepts any email).

    Tests with a random non-existent address. If the server accepts it,
    the domain is catch-all and SMTP verification is unreliable.
    """
    import asyncio
    import random
    import string

    def _check():
        random_email = "".join(random.choices(string.ascii_lowercase, k=12))
        test_email = f"{random_email}@{domain}"
        mx_host = _get_mx_host(domain)
        if not mx_host:
            return False
        code = _smtp_rcpt_check(mx_host, test_email, 10)
        return code is not None and code == 250

    return await asyncio.to_thread(_check)


async def verify_emails_with_smtp(emails: list[dict]) -> list[dict]:
    """Verify a list of email guesses using SMTP, marking catch-all domains
    and providers whose answers can't be trusted (Gmail/M365/Yahoo).

    Provider-aware grading:
    - Zoho / unknown providers: honest 250/550 → result is meaningful.
    - Gmail/M365/Yahoo: 250 is unreliable (or async bounce) → smtp_valid is
      set to None and provider_risky=True instead of a false positive.
    """
    if not emails:
        return emails

    # Resolve MX hosts once per domain
    mx_hosts: dict[str, Optional[str]] = {}
    for e in emails:
        addr = e.get("address", "")
        if "@" in addr:
            domain = addr.split("@")[1]
            if domain not in mx_hosts:
                mx_hosts[domain] = _get_mx_host(domain)

    import asyncio
    import random
    import string

    async def _verify_one(addr: str, mx_host: str) -> Optional[int]:
        return await asyncio.to_thread(_smtp_rcpt_check, mx_host, addr, 10)

    # Detect catch-all domains
    catch_all_domains = set()
    for domain, mx_host in mx_hosts.items():
        if not mx_host:
            continue
        test_email = f"{''.join(random.choices(string.ascii_lowercase, k=12))}@{domain}"
        code = await _verify_one(test_email, mx_host)
        if code == 250:
            catch_all_domains.add(domain)

    # Verify each email
    for e in emails:
        addr = e.get("address", "")
        if "@" not in addr:
            continue

        domain = addr.split("@")[1]
        mx_host = mx_hosts.get(domain)
        provider = _provider_risk(mx_host) if mx_host else "unknown"
        e["smtp_provider"] = provider

        if domain in catch_all_domains:
            e["smtp_valid"] = None
            e["catch_all"] = True
            e["provider_risky"] = True
            e["confidence"] = max(0.1, e.get("confidence", 0) - 0.2)
            continue

        code = await _verify_one(addr, mx_host) if mx_host else None
        e["catch_all"] = False
        if provider in ("gmail", "m365", "yahoo"):
            # These providers defeat SMTP existence checks — never claim a
            # positive. A 550 still tells us the mailbox is invalid.
            e["provider_risky"] = True
            if code == 550:
                e["smtp_valid"] = False
                e["confidence"] = max(0.05, e.get("confidence", 0) - 0.3)
            else:
                e["smtp_valid"] = None
        else:
            e["provider_risky"] = False
            e["smtp_valid"] = code == 250 if code is not None else None
            if e.get("smtp_valid") is True:
                e["confidence"] = min(1.0, e.get("confidence", 0) + 0.3)

    # Sort by confidence (best first)
    emails.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return emails


# ---------------------------------------------------------------------------
# Mailto URI creation and handoff
# ---------------------------------------------------------------------------

def create_mailto_uri(to: str, subject: str = "", body: str = "") -> str:
    """Create a properly encoded mailto: URI."""
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


def create_gmail_compose_url(to: str, subject: str = "", body: str = "") -> str:
    """Create a web Gmail compose URL that opens directly in a new tab."""
    params = {"view": "cm", "fs": "1", "to": to}
    if subject:
        params["su"] = subject
    if body:
        params["body"] = body

    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"https://mail.google.com/mail/?{query}"


def open_mail_client(mailto_uri: str) -> bool:
    """Open the user's default mail client with the mailto URI."""
    try:
        webbrowser.open(mailto_uri)
        log.info("mail_client_opened", uri_length=len(mailto_uri))
        return True
    except Exception as exc:
        log.error("mail_client_error", error=str(exc))
        return False

