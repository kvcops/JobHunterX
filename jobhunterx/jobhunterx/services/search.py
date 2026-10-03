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
import re
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from jobhunterx import storage
from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.discovery import ats, dedupe, page, search, validate, watchlist
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import AtsRef, JobPosting
from jobhunterx.intelligence import job as job_ai
from jobhunterx.intelligence.matching import assess, build_idf, candidate_work_text
from jobhunterx.intelligence.policy import get_policy
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
BOARD_CONCURRENCY = 8
WATCH_BOARDS_MAX = 80
WATCH_NEW_PER_CHECK = 20


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
        "total": 0, "activity": [], "person_id": storage.active_person(),
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
    if snap.open_to_international:
        return True
    forms = {f for p in snap.locations for f in [p.city, p.country, *p.aliases] if f}
    if snap.willing_to_relocate and snap.home_country:
        forms.add(snap.home_country)
    if any(term_in_text(f, text) for f in forms):
        return True
    if include_remote and (job.work_mode == WorkMode.REMOTE or term_in_text(WorkMode.REMOTE.value, text)):
        # "Remote" alone may include the candidate; "Remote - US" / "Remote, Germany" does not.
        if snap.home_country and term_in_text(snap.home_country, text):
            return True
        return not _REMOTE_LEFTOVER.sub(" ", text).strip(" ;,/-|()")
    return False


_REMOTE_LEFTOVER = re.compile(r"(?i)\b(remote|anywhere|worldwide|global|work from home|wfh|fully|first|"
                              r"apac|asia|asia pacific)\b|[;,/|()\-–]")


def _title_relevance(job: JobPosting, snap: CandidateSnapshot) -> float:
    jt = set(tokens(job.title))
    best = 0.0
    for label in [*snap.target_titles, *snap.adjacent_titles, *[f.label for f in snap.role_families]]:
        lt = set(tokens(label))
        if jt and lt:
            best = max(best, len(jt & lt) / len(jt | lt))
    return best


async def _expand_boards(refs: list[tuple[AtsRef, Optional[watchlist.WatchCompany]]], snap: CandidateSnapshot,
                         include_remote: bool, titles: list[str]) -> list[JobPosting]:
    """For each ATS board (watchlist or discovered), pull its open jobs and keep the relevant ones.

    Jobs outside the candidate's locations are dropped here. A foreign
    company's board can list dozens of US/Europe roles; keeping them would
    fill the result slots with jobs the candidate can never take and push
    out the local roles found by web search.
    """
    out: list[JobPosting] = []
    sem = asyncio.Semaphore(BOARD_CONCURRENCY)

    async def one(ref: AtsRef, company: Optional[watchlist.WatchCompany]):
        async with sem:
            jobs = await ats.ADAPTERS[ref.kind].search_jobs(ref.token, titles[:4] or None)
        if not jobs:
            return []
        jobs = [j for j in jobs if _location_prefilter(j, snap, include_remote)]
        for j in jobs:
            j.id = j.id or str(uuid.uuid4())
            if company:
                j.company = company.name          # ATS boards often carry a token or legal-entity name
        keep = [(j, _title_relevance(j, snap)) for j in jobs]
        keep = [jr for jr in keep if jr[1] > 0]
        keep.sort(key=lambda jr: (-jr[1], _age_days(jr[0])))
        picked = [j for j, _ in keep[:BOARD_JOBS_PER_BOARD]]
        # Some board APIs (e.g. SmartRecruiters) list jobs without their text — fetch it for the ones we keep.
        adapter = ats.ADAPTERS[ref.kind]

        async def hydrate(j: JobPosting) -> JobPosting:
            if j.description or not (j.ats and j.ats.job_id):
                return j
            async with sem:
                state, full = await adapter.check(j.ats)
            if state == "live" and full and full.description:
                j.description = full.description
            return j

        return list(await asyncio.gather(*(hydrate(j) for j in picked)))

    results = await asyncio.gather(*(one(r, c) for r, c in refs), return_exceptions=True)
    for r in results:
        if isinstance(r, list):
            out += r
        elif isinstance(r, Exception):
            log.debug("board_expand_failed", error=str(r)[:120])
    return out


def _age_days(p: JobPosting) -> float:
    if not p.posted_at:
        return 999.0
    return max(0.0, (datetime.now(timezone.utc) - p.posted_at).total_seconds() / 86400)


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

    watch_mode = request.get("mode") == "watch"
    scope = search.scope_from_snapshot(snap, locations=request.get("locations") or None,
                                       role_focus=request.get("role_focus") or None,
                                       work_modes=request.get("work_modes") or None)
    watch_cos = watchlist.for_candidate(snap)
    watch_refs = watchlist.board_refs(watch_cos)[:WATCH_BOARDS_MAX]

    # 2. Plan -----------------------------------------------------------------
    await run.stage("plan")
    if watch_mode:
        queries, plan_method = [], "watchlist"
        await run.say("plan", f"Checking {len(watch_refs)} watchlist companies' own job boards for new roles", "work")
    else:
        await run.say("plan", "Deciding which titles and places to search", "work")
        max_queries = max(4, min(16, max_jobs // 4))
        queries, plan_method = await search.plan_queries(snap, scope, max_queries)
    c["queries"] = len(queries)
    run.data["plan"] = {"role_families": [f.label for f in snap.role_families], "titles": scope.titles,
                        "locations": scope.locations, "queries": queries, "method": plan_method,
                        "watchlist": len(watch_refs)}
    await run.stage("plan", "done", f"{len(queries)} queries · {len(watch_refs)} watchlist boards")
    if not watch_mode:
        where = ", ".join(scope.locations[:3]) or "your preferred locations"
        titles = ", ".join(scope.titles[:3]) + (f" and {len(scope.titles) - 3} more" if len(scope.titles) > 3 else "")
        await run.say("plan", f"Looking for {titles} in {where} — {len(queries)} searches planned"
                      + (f", plus {len(watch_refs)} researched companies checked directly" if watch_refs else ""), "info")

    # 3. Discover -------------------------------------------------------------
    await run.stage("discover")
    leads = []
    if queries:
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
    if queries:
        await run.say("discover", f"Found {len(leads)} search results"
                      + (f", including {len(boards)} company career boards" if boards else ""), "info")
    known = {(r.kind, r.token.lower()) for r, _ in watch_refs}
    found_refs = [(r, watchlist.find_board(r)) for k, r in boards.items() if k not in known][:12]
    board_refs = watch_refs + found_refs
    if watch_refs:
        await run.say("discover", f"Opening {len(watch_refs)} researched companies' own job boards — "
                      "new roles there are usually seen before the crowd arrives", "work")
    for ref, _ in found_refs[:6]:
        await run.say("discover", f"Opening {_pretty_board(ref.token)}'s careers board on {ref.kind.title()}", "work")
    board_jobs = await _expand_boards(board_refs, snap, scope.include_remote, scope.titles)
    if board_refs:
        await run.say("discover", f"Pulled {len(board_jobs)} relevant openings straight from employer boards", "good")
    if watch_mode:
        before = len(board_jobs)
        stale_after = get_policy().stale_after_days
        board_jobs = [j for j in board_jobs if _age_days(j) <= stale_after or not j.posted_at]
        board_jobs = [j for j in board_jobs if not await storage.job_exists(j)]
        # Free AI tiers allow ~1 deep read a minute; take the best new ones now, the rest next check.
        max_jobs = min(max_jobs, WATCH_NEW_PER_CHECK)
        await run.say("discover", f"{len(board_jobs)} of them are new since the last check"
                      if before else "No matching openings on watchlist boards right now", "info")
    await run.stage("discover", "done", f"{len(leads)} search results · {len(board_refs)} employer job boards")

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
    unique.sort(key=lambda p: (-(p.primary_source.first_party if p.primary_source else 0),
                               -round(_title_relevance(p, snap), 1), _age_days(p)))
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
            use_llm = llm_budget > 0 and p.validation.status not in ("invalid",)
            ref = _job_ref(p)
            if use_llm:
                await run.say("extract", f"Reading the requirements for {ref['title']} at {ref['company']}", "work", ref)
            method = await job_ai.understand_job(p, snap, use_llm=use_llm)
            if method == "llm":
                llm_budget -= 1
                n_req = len(p.requirements.required_skills)
                await run.say("extract", f"{ref['title']} asks for {_years(p)}"
                              + (f" and {n_req} required skills" if n_req else ""), "info", ref)
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

    async def wait(self) -> None:
        """Wait for the active run to end (completed, failed or cancelled)."""
        if self._task and not self._task.done():
            try:
                await asyncio.shield(self._task)
            except (asyncio.CancelledError, Exception):
                pass

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
