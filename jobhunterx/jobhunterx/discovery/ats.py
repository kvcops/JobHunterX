"""
First-party ATS integrations (public, unauthenticated job-board APIs).

Each adapter knows three things about one ATS:
  * how to recognise its job / board URLs (→ AtsRef),
  * how to list a company's open jobs as normalized JobPostings,
  * how to verify a single posting is still open (live / gone / unknown).

Data from these APIs is first-party (the employer's own hiring system), so
title, company board, location and dates are marked *verified*.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Literal, Optional
from urllib.parse import parse_qs, urlparse

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery.htmltext import html_to_text
from jobhunterx.discovery import net
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import AtsRef, FieldCheck, JobPosting, Salary, SourceRef
from jobhunterx.intelligence.text import parse_iso_datetime

log = get_logger("ats")

Liveness = Literal["live", "gone", "unknown"]


def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None


def _mode(value: str) -> WorkMode:
    v = (value or "").lower().replace("-", "").replace("_", "").replace(" ", "")
    if v in ("remote", "fullyremote"):
        return WorkMode.REMOTE
    if v == "hybrid":
        return WorkMode.HYBRID
    if v in ("onsite", "inoffice", "office"):
        return WorkMode.ONSITE
    return WorkMode.UNKNOWN


def _etype(value: str) -> str:
    v = re.sub(r"[^a-z]", "", (value or "").lower())
    return {"fulltime": "full_time", "parttime": "part_time", "contract": "contract", "contractor": "contract",
            "intern": "internship", "internship": "internship", "temporary": "temporary", "temp": "temporary"}.get(v, "")


class AtsAdapter(ABC):
    kind: str = ""
    url_patterns: tuple[str, ...] = ()       # regexes with (?P<token>) and optional (?P<job>)
    search_hosts: tuple[str, ...] = ()       # public job-page hosts, for site: searches

    def parse_url(self, url: str) -> Optional[AtsRef]:
        for pat in self.url_patterns:
            m = re.search(pat, url or "", re.I)
            if m:
                token = m.group("token")
                job = m.groupdict().get("job") or ""
                if token and token.lower() not in ("embed", "api", "v1", "jobs"):
                    return AtsRef(kind=self.kind, token=token, job_id=job)
        return None

    @abstractmethod
    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        """None = board unreachable/unknown; [] = board has no jobs."""

    async def search_jobs(self, token: str, queries: Optional[list[str]] = None) -> Optional[list[JobPosting]]:
        """Jobs worth looking at on this board. Small boards return everything; huge ones search by `queries`."""
        return await self.list_jobs(token)

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        jobs = await self.list_jobs(ref.token)
        if jobs is None:
            return "unknown", None
        for j in jobs:
            if j.ats and j.ats.job_id == ref.job_id:
                return "live", j
        return "gone", None

    def _posting(self, *, token: str, job_id: str, title: str, company: str, location: str, description: str,
                 url: str, apply_url: str = "", posted=None, mode: WorkMode = WorkMode.UNKNOWN,
                 employment_type: str = "", department: str = "", salary: Optional[Salary] = None,
                 countries: Optional[list[str]] = None) -> JobPosting:
        p = JobPosting(
            title=(title or "").strip(),
            company=(company or "").strip(),
            location_raw=(location or "").strip(),
            description=description,
            apply_url=apply_url or url,
            canonical_url=url,
            work_mode=mode,
            employment_type=employment_type,
            department=department or "",
            salary=salary,
            posted_at=parse_iso_datetime(posted),
            countries=countries or [],
            ats=AtsRef(kind=self.kind, token=token, job_id=str(job_id)),
            sources=[SourceRef(name=self.kind, kind="ats_api", url=url, first_party=True, confidence=0.95)],
        )
        checks = p.validation.checks
        checks["ats_confirmed"] = FieldCheck(status="verified", value=f"{self.kind}:{token}",
                                             evidence=f"Listed on the employer's {self.kind.title()} job board API")
        checks["title"] = FieldCheck(status="verified", value=p.title, evidence="ATS API")
        if p.location_raw:
            checks["location"] = FieldCheck(status="verified", value=p.location_raw, evidence="ATS API")
        if p.posted_at:
            checks["posted_at"] = FieldCheck(status="verified", value=p.posted_at.isoformat(), evidence="ATS API")
        if mode != WorkMode.UNKNOWN:
            checks["work_mode"] = FieldCheck(status="verified", value=mode.value, evidence="ATS API")
        if employment_type:
            checks["employment_type"] = FieldCheck(status="verified", value=employment_type, evidence="ATS API")
        if salary:
            checks["salary"] = FieldCheck(status="verified", value=salary.raw, evidence="ATS API")
        return p


class Greenhouse(AtsAdapter):
    search_hosts = ("job-boards.greenhouse.io", "boards.greenhouse.io")
    kind = "greenhouse"
    url_patterns = (
        r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?P<token>[\w\-]+)/jobs/(?P<job>\d+)",
        r"greenhouse\.io/embed/job_app\?(?:.*&)?for=(?P<token>[\w\-]+)(?:&.*?)?(?:&token=(?P<job>\d+))?",
        r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?P<token>[\w\-]+)/?(?:$|\?)",
        r"boards-api\.greenhouse\.io/v1/boards/(?P<token>[\w\-]+)",
    )

    def parse_url(self, url: str) -> Optional[AtsRef]:
        ref = super().parse_url(url)
        if ref and not ref.job_id:
            q = parse_qs(urlparse(url).query)
            ref.job_id = (q.get("token") or q.get("gh_jid") or [""])[0]
        return ref

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        data, res = await net.fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
        if not isinstance(data, dict):
            return None
        meta, _ = await net.fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}")
        company = (meta or {}).get("name") or token
        out = []
        for it in data.get("jobs") or []:
            loc = (it.get("location") or {}).get("name", "") if isinstance(it.get("location"), dict) else ""
            out.append(self._posting(
                token=token, job_id=str(it.get("id", "")), title=it.get("title", ""), company=company,
                location=loc, description=html_to_text(it.get("content", "")), url=it.get("absolute_url", ""),
                posted=_first(it.get("first_published"), it.get("updated_at")),
                department=", ".join(d.get("name", "") for d in it.get("departments") or [] if isinstance(d, dict)),
            ))
        return out

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        if not ref.job_id:
            return "unknown", None
        data, res = await net.fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{ref.token}/jobs/{ref.job_id}")
        if res.status == 404:
            return "gone", None
        if not isinstance(data, dict):
            return "unknown", None
        loc = (data.get("location") or {}).get("name", "") if isinstance(data.get("location"), dict) else ""
        return "live", self._posting(
            token=ref.token, job_id=ref.job_id, title=data.get("title", ""), company=data.get("company_name") or ref.token,
            location=loc, description=html_to_text(data.get("content", "")), url=data.get("absolute_url", ""),
            posted=_first(data.get("first_published"), data.get("updated_at")),
        )


class Lever(AtsAdapter):
    search_hosts = ("jobs.lever.co",)
    kind = "lever"
    url_patterns = (
        r"jobs(?:\.eu)?\.lever\.co/(?P<token>[\w\-]+)/(?P<job>[0-9a-f\-]{36})",
        r"jobs(?:\.eu)?\.lever\.co/(?P<token>[\w\-]+)/?(?:$|\?)",
        r"api(?:\.eu)?\.lever\.co/v0/postings/(?P<token>[\w\-]+)",
    )

    def _to_posting(self, token: str, it: dict) -> JobPosting:
        cats = it.get("categories") or {}
        lists = "\n".join(f"{l.get('text', '')}\n{html_to_text(l.get('content', ''))}" for l in it.get("lists") or [])
        desc = "\n".join(x for x in [it.get("descriptionPlain") or html_to_text(it.get("description", "")), lists,
                                     it.get("additionalPlain") or ""] if x)
        sr = it.get("salaryRange") or {}
        salary = None
        if sr.get("min") is not None:
            salary = Salary(min=sr.get("min"), max=sr.get("max"), currency=sr.get("currency", ""),
                            period={"per-year-salary": "year", "per-month-salary": "month",
                                    "per-hour-wage": "hour"}.get(sr.get("interval", ""), "year"),
                            raw=f"{sr.get('min')}–{sr.get('max')} {sr.get('currency', '')}")
        return self._posting(
            token=token, job_id=it.get("id", ""), title=it.get("text", ""), company=token,
            location=cats.get("location", "") or ", ".join(cats.get("allLocations") or []),
            description=desc, url=it.get("hostedUrl", ""), apply_url=it.get("applyUrl", ""),
            posted=it.get("createdAt"), mode=_mode(it.get("workplaceType", "")),
            employment_type=_etype(cats.get("commitment", "")), department=cats.get("team", ""),
            salary=salary, countries=[it["country"]] if it.get("country") else [],
        )

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        data, _ = await net.fetch_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        if not isinstance(data, list):
            return None
        return [self._to_posting(token, it) for it in data if isinstance(it, dict)]

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        if not ref.job_id:
            return "unknown", None
        data, res = await net.fetch_json(f"https://api.lever.co/v0/postings/{ref.token}/{ref.job_id}?mode=json")
        if res.status == 404:
            return "gone", None
        if not isinstance(data, dict):
            return "unknown", None
        return "live", self._to_posting(ref.token, data)


class Ashby(AtsAdapter):
    search_hosts = ("jobs.ashbyhq.com",)
    kind = "ashby"
    url_patterns = (
        r"jobs\.ashbyhq\.com/(?P<token>[^/?#]+)/(?P<job>[0-9a-f\-]{36})",
        r"jobs\.ashbyhq\.com/(?P<token>[^/?#]+)/?(?:$|\?)",
        r"api\.ashbyhq\.com/posting-api/job-board/(?P<token>[^/?#]+)",
    )

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        data, _ = await net.fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true")
        if not isinstance(data, dict):
            return None
        out = []
        for it in data.get("jobs") or []:
            if it.get("isListed") is False:
                continue
            locs = [it.get("location", "")] + [s.get("location", "") for s in it.get("secondaryLocations") or [] if isinstance(s, dict)]
            mode = _mode(it.get("workplaceType", "")) if it.get("workplaceType") else (WorkMode.REMOTE if it.get("isRemote") else WorkMode.UNKNOWN)
            comp = (it.get("compensation") or {}).get("compensationTierSummary") or ""
            out.append(self._posting(
                token=token, job_id=it.get("id", ""), title=it.get("title", ""), company=token,
                location="; ".join(l for l in locs if l), description=it.get("descriptionPlain") or html_to_text(it.get("descriptionHtml", "")),
                url=it.get("jobUrl", ""), apply_url=it.get("applyUrl", ""), posted=it.get("publishedAt"),
                mode=mode, employment_type=_etype(it.get("employmentType", "")), department=it.get("department", ""),
                salary=Salary(raw=comp) if comp else None,
            ))
        return out


class SmartRecruiters(AtsAdapter):
    search_hosts = ("jobs.smartrecruiters.com",)
    kind = "smartrecruiters"
    url_patterns = (
        r"(?:jobs|careers)\.smartrecruiters\.com/(?P<token>[\w\-]+)/(?P<job>\d+)",
        r"(?:jobs|careers)\.smartrecruiters\.com/(?P<token>[\w\-]+)/?(?:$|\?)",
        r"api\.smartrecruiters\.com/v1/companies/(?P<token>[\w\-]+)",
    )

    def _to_posting(self, token: str, it: dict, description: str = "") -> JobPosting:
        loc = it.get("location") or {}
        mode = WorkMode.REMOTE if loc.get("remote") else (WorkMode.HYBRID if loc.get("hybrid") else WorkMode.UNKNOWN)
        return self._posting(
            token=token, job_id=str(it.get("id", "")), title=it.get("name", ""),
            company=(it.get("company") or {}).get("name") or token,
            location=", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x),
            description=description, url=it.get("postingUrl") or f"https://jobs.smartrecruiters.com/{token}/{it.get('id')}",
            apply_url=it.get("applyUrl", ""), posted=it.get("releasedDate"), mode=mode,
            employment_type=_etype((it.get("typeOfEmployment") or {}).get("label", "")),
            department=(it.get("department") or {}).get("label", ""),
        )

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        out, offset = [], 0
        while offset < 500:
            data, _ = await net.fetch_json(f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100&offset={offset}")
            if not isinstance(data, dict):
                return None if not out else out
            chunk = data.get("content") or []
            out += [self._to_posting(token, it) for it in chunk]
            offset += len(chunk)
            if not chunk or offset >= int(data.get("totalFound") or 0):
                break
        return out

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        if not ref.job_id:
            return "unknown", None
        data, res = await net.fetch_json(f"https://api.smartrecruiters.com/v1/companies/{ref.token}/postings/{ref.job_id}")
        if res.status == 404:
            return "gone", None
        if not isinstance(data, dict):
            return "unknown", None
        if data.get("active") is False:
            return "gone", None
        sections = (data.get("jobAd") or {}).get("sections") or {}
        desc = "\n".join(html_to_text((sections.get(k) or {}).get("text", "")) for k in sections)
        return "live", self._to_posting(ref.token, data, desc)


class Recruitee(AtsAdapter):
    search_hosts = ("recruitee.com",)
    kind = "recruitee"
    url_patterns = (r"(?P<token>[\w\-]+)\.recruitee\.com/o/(?P<job>[\w\-]+)", r"(?P<token>[\w\-]+)\.recruitee\.com")

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        data, _ = await net.fetch_json(f"https://{token}.recruitee.com/api/offers/")
        if not isinstance(data, dict):
            return None
        out = []
        for it in data.get("offers") or []:
            mode = WorkMode.REMOTE if it.get("remote") else WorkMode.HYBRID if it.get("hybrid") else \
                WorkMode.ONSITE if it.get("on_site") else WorkMode.UNKNOWN
            desc = html_to_text((it.get("description") or "") + "\n" + (it.get("requirements") or ""))
            p = self._posting(token=token, job_id=it.get("slug", ""), title=it.get("title", ""),
                              company=it.get("company_name") or token, location=it.get("location", ""), description=desc,
                              url=it.get("careers_url", ""), apply_url=it.get("careers_apply_url", ""),
                              posted=it.get("published_at"), mode=mode,
                              employment_type=_etype(it.get("employment_type_code", "")))
            out.append(p)
        return out


class Workable(AtsAdapter):
    search_hosts = ("apply.workable.com",)
    kind = "workable"
    url_patterns = (r"apply\.workable\.com/(?P<token>[\w\-]+)/j/(?P<job>[A-Z0-9]+)", r"apply\.workable\.com/(?P<token>[\w\-]+)/?(?:$|\?)")

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        data, _ = await net.fetch_json(f"https://apply.workable.com/api/v1/widget/accounts/{token}?details=true")
        if not isinstance(data, dict):
            return None
        company = data.get("name") or token
        out = []
        for it in data.get("jobs") or []:
            loc = ", ".join(x for x in [it.get("city"), it.get("state"), it.get("country")] if x)
            mode = WorkMode.REMOTE if it.get("telecommuting") else WorkMode.UNKNOWN
            out.append(self._posting(token=token, job_id=it.get("shortcode", ""), title=it.get("title", ""),
                                     company=company, location=loc, description=html_to_text(it.get("description", "")),
                                     url=it.get("url") or it.get("shortlink", ""), apply_url=it.get("application_url", ""),
                                     posted=it.get("published_on") or it.get("created_at"), mode=mode,
                                     employment_type=_etype(it.get("employment_type", ""))))
        return out


class Workday(AtsAdapter):
    """Workday career sites (most GCCs in India hire through Workday).

    Token: "<tenant>.<wdN>/<site>", e.g. "acme.wd5/AcmeCareers". Boards can hold
    thousands of jobs, so listing is a keyword search, not a full download.
    """
    search_hosts = ("myworkdayjobs.com",)
    kind = "workday"
    _URL = re.compile(r"(?P<tenant>[\w\-]+)\.(?P<wd>wd\d+)\.myworkdayjobs\.com/(?:wday/cxs/[\w\-]+/)?"
                      r"(?:[a-z]{2}-[A-Z]{2}/)?(?P<site>[\w\-]+)(?:/job/(?P<path>[^?#]+))?", re.I)
    DEFAULT_QUERIES = ("AI engineer", "machine learning", "generative AI", "LLM")
    PER_QUERY = 40
    MAX_DETAILS = 30

    def parse_url(self, url: str) -> Optional[AtsRef]:
        m = self._URL.search(url or "")
        if not m or m.group("site").lower() in ("job", "wday", "cxs"):
            return None
        return AtsRef(kind=self.kind, token=f"{m.group('tenant')}.{m.group('wd')}/{m.group('site')}",
                      job_id=(m.group("path") or "").strip("/"))

    @staticmethod
    def _base(token: str) -> tuple[str, str, str]:
        host, _, site = token.partition("/")
        tenant = host.split(".")[0]
        return f"https://{host}.myworkdayjobs.com", tenant, site

    async def _detail(self, token: str, path: str) -> tuple[Liveness, Optional[JobPosting]]:
        root, tenant, site = self._base(token)
        data, res = await net.fetch_json(f"{root}/wday/cxs/{tenant}/{site}/job/{path}")
        if res.status in (404, 410):
            return "gone", None
        info = (data or {}).get("jobPostingInfo") if isinstance(data, dict) else None
        if not isinstance(info, dict):
            return "unknown", None
        if info.get("canApply") is False or info.get("posted") is False:
            return "gone", None
        locs = [info.get("location", "")] + list(info.get("additionalLocations") or [])
        country = (info.get("country") or {}).get("descriptor", "") if isinstance(info.get("country"), dict) else ""
        remote = str(info.get("remoteType") or "").lower()
        mode = WorkMode.REMOTE if "remote" in remote else WorkMode.HYBRID if "hybrid" in remote else _mode(remote)
        url = info.get("externalUrl") or f"{root}/{site}/job/{path}"
        return "live", self._posting(
            token=token, job_id=path, title=info.get("title", ""),
            company=((data.get("hiringOrganization") or {}).get("name") or tenant).strip(),
            location="; ".join(l for l in locs if l), description=html_to_text(info.get("jobDescription", "")),
            url=url, apply_url=f"{url.rstrip('/')}/apply" if "/apply" not in url else url, posted=info.get("startDate"),
            mode=mode, employment_type=_etype(info.get("timeType", "")), countries=[country] if country else [],
        )

    async def search_jobs(self, token: str, queries: Optional[list[str]] = None) -> Optional[list[JobPosting]]:
        root, tenant, site = self._base(token)
        paths: dict[str, None] = {}
        reached = False
        pages = await asyncio.gather(*(
            net.fetch_json(f"{root}/wday/cxs/{tenant}/{site}/jobs", method="POST",
                           json_body={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q})
            for q in (queries or self.DEFAULT_QUERIES)[:4]))
        for data, _ in pages:
            if not isinstance(data, dict):
                continue
            reached = True
            for it in (data.get("jobPostings") or [])[: self.PER_QUERY]:
                path = str(it.get("externalPath") or "").split("/job/", 1)[-1].strip("/")
                if path:
                    paths.setdefault(path)
        if not reached:
            return None
        sem = asyncio.Semaphore(5)

        async def one(path: str) -> Optional[JobPosting]:
            async with sem:
                state, p = await self._detail(token, path)
                return p if state == "live" else None

        found = await asyncio.gather(*(one(p) for p in list(paths)[: self.MAX_DETAILS]))
        return [p for p in found if p]

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        return await self.search_jobs(token)

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        if not ref.job_id:
            return "unknown", None
        return await self._detail(ref.token, ref.job_id)


class Keka(AtsAdapter):
    """Keka hiring portals (common with Indian product companies, especially in Hyderabad).

    Token: the portal host, e.g. "acme.keka.com". Experience ranges are given
    per job ("1-3").
    """
    search_hosts = ()                      # Keka job pages aren't indexed usefully; polled via the watchlist
    kind = "keka"
    _URL = re.compile(r"(?P<host>[\w\-]+\.keka\.com)/careers", re.I)

    def parse_url(self, url: str) -> Optional[AtsRef]:
        m = self._URL.search(url or "")
        if not m:
            return None
        job = re.search(r"/careers/jobdetails/(\d+)", url)
        return AtsRef(kind=self.kind, token=m.group("host").lower(), job_id=job.group(1) if job else "")

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        host = token.split("/")[0]
        data, _ = await net.fetch_json(f"https://{host}/careers/api/jobs/default/active")
        if not isinstance(data, list):
            return None
        out = []
        for it in data:
            if not isinstance(it, dict):
                continue
            locs = [l for l in it.get("jobLocations") or [] if isinstance(l, dict)]
            loc = "; ".join(", ".join(x for x in [l.get("city"), l.get("countryName")] if x) for l in locs)
            exp = str(it.get("experience") or "").strip()
            desc = html_to_text(it.get("description", ""))
            if exp and "experience" not in desc[:300].lower():
                desc = f"Experience: {exp} years\n{desc}"     # stated on the board, not always in the text
            url = f"https://{host}/careers/jobdetails/{it.get('id')}"
            out.append(self._posting(
                token=token, job_id=str(it.get("id", "")), title=it.get("title", ""), company=host.split(".")[0],
                location=loc, description=desc, url=url, posted=it.get("publishedOn"),
                department=it.get("departmentName", ""),
                countries=list(dict.fromkeys(l.get("countryName") for l in locs if l.get("countryName"))),
            ))
        return out


class OracleRecruiting(AtsAdapter):
    """Oracle Recruiting Cloud career sites (JPMorgan, Oracle and many large employers / GCCs in India).

    Token: "<host>/<site>", e.g. "jpmc.fa.oraclecloud.com/CX_1001". The career site's own page reads these public
    REST endpoints; boards hold thousands of jobs, so listing is a keyword search, then a detail read per job.
    """
    kind = "oracle"
    search_hosts = ("oraclecloud.com/hcmUI/CandidateExperience",)
    _URL = re.compile(r"(?P<host>[\w\-]+(?:\.[\w\-]+)*\.oraclecloud\.com)/hcmUI/CandidateExperience/[\w\-]+/sites/"
                      r"(?P<site>[\w\-]+)(?:/(?:job|requisitions/preview)/(?P<job>\d+))?", re.I)
    DEFAULT_QUERIES = ("engineer", "developer", "analyst")
    PER_QUERY = 25
    MAX_DETAILS = 30

    def parse_url(self, url: str) -> Optional[AtsRef]:
        m = self._URL.search(url or "")
        if not m:
            return None
        return AtsRef(kind=self.kind, token=f"{m.group('host').lower()}/{m.group('site')}", job_id=m.group("job") or "")

    @staticmethod
    def _split(token: str) -> tuple[str, str]:
        host, _, site = token.partition("/")
        return host, site

    async def _detail(self, token: str, job_id: str, hint: Optional[dict] = None) -> tuple[Liveness, Optional[JobPosting]]:
        host, site = self._split(token)
        url = (f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
               f"&finder=ById;Id=%22{job_id}%22,siteNumber={site}")
        data, res = await net.fetch_json(url)
        if res.status in (404, 410):
            return "gone", None
        if not isinstance(data, dict):
            return "unknown", None
        items = data.get("items") or []
        if not items:
            return "gone", None
        it = items[0]
        hint = hint or {}
        locs = [it.get("PrimaryLocation") or hint.get("PrimaryLocation") or ""]
        locs += [l.get("Name", "") for l in (it.get("secondaryLocations") or hint.get("secondaryLocations") or []) if isinstance(l, dict)]
        workplace = str(it.get("WorkplaceType") or hint.get("WorkplaceType") or "").lower()
        mode = WorkMode.REMOTE if "remote" in workplace else WorkMode.HYBRID if "hybrid" in workplace else \
            WorkMode.ONSITE if "site" in workplace or "office" in workplace else WorkMode.UNKNOWN
        parts = [it.get("ExternalDescriptionStr"), it.get("ExternalResponsibilitiesStr"), it.get("ExternalQualificationsStr"),
                 it.get("CorporateDescriptionStr")]
        description = "\n\n".join(html_to_text(x) for x in parts if x)
        page_url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{job_id}"
        country = it.get("PrimaryLocationCountry") or hint.get("PrimaryLocationCountry") or ""
        return "live", self._posting(
            token=token, job_id=str(job_id), title=it.get("Title") or hint.get("Title", ""),
            company=(it.get("LegalEmployer") or hint.get("LegalEmployer") or host.split(".")[0]).strip(),
            location="; ".join(l for l in dict.fromkeys(locs) if l), description=description, url=page_url,
            apply_url=f"{page_url}/apply", posted=it.get("ExternalPostedStartDate") or hint.get("PostedDate"), mode=mode,
            employment_type=_etype(it.get("JobSchedule") or hint.get("JobSchedule") or ""),
            department=it.get("JobFunction") or hint.get("JobFunction") or "",
            countries=[_COUNTRY_CODES.get(country, country)] if country else [],
        )

    COUNTRY = "India"              # JobHunterX searches India; the board's own location filter keeps results local
    _country_ids: dict[str, Optional[int]] = {}

    async def _country_id(self, host: str, site: str) -> Optional[int]:
        """The board's location-facet id for India (keyword search matches titles only, so location must be a filter)."""
        key = f"{host}/{site}"
        if key not in self._country_ids:
            data, _ = await net.fetch_json(
                f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=locationsFacet"
                f"&finder=findReqs;siteNumber={site},facetsList=LOCATIONS,limit=1")
            facets = [f for b in ((data or {}).get("items") or []) if isinstance(b, dict) for f in b.get("locationsFacet") or []]
            hit = next((f for f in facets if str(f.get("Name", "")).strip().lower() == self.COUNTRY.lower()), None)
            self._country_ids[key] = int(hit["Id"]) if hit and hit.get("Id") else None
        return self._country_ids[key]

    async def search_jobs(self, token: str, queries: Optional[list[str]] = None) -> Optional[list[JobPosting]]:
        from urllib.parse import quote
        host, site = self._split(token)
        found: dict[str, dict] = {}
        reached = False
        loc_id = await self._country_id(host, site)
        loc = f"locationId={loc_id}," if loc_id else ""
        pages = await asyncio.gather(*(
            net.fetch_json(f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
                           f"&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber={site},{loc}"
                           f"limit={self.PER_QUERY},sortBy=POSTING_DATES_DESC,keyword=%22{quote(q)}%22")
            for q in (queries or self.DEFAULT_QUERIES)[:4]))
        for data, _ in pages:
            if not isinstance(data, dict):
                continue
            reached = True
            for block in data.get("items") or []:
                for r in block.get("requisitionList") or []:
                    if r.get("Id"):
                        found.setdefault(str(r["Id"]), r)
        if not reached:
            return None
        sem = asyncio.Semaphore(5)

        async def one(job_id: str, hint: dict) -> Optional[JobPosting]:
            async with sem:
                state, p = await self._detail(token, job_id, hint)
                return p if state == "live" else None

        got = await asyncio.gather(*(one(i, h) for i, h in list(found.items())[: self.MAX_DETAILS]))
        return [p for p in got if p]

    async def list_jobs(self, token: str) -> Optional[list[JobPosting]]:
        return await self.search_jobs(token)

    async def check(self, ref: AtsRef) -> tuple[Liveness, Optional[JobPosting]]:
        if not ref.job_id:
            return "unknown", None
        return await self._detail(ref.token, ref.job_id)


_COUNTRY_CODES = {"IN": "India", "US": "United States", "GB": "United Kingdom", "SG": "Singapore", "IE": "Ireland",
                  "DE": "Germany", "CA": "Canada", "AU": "Australia", "PH": "Philippines", "PL": "Poland"}


ADAPTERS: dict[str, AtsAdapter] = {a.kind: a for a in [Greenhouse(), Lever(), Ashby(), SmartRecruiters(), Recruitee(),
                                                       Workable(), Workday(), Keka(), OracleRecruiting()]}


def parse_ats_url(url: str) -> Optional[AtsRef]:
    for a in ADAPTERS.values():
        ref = a.parse_url(url)
        if ref:
            return ref
    return None


def ats_site_hints() -> list[str]:
    """Job-board hostnames of the supported ATSs (used for site: search queries)."""
    return [h for a in ADAPTERS.values() for h in a.search_hosts]
