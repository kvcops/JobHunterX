"""
How old is the website a posting sends you to?

Fake job sites are usually registered days or weeks before the scam starts. The registration date comes from RDAP —
the public, keyless successor of WHOIS run by the domain registries (rdap.org redirects each query to the right
registry, .in included). Only the posting's own apply link and the company email it asks applications to go to are
checked; known job boards, ATS platforms and big mail / social sites are skipped. Results are cached for 30 days.

The age is stored on the posting as the `domain_age` validation check, and the scam rules read it from there.
A young domain alone is a caution, not proof: genuine new startups have new domains too.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.job import FieldCheck, JobPosting

log = get_logger("domain_age")

RDAP = "https://rdap.org/domain/{domain}"
CACHE_S = 30 * 86400
TIMEOUT_S = 8
_MULTI = {"co.in", "net.in", "org.in", "firm.in", "gen.in", "ind.in", "ac.in", "edu.in", "res.in", "gov.in", "nic.in",
          "co.uk", "org.uk", "ac.uk", "com.au", "net.au", "co.nz", "com.sg", "com.br", "co.jp", "com.cn", "co.za", "com.my"}
# platforms whose age says nothing about the employer behind the posting
_SKIP = ("greenhouse.io", "lever.co", "ashbyhq.com", "smartrecruiters.com", "workable.com", "recruitee.com",
         "myworkdayjobs.com", "workday.com", "keka.com", "oraclecloud.com", "darwinbox.in", "darwinbox.com", "zohorecruit",
         "zoho.com", "zoho.in", "freshteam.com", "successfactors", "taleo.net", "icims.com", "jobvite.com", "bamboohr.com",
         "breezy.hr", "pyjamahr.com", "turbohire.co", "superset.com", "linkedin.com", "naukri.com", "indeed.com", "indeed.co.in",
         "instahyre.com", "cutshort.io", "wellfound.com", "workatastartup.com", "ycombinator.com", "foundit.in", "iimjobs.com",
         "hirist.tech", "hirist.com", "internshala.com", "glassdoor", "google.com", "gmail.com", "outlook.com", "yahoo.com",
         "hotmail.com", "rediffmail.com", "proton.me", "protonmail.com", "x.com", "twitter.com", "reddit.com", "github.com",
         "notion.site", "notion.so", "forms.gle", "bit.ly", "tinyurl.com", "t.me", "wa.me", "whatsapp.com", "apple.com",
         "microsoft.com", "amazon.com", "news.ycombinator.com", "adzuna.in", "adzuna.com")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


def registrable(host: str) -> str:
    """careers.acme.co.in → acme.co.in"""
    h = (host or "").lower().strip(".")
    h = h[4:] if h.startswith("www.") else h
    parts = h.split(".")
    if len(parts) < 2 or re.fullmatch(r"[\d.]+", h):
        return ""
    n = 3 if ".".join(parts[-2:]) in _MULTI else 2
    return ".".join(parts[-n:]) if len(parts) >= n else ""


def _skipped(domain: str) -> bool:
    return not domain or any(domain == s or domain.endswith("." + s) if "." in s else s in domain for s in _SKIP)


def domains_of(job: JobPosting) -> list[str]:
    """The employer-controlled domains this posting points applicants to."""
    from jobhunterx.intelligence.reach import application_email
    out = []
    host = urlparse(job.apply_url or "").hostname or ""
    if job.ats is None:
        out.append(registrable(host))
    email = application_email(job)
    if email:
        m = _EMAIL.match(email)
        if m:
            out.append(registrable(m.group(1)))
    return [d for d in dict.fromkeys(out) if not _skipped(d)]


def registered_on(rdap: dict) -> Optional[datetime]:
    for e in (rdap or {}).get("events") or []:
        if (e.get("eventAction") or "").lower() == "registration" and e.get("eventDate"):
            try:
                d = datetime.fromisoformat(e["eventDate"].replace("Z", "+00:00"))
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
    return None


_store = None


def _cache():
    global _store
    if _store is None:
        from jobhunterx.config import capacity
        from jobhunterx.config.settings import get_settings
        _store = capacity.disk_cache(get_settings().cache_full_path / "domain_age", 8)
    return _store


async def lookup(domain: str) -> Optional[datetime]:
    """Registration date of a domain, or None when the registry doesn't say (cached either way)."""
    from jobhunterx.discovery import job_apis
    try:
        hit = _cache().get(domain)
    except Exception:
        hit = None
    if hit and time.time() - hit["at"] < CACHE_S:
        return datetime.fromisoformat(hit["date"]) if hit["date"] else None
    try:
        data = await asyncio.wait_for(job_apis.fetch_json(RDAP.format(domain=domain),
                                                          headers={"Accept": "application/rdap+json, application/json"}), TIMEOUT_S)
    except asyncio.TimeoutError:
        return None                     # not cached: try again next time
    if data is None:
        return None
    when = registered_on(data)
    try:
        _cache().set(domain, {"at": time.time(), "date": when.isoformat() if when else ""})
    except Exception:
        pass
    return when


async def annotate(job: JobPosting, now: Optional[datetime] = None) -> Optional[int]:
    """Look up the youngest employer domain of this posting and record it as the `domain_age` check. Returns its age in days."""
    from jobhunterx.config.settings import get_settings
    if not getattr(get_settings(), "enable_domain_age_check", True):
        return None
    now = now or datetime.now(timezone.utc)
    domains = domains_of(job)
    if not domains:
        return None
    dates = await asyncio.gather(*(lookup(d) for d in domains), return_exceptions=True)
    known = [(d, w) for d, w in zip(domains, dates) if isinstance(w, datetime)]
    if not known:
        return None
    domain, when = max(known, key=lambda x: x[1])
    days = max(0, (now - when).days)
    job.validation.checks["domain_age"] = FieldCheck(
        status="verified", value=str(days),
        evidence=f"{domain} was registered on {when.date().isoformat()} (public domain registry, RDAP)")
    return days
