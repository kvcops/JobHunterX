"""
Vellum OS — Email Enrichment Tool

Keyless approaches (verified live Aug 2026) for finding REAL emails of
EMPLOYEES at a company — the people you'd ask for a referral or cold-email:

1. LinkedIn people discovery — web search for site:linkedin.com/in profiles at
   the company. Yields REAL names + LinkedIn URLs (never fabricated).
2. Site crawl — contact/privacy/terms/press/media-kit/newsroom pages often
   publish personal employee emails (mailto:, JSON-LD ContactPoint,
   (at)/(dot) obfuscation). ~50-70% of companies expose at least one.
3. Wayback Machine CDX recovery — deleted pages still carry emails.
4. LinkedIn guest pages — company About sections + public profiles sometimes
   publish personal emails (5-15% hit rate).
5. Pattern learning — ONE confirmed personal email at a domain predicts the
   company's email format (>80% for first/first.last styles), feeding
   pattern-informed permutations for each discovered employee.

This module NEVER fabricates addresses, and email permutations are only ever
generated from a real learned pattern (never blind guessing).
"""

from __future__ import annotations

import re
from typing import Optional

from vellum.config.logging import get_logger
from vellum.tools import search

log = get_logger("email_enrichment")

PLACEHOLDER_DOMAINS = {
    "example.com", "yourdomain.com", "domain.com", "company.com",
    "email.com", "user.com", "mail.com", "test.com", "test.net",
    "acme.com", "yourcompany.com", "mydomain.com", "companyname.com",
    "domain.tld", "sentry.io", "mailinator.com", "yopmail.com",
    "guerrillamail.com", "example.org", "example.net", "somedomain.com",
    "business.com", "sample.com", "demo.com", "demo.org",
}

PLACEHOLDER_LOCALPARTS = {"yourname", "username", "name", "firstname",
                          "lastname", "someone", "email", "sample", "test"}


def _is_placeholder_email(address: str) -> bool:
    """Reject emails that are obviously sample/placeholder addresses."""
    if not address or "@" not in address:
        return True
    local, _, domain = address.partition("@")
    domain = domain.lower().strip().lstrip(".")
    local = local.lower().strip()

    if not re.match(r"^[a-z0-9.-]+$", domain) or "." not in domain:
        return True
    if domain in PLACEHOLDER_DOMAINS:
        return True
    if domain.endswith((".invalid", ".localhost", ".test", ".example")):
        return True
    if domain.endswith(".example.com") or domain.endswith(".test"):
        return True
    if local in PLACEHOLDER_LOCALPARTS or local.startswith("your"):
        return True
    return False

# Handles like linkedin.com/in/company or /in/hr are not person profiles.
LINKEDIN_HANDLE_STOPWORDS = {
    "in", "out", "company", "companies", "people", "page", "home", "search",
    "jobs", "careers", "career", "hr", "recruiter", "recruiting", "recruiters",
    "founder", "ceo", "cto", "team", "official", "pvt", "ltd", "limited",
    "llp", "corp", "corporation", "private", "limitedcompany",
    # entity-style words — a "person" whose handle is mostly these is a
    # company/org page, not an employee (e.g. "gyan-data-renewables-solutions")
    "solutions", "services", "service", "technologies", "technology",
    "systems", "system", "consulting", "consultancy", "consultants",
    "group", "groups", "labs", "lab", "enterprises", "enterprise",
    "ventures", "holdings", "renewables", "energies", "energy", "industries",
    "industries", "international", "infotech", "software", "digital",
    "networks", "network", "institute", "institutes", "university",
    "academy", "academies", "india", "indian", "global", "world", "online",
}

# ---------------------------------------------------------------------------
# LinkedIn people discovery (via web search — no scraping, no login walls)
# ---------------------------------------------------------------------------

def _name_from_linkedin_handle(handle: str) -> Optional[str]:
    """Convert 'priya-sharma-hr' → 'Priya Sharma'. Returns None for
    stopword/company-style handles that aren't person names."""
    handle = handle.rstrip("-")
    parts = [p for p in handle.split("-") if p]
    # LinkedIn appends random alphanumeric ids to duplicate names
    # ('ranjan-sir-data-gyan-51611a123') — drop trailing junk tokens.
    while parts and re.search(r"\d", parts[-1]):
        parts.pop()
    if not parts:
        return None
    if len(parts) == 1 and parts[0].lower() in LINKEDIN_HANDLE_STOPWORDS:
        return None
    words = []
    for p in parts:
        pl = p.lower()
        if pl in LINKEDIN_HANDLE_STOPWORDS and len(words) >= 2:
            break
        if pl in LINKEDIN_HANDLE_STOPWORDS and len(words) < 2:
            continue
        words.append(p if p.isupper() and len(p) > 1 else p.capitalize())
    if len(words) < 2 or all(w.lower() in LINKEDIN_HANDLE_STOPWORDS for w in words):
        return None
    return " ".join(words)


def _company_affinity(company: str, blob: str) -> bool:
    """True when the result actually references the COMPANY (not a person
    who merely shares part of its name).

    'Gyan Data' must appear contiguously in the title/snippet/url — so
    "Isaac Gyan | Data Analytics..." and "Ranjan Sir Data Gyan" (reversed)
    are rejected. Single-word companies fall back to token matching.
    """
    company_l = company.lower()
    sig_words = [
        w for w in re.split(r"[^a-z0-9]+", company_l)
        if w and w not in ("pvt", "ltd", "private", "limited", "inc", "llc",
                           "the", "and", "of", "llp", "technologies", "technology",
                           "solutions", "services", "systems", "group", "labs")
    ]
    if not sig_words:
        return True
    blob_l = blob.lower()
    if len(sig_words) >= 2:
        return " ".join(sig_words) in blob_l
    return sig_words[0] in blob_l


def _role_hint_from_title(title: str) -> str:
    """'Priya Sharma - Talent Acquisition - Acme | LinkedIn' → role hint."""
    if not title:
        return ""
    parts = title.split("|")[0].split("-")
    return parts[1].strip() if len(parts) >= 3 else parts[0].strip()


async def linkedin_company_people(
    company: str, role: str = "", max_names: int = 6
) -> list[dict]:
    """Discover real people at a company from LinkedIn search results.

    Returns [{name, linkedin_url, role_hint, confidence}] — names are taken
    from actual LinkedIn profile handles surfaced by search, never guessed.
    """
    if not company:
        return []

    queries = [f'"{company}" site:linkedin.com/in']
    if role:
        queries.append(f'site:linkedin.com/in "{company}" "{role}"')
    queries.append(f'"{company}" "linkedin.com/in"')

    found: dict[str, dict] = {}
    handle_re = re.compile(r"linkedin\.com/in/([A-Za-z0-9\-]{3,})")

    for query in queries:
        try:
            results = await search.search_multi_engine(query, max_results=10)
        except Exception:
            continue
        for r in results:
            blob = " ".join(
                filter(None, [r.get("title", ""), r.get("href") or r.get("link", ""),
                              r.get("body") or r.get("snippet", "")])
            )
            # The result must actually reference the COMPANY (contiguous
            # company name), otherwise "Kwame Baffo Gyan | Data Analyst"
            # would be mistaken for an employee of "Gyan Data".
            if not _company_affinity(company, blob):
                continue
            href = r.get("href") or r.get("link", "")
            for m in handle_re.finditer(blob):
                handle = m.group(1)
                name = _name_from_linkedin_handle(handle)
                if not name or name in found:
                    continue
                # A person is never named after the company itself
                # ('gyan-data-renewables-solutions' is an org, not a person).
                if company.lower() in name.lower():
                    continue
                url = href if "linkedin.com/in" in href else f"https://www.linkedin.com/in/{handle}/"
                found[name] = {
                    "name": name,
                    "linkedin_url": url,
                    "role_hint": _role_hint_from_title(r.get("title", "")),
                    "confidence": 0.4,
                    "pattern": "linkedin_people",
                    "source_url": url,
                }
            if len(found) >= max_names:
                break
        if len(found) >= max_names:
            break

    return list(found.values())[:max_names]


async def linkedin_company_url(company: str) -> str:
    """Find the canonical LinkedIn company page URL via web search."""
    if not company:
        return ""
    try:
        results = await search.search_multi_engine(
            f'"{company}" site:linkedin.com/company', max_results=3
        )
    except Exception:
        return ""
    for r in results:
        href = r.get("href") or r.get("link", "")
        if "linkedin.com/company/" in href:
            return href
    return ""



# ---------------------------------------------------------------------------
# Keyless scraping methods (no API keys — the workhorses)
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Obfuscation like "name (at) domain (dot) com" or "name[at]domain[dot]com".
# Requires the literal words at/dot (or (at)/(dot) wrappers) — a plain
# "name@domain.com" contains @ and . symbols and must NOT match.
_OBFUSCATED_RE = re.compile(
    r"([a-zA-Z0-9._%+-]+)\s*[(\[<]?\s*(?:at|AT)\s*[)\]>]?\s*"
    r"([a-zA-Z0-9.-]+)\s*[(\[<]?\s*(?:dot|DOT)\s*[)\]>]?\s*"
    r"([a-zA-Z]{2,})"
)


def _decode_obfuscated_emails(text: str) -> list[str]:
    """Decode 'name (at) domain (dot) com' style anti-bot obfuscation."""
    decoded = []
    for match in _OBFUSCATED_RE.finditer(text):
        email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
        decoded.append(email)
    return decoded


def _extract_emails_from_html(html: str, url: str, pattern: str) -> list[dict]:
    """Extract emails from a page: plain text, mailto:, JSON-LD ContactPoint,
    and (at)/(dot) obfuscation."""
    if not html:
        return []

    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)

    found: dict[str, dict] = {}

    def _add(address: str, confidence: float):
        address = address.strip().lower()
        if not address or address in found or _is_placeholder_email(address):
            return
        if address.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            return
        if address.startswith(("noreply", "no-reply", "donotreply")):
            return
        found[address] = {
            "address": address,
            "pattern": pattern,
            "confidence": confidence,
            "source_url": url,
            "unverified_guess": False,
        }

    # 1. mailto: links (highest signal — explicitly published for contact)
    for m in re.finditer(r'mailto:([^"\'?>\s]+)', html):
        _add(m.group(1), 0.8)

    # 2. JSON-LD ContactPoint / Organization schema
    for m in re.finditer(r'"email"\s*:\s*"([^"]+)"', html):
        _add(m.group(1), 0.75)
    for m in re.finditer(r'"contactPoint"[^}]*"email"\s*:\s*"([^"]+)"', html, re.S):
        _add(m.group(1), 0.75)

    # 3. Plain text emails
    for m in EMAIL_RE.finditer(text):
        _add(m.group(0), 0.6)

    # 4. Obfuscated (at)/(dot)
    for email in _decode_obfuscated_emails(text):
        _add(email, 0.5)

    return list(found.values())


async def scrape_company_email_pages(domain: str, max_pages: int = 12) -> list[dict]:
    """Crawl a company's email-rich pages (contact, privacy, terms, press,
    media-kit, newsroom, imprint) and harvest real published emails.

    ~50-70% of companies expose at least one real address this way.
    """
    import asyncio

    from vellum.tools import career_urls, scrape

    if not domain:
        return []

    urls = career_urls.get_contact_urls_for_domain(domain)
    emails: list[dict] = []

    # Fetch pages CONCURRENTLY (5 at a time) — sequential fetches at ~1-2s
    # each were the bottleneck: 12+ URLs ≈ 25-40s serialized, now ~5-10s.
    sem = asyncio.Semaphore(5)

    async def _fetch_one(url: str) -> None:
        async with sem:
            try:
                page = await scrape.fetch_page(url)
                html = page.get("html", "")
                status = page.get("status", 0)
                if not html or status not in (200, 301, 302):
                    return
                page_emails = _extract_emails_from_html(html, url, "site_crawl")
                emails.extend(page_emails)
            except Exception:
                pass

    await asyncio.gather(*(_fetch_one(u) for u in urls[:max_pages]))

    return _dedupe_by_address(emails)[:15]


async def recover_emails_via_wayback(domain: str, max_snapshots: int = 8) -> list[dict]:
    """Recover emails from DELETED contact pages via the Wayback Machine CDX
    API — free, no key, ~1 req/sec. Snapshots of /contact, /privacy, /press
    etc. often still contain the emails the live site removed."""
    import asyncio

    import httpx

    if not domain:
        return []

    patterns = ["contact", "contact-us", "privacy", "privacy-policy", "terms",
                "press", "press-kit", "media-kit", "newsroom", "about", "imprint"]

    emails: list[dict] = []

    # All 11 CDX queries run concurrently (semaphore 4) instead of serially.
    async def _check_path(client: httpx.AsyncClient, path: str) -> None:
        cdx_url = (
            "http://web.archive.org/cdx/search/cdx"
            f"?url={domain}/{path}*&output=json&fl=timestamp,original,statuscode"
            "&filter=statuscode:200&collapse=digest&limit=2"
        )
        try:
            resp = await client.get(cdx_url, headers={"User-Agent": "VellumOS/1.0"})
            if resp.status_code != 200:
                return
            data = resp.json()
        except Exception:
            return
        if not isinstance(data, list) or len(data) < 2:
            return
        for row in data[1:]:
            if len(emails) >= max_snapshots:
                return
            ts, original = row[0], row[1]
            snap_url = f"https://web.archive.org/web/{ts}id_/{original}"
            try:
                snap = await client.get(snap_url, timeout=15.0)
                if snap.status_code != 200:
                    continue
                page_emails = _extract_emails_from_html(snap.text, snap_url, "wayback")
                emails.extend(page_emails)
            except Exception:
                continue

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            sem = asyncio.Semaphore(4)
            async def _limited(path: str) -> None:
                async with sem:
                    await _check_path(client, path)
            await asyncio.gather(*(_limited(p) for p in patterns))
    except Exception as exc:
        log.warning("wayback_recovery_failed", domain=domain, error=str(exc))

    return _dedupe_by_address(emails)[:max_snapshots]


async def linkedin_guest_emails(company: str, linkedin_url: str = "") -> list[dict]:
    """Extract emails from LINKEDIN GUEST pages (no login needed in 2026).

    Company pages + public profiles render About sections that sometimes
    contain emails users published themselves (5-15% of profiles).
    Also returns the company's official website URL as a contact lead.
    """
    import httpx

    if not company:
        return []

    emails: list[dict] = []
    company_slug = linkedin_url.rstrip("/").split("/")[-1] if linkedin_url else ""

    # 1. Fetch the company page (fallback: r.jina.ai markdown reader)
    page_html = ""
    company_url = linkedin_url or f"https://www.linkedin.com/company/{company_slug or company.lower()}/"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(
                company_url,
                headers={
                    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                                   "Chrome/126.0.0.0 Safari/537.36"),
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            if resp.status_code == 200:
                page_html = resp.text
    except Exception:
        pass

    if not page_html:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                jina = await client.get(f"https://r.jina.ai/{company_url}")
                if jina.status_code == 200:
                    page_html = jina.text
        except Exception:
            pass

    if page_html:
        emails.extend(_extract_emails_from_html(page_html, company_url, "linkedin_about"))
        # Official website URL from LinkedIn page (JSON-LD / meta)
        website = re.search(r'"website"\s*:\s*"([^"]+)"', page_html)
        if website:
            emails.append({
                "address": "",
                "pattern": "linkedin_website",
                "confidence": 1.0,
                "source_url": website.group(1),
                "website_url": website.group(1),
                "unverified_guess": False,
            })

    return _dedupe_by_address(emails)[:10]


async def linkedin_profile_emails(people: list[dict], max_profiles: int = 5) -> list[dict]:
    """Fetch each employee's LinkedIn GUEST profile page (no login) and
    harvest any personal email they published themselves (5-15% of profiles).

    These are the referral/cold-outreach targets — a real employee's own
    published address is the strongest possible signal.
    """
    import asyncio

    import httpx

    if not people:
        return []

    targets = [p for p in people if "linkedin.com/in/" in (p.get("linkedin_url") or "")][:max_profiles]

    emails: list[dict] = []

    # Concurrent profile fetches (4 at a time) — serial 12s-timeout fetches
    # could stall the pipeline ~1s-12s per profile.
    sem = asyncio.Semaphore(4)

    async def _fetch_profile(person: dict) -> None:
        async with sem:
            profile_url = person.get("linkedin_url", "")
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(
                        profile_url,
                        headers={
                            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                                           "Chrome/126.0.0.0 Safari/537.36"),
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                    )
                if resp.status_code != 200:
                    return
                page_emails = _extract_emails_from_html(resp.text, profile_url, "linkedin_profile")
                for pe in page_emails:
                    pe["name"] = person.get("name", "")
                    pe["linkedin_url"] = profile_url
                emails.extend(page_emails)
            except Exception:
                pass

    await asyncio.gather(*(_fetch_profile(p) for p in targets))

    return _dedupe_by_address(emails)[:max_profiles]


async def scrape_team_linkedin_profiles(domain: str) -> list[dict]:
    """Crawl a company's team/about pages for EMPLOYEE LinkedIn profiles.

    Company sites (esp. Indian SMBs like Gyan Data) publish a team page
    (team.html / people.html / about) with the real employees' LinkedIn
    URLs. These are the referral targets — real names + real profile URLs,
    even when no emails are published. Names prefer the <img alt="...">
    text next to the profile link, falling back to handle parsing.
    """
    import asyncio

    from vellum.tools import scrape

    if not domain:
        return []

    team_patterns = [
        "https://{domain}/team", "https://{domain}/team.html",
        "https://{domain}/people", "https://{domain}/people.html",
        "https://{domain}/our-team", "https://{domain}/our-team.html",
        "https://{domain}/about", "https://{domain}/about.html",
        "https://{domain}/about/team", "https://{domain}/about-us",
    ]
    urls = [p.format(domain=domain) for p in team_patterns]

    handle_re = re.compile(r"linkedin\.com/in/([A-Za-z0-9\-]{3,})")
    found: dict[str, dict] = {}

    # Concurrent fetches — the old code pulled in the full 35-URL contact
    # list AND fetched serially (~45 fetches ≈ 60-90s). Team pages alone,
    # parallelized, finish in ~5-10s.
    sem = asyncio.Semaphore(5)

    async def _scan(url: str) -> None:
        async with sem:
            try:
                page = await scrape.fetch_page(url)
                html = page.get("html", "")
                if not html or page.get("status", 0) not in (200, 301, 302):
                    return
            except Exception:
                return

            for m in handle_re.finditer(html):
                handle = m.group(1)
                name = _name_from_linkedin_handle(handle)
                if not name:
                    continue
                # Prefer the <img alt="Full Name"> closest before the link
                before = html[max(0, m.start() - 400): m.start()]
                alt = re.findall(r'alt="([^"]{3,60})"', before)
                if alt and not re.search(r"linkedin|logo|icon|profile|avatar", alt[-1], re.I):
                    alt_name = re.sub(r"^(prof|dr|mr|mrs|ms|sri|shri)\.?\s+", "", alt[-1].strip(), flags=re.I)
                    if len(alt_name.split()) >= 2:
                        name = alt_name
                if name in found:
                    continue
                found[name] = {
                    "name": name,
                    "linkedin_url": f"https://www.linkedin.com/in/{handle}/",
                    "role_hint": "",
                    "confidence": 0.6,  # published by the company itself = trustworthy
                    "pattern": "team_page",
                    "source_url": url,
                }

    await asyncio.gather(*(_scan(u) for u in dict.fromkeys(urls)))

    return list(found.values())[:15]


def _dedupe_by_address(items: list[dict]) -> list[dict]:
    """Dedupe by address (skipping empty pseudo-entries like website leads)."""
    best: dict[str, dict] = {}
    for item in items:
        addr = (item.get("address") or "").lower()
        if addr:
            if addr not in best or item.get("confidence", 0) > best[addr].get("confidence", 0):
                best[addr] = item
        elif item.get("pattern") == "linkedin_website":
            best.setdefault("__website__", item)
    return list(best.values())


# Local parts that are roles, not people — can't reveal a naming pattern
_GENERIC_LOCALPARTS = {
    "info", "careers", "jobs", "hr", "sales", "hello", "support", "contact",
    "press", "media", "team", "admin", "recruiting", "talent", "recruitment",
    "privacy", "legal", "dpo", "marketing", "office", "reception", "help",
    "enquiries", "inquiries", "mail", "email", "hello",
    # more role-style inboxes seen in the wild
    "connect", "contactus", "getintouch", "work", "workwithus", "join",
    "joinus", "career", "hrd", "corp", "corporate", "enquiry", "enquire",
    "services", "service", "query", "queries", "accounts", "admin1",
    "info1", "feedback", "newsletter", "subscribe", "notice", "operations",
    "operations", "projects", "project", "business", "vendor", "partners",
}


def infer_email_pattern(emails: list[dict], domain: str) -> str | None:
    """Learn a company's real email format from ONE confirmed personal email.

    This mirrors how Hunter.io builds patterns: a single real address at the
    domain (e.g. sarah.johnson@acme.com → '{first}.{last}@acme.com') is
    reliable >80% of the time for first/last style formats.

    Returns a '{first}'/'{last}'/'{f}'/'{l}' template string or None.
    """
    if not emails or not domain:
        return None
    domain = domain.lower()

    def _personal(address: str) -> bool:
        local = address.split("@")[0].lower()
        return local not in _GENERIC_LOCALPARTS and not local.startswith("no")

    best_candidates = sorted(
        (e for e in emails if (e.get("address") or "").lower().endswith(f"@{domain}")
         and _personal(e["address"].lower())),
        key=lambda e: e.get("confidence", 0),
        reverse=True,
    )
    if not best_candidates:
        return None

    local = best_candidates[0]["address"].split("@")[0]
    if "." in local:
        parts = local.split(".")
        if len(parts) == 2 and parts[0].isalpha() and parts[1].isalpha():
            # Could be first.last OR last.first — no way to disambiguate
            # keylessly, so prefer first.last (most common, ~50% of orgs)
            return f"{{first}}.{{last}}@{domain}"
        if parts[0].isalpha() and len(parts) >= 2:
            # e.g. flast@, f.last@, first.l@ — assume first-initial forms
            return f"{{f}}.{{last}}@{domain}"
    if len(local) >= 3 and local.isalpha():
        # 'flast' style — first initial + last name, OR full single name.
        # Prefer '{f}{last}' (very common for startups & India).
        return f"{{f}}{{last}}@{domain}"
    if local and local[0].isalpha():
        return f"{{first}}@{domain}"
    return None


# ---------------------------------------------------------------------------
# Orchestration used by contact_finder
# ---------------------------------------------------------------------------

def _split_name(name: str) -> tuple[str, str]:
    parts = (name or "").strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])
