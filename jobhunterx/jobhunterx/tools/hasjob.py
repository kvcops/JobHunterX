"""
JobHunterX — Hasjob feed client (automatic Indian-startup job stream)

Hasjob (hasjob.co) is an India-focused job board for startups and tech
companies — no recruiters, no placement agencies, no mass-applicant firms.
Its public ATOM feed (https://www.hasjob.co/feed) is unauthenticated and
works reliably, giving us automatic discovery of startups the seed list
doesn't cover: title, company, location, description, apply page.
"""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

from jobhunterx.config.logging import get_logger

log = get_logger("hasjob")

FEED_URL = "https://www.hasjob.co/feed"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _clean_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_feed(xml_text: str) -> list[dict]:
    """Parse the ATOM feed into job dicts:
    {title, company, website, location, jd_text, apply_url, posted_at}
    """
    jobs = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("hasjob_feed_parse_error", error=str(exc)[:120])
        return jobs

    for entry in root.findall("a:entry", _ATOM_NS):
        title = (entry.findtext("a:title", "", _ATOM_NS) or "").strip()
        apply_url = (entry.findtext("a:id", "", _ATOM_NS) or "").strip()
        link_el = entry.find("a:link", _ATOM_NS)
        if link_el is not None and apply_url == "":
            apply_url = link_el.get("href", "")
        location = (entry.findtext("a:location", "", _ATOM_NS) or "").strip()
        published = (entry.findtext("a:published", "", _ATOM_NS) or "").strip()
        content_html = (entry.findtext("a:content", "", _ATOM_NS) or "")

        # Company name + website come from the first <strong><a href="..">..</a></strong>
        company = ""
        website = ""
        m = re.search(r'<strong>\s*<a href="([^"]+)">([^<]+)</a>', content_html)
        if m:
            website, company = m.group(1).strip(), m.group(2).strip()
        if not company:
            m = re.search(r'<a href="[^"]+">([^<]+)</a>', content_html)
            if m:
                company = m.group(1).strip()

        if not company or not apply_url:
            continue

        jobs.append({
            "title": title,
            "company": company,
            "website": website,
            "location": location,
            "jd_text": _clean_html(content_html),
            "apply_url": apply_url,
            "posted_at": published,
            "source": "hasjob",
        })
    return jobs


async def fetch_feed(timeout: float = 20.0) -> list[dict]:
    """Fetch and parse the Hasjob feed. Returns [] on any failure."""
    def _fetch() -> Optional[str]:
        try:
            from curl_cffi import requests as cffi
            resp = cffi.get(FEED_URL, impersonate="chrome", timeout=timeout)
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception as exc:
            log.debug("hasjob_curl_failed", error=str(exc)[:100])
        try:
            import httpx
            with httpx.Client(timeout=timeout, headers={"User-Agent": _UA}) as client:
                resp = client.get(FEED_URL)
                if resp.status_code == 200:
                    return resp.text
        except Exception as exc:
            log.debug("hasjob_httpx_failed", error=str(exc)[:100])
        return None

    try:
        xml_text = await asyncio.to_thread(_fetch)
    except Exception:
        return []
    if not xml_text:
        return []
    jobs = _parse_feed(xml_text)
    log.info("hasjob_feed_fetched", count=len(jobs))
    return jobs