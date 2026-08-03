"""
Vellum OS — Hacker News "Who's Hiring" feed client (free, unauthenticated)

HN posts a "Who's Hiring?" thread on the first weekday of every month.
Companies reply with structured-ish postings: "Company | Role | Location |
Remote | Link | Note". Two free JSON APIs expose it:

  1. Algolia search API — find the latest thread story id.
  2. Firebase Realtime DB API — fetch top-level comments (one per company).

No API key, no auth, no rate-limit drama. Gives a second live discovery
source alongside the hasjob feed (global + remote heavy).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("hn_hiring")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_MAX_COMMENTS = 120          # cap thread depth per run (1 comment = 1 company)
_COMMENT_CONCURRENCY = 6     # parallel comment fetches


# ---------------------------------------------------------------------------
# Low-level JSON fetch (httpx, with curl_cffi fallback)
# ---------------------------------------------------------------------------

def _json_get(url: str, timeout: float = 20.0) -> Optional[dict]:
    try:
        import httpx
        with httpx.Client(timeout=timeout, headers={"User-Agent": _UA},
                          follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        log.debug("hn_httpx_failed", error=str(exc)[:100])
    try:
        from curl_cffi import requests as cffi
        resp = cffi.get(url, impersonate="chrome", timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        log.debug("hn_curl_failed", error=str(exc)[:100])
    return None


# ---------------------------------------------------------------------------
# Thread lookup
# ---------------------------------------------------------------------------

def _find_latest_thread() -> Optional[dict]:
    """Latest 'Who Is Hiring' story via Algolia. Returns {id, title}."""
    url = ("https://hn.algolia.com/api/v1/search_by_date?tags=story&query="
           "%22Who%20is%20hiring%22&hitsPerPage=5")
    data = _json_get(url)
    if not data:
        return None
    for hit in data.get("hits", []):
        title = (hit.get("title") or "")
        if "who" in title.lower() and "hiring" in title.lower():
            return {"id": hit.get("objectID"), "title": title}
    return None


# ---------------------------------------------------------------------------
# Comment parsing → jobs
# ---------------------------------------------------------------------------

def _split_header(line: str):
    """Best-effort parse of 'Company | Role | Location | ...' header lines."""
    parts = [p.strip() for p in line.split("|")]
    return parts


def _clean_part(raw: str) -> str:
    """Strip HTML tags + unescape entities + collapse whitespace."""
    import html as html_mod
    s = re.sub(r"<[^>]+>", " ", raw or "")
    s = html_mod.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _role_looks_ok(role: str) -> bool:
    """Reject roles that are actually salaries, URLs or locations."""
    r = role.strip()
    if not r or len(r) < 2:
        return False
    if r.lower().startswith("http") or ".com" in r.lower() or r.endswith(".co"):
        return False
    if re.match(r"^\$?[\d,.]+[kK]?\+?", r):          # "150-250k+"
        return False
    if re.match(r"^\d+(\.\d+)?\s*[-–]\s*\d+", r):    # "80-120"
        return False
    if re.search(r",\s*(US|CA|UK|IN|EU|DE|NL|SG|AE|JP|ON|NY|TX|WA|OR|MA|MN|MD)\b", r, re.I):
        return False
    return True


def _parse_comment(comment_text: str) -> list[dict]:
    """One company comment → list of job dicts.

    HN format is free-form text. We do a forgiving parse:
      - first non-empty line with pipes = header: [company, role, location...]
      - if the header has only 1 part, treat it as company
      - any '|' separated lines under it with >= 2 parts become extra roles
    """
    lines = [_clean_part(ln) for ln in (comment_text or "").splitlines() if ln.strip()]
    if not lines:
        return []

    jobs: list[dict] = []
    company = ""
    for ln in lines:
        if ln.startswith(">") or ln.startswith("http") or "&#x" in ln:
            continue
        parts = _split_header(ln)
        if len(parts) >= 2:
            first, second = parts[0], parts[1]
            if not company and first:
                company = first
            # second part should look like a role, not a location/sentence
            if not second or len(second) < 2 or second.isdigit():
                continue
            if second == first:
                continue
            if not _role_looks_ok(second):
                continue
            role = second
            location = parts[2] if len(parts) > 2 else ""
            jobs.append({
                "company": first or company,
                "role": role,
                "location": location,
                "note": " | ".join(parts[3:]),
                "jd_text": comment_text[:4000],
            })
    if not jobs and company:
        # Single line like "Company – Senior Dev (Remote)" (no pipes)
        fallback_role = lines[0]
        if "|" not in fallback_role and _role_looks_ok(fallback_role):
            jobs.append({
                "company": company,
                "role": fallback_role,
                "location": "Anywhere" if "remote" in fallback_role.lower() else "",
                "note": "",
                "jd_text": comment_text[:4000],
            })
    return jobs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_hiring_posts(
    max_comments: int = _MAX_COMMENTS,
    timeout: float = 20.0,
) -> list[dict]:
    """Fetch the latest 'Who's Hiring' thread → list of job dicts.

    Each dict: {company, role, location, jd_text, apply_url, posted_at, source}.
    apply_url is the HN comment link when no explicit URL is present.
    """
    thread = await asyncio.to_thread(_find_latest_thread)
    if not thread:
        log.warning("hn_thread_not_found")
        return []

    story_url = f"https://hacker-news.firebaseio.com/v0/item/{thread['id']}.json"
    story = await asyncio.to_thread(_json_get, story_url)
    kids = (story or {}).get("kids") or []
    if not kids:
        log.warning("hn_thread_empty", thread_id=thread["id"])
        return []
    kids = kids[:max_comments]

    async def fetch_one(item_id: int) -> Optional[dict]:
        data = await asyncio.to_thread(
            _json_get, f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        )
        return data

    sem = asyncio.Semaphore(_COMMENT_CONCURRENCY)

    async def fetch_limited(item_id: int):
        async with sem:
            return await fetch_one(item_id)

    comments = await asyncio.gather(*(fetch_limited(k) for k in kids))
    comments = [c for c in comments if c and c.get("text")]

    jobs: list[dict] = []
    for c in comments:
        comment_jobs = _parse_comment(c["text"])
        for j in comment_jobs:
            if not j["company"] or not j["role"]:
                continue
            j["apply_url"] = f"https://news.ycombinator.com/item?id={c['id']}"
            j["posted_at"] = ""
            j["source"] = "hn"
            j["hn_thread"] = thread["title"]
            jobs.append(j)

    log.info("hn_hiring_fetched", thread=thread["title"],
             comments=len(comments), jobs=len(jobs))
    return jobs