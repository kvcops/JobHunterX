"""
Stage 6 — Deduplication across sources.

Signals, strongest first:
  1. Same ATS posting (kind, board, job id).
  2. Same canonical URL.
  3. Same fingerprint: company + title words + primary location.
  4. Near-identical description (word-shingle Jaccard) at the same company.

When duplicates merge, the record from the most trustworthy source
(first-party ATS > first-party career page > job board > search result)
wins, and every source is kept on the merged posting.
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from jobhunterx.domain.candidate import norm_term
from jobhunterx.domain.job import JobPosting
from jobhunterx.intelligence.text import tokens

SHINGLE = 5
NEAR_DUP = 0.8


def canonical_url(url: str) -> str:
    """Lowercase host, drop fragment/trailing slash; keep only query params that look like identifiers."""
    if not url:
        return ""
    p = urlparse(url.strip())
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    keep = [(k, v) for k, v in parse_qsl(p.query) if re.search(r"\d", v) and len(v) <= 64 and not k.lower().startswith("utm")]
    return urlunparse(("https", host, p.path.rstrip("/"), "", urlencode(sorted(keep)), ""))


def fingerprint(job: JobPosting) -> str:
    company = norm_term(job.company)
    title = " ".join(sorted(set(tokens(job.title))))
    place = norm_term((job.locations or [job.location_raw or ""])[0])
    return hashlib.sha1(f"{company}|{title}|{place}".encode()).hexdigest()[:20]


def ats_key(job: JobPosting) -> str:
    if job.ats and job.ats.job_id:
        return f"{job.ats.kind}:{job.ats.token.lower()}:{job.ats.job_id}"
    return ""


def _shingles(text: str) -> set[int]:
    words = tokens(text)[:1500]
    return {hash(" ".join(words[i:i + SHINGLE])) for i in range(max(0, len(words) - SHINGLE + 1))}


def _trust(job: JobPosting) -> tuple:
    src = job.primary_source
    rank = {"ats_api": 4, "career_page": 3, "job_board": 2, "aggregator": 1, "search_result": 0}
    return (bool(src and src.first_party), rank.get(src.kind, 0) if src else 0, src.confidence if src else 0,
            len(job.description))


def merge(primary: JobPosting, other: JobPosting) -> JobPosting:
    """Keep `primary`'s data, add `other`'s sources and fill gaps."""
    urls = {s.url for s in primary.sources}
    for s in other.sources:
        if s.url not in urls:
            primary.sources.append(s)
            urls.add(s.url)
    for field in ("company", "location_raw", "employment_type", "department", "apply_url", "company_domain"):
        if not getattr(primary, field) and getattr(other, field):
            setattr(primary, field, getattr(other, field))
    for field in ("salary", "posted_at", "valid_through", "ats"):
        if getattr(primary, field) is None and getattr(other, field) is not None:
            setattr(primary, field, getattr(other, field))
    if len(other.description) > len(primary.description) * 1.5 and not (primary.ats and primary.description):
        primary.description = other.description
    for k, v in other.validation.checks.items():
        primary.validation.checks.setdefault(k, v)
    return primary


def deduplicate(jobs: Iterable[JobPosting]) -> tuple[list[JobPosting], int]:
    """Return (unique jobs, number of duplicates merged)."""
    ordered = sorted(jobs, key=_trust, reverse=True)
    kept: list[JobPosting] = []
    by_key: dict[str, JobPosting] = {}
    shingles: list[tuple[set[int], JobPosting]] = []
    dups = 0
    for job in ordered:
        job.canonical_url = canonical_url(job.canonical_url or job.apply_url)
        job.fingerprint = fingerprint(job)
        keys = [k for k in (ats_key(job), "u:" + job.canonical_url if job.canonical_url else "",
                            "f:" + job.fingerprint if job.company and job.title else "") if k]
        target = next((by_key[k] for k in keys if k in by_key), None)
        sh = _shingles(job.description) if not target and job.description else set()
        if target is None and sh:
            for other_sh, other in shingles:
                same_company = not job.company or not other.company or norm_term(job.company) == norm_term(other.company)
                if same_company and other_sh:
                    inter = len(sh & other_sh)
                    if inter and inter / len(sh | other_sh) >= NEAR_DUP:
                        target = other
                        break
        if target is not None:
            merge(target, job)
            for k in keys:
                by_key.setdefault(k, target)
            dups += 1
            continue
        kept.append(job)
        for k in keys:
            by_key[k] = job
        if sh:
            shingles.append((sh, job))
    return kept, dups
