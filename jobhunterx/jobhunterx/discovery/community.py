"""
Community and startup sources — where early-career roles show up before (or instead of) the big boards.

* YC Work at a Startup — the public ycombinator.com/jobs pages (no login). Each listing carries the company's own
  minimum experience ("Any (new grads ok)", "1+ years"), so a fresher can see at a glance which ones are open to them,
  and the job page names the founder who is hiring.
* r/developersIndia — the monthly "Who's hiring?" megathread, where each top-level comment fills a fixed template
  (company, link, location, role, experience, pay). Read through Reddit's public JSON, with the RSS feeds as a
  fallback (Reddit refuses JSON from many cloud addresses, and rate-limits). A refused source is skipped.
* Founder hiring posts — "we're hiring" posts on X / LinkedIn, found only through the web search providers you already
  use. JobHunterX never opens or logs in to X or LinkedIn: it keeps the search result's title and snippet, and you open
  the post yourself.

Everything here is discovery only: each lead becomes a JobPosting and goes through the same dedupe, validation, scam
checks and matching as every other source.
"""

from __future__ import annotations

import asyncio
import html as _html
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import FieldCheck, JobPosting, SourceRef
from jobhunterx.intelligence.text import title_overlap

log = get_logger("community")

YC_BASE = "https://www.ycombinator.com"
YC_DETAIL_LIMIT = 12
YC_MAX_AGE_DAYS = 120               # some company pages still list roles from years ago
REDDIT_SUBS = ("developersIndia",)
REDDIT_MAX_AGE_DAYS = 30
REDDIT_HEADERS = {"User-Agent": "python:jobhunterx:1.0 (personal job search assistant)", "Accept": "application/json"}
_INDIA_LOC = re.compile(r"(?i)\b(india|(?-i:IN)\b|hyderabad|secunderabad|bengaluru|bangalore|chennai|pune|mumbai|delhi|gurugram|"
                        r"gurgaon|noida|kochi|coimbatore|kolkata|ahmedabad|jaipur|indore|visakhapatnam|vizag)")
_YC_PLACE_SLUGS = {"bengaluru": "bengaluru", "bangalore": "bengaluru", "hyderabad": "hyderabad", "secunderabad": "hyderabad"}


def _common() -> set[str]:
    """Words in a large share of all job titles ("engineer", "senior"), measured on the daily employer-boards index."""
    try:
        from jobhunterx.discovery import ats_index
        ats_index._load()
        return ats_index._common()
    except Exception:
        return set()


def _related(title: str, labels: list[str]) -> bool:
    return title_overlap(title, labels, _common()) > 0


def _data_page(page: str) -> Optional[dict]:
    """ycombinator.com pages carry their data as JSON in a data-page attribute (Inertia)."""
    m = re.search(r'data-page="([^"]+)"', page or "")
    if not m:
        return None
    try:
        return json.loads(_html.unescape(m.group(1))).get("props") or {}
    except ValueError:
        return None


def relative_age(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """'7 days', 'about 2 months', 'over 1 year' → an approximate date."""
    now = now or datetime.now(timezone.utc)
    m = re.search(r"(\d+|an?)\s+(minute|hour|day|week|month|year)s?", text or "", re.I)
    if not m:
        return None
    n = 1 if m.group(1).lower() in ("a", "an") else int(m.group(1))
    days = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}[m.group(2).lower()] * n
    return now - timedelta(days=days)


def _yc_place_ok(location: str, include_remote: bool) -> bool:
    loc = location or ""
    if _INDIA_LOC.search(loc):
        return True
    if not include_remote or "remote" not in loc.lower():
        return False
    # "Remote (US)", "Remote (BR)": a remote role tied to another country is not open to India
    regions = re.findall(r"(?i)remote\s*\(([^)]*)\)", loc)
    return not regions or any(re.search(r"(?i)\b(IN|india|asia|apac|anywhere|global|worldwide)\b", r) for r in regions)


def yc_years(min_exp: str) -> Optional[int]:
    if not min_exp:
        return None
    if re.search(r"(?i)any|new grad", min_exp):
        return 0
    m = re.search(r"(\d+)", min_exp)
    return int(m.group(1)) if m else None


def parse_yc_listing(props: dict, labels: list[str], include_remote: bool, now: Optional[datetime] = None) -> list[JobPosting]:
    out = []
    for j in (props or {}).get("jobPostings") or []:
        title, company, url = (j.get("title") or "").strip(), (j.get("companyName") or "").strip(), j.get("url") or ""
        if not (title and company and url) or j.get("role") not in ("eng", "science", None, ""):
            continue
        if not _yc_place_ok(j.get("location") or "", include_remote) or not _related(title, labels):
            continue
        posted = relative_age(j.get("createdAt") or "", now)
        if posted and (now or datetime.now(timezone.utc)) - posted > timedelta(days=YC_MAX_AGE_DAYS):
            continue
        full = YC_BASE + url if url.startswith("/") else url
        exp = j.get("minExperience") or ""
        lines = [f"{company} (YC {j.get('companyBatchName') or ''}) — {j.get('companyOneLiner') or ''}".strip(),
                 f"Location: {j.get('location') or ''}", f"Type: {j.get('type') or ''} · {j.get('roleSpecificType') or ''}"]
        if exp:
            lines.append(f"Minimum experience: {exp}")
        if j.get("salaryRange"):
            lines.append(f"Salary: {j['salaryRange']}")
        if j.get("visa"):
            lines.append(f"Visa: {j['visa']}")
        p = JobPosting(title=title[:140], company=company, location_raw=j.get("location") or "",
                       posted_at=posted, description="\n".join(lines),
                       canonical_url=full, apply_url=full, employment_type="full_time" if j.get("type") == "Full-time" else "",
                       work_mode=WorkMode.REMOTE if "remote" in (j.get("location") or "").lower() and not _INDIA_LOC.search(j.get("location") or "")
                       else WorkMode.UNKNOWN,
                       discovered_by_query="YC Work at a Startup",
                       sources=[SourceRef(name="yc_waas", kind="job_board", url=full, confidence=0.7)])
        p.validation.checks["title"] = FieldCheck(status="verified", value=title, evidence="YC Work at a Startup listing")
        if exp:
            p.validation.checks["experience"] = FieldCheck(status="verified", value=exp, evidence="YC listing: minimum experience")
        out.append(p)
    return out


def enrich_yc(p: JobPosting, props: dict) -> JobPosting:
    """Add the job page's description, the founder who is hiring and the company website."""
    job, company = (props or {}).get("job") or {}, (props or {}).get("company") or {}
    extra = []
    hm = job.get("hiringManager") or {}
    if hm.get("first_name"):
        extra.append(f"Hiring manager: {hm.get('first_name')} {hm.get('last_name') or ''}".strip())
    if company.get("website"):
        extra.append(f"Company website: {company['website']}")
    if company.get("team_size"):
        extra.append(f"Team size: {company['team_size']}")
    body = (job.get("description") or "").strip()
    if job.get("interview_process"):
        body += "\n\nInterview process:\n" + str(job["interview_process"]).strip()
    p.description = "\n".join([p.description, *extra]) + ("\n\n" + body if body else "")
    p.description = p.description[:20000]
    return p


async def yc_search(labels: list[str], places: list[str], *, include_remote: bool = True, limit: int = 30) -> list[JobPosting]:
    from jobhunterx.discovery import job_apis
    slugs = ["india", *dict.fromkeys(_YC_PLACE_SLUGS[p.lower()] for p in places if p and p.lower() in _YC_PLACE_SLUGS)]
    paths = [f"/jobs/location/{s}" for s in slugs] + [f"/jobs/role/software-engineer/{s}" for s in slugs[:2]]
    if include_remote:
        paths.append("/jobs/location/remote")
    now = datetime.now(timezone.utc)
    pages = await asyncio.gather(*(job_apis.fetch_text(YC_BASE + p) for p in paths))
    found: dict[str, JobPosting] = {}
    for page in pages:
        for p in parse_yc_listing(_data_page(page or "") or {}, labels, include_remote, now):
            found.setdefault(p.canonical_url, p)
    # new-grad-friendly and newest first; the best few get their full job page (description, hiring founder)
    jobs = sorted(found.values(), key=lambda p: ((yc_years(_exp(p)) or 0) > 2, -(p.posted_at or now - timedelta(days=999)).timestamp()))
    jobs = jobs[:limit]
    sem = asyncio.Semaphore(4)

    async def detail(p: JobPosting) -> None:
        async with sem:
            props = _data_page(await job_apis.fetch_text(p.canonical_url) or "")
        if props:
            enrich_yc(p, props)
    await asyncio.gather(*(detail(p) for p in jobs[:YC_DETAIL_LIMIT]), return_exceptions=True)
    return jobs


def _exp(p: JobPosting) -> str:
    c = p.validation.checks.get("experience")
    return (c.value or "") if c else ""


# ------------------------------------------------------------------ Reddit
# r/developersIndia keeps hiring in one "Who's hiring? - Monthly Megathread", where each top-level comment fills a fixed
# template (Company Name / Link / Location / Role/Position / Type / Experience Required / Pay Range / ...).
_MEGATHREAD = re.compile(r"(?i)who['’]?s\s+hiring|hiring\s+megathread")
_FIELDS = {"company": r"company(?:\s+name)?", "link": r"(?:company\s+)?(?:link|website)", "location": r"location",
           "role": r"role(?:\s*/\s*position)?|position|job\s+title", "type": r"(?:job\s+)?type",
           "experience": r"experience(?:\s+required)?|yoe", "pay": r"pay(?:\s+range)?|ctc|salary|compensation",
           "skills": r"tech\s+stack(?:\s*/\s*skills(?:\s+required)?)?|skills(?:\s+required)?",
           "apply": r"application\s+link(?:\s*/\s*contact\s+email)?|how\s+to\s+apply|contact(?:\s+email)?|apply"}
_FIELD_LINE = re.compile(r"(?im)^\s*[*_>\-\s]*(" + "|".join(f"(?P<{k}>{v})" for k, v in _FIELDS.items()) + r")\s*[*_]*\s*[:\-–]\s*[*_]*\s*(.*)$")


def _md_text(body: str) -> str:
    """A comment's HTML (RSS) or markdown (JSON) → plain lines; links keep their address."""
    t = _html.unescape(body or "")
    t = re.sub(r'(?is)<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: m.group(2) if m.group(2).strip() == m.group(1) else
               f"{m.group(2)} {m.group(1)}", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|<p>", "\n", t)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 \2", t)          # markdown links
    t = re.sub(r"\*\*|__|\\(?=[_*\-])", "", t)
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n") if ln.strip())


_LABELS_INLINE = re.compile(r"(?i)[ \t]+(?=(?:" + "|".join(_FIELDS.values()) + r")\s*:)")


def megathread_fields(text: str) -> dict[str, str]:
    """Template fields of one post. Some posts put them all on one line: each "Label:" starts a new line first."""
    text = _LABELS_INLINE.sub("\n", text)
    out: dict[str, str] = {}
    for m in _FIELD_LINE.finditer(text):
        key = next(k for k in _FIELDS if m.group(k))
        out.setdefault(key, m.group(m.lastindex).strip(" *_"))
    return out


_SECTION = re.compile(r"(?i)\s+(?:overview|about\s+(?:us|the)|description|responsibilities|requirements|duration|we\s+are|"
                      r"you\s+will|work\s+from)\b")


def _short(value: str, limit: int = 120) -> str:
    """A field that ran into the post's prose (one-line posts) is cut where the prose starts."""
    v = _SECTION.split(value.strip(), maxsplit=1)[0].strip(" .|-–")
    return v[:limit].rsplit(" ", 1)[0] if len(v) > limit else v


def parse_megathread_comment(c: dict, labels: list[str], *, include_remote: bool = True,
                             now: Optional[datetime] = None) -> Optional[JobPosting]:
    """One top-level comment {body, permalink, created_utc, author} → a posting, or None (questions, other fields, abroad)."""
    now = now or datetime.now(timezone.utc)
    text = _md_text(c.get("body") or "")
    f = megathread_fields(text)
    company, role = _short(f.get("company") or ""), _short(f.get("role") or "")
    if not company or not role or len(company) > 80 or re.search(r"(?i):\s*$|^link\b|^\W*$", company):
        return None                     # the thread's own empty template, or a question
    when = datetime.fromtimestamp(c["created_utc"], tz=timezone.utc) if c.get("created_utc") else None
    if when and now - when > timedelta(days=REDDIT_MAX_AGE_DAYS + 31):
        return None
    if not _related(role, labels):
        return None
    loc = _short(f.get("location") or "", 80)
    if loc and not _yc_place_ok(loc, include_remote):
        return None
    link = c.get("permalink") or ""
    link = "https://www.reddit.com" + link if link.startswith("/") else link
    urls = [u.rstrip(".,;)") for u in re.findall(r"https?://[^\s<>\"']+", f"{f.get('apply', '')} {f.get('link', '')}")
            if "reddit.com" not in u]
    email = next(iter(re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", f.get("apply", "") + " " + text)), "")
    desc = text + (f"\n\nApply by email: {email}" if email and "apply by email" not in text.lower() else "")
    p = JobPosting(title=role[:140], company=company, location_raw=loc or "India", posted_at=when, description=desc[:20000],
                   canonical_url=link, apply_url=urls[0] if urls else link,
                   employment_type="contract" if re.search(r"(?i)contract", f.get("type", "")) else
                   "internship" if re.search(r"(?i)intern", f.get("type", "") + role) else
                   "full_time" if re.search(r"(?i)full", f.get("type", "")) else "",
                   work_mode=WorkMode.REMOTE if re.search(r"(?i)remote", loc) and not _INDIA_LOC.search(loc.replace("India", "")) else WorkMode.UNKNOWN,
                   discovered_by_query="Reddit r/developersIndia: Who's hiring? megathread",
                   sources=[SourceRef(name="reddit", kind="community", url=link, confidence=0.45)])
    p.validation.checks["title"] = FieldCheck(status="inferred", value=p.title, evidence="r/developersIndia hiring megathread")
    if f.get("experience"):
        p.validation.checks["experience"] = FieldCheck(status="inferred", value=f["experience"][:60], evidence="Megathread post")
    return p


def parse_reddit_rss(xml: str) -> list[dict]:
    """Atom entries → dicts like the JSON API's (title, body, permalink, created_utc, author)."""
    out = []
    for e in re.findall(r"(?s)<entry>(.*?)</entry>", xml or ""):
        def tag(t: str) -> str:
            m = re.search(rf"(?s)<{t}[^>]*>(.*?)</{t}>", e)
            return m.group(1).strip() if m else ""
        link = re.search(r'<link href="([^"]+)"', e)
        updated = tag("updated") or tag("published")
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = None
        out.append({"title": _html.unescape(tag("title")), "body": _html.unescape(tag("content")),
                    "permalink": urlparse(link.group(1)).path if link else "", "created_utc": ts,
                    "author": _html.unescape(tag("name")).removeprefix("/u/")})
    return out


async def _reddit(url: str, params: dict, *, as_json: bool):
    """GET with Reddit's limits in mind: a 429 waits the time Reddit asks for (at most 8 s) and tries once more."""
    import httpx
    from jobhunterx.discovery import job_apis
    for attempt in (1, 2):
        try:
            r = await job_apis._http().get(url, params=params, headers={**REDDIT_HEADERS, "Accept": "application/json" if as_json
                                                                        else "application/atom+xml,application/xml;q=0.9,*/*;q=0.5"})
        except httpx.HTTPError:
            return None
        if r.status_code == 429 and attempt == 1:
            try:
                wait = float(r.headers.get("retry-after") or 5)
            except ValueError:
                wait = 5.0
            await asyncio.sleep(min(8.0, max(2.0, wait)))
            continue
        if r.status_code != 200:
            log.info("reddit_status", status=r.status_code, path=url.split("reddit.com")[-1][:60])
            return None
        if not as_json:
            return r.text
        try:
            return r.json()
        except ValueError:
            return None
    return None


def _thread_id(permalink: str) -> str:
    m = re.search(r"/comments/([a-z0-9]+)/", permalink or "")
    return m.group(1) if m else ""


async def _megathreads(sub: str) -> list[dict]:
    """This month's and last month's hiring megathreads (title, permalink, created_utc)."""
    params = {"q": 'title:"hiring" title:"megathread"', "restrict_sr": "1", "sort": "new", "t": "year", "limit": "5"}
    data = await _reddit(f"https://www.reddit.com/r/{sub}/search.json", params, as_json=True)
    posts = [c.get("data") or {} for c in ((data or {}).get("data") or {}).get("children") or []] if isinstance(data, dict) else []
    if not posts:                  # JSON refused (common from cloud addresses): the RSS feed usually still answers
        posts = parse_reddit_rss(await _reddit(f"https://www.reddit.com/r/{sub}/search.rss", params, as_json=False) or "")
    return [p for p in posts if _MEGATHREAD.search(p.get("title") or "") and _thread_id(p.get("permalink") or "")][:2]


async def _comments(sub: str, thread: dict) -> list[dict]:
    tid = _thread_id(thread.get("permalink") or "")
    data = await _reddit(f"https://www.reddit.com/comments/{tid}.json", {"limit": "500", "depth": "1", "sort": "new"}, as_json=True)
    if isinstance(data, list) and len(data) > 1:
        return [c.get("data") or {} for c in (data[1].get("data") or {}).get("children") or [] if c.get("kind") == "t1"]
    xml = await _reddit(f"https://www.reddit.com/r/{sub}/comments/{tid}/.rss", {"limit": "100", "sort": "new"}, as_json=False)
    return [c for c in parse_reddit_rss(xml or "") if _thread_id(c["permalink"]) == tid and c["permalink"].rstrip("/").count("/") > 5]


async def reddit_search(labels: list[str], *, include_remote: bool = True, limit: int = 25) -> list[JobPosting]:
    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    seen: set[str] = set()
    for sub in REDDIT_SUBS:
        for thread in await _megathreads(sub):
            for c in await _comments(sub, thread):
                p = parse_megathread_comment(c, labels, include_remote=include_remote, now=now)
                if p and p.canonical_url not in seen:
                    seen.add(p.canonical_url)
                    out.append(p)
    out.sort(key=lambda p: p.posted_at or now - timedelta(days=999), reverse=True)
    return out[:limit]


# ------------------------------------------------------------------ founder posts (via web search only)
_POST_URL = re.compile(r"(?i)^https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)/([A-Za-z0-9_]{1,15})/status/\d+"
                       r"|^https?://(?:[a-z]{2,3}\.)?linkedin\.com/posts/([A-Za-z0-9\-_%]+?)_")
_HIRING_POST = re.compile(r"(?i)(#hiring\b|\b(?:is|are)\s+hiring\b)|\b(we(?:'re|’re| are)\s+hiring|i(?:'m|’m| am)\s+hiring|hiring\s+(?:for|a|an|our|my)|"
                          r"looking\s+for\s+(?:a|an)\s+[\w\s/]{0,30}(?:engineer|developer|intern)|join\s+(?:us|our\s+team)|"
                          r"dm\s+me|send\s+(?:me\s+)?your\s+(?:cv|resume))")


def _company_hint(text: str) -> str:
    for rx in (r"\bat\s+@?([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,2})\b", r"\|\s*([A-Z][\w&.\- ]{1,40}?)\s*\|",
               r"(?i)\b(?:company|startup)\s*[:\-]\s*([A-Z][\w&.\- ]{1,40})"):
        m = re.search(rx, text[:800])
        if m:
            name = m.group(1).strip(" .-|")
            if name.lower() not in ("india", "remote", "bangalore", "bengaluru", "hyderabad", "the", "our", "a", "x", "linkedin"):
                return name
    return ""


def _place_hint(text: str) -> str:
    m = _INDIA_LOC.search(text[:1500])
    remote = re.search(r"(?i)\bremote\b", text[:1500])
    place = m.group(1).title() if m and m.group(1) != "IN" else ""
    return ", ".join(x for x in (place, "Remote" if remote else "") if x)


def founder_queries(titles: list[str], places: list[str], fresher: bool, limit: int = 4) -> list[str]:
    """Plain queries work best on the free engines: operators like OR-groups or a year cut results to nothing."""
    place = next((p for p in places if p and p.lower() != "india"), "India")
    out = []
    for t in titles[:2]:
        out.append(f'site:linkedin.com/posts hiring "{t}" {place}' + (" fresher" if fresher else ""))
        out.append(f'site:x.com "hiring" "{t}" {place}')
    return out[:limit]


FOUNDER_MAX_AGE_DAYS = 60
_X_EPOCH_MS = 1288834974657


def post_date(url: str) -> Optional[datetime]:
    """LinkedIn activity ids and X status ids carry their creation time in the top bits (snowflake ids)."""
    m = re.search(r"activity[-:](\d{15,20})", url or "")
    if m:
        ms = int(m.group(1)) >> 22
    else:
        m = re.search(r"/status/(\d{15,20})", url or "")
        if not m:
            return None
        ms = (int(m.group(1)) >> 22) + _X_EPOCH_MS
    try:
        d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return d if datetime(2010, 1, 1, tzinfo=timezone.utc) < d <= datetime.now(timezone.utc) + timedelta(days=1) else None


def parse_founder_lead(url: str, title: str, snippet: str, labels: list[str], query: str = "",
                       now: Optional[datetime] = None) -> Optional[JobPosting]:
    m = _POST_URL.match(url or "")
    if not m:
        return None
    text = f"{title} {snippet}"
    if not _HIRING_POST.search(text) or not _related(text, labels):
        return None
    when = post_date(url)
    if when and (now or datetime.now(timezone.utc)) - when > timedelta(days=FOUNDER_MAX_AGE_DAYS):
        return None                     # an old post: the role is very likely filled
    handle = m.group(1) or ""
    person = re.sub(r"[-_]+", " ", _html.unescape(m.group(2) or "")).strip().title()
    site = "X" if handle else "LinkedIn"
    company = _company_hint(text) or (f"@{handle}" if handle else person) or f"{site} post"
    role = next((ln.strip() for ln in re.split(r"[.!\n|]", snippet or title) if title_overlap(ln, labels) > 0), title)[:140]
    p = JobPosting(title=role or "Hiring post", company=f"{company} ({site} hiring post)"[:80],
                   location_raw=_place_hint(text) or "India", posted_at=when,
                   description=f"{title}\n\n{snippet}\n\nOpen the post: {url}",
                   canonical_url=url, apply_url=url, discovered_by_query=query or "Founder hiring posts",
                   sources=[SourceRef(name="founder_post", kind="community", url=url, confidence=0.35)])
    p.validation.checks["title"] = FieldCheck(status="inferred", value=p.title,
                                              evidence=f"Search result for a public {site} post (not opened by JobHunterX)")
    return p


async def founder_posts(titles: list[str], places: list[str], labels: list[str], *, fresher: bool = False,
                        limit: int = 15) -> list[JobPosting]:
    from jobhunterx.discovery import search as web
    qs = founder_queries(titles, places, fresher)
    if not qs:
        return []
    leads = await web.run_queries(qs, per_query=10)
    out, seen = [], set()
    for lead in leads:
        p = parse_founder_lead(lead.url, lead.title, lead.snippet, labels, lead.query)
        if p and p.canonical_url not in seen:
            seen.add(p.canonical_url)
            out.append(p)
    return out[:limit]
