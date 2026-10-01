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


ADAPTERS: dict[str, AtsAdapter] = {a.kind: a for a in [Greenhouse(), Lever(), Ashby(), SmartRecruiters(), Recruitee(), Workable()]}


def parse_ats_url(url: str) -> Optional[AtsRef]:
    for a in ADAPTERS.values():
        ref = a.parse_url(url)
        if ref:
            return ref
    return None


def ats_site_hints() -> list[str]:
    """Job-board hostnames of the supported ATSs (used for site: search queries)."""
    return [h for a in ADAPTERS.values() for h in a.search_hosts]
