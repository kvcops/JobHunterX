"""
Search run orchestration — the full discovery → ranking pipeline.

  understand → plan → discover → normalize → dedupe → validate → extract → match → rank

* One active run at a time; starting a new run cancels the previous one.
* Every event and every stored job carries the run id, so clients can ignore
  stale events from a cancelled run.
* Jobs are processed in small chunks after deduplication, so ranked results
  stream to the UI while the run continues.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.discovery import ats, dedupe, page, search, validate
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import JobPosting
from jobhunterx.intelligence import job as job_ai
from jobhunterx.intelligence.matching import assess, build_idf, candidate_work_text
from jobhunterx.intelligence.text import term_in_text, tokens
from jobhunterx.services import profile as profile_svc
from jobhunterx.services.jobs import summary

log = get_logger("search_run")

Emit = Callable[[dict], Awaitable[None]]

STAGES = [
    ("understand", "Understanding your profile"),
    ("plan", "Planning searches"),
    ("discover", "Discovering postings"),
    ("normalize", "Reading job pages"),
    ("dedupe", "Removing duplicates"),
    ("validate", "Verifying postings"),
    ("extract", "Extracting requirements"),
    ("match", "Matching against your profile"),
    ("rank", "Ranking & explaining"),
]

# Plain-language "who is doing what" feed shown live in the UI. Every line is
# generated from what the pipeline actually just did — nothing is scripted.
AGENTS = {
    "understand": "Profile analyst", "plan": "Planner", "discover": "Scout", "normalize": "Reader",
    "dedupe": "Curator", "validate": "Verifier", "extract": "Analyst", "match": "Analyst", "rank": "Ranker",
}
FEED_KEEP = 150
READ_NARRATE_MAX = 12
VERDICT_WORDS = {"strong": "Strong match", "good": "Good match", "stretch": "Stretch", "weak": "Weak match",
                 "incompatible": "Not a fit"}

CHUNK = 6
FETCH_CONCURRENCY = 6
BOARD_JOBS_PER_BOARD = 15


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run(profile_hash: str) -> dict:
    return {
        "id": str(uuid.uuid4()), "status": "queued", "started_at": _now(), "finished_at": None,
        "stage": "understand",
        "stages": [{"key": k, "label": label, "status": "pending", "detail": ""} for k, label in STAGES],
        "counts": {k: 0 for k in ("queries", "search_results", "candidates", "duplicates", "fetched", "invalid",
                                  "scored", "recommended", "rejected")},
        "plan": None, "error": None, "profile_hash": profile_hash,
        "total": 0, "activity": [],
    }


def _pretty_board(token: str) -> str:
    return token.replace("-", " ").replace("_", " ").strip().title() or token


def _job_ref(p: JobPosting) -> dict:
    return {"id": p.id, "title": p.title or "Untitled role", "company": p.company or "Unknown company"}


def _years(p: JobPosting) -> str:
    r = p.requirements
    if r.experience_min is None:
        return "no stated experience requirement"
    if r.experience_max is not None and r.experience_max != r.experience_min:
        return f"{r.experience_min:g}–{r.experience_max:g} years"
    return f"{r.experience_min:g}+ years"


class Run:
    def __init__(self, data: dict, emit: Emit):
        self.data = data
        self._emit = emit
        self._seq = 0

    @property
    def id(self) -> str:
        return self.data["id"]

    async def publish(self) -> None:
        await storage.save_run(self.data)
        await self._emit({"type": "search.run", "run_id": self.id, "data": {"run": self.data}, "ts": _now()})

    async def stage(self, key: str, status: str = "running", detail: str = "") -> None:
        for st in self.data["stages"]:
            if st["key"] == key:
                st["status"] = status
                if detail:
                    st["detail"] = detail
        if status == "running":
            self.data["stage"] = key
        await self.publish()

    async def say(self, stage: str, message: str, kind: str = "info", job: Optional[dict] = None) -> None:
        """Append one human-readable activity line and stream it to the UI.

        kind: work (in progress) · info · good · warn · reject · done
        """
        self._seq += 1
        item = {"id": self._seq, "ts": _now(), "stage": stage, "agent": AGENTS.get(stage, "JobHunterX"),
                "kind": kind, "message": message}
        if job:
            item["job"] = job
        feed = self.data.setdefault("activity", [])
        feed.append(item)
        del feed[:-FEED_KEEP]
        await self._emit({"type": "search.activity", "run_id": self.id, "data": {"item": item}, "ts": item["ts"]})

    async def log(self, message: str, level: str = "info") -> None:
        await self._emit({"type": "log", "run_id": self.id, "message": message,
                          "data": {"level": level, "source": "search"}, "ts": _now()})


def _location_prefilter(job: JobPosting, snap: CandidateSnapshot, include_remote: bool) -> bool:
    """Cheap check for board expansion: keep jobs at candidate places or remote."""
    text = "; ".join([job.location_raw, *job.locations, *job.countries])
    if not text.strip(" ;"):
        return True
    if include_remote and (job.work_mode == WorkMode.REMOTE or term_in_text(WorkMode.REMOTE.value, text)):
        return True
    forms = {f for p in snap.locations for f in [p.city, p.country, *p.aliases] if f}
    if snap.willing_to_relocate and snap.home_country:
        forms.add(snap.home_country)
    if snap.open_to_international:
        return True
    return any(term_in_text(f, text) for f in forms)


def _title_relevance(job: JobPosting, snap: CandidateSnapshot) -> float:
    jt = set(tokens(job.title))
    best = 0.0
    for label in [*snap.target_titles, *snap.adjacent_titles, *[f.label for f in snap.role_families]]:
        lt = set(tokens(label))
        if jt and lt:
            best = max(best, len(jt & lt) / len(jt | lt))
    return best


async def _expand_boards(refs: list, snap: CandidateSnapshot, include_remote: bool,
                         skip_llm: set[str]) -> list[JobPosting]:
    """For each discovered ATS board, pull its open jobs and keep the relevant ones.

    Jobs outside the candidate's locations are kept (so the user can see why
    they were excluded) but marked to skip LLM analysis — their location
    already makes them incompatible, so spending a model call would be waste.
    """
    out: list[JobPosting] = []

    async def one(ref):
        jobs = await ats.ADAPTERS[ref.kind].list_jobs(ref.token)
        if not jobs:
            return []
        for j in jobs:
            j.id = j.id or str(uuid.uuid4())
            if not _location_prefilter(j, snap, include_remote):
                skip_llm.add(j.id)
        keep = [(j, _title_relevance(j, snap)) for j in jobs]
        keep = [jr for jr in keep if jr[1] > 0]
        keep.sort(key=lambda jr: -jr[1])
        return [j for j, _ in keep[:BOARD_JOBS_PER_BOARD]]

    results = await asyncio.gather(*(one(r) for r in refs), return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            out += r
    return out


async def execute(run: Run, profile: CandidateProfile, request: dict) -> None:
    settings = get_settings()
    max_jobs = int(request.get("max_jobs") or settings.max_jobs_per_search)
    c = run.data["counts"]

    # 1. Understand ----------------------------------------------------------
    run.data["status"] = "running"
    await run.stage("understand")
    await run.say("understand", "Reading your profile — experience, skills and what you want next", "work")
    snap = await profile_svc.get_snapshot(profile)
    if request.get("include_international"):
        snap = snap.model_copy(update={"open_to_international": True})
    await run.stage("understand", "done",
                    f"{snap.professional_years:g} yrs · {snap.seniority.value} · "
                    + ", ".join(f.label for f in snap.role_families[:3]))
    tracks = ", ".join(f.label for f in snap.role_families[:2]) or "your field"
    await run.say("understand", f"You read as a {snap.seniority.value} profile with about {snap.professional_years:g} years "
                  f"of experience, strongest in {tracks}", "good")

    # 2. Plan -----------------------------------------------------------------
    await run.stage("plan")
    await run.say("plan", "Deciding which titles and places to search", "work")
    scope = search.scope_from_snapshot(snap, locations=request.get("locations") or None,
                                       role_focus=request.get("role_focus") or None,
                                       work_modes=request.get("work_modes") or None)
    max_queries = max(4, min(16, max_jobs // 4))
    queries, plan_method = await search.plan_queries(snap, scope, max_queries)
    c["queries"] = len(queries)
    run.data["plan"] = {"role_families": [f.label for f in snap.role_families], "titles": scope.titles,
                        "locations": scope.locations, "queries": queries, "method": plan_method}
    await run.stage("plan", "done", f"{len(queries)} queries across {len(scope.titles)} titles")
    where = ", ".join(scope.locations[:3]) or "your preferred locations"
    titles = ", ".join(scope.titles[:3]) + (f" and {len(scope.titles) - 3} more" if len(scope.titles) > 3 else "")
    await run.say("plan", f"Looking for {titles} in {where} — {len(queries)} searches planned", "info")

    # 3. Discover -------------------------------------------------------------
    await run.stage("discover")
    await run.say("discover", f"Searching job sites and company career pages ({len(queries)} searches)", "work")
    leads = await search.run_queries(queries)
    c["search_results"] = len(leads)
    posting_leads, boards = [], {}
    for lead in leads:
        ref = ats.parse_ats_url(lead.url)
        if ref and not ref.job_id:
            boards[(ref.kind, ref.token.lower())] = ref
        else:
            posting_leads.append(lead)
            if ref:
                boards.setdefault((ref.kind, ref.token.lower()), ref.model_copy(update={"job_id": ""}))
    await run.say("discover", f"Found {len(leads)} search results"
                  + (f", including {len(boards)} company career boards" if boards else ""), "info")
    skip_llm: set[str] = set()
    board_refs = list(boards.values())[:12]
    for ref in board_refs[:6]:
        await run.say("discover", f"Opening {_pretty_board(ref.token)}'s careers board on {ref.kind.title()}", "work")
    board_jobs = await _expand_boards(board_refs, snap, scope.include_remote, skip_llm)
    if board_refs:
        await run.say("discover", f"Pulled {len(board_jobs)} relevant openings straight from employer boards", "good")
    await run.stage("discover", "done", f"{len(leads)} search results · {len(boards)} employer job boards")

    # 4. Normalize ------------------------------------------------------------
    await run.stage("normalize")
    sem = asyncio.Semaphore(FETCH_CONCURRENCY)
    to_read = posting_leads[: max_jobs * 2]
    if to_read:
        await run.say("normalize", f"Opening {len(to_read)} job pages to read the full descriptions", "work")
    narrated = {"n": 0}

    async def resolve(lead) -> Optional[JobPosting]:
        async with sem:
            try:
                p, _ = await page.posting_from_url(lead.url, hint_title=lead.title, hint_snippet=lead.snippet)
            except Exception as exc:
                log.debug("lead_resolve_failed", url=lead.url[:80], error=str(exc)[:100])
                return None
        if p:
            p.discovered_by_query = lead.query
            narrated["n"] += 1
            if narrated["n"] <= READ_NARRATE_MAX:
                await run.say("normalize", f"Read “{p.title or 'a posting'}” at {p.company or 'an employer'}", "info", job=None)
        return p

    resolved = await asyncio.gather(*(resolve(l) for l in to_read))
    candidates = [p for p in resolved if p] + board_jobs
    c["fetched"] = len([p for p in resolved if p])
    c["candidates"] = len(candidates)
    await run.stage("normalize", "done", f"{len(candidates)} postings read ({len(board_jobs)} from employer boards)")
    unreadable = len(to_read) - c["fetched"]
    await run.say("normalize", f"{len(candidates)} postings ready to check"
                  + (f" — {unreadable} pages couldn't be read and were skipped" if unreadable > 0 else ""), "info")

    # 5. Dedupe ---------------------------------------------------------------
    await run.stage("dedupe")
    await run.say("dedupe", "Looking for the same job posted on several sites", "work")
    unique, dups = dedupe.deduplicate(candidates)
    c["duplicates"] = dups
    for p in unique:
        p.id = p.id or str(uuid.uuid4())
    unique.sort(key=lambda p: (-(p.primary_source.first_party if p.primary_source else 0), -_title_relevance(p, snap)))
    unique = unique[:max_jobs]
    run.data["total"] = len(unique)
    await run.stage("dedupe", "done", f"{dups} duplicates merged · {len(unique)} unique")
    await run.say("dedupe", (f"Merged {dups} duplicate listings — " if dups else "No duplicates — ")
                  + f"{len(unique)} unique jobs to analyse, employer sources first", "good" if dups else "info")

    # 6–9. Validate → extract → match → rank, streamed in chunks --------------
    text = candidate_work_text(profile.model_dump(mode="json"))
    idf = build_idf([p.description for p in unique] + [text])
    llm_budget = settings.max_llm_jd_extractions_per_search
    for key in ("validate", "extract", "match", "rank"):
        await run.stage(key)
    best: Optional[tuple[int, JobPosting]] = None
    for i in range(0, len(unique), CHUNK):
        chunk = unique[i:i + CHUNK]

        async def check(p: JobPosting):
            listed_now = bool(p.ats and p.sources and p.sources[0].kind == "ats_api" and p.validation.status != "closed")
            live = ("live", f"{p.ats.kind.title()} API: listed now") if listed_now else await validate.check_liveness(p)
            validate.finalize(p, live)

        await run.say("validate", f"Checking that the next {len(chunk)} jobs are real and still open", "work")
        await asyncio.gather(*(check(p) for p in chunk))
        for p in chunk:
            ref, st = _job_ref(p), p.validation.status
            name = f"{ref['title']} at {ref['company']}"
            if st in ("active", "likely_active"):
                await run.say("validate", f"{name} is live and accepting applications", "good", ref)
            elif st == "closed":
                await run.say("validate", f"{name} has closed — it won't be recommended", "reject", ref)
            elif st == "invalid":
                await run.say("validate", f"“{ref['title']}” isn't a real job posting — skipped", "reject", ref)
            elif st == "stale":
                await run.say("validate", f"{name} looks old — kept, but marked possibly stale", "warn", ref)
            else:
                await run.say("validate", f"Couldn't confirm {name} is still open — marked unverified", "warn", ref)
        for p in chunk:
            use_llm = llm_budget > 0 and p.validation.status not in ("invalid",) and p.id not in skip_llm
            ref = _job_ref(p)
            if use_llm:
                await run.say("extract", f"Reading the requirements for {ref['title']} at {ref['company']}", "work", ref)
            method = await job_ai.understand_job(p, snap, use_llm=use_llm)
            if method == "llm":
                llm_budget -= 1
                n_req = len(p.requirements.required_skills)
                await run.say("extract", f"{ref['title']} asks for {_years(p)}"
                              + (f" and {n_req} required skills" if n_req else ""), "info", ref)
            elif p.id in skip_llm:
                await run.say("extract", f"Skipped a deep read of {ref['title']} — it's outside your locations", "info", ref)
            validate.finalize(p)   # extraction may reveal closed / not-a-posting
        fits = await job_ai.assess_role_fit(snap, chunk)
        for p in chunk:
            m = assess(snap, p, role_fit=fits[p.id], candidate_text=text, idf=idf)
            if p.validation.status == "invalid":
                c["invalid"] += 1
            job_id = await storage.save_job(p, m, run.id)
            c["scored"] += 1
            if m.verdict == "incompatible" or p.validation.status in ("closed", "invalid"):
                c["rejected"] += 1
            elif m.verdict in ("strong", "good", "stretch"):
                c["recommended"] += 1
            row = await storage.get_row(job_id)
            await run._emit({"type": "search.job", "run_id": run.id,
                             "data": {"job": summary(row, snap.profile_hash)}, "ts": _now()})
            ref = {**_job_ref(p), "id": job_id, "score": m.score, "verdict": m.verdict}
            kind = {"strong": "good", "good": "good", "stretch": "warn", "weak": "warn"}.get(m.verdict, "reject")
            if p.validation.status in ("closed", "invalid"):
                kind = "reject"
            elif m.verdict in ("strong", "good", "stretch") and (best is None or m.score > best[0]):
                best = (m.score, p)
            word = VERDICT_WORDS.get(m.verdict, m.verdict)
            why = m.headline or ""
            if why.lower().startswith(word.lower()):          # headline may already lead with the verdict
                why = why[len(word):].lstrip(" :—-")
            await run.say("match", f"{word} · {ref['title']} at {ref['company']}" + (f" — {why}" if why else ""), kind, ref)
        await run.stage("match", "running", f"{c['scored']}/{len(unique)} scored")
    for key in ("validate", "extract", "match"):
        await run.stage(key, "done")
    await run.stage("rank", "done", f"{c['recommended']} recommended · {c['rejected']} not a fit")
    summary_line = f"Done — {c['recommended']} of {c['scored']} roles fit you"
    if best:
        summary_line += f". Best match: {best[1].title} at {best[1].company} ({best[0]})"
    elif c["scored"]:
        summary_line += ". Check “Not a fit” to see exactly why the others were ruled out"
    await run.say("rank", summary_line, "done")
    run.data["status"] = "completed"
    run.data["finished_at"] = _now()
    await run.publish()


class SearchManager:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._run: Optional[Run] = None

    @property
    def current(self) -> Optional[dict]:
        return self._run.data if self._run else None

    async def cancel(self, run_id: Optional[str] = None) -> Optional[dict]:
        if self._run and (run_id is None or self._run.id == run_id) and self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
        return self.current if (run_id is None or (self._run and self._run.id == run_id)) else await storage.get_run(run_id)

    async def start(self, profile: CandidateProfile, request: dict, emit: Emit) -> dict:
        await self.cancel()
        run = Run(new_run(profile.content_hash()), emit)
        self._run = run
        await run.publish()

        async def _go():
            try:
                await execute(run, profile, request)
            except asyncio.CancelledError:
                await run.say(run.data.get("stage", "rank"), "Search stopped — results found so far are kept", "warn")
                run.data.update(status="cancelled", finished_at=_now())
                for st in run.data["stages"]:
                    if st["status"] == "running":
                        st["status"] = "skipped"
                await run.publish()
                raise
            except Exception as exc:
                log.error("search_run_failed", run_id=run.id, error=str(exc)[:300])
                try:
                    await run.say(run.data.get("stage", "rank"), "Something went wrong and the search had to stop", "reject")
                except Exception:
                    pass
                run.data.update(status="failed", finished_at=_now(), error=f"{type(exc).__name__}: {str(exc)[:200]}")
                for st in run.data["stages"]:
                    if st["status"] == "running":
                        st["status"] = "failed"
                await run.publish()

        self._task = asyncio.create_task(_go())
        return run.data


manager = SearchManager()
