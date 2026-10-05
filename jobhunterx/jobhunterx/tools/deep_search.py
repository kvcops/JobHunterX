"""
JobHunterX Deep Search — keyless web search built for finding job postings.

Paid search APIs (Tavily, Exa…) ask several indexes, read the pages and rank by meaning. Deep Search does that with
free parts, and then does the one thing a general search API cannot: it turns what it finds into postings on the
employer's own job board, where far fewer people apply.

1. **Understand the query** — role words, places (Indian cities, "India", "remote") and modifiers are told apart.
2. **Fan-out with variants** — the query goes to several free engines at once (Bing, Yandex, Mullvad-Google,
   Mullvad-Brave, Yahoo, DuckDuckGo via `ddgs`), plus two rewritten variants: one aimed at applicant-tracking-system
   job pages (Greenhouse, Lever, Ashby, Workday, Keka) and one at company careers pages. Failing engines rest.
3. **Fusion + triage** — reciprocal-rank fusion merges everything; each result is classified (a single posting, an
   aggregator's single-job page, a job *list*, a salary page, a personal profile, a blog…) and weighted for it.
4. **Company resolution** — company names are read from aggregator titles ("Acme hiring AI Engineer…", "… Job in
   Acme at Hyderabad") and careers-site domains, matched against the researched watchlist and probed on public ATS
   APIs. Matching open roles in the searched place are pulled straight from those boards (verified, first-party).
   Board look-ups are remembered for a week.
5. **Crawl** — the best careers / listing pages are opened: ATS links and same-site job links are mined, and the
   page's own schema.org `JobPosting` data (date posted, valid through, location) is read; expired postings sink.
6. **Signals** — freshness ("2 days ago", dates), place match, and foreign-only locations adjust the score.
7. **Rerank** — when an AI model is available it scores the top candidates for "a real, open posting that matches";
   clearly irrelevant results are dropped when enough good ones remain.

Everything degrades gracefully: no AI → fusion order; a blocked engine → the others answer; a board that does not
exist → skipped (and remembered); a page that will not load → its search snippet is kept.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger

log = get_logger("deep_search")

ENGINES = ["bing", "yandex", "mullvad_google", "mullvad_brave", "yahoo", "duckduckgo"]
VARIANT_ENGINES = {"ats": ["bing", "yahoo", "mullvad_google"], "careers": ["bing", "yandex"]}
PER_ENGINE = 10
RRF_K = 60
CRAWL_PAGES = 8               # pages opened per query
CRAWL_LINKS_PER_PAGE = 12     # job links taken from one page
ENGINE_REST_S = 600           # an engine that keeps failing sits out for 10 minutes
STRAGGLER_S = 3.0             # grace for the last few engines once 70% have answered
RERANK_TOP = 30
RERANK_BUDGET_S = 12.0        # a slow model never holds the search up: fusion order is used instead
COMPANIES_PER_QUERY = 10      # company names resolved to job boards per query
BOARD_JOBS_PER_COMPANY = 4
RESOLVE_BUDGET_S = 8.0

# Hosts that only aggregate other employers' posts: fine as discovery leads, never better than the employer's own page.
AGGREGATORS = ("linkedin.com", "naukri.com", "indeed.", "glassdoor.", "foundit.in", "monsterindia.com", "shine.com",
               "timesjobs.com", "simplyhired", "ziprecruiter", "jooble", "talent.com", "apna.co", "internshala.com",
               "instahyre.com", "cutshort.io", "wellfound.com", "hirist.", "iimjobs.com", "workindia.in", "jobgether.com")
# People-lookup / contact-scraping / content sites: never job postings, often rank high for role names.
NOISE = ("rocketreach.co", "zoominfo.com", "signalhire.com", "contactout.com", "apollo.io", "lusha.com", "theorg.com",
         "crunchbase.com", "youtube.com", "medium.com", "quora.com", "reddit.com", "wikipedia.org", "datacamp.com",
         "github.com", "geeksforgeeks.org", "coursera.org", "udemy.com", "ambitionbox.com", "payscale.com")
_JOB_SITE_NAME = re.compile(r"(?i)(jobs?|careers?|hiring|vacanc|recruitment|naukri)")
MAX_PER_SITE = 3              # results kept from one site (an ATS counts per employer board, not per host)
_CAREERS_PATH = re.compile(r"/(careers?|jobs?|join-us|join|work-with-us|openings|vacancies|positions)(/|$|\?)", re.I)
_JOB_ANCHOR = re.compile(r"\b(engineer|developer|scientist|analyst|manager|architect|intern|lead|specialist|consultant|designer)\b", re.I)
# a single posting on an aggregator (a crowded channel, but a real job — and its company can be resolved)
_AGG_POSTING = re.compile(r"(?i)(linkedin\.com/jobs/view/|indeed\.[a-z.]+/(viewjob|rc/clk|m/viewjob)|naukri\.com/job-listings-|"
                          r"foundit\.in/job/|glassdoor\.[a-z.]+/job-listing/|instahyre\.com/job-|cutshort\.io/job/|wellfound\.com/jobs/\d)")
# titles of result *lists*, salary pages, guides and profiles
_LISTING = re.compile(r"(?i)(^\s*\d[\d,]*\+?\s+.*\bjobs?\b|\bjobs?\s+(in|at|for)\b|\(\d[\d,]*\+?\s+(open\s+)?(roles|jobs|openings)\)|"
                      r"\b\d[\d,]*\+?\s+(open\s+)?(roles|jobs|openings|vacancies)\b|\bjob\s+vacancies\b|\bopenings\s+for\b|"
                      r"\blatest\s+openings\b|\bjob\s+search\b)")
_SALARY = re.compile(r"(?i)\bsalar(y|ies)\b|\bpay\s+scale\b|\bhow much\b")
_GUIDE = re.compile(r"(?i)\b(how to|guide|tips|interview questions|roadmap|course|tutorial|what is|vs\.?|hire (the )?best)\b|/blog/|/guide")
_PROFILE_PATH = re.compile(r"(?i)/(in|talent|portfolio|people|profile|u|user)/")


@dataclass
class _Engine:
    name: str
    fails: int = 0
    rest_until: float = 0.0


_engines = {n: _Engine(n) for n in ENGINES}


@dataclass
class Hit:
    url: str
    title: str
    snippet: str
    score: float = 0.0
    engines: set = field(default_factory=set)
    kind: str = "page"            # posting | agg_posting | board | careers | aggregator | listing | page | profile | noise
    via: str = ""                 # how it was found: engine names, "crawl:<page>" or "board:<ats>:<token>"
    company: str = ""


def _norm(url: str) -> str:
    u = re.sub(r"[#?].*$", "", (url or "").strip())
    return u.rstrip("/").lower()


def _host(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def classify(url: str, title: str = "") -> str:
    from jobhunterx.discovery import ats
    ref = ats.parse_ats_url(url)
    if ref:
        return "posting" if ref.job_id else "board"
    h = _host(url)
    path = urlparse(url).path or "/"
    if any(h == n or h.endswith("." + n) for n in NOISE):
        return "noise"
    if title and (_SALARY.search(title) or _GUIDE.search(title + " " + path)):
        return "noise"
    if _AGG_POSTING.search(url):
        return "agg_posting"
    if title and _LISTING.search(title):
        return "listing"
    if any(a in h for a in AGGREGATORS):
        return "aggregator"
    site_name = h.split(".")[-2] if h.count(".") >= 1 else h
    if _JOB_SITE_NAME.search(site_name):
        return "aggregator"
    if _CAREERS_PATH.search(path) or h.startswith(("careers.", "jobs.")):
        return "careers"
    if _PROFILE_PATH.search(path) or (path in ("", "/") and title and re.search(r"(?i)\b(engineer|developer|analyst|scientist)\b", title)
                                       and re.search(r"[|—–-]", title)):
        return "profile"                       # someone's portfolio / profile, not a job
    return "page"


KIND_BOOST = {"posting": 1.7, "board": 1.4, "careers": 1.25, "agg_posting": 1.05, "page": 0.9, "aggregator": 0.6,
              "listing": 0.3, "profile": 0.15, "noise": 0.1}


# ---------------------------------------------------------------- 1. understand the query
CITIES = {"hyderabad": ["hyderabad", "secunderabad", "telangana", "hitec city", "gachibowli"],
          "bengaluru": ["bengaluru", "bangalore", "karnataka"], "chennai": ["chennai", "tamil nadu"], "pune": ["pune", "maharashtra"],
          "mumbai": ["mumbai", "maharashtra"], "delhi": ["delhi", "ncr", "gurugram", "gurgaon", "noida"], "kochi": ["kochi", "kerala"],
          "kolkata": ["kolkata"], "ahmedabad": ["ahmedabad"], "vizag": ["visakhapatnam", "vizag"]}
_CITY_FORMS = {f: c for c, forms in CITIES.items() for f in forms}
_MODIFIERS = {"fresher", "freshers", "entry", "level", "junior", "senior", "sr", "jr", "lead", "years", "year", "yrs", "experience", "exp",
              "job", "jobs", "hiring", "opening", "openings", "vacancy", "vacancies", "role", "roles", "position", "full", "time",
              "fulltime", "remote", "hybrid", "onsite", "india", "careers", "apply", "in", "at", "for", "the", "and", "or", "with"}
_ROLE_NOUNS = {"engineer", "developer", "analyst", "scientist", "manager", "architect", "intern", "specialist", "consultant", "designer", "administrator", "admin"}
_SYN = {"ml": ["machine", "learning"], "ai": ["artificial", "intelligence"], "sde": ["software", "engineer"], "genai": ["generative", "ai"]}


@dataclass
class Query:
    raw: str
    core: str                 # the query without site: operators
    role: list[str]           # role tokens ("ai", "engineer")
    places: list[str]         # canonical cities found
    india: bool
    remote: bool


def understand(q: str) -> Query:
    core = re.sub(r"\(?\s*site:\S+(\s+OR\s+site:\S+)*\s*\)?", " ", q, flags=re.I)
    core = re.sub(r"\s+", " ", core.replace('"', " ")).strip()
    toks = re.findall(r"[a-z0-9+#.]+", core.lower())
    places, role = [], []
    i = 0
    while i < len(toks):
        two = " ".join(toks[i:i + 2])
        if two in _CITY_FORMS:
            places.append(_CITY_FORMS[two]); i += 2; continue
        if toks[i] in _CITY_FORMS:
            places.append(_CITY_FORMS[toks[i]])
        elif toks[i] not in _MODIFIERS and not toks[i].isdigit() and len(toks[i]) > 1:
            role.append(toks[i])
        i += 1
    return Query(raw=q, core=core, role=role[:6], places=list(dict.fromkeys(places)), india="india" in toks or bool(places),
                 remote="remote" in toks)


def _variants(q: Query) -> list[tuple[str, str, list[str]]]:
    """(name, query text, engines). The raw query always goes everywhere; variants only when the query is plain text."""
    out = [("raw", q.raw, ENGINES)]
    if "site:" in q.raw.lower() or not q.role:
        return out
    role = " ".join(q.role)
    where = " ".join(q.places) or ("India" if q.india else "")
    if q.remote:
        where = (where + " remote").strip()
    ats = ("(site:boards.greenhouse.io OR site:job-boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com "
           "OR site:myworkdayjobs.com OR site:keka.com)")
    out.append(("ats", f'"{role}" {where} {ats}'.strip(), VARIANT_ENGINES["ats"]))
    out.append(("careers", f"{role} {where} careers apply now".strip(), VARIANT_ENGINES["careers"]))
    return out


# ---------------------------------------------------------------- 2. fan-out
async def _engine_search(engine: _Engine, query: str) -> list[dict]:
    def run():
        from ddgs import DDGS
        with DDGS(timeout=10) as d:
            return list(d.text(query, max_results=PER_ENGINE, region="in-en", backend=engine.name))
    try:
        res = await asyncio.wait_for(asyncio.to_thread(run), timeout=14)
        engine.fails = 0
        return res
    except Exception as exc:
        msg = str(exc).lower()
        if "no results" not in msg:              # "no results" is an answer, not a failure
            engine.fails += 1
            if engine.fails >= 2:
                engine.rest_until = time.monotonic() + ENGINE_REST_S
                log.info("deep_search_engine_resting", engine=engine.name, error=str(exc)[:80])
        return []


async def fan_out(query: str, variants: Optional[list[tuple[str, str, list[str]]]] = None) -> dict[str, Hit]:
    now = time.monotonic()
    jobs = []
    for name, text, engines in (variants or [("raw", query, ENGINES)]):
        live = [_engines[e] for e in engines if _engines[e].rest_until <= now] or [_engines[e] for e in engines]
        jobs += [(name, e, text) for e in live]
    tasks = [asyncio.ensure_future(_engine_search(e, text)) for _, e, text in jobs]
    pending = set(tasks)
    while pending:                                 # once most engines answered, stragglers get a short grace, not 14 s
        quorum = len(pending) <= len(tasks) * 0.3
        done, pending = await asyncio.wait(pending, timeout=STRAGGLER_S if quorum else None,
                                           return_when=asyncio.ALL_COMPLETED if quorum else asyncio.FIRST_COMPLETED)
        if quorum:
            break
    for t in pending:
        t.cancel()
    results = [t.result() if t.done() and not t.cancelled() and not t.exception() else [] for t in tasks]
    hits: dict[str, Hit] = {}
    for (vname, engine, _), rows in zip(jobs, results):
        weight = 1.0 if vname == "raw" else 0.9
        for rank, r in enumerate(rows):
            url = r.get("href") or r.get("url") or ""
            if not url.startswith("http"):
                continue
            key = _norm(url)
            h = hits.get(key)
            if not h:
                title = r.get("title", "")
                h = hits[key] = Hit(url=url, title=title, snippet=r.get("body") or "", kind=classify(url, title))
            h.score += weight / (RRF_K + rank + 1)
            h.engines.add(engine.name if vname == "raw" else f"{engine.name}:{vname}")
            if len(r.get("body") or "") > len(h.snippet):
                h.snippet = r.get("body") or ""
    for h in hits.values():
        h.score *= KIND_BOOST.get(h.kind, 1.0)
        h.via = ",".join(sorted(h.engines))
    return hits


# ---------------------------------------------------------------- 3. company resolution -> first-party postings
_CO_PATTERNS = [
    re.compile(r"^(?P<c>.+?)\s+(?:is\s+)?hiring\s+(?:for\s+)?.+", re.I),                       # LinkedIn: "Acme hiring AI Engineer in …"
    re.compile(r"\bjob\s+in\s+(?P<c>.+?)\s+at\s+", re.I),                                       # Naukri: "… Job in Acme at Hyderabad"
    re.compile(r"^[^|–—-]+?\s[-–—|]\s(?P<c>[^|–—-]{2,60}?)\s[-–—|]\s", re.I),                   # Indeed: "Title - Acme - Hyderabad"
    re.compile(r"\bat\s+(?P<c>[A-Z][\w&.' ]{1,50}?)(?:\s*[|–—-]|\s+in\s+|$)"),                  # "AI Engineer at Acme | …"
]
_CO_STRIP = re.compile(r"(?i)\b(pvt\.?|private|ltd\.?|limited|inc\.?|llc|llp|corp(oration)?|technologies|technology|solutions|software|"
                       r"services|india|global|labs?|co\.?)\b")
_CO_BAD = re.compile(r"(?i)^(linkedin|indeed|naukri|glassdoor|foundit|jobs?|careers?|hiring|urgent|new|top|latest|remote|india|"
                     r"hyderabad|bengaluru|bangalore|\d+)$")


def _company_from(hit: Hit) -> Optional[str]:
    title = re.sub(r"\s*[|–—]\s*(LinkedIn|Indeed.*|Naukri.*|Glassdoor|foundit.*)$", "", hit.title or "", flags=re.I).strip()
    if hit.kind in ("agg_posting", "aggregator"):
        for pat in _CO_PATTERNS:
            m = pat.search(title)
            if m:
                c = m.group("c").strip(" .,-|")
                low = c.lower()
                if (1 < len(c) <= 60 and not _CO_BAD.match(c) and not _JOB_ANCHOR.search(c)
                        and not any(f in low for f in _CITY_FORMS) and "," not in c.rstrip(".").replace(", llc", "").replace(", inc", "")):
                    return c
        return None
    if hit.kind == "careers":                  # the employer's own careers site: the domain is the company
        h = _host(hit.url)
        if not (h.startswith(("careers.", "jobs.", "career.")) or "/careers" in urlparse(hit.url).path.lower()):
            return None                        # "/jobs/" paths are as often job sites as employers
        parts = [p for p in h.split(".") if p not in ("careers", "career", "jobs", "www", "apply", "work")]
        if parts and not _JOB_SITE_NAME.search(parts[0]) and not any(a in h for a in AGGREGATORS):
            return parts[0]
    return None


def _slugs(name: str) -> list[str]:
    base = _CO_STRIP.sub(" ", name.lower())
    words = re.findall(r"[a-z0-9]+", base) or re.findall(r"[a-z0-9]+", name.lower())
    if not words:
        return []
    cands = ["".join(words), "-".join(words)]
    if len(words) > 1 and len(words[0]) >= 5:
        cands.append(words[0])
    full = re.findall(r"[a-z0-9]+", name.lower())
    if full and "".join(full) not in cands:
        cands.append("".join(full))
    return list(dict.fromkeys(c for c in cands if 2 < len(c) <= 40))


_store = None


def _cache():
    global _store
    if _store is None:
        from diskcache import Cache
        from jobhunterx.config.settings import get_settings
        _store = Cache(str(get_settings().cache_full_path / "deep_boards"))
    return _store


def _same_company(a: str, b: str) -> bool:
    na = re.sub(r"[^a-z0-9]", "", _CO_STRIP.sub(" ", a.lower())); nb = re.sub(r"[^a-z0-9]", "", _CO_STRIP.sub(" ", b.lower()))
    return bool(na and nb) and (na == nb or na.startswith(nb) or nb.startswith(na))


async def _probe(kind: str, slug: str, name: str) -> bool:
    """Does `slug` exist on this ATS and belong to `name`? Cheap public endpoints; answers cached for a week."""
    from jobhunterx.discovery import net
    key = f"{kind}:{slug}"
    store = _cache()
    if key in store:
        return store[key]
    ok = False
    try:
        if kind == "greenhouse":
            data, res = await net.fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=6)
            ok = isinstance(data, dict) and bool(data.get("name")) and _same_company(data.get("name", ""), name)
        elif kind == "lever":
            data, res = await net.fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1", timeout=6)
            ok = isinstance(data, list) and len(data) > 0 and _same_company(slug, name)
        elif kind == "ashby":
            data, res = await net.fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=6)
            ok = isinstance(data, dict) and bool(data.get("jobs")) and _same_company(slug, name)
    except Exception:
        return False                             # network trouble: don't remember a wrong "no"
    store.set(key, ok, expire=7 * 86400)
    return ok


def _role_match(title: str, q: Query) -> float:
    toks = set(re.findall(r"[a-z0-9+#.]+", (title or "").lower()))
    for short, longs in _SYN.items():
        if short in toks:
            toks.update(longs)
        if all(l in toks for l in longs):
            toks.add(short)
    role = [r for r in q.role]
    if not role:
        return 0.0
    hits = sum(1 for r in role if r in toks or any(r in _SYN.get(t, []) for t in toks))
    specific = [r for r in role if r not in _ROLE_NOUNS]
    if specific and not any(r in toks or any(r in _SYN.get(t, []) for t in toks) for r in specific):
        return 0.0                               # "Software Engineer" is not an "AI Engineer"
    return hits / len(role)


def _place_ok(location: str, countries: list[str], q: Query) -> bool:
    text = f"{location} {' '.join(countries)}".lower()
    if not text.strip():
        return True
    if q.places:
        if any(f in text for c in q.places for f in CITIES.get(c, [c])):
            return True
        return q.remote and "remote" in text and ("india" in text or not countries)
    return "india" in text or ("remote" in text and q.remote) or not q.india


async def resolve_companies(hits: list[Hit], q: Query) -> list[Hit]:
    """Company names from the results -> their own job boards -> matching open roles there (first-party)."""
    from jobhunterx.discovery import ats, watchlist
    from jobhunterx.domain.candidate import norm_term
    names: dict[str, tuple[str, float]] = {}
    for h in hits:
        c = _company_from(h)
        if c:
            k = re.sub(r"[^a-z0-9]", "", c.lower())
            if k and k not in names:           # names read from aggregator posts first: those are the crowded channels
                names[k] = (c, h.score * (2.0 if h.kind == "agg_posting" else 1.0))
    picked = sorted(names.values(), key=lambda x: -x[1])[:COMPANIES_PER_QUERY]
    if not picked:
        return []
    by_name = watchlist._index()[1]
    sem = asyncio.Semaphore(10)

    async def boards_for(name: str) -> list[tuple[str, str, str]]:
        wc = by_name.get(norm_term(name)) or next((w for n, w in by_name.items() if len(n) > 3 and _same_company(n, name)), None)
        if wc and wc.board:
            return [(wc.board.kind, wc.board.token, wc.name)]
        found = []
        for slug in _slugs(name)[:3]:
            for kind in ("greenhouse", "lever", "ashby"):
                async with sem:
                    if await _probe(kind, slug, name):
                        found.append((kind, slug, name))
            if found:
                break
        return found

    async def jobs_from(kind: str, token: str, company: str, base: float) -> list[Hit]:
        adapter = ats.ADAPTERS.get(kind)
        if not adapter:
            return []
        async with sem:
            jobs = await adapter.search_jobs(token, [" ".join(q.role)]) if kind in ("workday", "oracle") else await adapter.list_jobs(token)
        out = []
        for j in jobs or []:
            m = _role_match(j.title, q)
            if m < 0.6 or not _place_ok(j.location_raw, j.countries, q):
                continue
            age = (datetime.now(timezone.utc) - j.posted_at).days if j.posted_at else None
            fresh = 1.15 if age is not None and age <= 14 else 0.75 if age is not None and age > 60 else 1.0
            out.append(Hit(url=j.canonical_url or j.apply_url, title=f"{j.title} — {company}", company=company, kind="posting",
                           snippet=f"{company} · {j.location_raw or 'location not stated'}" + (f" · posted {age} days ago" if age is not None else "")
                           + " · on the employer's own job board", score=base * 1.25 * m * fresh * KIND_BOOST["posting"],
                           via=f"board:{kind}:{token}", engines={"board"}))
        out.sort(key=lambda h: -h.score)
        return out[:BOARD_JOBS_PER_COMPANY]

    async def one(name: str, base: float) -> list[Hit]:
        res = []
        for kind, token, company in await boards_for(name):
            res += await jobs_from(kind, token, company, base)
        return res

    top = max((s for _, s in picked), default=0.01)
    try:
        groups = await asyncio.wait_for(asyncio.gather(*(one(n, max(s, top * 0.6)) for n, s in picked), return_exceptions=True),
                                        RESOLVE_BUDGET_S)
    except asyncio.TimeoutError:
        log.info("deep_resolve_timeout", companies=len(picked))
        return []
    out = [h for g in groups if isinstance(g, list) for h in g]
    log.info("deep_resolve", companies=len(picked), names=[n for n, _ in picked][:6], postings=len(out))
    return out


# ---------------------------------------------------------------- 4. crawl
def _jsonld_jobs(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.I | re.S):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if d.get("@type") == "JobPosting" or (isinstance(d.get("@type"), list) and "JobPosting" in d["@type"]):
                    out.append(d)
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
            elif isinstance(d, list):
                stack.extend(d)
    return out


def _date(s) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _crawl_page(hit: Hit, sem: asyncio.Semaphore) -> list[Hit]:
    from jobhunterx.discovery import ats, net
    from jobhunterx.discovery.htmltext import html_to_text
    async with sem:
        res = await net.fetch(hit.url, timeout=10)
    if not res.ok or not res.text:
        return []
    html = res.text
    base = res.url or hit.url
    found: dict[str, Hit] = {}
    for m in re.finditer(r"""<(?:a|iframe)\b[^>]*?(?:href|src|data-url)=["']([^"'#\s]+)["'][^>]*>(.{0,600}?)(?:</a>|</iframe>|<a\b)""",
                         html, re.I | re.S):
        url = urljoin(base, m.group(1))
        if not url.startswith("http"):
            continue
        anchor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2) or "")).strip()[:140]
        ref = ats.parse_ats_url(url)
        kind = ("posting" if ref.job_id else "board") if ref else None
        if (not kind and hit.kind == "careers" and _host(url) == _host(base) and _JOB_ANCHOR.search(anchor)
                and _CAREERS_PATH.search(urlparse(url).path or "") and (urlparse(url).path or "").count("/") >= 3):
            kind = "posting"                       # a job link on the company's own careers page
        if not kind:
            continue
        key = _norm(url)
        if key in found or key == _norm(hit.url):
            continue
        if kind == "posting" and not ref and not anchor:
            continue
        found[key] = Hit(url=url, title=anchor or hit.title, snippet=f"Found on {_host(base)}", kind=kind,
                         score=hit.score * (0.9 if kind == "posting" else 0.8), via=f"crawl:{_host(base)}")
        if len(found) >= CRAWL_LINKS_PER_PAGE:
            break
    # the page's own structured job data: real dates and places
    jl = _jsonld_jobs(html)
    if jl:
        j = jl[0]
        now = datetime.now(timezone.utc)
        until, posted = _date(j.get("validThrough")), _date(j.get("datePosted"))
        if until and until < now:
            hit.kind, hit.score = "noise", hit.score * 0.2            # expired
        else:
            hit.kind = "posting"
            hit.score *= 1.3 * (1.15 if posted and (now - posted).days <= 14 else 1.0)
            if posted:
                hit.snippet = f"posted {(now - posted).days} days ago · " + hit.snippet
    if len(hit.snippet) < 160:
        text = html_to_text(html)[:600]
        if text:
            hit.snippet = text
    return list(found.values())


async def crawl(hits: list[Hit]) -> list[Hit]:
    order = {"careers": 0, "page": 1, "agg_posting": 2}
    targets = sorted([h for h in hits if h.kind in order], key=lambda h: (order[h.kind], -h.score))[:CRAWL_PAGES]
    if not targets:
        return []
    sem = asyncio.Semaphore(5)
    out = await asyncio.gather(*(_crawl_page(h, sem) for h in targets), return_exceptions=True)
    return [h for group in out if isinstance(group, list) for h in group]


# ---------------------------------------------------------------- 5. signals
_FOREIGN = re.compile(r"(?i)\b(united states|usa|u\.s\.|canada|united kingdom|london|germany|berlin|europe|emea|latam|brazil|mexico|"
                      r"philippines|pakistan|singapore|dubai|australia|new york|san francisco|seattle|toronto|remote[\s,\-–]+(us|uk|eu))\b")
_AGO = re.compile(r"(?i)\b(\d+)\s*(hour|hr|day|week|month)s?\s+ago\b|\b(today|yesterday|just posted)\b")
_OLD_YEAR = re.compile(r"\b(20[12]\d)\b")


def apply_signals(hits: list[Hit], q: Query) -> None:
    year = datetime.now(timezone.utc).year
    for h in hits:
        text = f"{h.title} {h.snippet}"
        m = _AGO.search(text)
        if m:
            if m.group(3):
                h.score *= 1.2
            else:
                n, unit = int(m.group(1)), m.group(2).lower()
                days = n / 24 if unit in ("hour", "hr") else n if unit == "day" else n * 7 if unit == "week" else n * 30
                h.score *= 1.2 if days <= 7 else 1.05 if days <= 21 else 0.7
        years = [int(y) for y in _OLD_YEAR.findall(h.title)]
        if years and max(years) < year:
            h.score *= 0.55                            # "… jobs December 2025" in a 2026 search
        if q.places or q.india:
            forms = [f for c in q.places for f in CITIES.get(c, [c])] + ["india"]
            local = any(f in text.lower() for f in forms)
            if local:
                h.score *= 1.12
            elif _FOREIGN.search(text):
                h.score *= 0.35


VERIFY_TOP = 18
VERIFY_BUDGET_S = 8.0


async def verify(hits: list[Hit], q: Query) -> list[Hit]:
    """Ask the employer's ATS about each top posting: closed ones go, the real place and date replace the snippet's guess."""
    from jobhunterx.discovery import ats
    todo = [(h, ats.parse_ats_url(h.url)) for h in hits if h.kind == "posting" and not h.via.startswith("board:")]
    todo = [(h, r) for h, r in todo if r and r.job_id and r.kind in ats.ADAPTERS][:VERIFY_TOP]
    if not todo:
        return hits
    sem = asyncio.Semaphore(8)

    async def one(ref):
        async with sem:
            return await ats.ADAPTERS[ref.kind].check(ref)

    tasks = [asyncio.ensure_future(one(r)) for _, r in todo]
    done, pending = await asyncio.wait(tasks, timeout=VERIFY_BUDGET_S)
    for t in pending:
        t.cancel()
    gone = set()
    now = datetime.now(timezone.utc)
    for (h, _), t in zip(todo, tasks):
        if t not in done or t.exception():
            continue
        state, job = t.result()
        if state == "gone":
            gone.add(id(h))
            continue
        if state != "live" or not job:
            continue
        age = (now - job.posted_at).days if job.posted_at else None
        h.company = job.company or h.company
        h.title = f"{job.title} — {job.company}" if job.company and job.company.lower() not in job.title.lower() else job.title
        h.snippet = (f"{job.location_raw or 'location not stated'}" + (f" · posted {age} days ago" if age is not None else "")
                     + " · verified open on the employer's job board")
        h.via += ",verified"
        if not _place_ok(job.location_raw, job.countries, q):
            h.score *= 0.2
        else:
            h.score *= 1.15 * (1.1 if age is not None and age <= 14 else 0.8 if age is not None and age > 90 else 1.0)
    log.info("deep_verify", checked=len(done), gone=len(gone), slow=len(pending))
    return [h for h in hits if id(h) not in gone]


# ---------------------------------------------------------------- 6. rerank
class _Score(BaseModel):
    i: int
    score: int = Field(ge=0, le=10, description="10 = an individual open job posting that matches the search; 0 = unrelated")


class _Rerank(BaseModel):
    scores: list[_Score] = Field(default_factory=list)


_RERANK_SYS = """You rank web search results for a job search. For each numbered result give a score 0-10:
10 = ONE currently open job posting that matches the role and place in the query (best on the employer's own site or ATS);
8 = the same but on a job board (LinkedIn, Naukri, Indeed…);
6 = the employer's own careers page / job board listing several matching roles;
2 = a page that only lists many jobs from many employers ("3,000 jobs in…");
0 = salary pages, people's profiles or portfolios, blogs, guides, courses, news, or a different role or country.
Judge only from the title, URL and snippet given. Return every index."""


async def rerank(query: str, hits: list[Hit], keep: int = 10) -> list[Hit]:
    top = hits[:RERANK_TOP]
    if len(top) < 3:
        return hits
    try:
        from jobhunterx.intelligence.llm_structured import call_structured
        lines = "\n".join(f"[{i}] {h.title[:110]} | {h.url[:120]} | {h.snippet[:170]}" for i, h in enumerate(top))
        res, _ = await asyncio.wait_for(
            call_structured(task="deep_rerank", version="v2", model=_Rerank, system=_RERANK_SYS,
                            user=f"Search: {query}\n\nResults:\n{lines}", chain="fast", max_tokens=900,
                            cache_parts=(query, *[h.url for h in top])), RERANK_BUDGET_S)
    except Exception as exc:                       # no AI available: keep fusion order
        log.debug("deep_rerank_skipped", error=str(exc)[:80])
        return hits
    if not res or not res.scores:
        return hits
    by_i = {s.i: s.score for s in res.scores if 0 <= s.i < len(top)}
    for i, h in enumerate(top):
        if i in by_i:
            h.score = h.score * (0.12 + by_i[i] / 10)     # meaning decides, fusion breaks ties
    ranked = sorted(hits, key=lambda h: -h.score)
    good = [h for i, h in enumerate(top) if by_i.get(i, 5) >= 4]
    if len(good) >= keep:                              # enough real results: drop what the model called irrelevant
        bad = {id(h) for i, h in enumerate(top) if by_i.get(i, 5) <= 2}
        ranked = [h for h in ranked if id(h) not in bad]
    return ranked


# ---------------------------------------------------------------- entry point
async def search(query: str, max_results: int = 10, use_ai: bool = True) -> list[Hit]:
    t0 = time.monotonic()
    q = understand(query)
    hits = await fan_out(query, _variants(q))
    ranked = sorted(hits.values(), key=lambda h: -h.score)
    # three independent steps at once: open pages, resolve companies to their boards, check ATS postings are still open
    crawled, resolved, alive = await asyncio.gather(crawl(ranked), resolve_companies(ranked, q), verify(ranked, q))
    kept = {id(h) for h in alive}
    for h in ranked:
        if id(h) not in kept:
            hits.pop(_norm(h.url), None)           # closed on the employer's board
    for h in crawled + resolved:
        key = _norm(h.url)
        if key in hits:
            hits[key].score += h.score * 0.5
            if h.kind == "posting":
                hits[key].kind = "posting"
        else:
            hits[key] = h
    ranked = list(hits.values())
    apply_signals(ranked, q)
    ranked.sort(key=lambda h: -h.score)
    if use_ai:
        ranked = await rerank(query, ranked, keep=max_results)
    # whatever the scores say: real postings and employer pages first, lists of jobs after, profiles and noise never
    ranked = [h for h in ranked if h.kind not in ("listing", "profile", "noise")] + [h for h in ranked if h.kind == "listing"]
    ranked = diversify(ranked)
    log.info("deep_search", query=query[:60], engines=sum(1 for e in _engines.values() if e.rest_until <= time.monotonic()),
             candidates=len(hits), crawled=len(crawled), first_party=len(resolved), ms=int((time.monotonic() - t0) * 1000))
    return ranked[:max_results]


def site_key(url: str) -> str:
    """One employer board per key on shared ATS hosts (greenhouse.io/acme ≠ greenhouse.io/other); else the host."""
    from jobhunterx.discovery import ats
    ref = ats.parse_ats_url(url)
    return f"{ref.kind}:{ref.token.lower()}" if ref else _host(url)


def diversify(hits: list, per_site: int = MAX_PER_SITE) -> list:
    """Keep order, but at most `per_site` results from one site and one copy of a title per site."""
    seen_site: dict[str, int] = {}
    seen_title: set[tuple[str, str]] = set()
    out = []
    for h in hits:
        k = site_key(h.url)
        t = (k, re.sub(r"\W+", " ", (h.title or "").lower()).strip())
        if seen_site.get(k, 0) >= per_site or (t[1] and t in seen_title):
            continue
        seen_site[k] = seen_site.get(k, 0) + 1
        seen_title.add(t)
        out.append(h)
    return out


def engine_status() -> dict:
    now = time.monotonic()
    return {e.name: ("resting" if e.rest_until > now else "ok") for e in _engines.values()}
