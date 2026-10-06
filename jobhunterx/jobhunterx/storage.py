"""
Persistence for the v2 domain (postings, matches, search runs, documents,
candidate snapshots), on the same SQLite database as the legacy tables.

The legacy `jobs` table is extended (not replaced) so the browser
auto-apply agent and interventions keep working: legacy columns (company,
role, location, apply_url, jd_text, match_score, status) are kept in sync.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

from jobhunterx.config import app_state
from jobhunterx.config import database as legacy
from jobhunterx.domain.candidate import CandidateSnapshot
from jobhunterx.domain.documents import GeneratedDocument
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment

TRACKING_STATUSES = ["new", "saved", "preparing", "applied", "interviewing", "offer", "rejected", "archived"]

_JOB_COLUMNS = {
    "posting_json": "TEXT", "match_json": "TEXT", "fingerprint": "TEXT", "canonical_url": "TEXT",
    "ats_key": "TEXT", "run_id": "TEXT", "saved_at": "TEXT", "tracking_status": "TEXT DEFAULT 'new'",
    "verdict": "TEXT", "fit_score": "INTEGER", "profile_hash": "TEXT", "validation_status": "TEXT",
    "reach_score": "INTEGER", "connect_json": "TEXT",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_runs (
    id TEXT PRIMARY KEY, status TEXT NOT NULL, data_json TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, job_id TEXT, title TEXT, focus TEXT,
    profile_hash TEXT, data_json TEXT NOT NULL, pdf BLOB, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_job ON documents(job_id, kind);
CREATE TABLE IF NOT EXISTS snapshots (
    profile_hash TEXT PRIMARY KEY, data_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, last_used_at TEXT
);
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS apply_sessions (
    job_id TEXT PRIMARY KEY, person_id TEXT, status TEXT NOT NULL, data_json TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""

SCHEMA_VERSION = 4
# Tables whose rows belong to one person (a "profile" in the UI). Every query on them is scoped.
_PERSON_TABLES = ("profiles", "jobs", "documents", "search_runs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    return aiosqlite.connect(legacy.get_db_path())


async def migrate() -> None:
    async with _conn() as db:
        cur = await db.execute("PRAGMA table_info(jobs)")
        have = {r[1] for r in await cur.fetchall()}
        for col, typ in _JOB_COLUMNS.items():
            if col not in have:
                await db.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typ}")
        await db.executescript(_SCHEMA)
        for col in ("fingerprint", "ats_key", "canonical_url", "run_id"):
            await db.execute(f"CREATE INDEX IF NOT EXISTS idx_jobs_{col} ON jobs({col})")
        # v4: multiple people. Add person_id everywhere, then give legacy rows an owner.
        for table in _PERSON_TABLES:
            cur = await db.execute(f"PRAGMA table_info({table})")
            if "person_id" not in {r[1] for r in await cur.fetchall()}:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN person_id TEXT")
            await db.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_person ON {table}(person_id)")
        orphans = 0
        for table in _PERSON_TABLES:
            orphans += (await (await db.execute(f"SELECT COUNT(*) FROM {table} WHERE person_id IS NULL")).fetchone())[0]
        if orphans:
            row = await (await db.execute("SELECT id FROM people ORDER BY COALESCE(last_used_at, created_at) DESC LIMIT 1")).fetchone()
            pid = row[0] if row else None
            if pid is None:
                name = "My profile"
                prof = await (await db.execute("SELECT data_json FROM profiles ORDER BY created_at DESC LIMIT 1")).fetchone()
                if prof:
                    try:
                        name = (json.loads(prof[0]).get("name") or "").strip() or name
                    except ValueError:
                        pass
                pid = str(uuid.uuid4())
                await db.execute("INSERT INTO people (id, name, created_at, last_used_at) VALUES (?, ?, ?, ?)", (pid, name, _now(), _now()))
            for table in _PERSON_TABLES:
                await db.execute(f"UPDATE {table} SET person_id = ? WHERE person_id IS NULL", (pid,))
        await db.execute("INSERT INTO schema_meta (key, value) VALUES ('version', ?) "
                         "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (str(SCHEMA_VERSION),))
        await db.commit()


# ---------------------------------------------------------------------------
# People (the profiles you can switch between)
# ---------------------------------------------------------------------------

def active_person() -> Optional[str]:
    return app_state.get("people.active")


def _scope(where: str = "", params: tuple = ()) -> tuple[str, tuple]:
    """Prefix a WHERE clause with the active person filter."""
    pid = active_person()
    clause = "person_id = ?" if pid else "person_id IS NULL"
    p = (pid,) if pid else ()
    return (f"{clause} AND ({where})" if where else clause), (*p, *params)


async def list_people() -> list[dict]:
    """Every person with a few facts for the picker (headline, location, job counts)."""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        people = [dict(r) for r in await (await db.execute(
            "SELECT p.*, "
            "(SELECT COUNT(*) FROM jobs j WHERE j.person_id = p.id) AS jobs, "
            "(SELECT COUNT(*) FROM jobs j WHERE j.person_id = p.id AND j.saved_at IS NOT NULL) AS saved "
            "FROM people p ORDER BY COALESCE(p.last_used_at, p.created_at) DESC")).fetchall()]
        for r in people:
            row = await (await db.execute("SELECT data_json FROM profiles WHERE person_id = ? ORDER BY created_at DESC LIMIT 1",
                                          (r["id"],))).fetchone()
            prof: dict = {}
            if row:
                try:
                    prof = json.loads(row[0])
                except ValueError:   # a corrupt profile row must never hide the person
                    prof = {}
            r["has_profile"] = bool(row)
            r["headline"] = (prof.get("suggested_role") or "").strip()
            r["location"] = (prof.get("location") or "").strip()
    return people


async def get_person(pid: str) -> Optional[dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM people WHERE id = ?", (pid,))).fetchone()
        return dict(row) if row else None


async def create_person(name: str) -> str:
    pid = str(uuid.uuid4())
    async with _conn() as db:
        await db.execute("INSERT INTO people (id, name, created_at, last_used_at) VALUES (?, ?, ?, ?)",
                         (pid, (name or "").strip()[:80] or "New profile", _now(), _now()))
        await db.commit()
    return pid


async def rename_person(pid: str, name: str) -> bool:
    async with _conn() as db:
        cur = await db.execute("UPDATE people SET name = ? WHERE id = ?", ((name or "").strip()[:80] or "Profile", pid))
        await db.commit()
        return cur.rowcount > 0


async def activate_person(pid: Optional[str]) -> None:
    if pid:
        async with _conn() as db:
            await db.execute("UPDATE people SET last_used_at = ? WHERE id = ?", (_now(), pid))
            await db.commit()
    await app_state.set("people.active", pid)


async def ensure_active_person(default_name: str = "") -> str:
    """Return the active person, creating one when the app has none yet (first upload / first save)."""
    pid = active_person()
    if pid and await get_person(pid):
        return pid
    people = await list_people()
    pid = people[0]["id"] if people else await create_person(default_name or "My profile")
    await activate_person(pid)
    return pid


async def heal_active_person() -> None:
    """At startup: the remembered person may have been deleted — fall back to the most recent one."""
    pid = active_person()
    if pid and await get_person(pid):
        return
    people = await list_people()
    await app_state.set("people.active", people[0]["id"] if people else None)


async def delete_person(pid: str) -> None:
    async with _conn() as db:
        ids = [r[0] for r in await (await db.execute("SELECT id FROM jobs WHERE person_id = ?", (pid,))).fetchall()]
    for jid in ids:
        await legacy.delete_job(jid)
    async with _conn() as db:
        for table in ("profiles", "documents", "search_runs", "apply_sessions"):
            await db.execute(f"DELETE FROM {table} WHERE person_id = ?", (pid,))
        await db.execute("DELETE FROM people WHERE id = ?", (pid,))
        await db.commit()
    if active_person() == pid:
        await app_state.set("people.active", None)
        await heal_active_person()


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def _ats_key(job: JobPosting) -> str:
    return f"{job.ats.kind}:{job.ats.token.lower()}:{job.ats.job_id}" if job.ats and job.ats.job_id else ""


async def find_existing(db, job: JobPosting) -> Optional[str]:
    for col, val in (("ats_key", _ats_key(job)), ("canonical_url", job.canonical_url), ("fingerprint", job.fingerprint)):
        if val:
            where, params = _scope(f"{col} = ?", (val,))
            cur = await db.execute(f"SELECT id FROM jobs WHERE {where} LIMIT 1", params)
            row = await cur.fetchone()
            if row:
                return row[0]
    return None


async def save_job(job: JobPosting, match: Optional[MatchAssessment], run_id: Optional[str]) -> str:
    """Insert or update a posting (dedup against stored jobs). Returns job id."""
    async with _conn() as db:
        existing = await find_existing(db, job)
        job.id = existing or job.id or str(uuid.uuid4())
        posting_json = job.model_dump_json()
        match_json = match.model_dump_json() if match else None
        url = job.apply_url or job.canonical_url
        pid = active_person()
        # the legacy UNIQUE hash is per person, so two people can track the same posting
        legacy_hash = hashlib.sha256(f"{pid or ''}|{url}".encode()).hexdigest() if url else None
        vals = {
            "company": job.company or "Unknown company", "role": job.title, "location": job.location_raw,
            "career_page_url": job.canonical_url, "apply_url": url, "jd_text": job.description,
            "source": job.primary_source.name if job.primary_source else "", "discovery_confidence": job.validation.confidence,
            "match_score": (match.score / 100) if match else None, "posting_json": posting_json, "match_json": match_json,
            "fingerprint": job.fingerprint, "canonical_url": job.canonical_url, "ats_key": _ats_key(job) or None,
            "verdict": match.verdict if match else None, "fit_score": match.score if match else None,
            "reach_score": match.reach.score if match and match.reach else None,
            "profile_hash": match.profile_hash if match else None, "validation_status": job.validation.status,
        }
        if existing:
            if run_id:
                vals["run_id"] = run_id
            sets = ", ".join(f"{k} = ?" for k in vals)
            await db.execute(f"UPDATE jobs SET {sets}, updated_at = ? WHERE id = ?", (*vals.values(), _now(), job.id))
        else:
            # apply_url_hash is UNIQUE in the legacy schema — a different posting with
            # the same URL is the same job.
            if legacy_hash:
                cur = await db.execute("SELECT id FROM jobs WHERE apply_url_hash = ?", (legacy_hash,))
                row = await cur.fetchone()
                if row:
                    job.id = row[0]
                    sets = ", ".join(f"{k} = ?" for k in vals)
                    await db.execute(f"UPDATE jobs SET {sets}, run_id = ?, updated_at = ? WHERE id = ?",
                                     (*vals.values(), run_id, _now(), job.id))
                    await db.commit()
                    return job.id
            vals.update({"id": job.id, "apply_url_hash": legacy_hash, "status": "discovered", "run_id": run_id, "person_id": pid,
                         "tracking_status": "new", "created_at": _now(), "updated_at": _now()})
            cols = ", ".join(vals)
            await db.execute(f"INSERT INTO jobs ({cols}) VALUES ({', '.join('?' for _ in vals)})", tuple(vals.values()))
        await db.commit()
    return job.id


async def update_match(job_id: str, match: MatchAssessment) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE jobs SET match_json = ?, verdict = ?, fit_score = ?, match_score = ?, reach_score = ?, profile_hash = ?, "
            "updated_at = ? WHERE id = ?",
            (match.model_dump_json(), match.verdict, match.score, match.score / 100,
             match.reach.score if match.reach else None, match.profile_hash, _now(), job_id))
        await db.commit()


async def set_connection(job_id: str, data: dict) -> None:
    """The Connector's referral kit for a job (routes to a real person + drafts)."""
    async with _conn() as db:
        await db.execute("UPDATE jobs SET connect_json = ? WHERE id = ?", (json.dumps(data), job_id))
        await db.commit()


def connection_of(row: dict) -> Optional[dict]:
    try:
        return json.loads(row["connect_json"]) if row.get("connect_json") else None
    except ValueError:
        return None


async def update_posting(job: JobPosting) -> None:
    async with _conn() as db:
        await db.execute("UPDATE jobs SET posting_json = ?, validation_status = ?, updated_at = ? WHERE id = ?",
                         (job.model_dump_json(), job.validation.status, _now(), job.id))
        await db.commit()


def row_to_objects(row: dict) -> tuple[Optional[JobPosting], Optional[MatchAssessment]]:
    posting = None
    if row.get("posting_json"):
        try:
            posting = JobPosting.model_validate_json(row["posting_json"])
        except ValueError:
            posting = None
    if posting is None:  # legacy row discovered by the old pipeline
        posting = JobPosting(id=row["id"], title=row.get("role") or "", company=row.get("company") or "",
                             location_raw=row.get("location") or "", description=row.get("jd_text") or "",
                             apply_url=row.get("apply_url") or "", canonical_url=row.get("career_page_url") or "")
    posting.id = row["id"]
    match = None
    if row.get("match_json"):
        try:
            match = MatchAssessment.model_validate_json(row["match_json"])
        except ValueError:
            match = None
    return posting, match


async def get_row(job_id: str) -> Optional[dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_rows(where: str = "", params: tuple = (), order: str = "fit_score DESC", limit: int = 200,
                    offset: int = 0) -> list[dict]:
    sql = "SELECT id, company, role, location, apply_url, status, posting_json, match_json, run_id, saved_at, " \
          "tracking_status, verdict, fit_score, reach_score, profile_hash, validation_status, created_at, updated_at, " \
          "(tailored_pdf IS NOT NULL) AS has_legacy_pdf, (connect_json IS NOT NULL) AS has_kit FROM jobs"
    where, params = _scope(where, params)
    sql += f" WHERE {where}"
    sql += f" ORDER BY {order}, id LIMIT ? OFFSET ?"          # id: a stable order, so pages never overlap or skip
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, (*params, limit, max(0, offset)))
        return [dict(r) for r in await cur.fetchall()]


async def count_many(conditions: dict[str, str], where: str = "", params: tuple = ()) -> dict[str, int]:
    """Several COUNTs in one query: one per named condition (no parameters), all within `where`."""
    where, params = _scope(where, params)
    cols = ", ".join(f"COALESCE(SUM(CASE WHEN {cond or '1=1'} THEN 1 ELSE 0 END), 0)" for cond in conditions.values())
    async with _conn() as db:
        cur = await db.execute(f"SELECT {cols} FROM jobs WHERE {where}", params)
        row = await cur.fetchone()
    return dict(zip(conditions, row))


async def job_exists_many(jobs: list[JobPosting]) -> set[int]:
    """Indexes of the given postings that are already stored — one connection for the whole batch."""
    out = set()
    async with _conn() as db:
        for i, job in enumerate(jobs):
            if await find_existing(db, job) is not None:
                out.add(i)
    return out


async def count(where: str = "", params: tuple = ()) -> int:
    where, params = _scope(where, params)
    async with _conn() as db:
        cur = await db.execute(f"SELECT COUNT(*) FROM jobs WHERE {where}", params)
        return (await cur.fetchone())[0]


async def set_saved(job_id: str, saved: bool) -> bool:
    async with _conn() as db:
        if saved:
            cur = await db.execute(
                "UPDATE jobs SET saved_at = COALESCE(saved_at, ?), "
                "tracking_status = CASE WHEN tracking_status IS NULL OR tracking_status = 'new' THEN 'saved' ELSE tracking_status END "
                "WHERE id = ?", (_now(), job_id))
        else:
            cur = await db.execute(
                "UPDATE jobs SET saved_at = NULL, "
                "tracking_status = CASE WHEN tracking_status = 'saved' THEN 'new' ELSE tracking_status END WHERE id = ?",
                (job_id,))
        await db.commit()
        return cur.rowcount > 0


async def set_tracking(job_id: str, status: str) -> bool:
    async with _conn() as db:
        saved_clause = ", saved_at = COALESCE(saved_at, ?)" if status != "new" else ""
        params = (status, _now(), job_id) if saved_clause else (status, job_id)
        cur = await db.execute(f"UPDATE jobs SET tracking_status = ?{saved_clause} WHERE id = ?", params)
        await db.commit()
        return cur.rowcount > 0


async def delete_jobs(scope: str) -> int:
    async with _conn() as db:
        where, params = _scope("1 = 1" if scope == "all" else
                               "saved_at IS NULL AND COALESCE(tracking_status,'new') IN ('new','archived')")
        ids = [r[0] for r in await (await db.execute(f"SELECT id FROM jobs WHERE {where}", params)).fetchall()]
    for jid in ids:
        await legacy.delete_job(jid)
    if ids:
        async with _conn() as db:
            await db.execute(f"DELETE FROM documents WHERE job_id IN ({','.join('?' for _ in ids)})", ids)
            await db.commit()
    return len(ids)


# ---------------------------------------------------------------------------
# Search runs
# ---------------------------------------------------------------------------

async def save_run(run: dict) -> None:
    async with _conn() as db:
        await db.execute(
            "INSERT INTO search_runs (id, status, data_json, created_at, updated_at, person_id) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status = excluded.status, data_json = excluded.data_json, updated_at = excluded.updated_at",
            (run["id"], run["status"], json.dumps(run, default=str), run.get("started_at") or _now(), _now(), run.get("person_id")))
        await db.commit()


async def get_run(run_id: str) -> Optional[dict]:
    async with _conn() as db:
        cur = await db.execute("SELECT data_json FROM search_runs WHERE id = ?", (run_id,))
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def latest_run() -> Optional[dict]:
    async with _conn() as db:
        where, params = _scope()
        cur = await db.execute(f"SELECT data_json FROM search_runs WHERE {where} ORDER BY created_at DESC LIMIT 1", params)
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def mark_interrupted_runs() -> None:
    """Runs left 'running' by a previous process can never finish."""
    async with _conn() as db:
        cur = await db.execute("SELECT id, data_json FROM search_runs WHERE status IN ('queued','running')")
        for rid, data in await cur.fetchall():
            run = json.loads(data)
            run.update(status="failed", error="Interrupted by a server restart.", finished_at=_now())
            await db.execute("UPDATE search_runs SET status = 'failed', data_json = ? WHERE id = ?", (json.dumps(run), rid))
        await db.commit()


# ---------------------------------------------------------------------------
# Auto-apply sessions (what the browser agent did, so you can continue later)
# ---------------------------------------------------------------------------

_APPLY_ACTIVE = ("preparing", "launching", "running", "paused", "stopping")


async def save_apply_session(snap: dict) -> None:
    async with _conn() as db:
        await db.execute(
            "INSERT INTO apply_sessions (job_id, person_id, status, data_json, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET status = excluded.status, data_json = excluded.data_json, "
            "updated_at = excluded.updated_at, person_id = COALESCE(excluded.person_id, apply_sessions.person_id)",
            (snap["job_id"], snap.get("person_id"), snap.get("status", ""), json.dumps(snap, default=str), _now()))
        await db.commit()


async def get_apply_session(job_id: str) -> Optional[dict]:
    async with _conn() as db:
        cur = await db.execute("SELECT data_json FROM apply_sessions WHERE job_id = ?", (job_id,))
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def latest_apply_session() -> Optional[dict]:
    where, params = _scope()
    async with _conn() as db:
        cur = await db.execute(f"SELECT data_json FROM apply_sessions WHERE {where} ORDER BY updated_at DESC LIMIT 1", params)
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def mark_interrupted_apply_sessions() -> None:
    """A browser from a previous process is gone; keep the steps so the user can start again from there."""
    async with _conn() as db:
        cur = await db.execute("SELECT job_id, status, data_json FROM apply_sessions")
        for jid, status, data in await cur.fetchall():
            snap = json.loads(data)
            if status in _APPLY_ACTIVE:
                snap.update(status="stopped", message="Stopped",
                            notice="The app restarted while this was running. Press Continue to pick up from the last page.")
            elif not snap.get("live"):
                continue
            snap.update(live=False, control="agent")
            await db.execute("UPDATE apply_sessions SET status = ?, data_json = ? WHERE job_id = ?", (snap["status"], json.dumps(snap), jid))
        await db.commit()


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

async def get_snapshot(profile_hash: str) -> Optional[CandidateSnapshot]:
    async with _conn() as db:
        cur = await db.execute("SELECT data_json FROM snapshots WHERE profile_hash = ?", (profile_hash,))
        row = await cur.fetchone()
    if not row:
        return None
    try:
        return CandidateSnapshot.model_validate_json(row[0])
    except ValueError:
        return None


async def put_snapshot(snap: CandidateSnapshot) -> None:
    async with _conn() as db:
        await db.execute("INSERT OR REPLACE INTO snapshots (profile_hash, data_json, created_at) VALUES (?, ?, ?)",
                         (snap.profile_hash, snap.model_dump_json(), _now()))
        await db.commit()


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

async def save_document(doc: GeneratedDocument, pdf: Optional[bytes]) -> str:
    doc.id = doc.id or str(uuid.uuid4())
    doc.has_pdf = bool(pdf)
    async with _conn() as db:
        await db.execute(
            "INSERT OR REPLACE INTO documents (id, kind, job_id, title, focus, profile_hash, data_json, pdf, created_at, person_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc.id, doc.kind, doc.job_id, doc.title, doc.focus, doc.profile_hash, doc.model_dump_json(), pdf,
             doc.created_at.isoformat(), active_person()))
        if doc.kind == "resume" and doc.job_id and pdf:
            # keep the legacy column in sync: the browser agent uploads this file
            await db.execute("UPDATE jobs SET tailored_pdf = ? WHERE id = ?", (pdf, doc.job_id))
        await db.commit()
    return doc.id


async def get_document(doc_id: str) -> Optional[GeneratedDocument]:
    async with _conn() as db:
        cur = await db.execute("SELECT data_json FROM documents WHERE id = ?", (doc_id,))
        row = await cur.fetchone()
    return GeneratedDocument.model_validate_json(row[0]) if row else None


async def get_document_pdf(doc_id: str) -> Optional[bytes]:
    async with _conn() as db:
        cur = await db.execute("SELECT pdf FROM documents WHERE id = ?", (doc_id,))
        row = await cur.fetchone()
    return row[0] if row else None


async def list_documents(job_id: Optional[str] = None, kind: Optional[str] = None) -> list[GeneratedDocument]:
    where, params = [], []
    if job_id:
        where.append("job_id = ?")
        params.append(job_id)
    if kind:
        where.append("kind = ?")
        params.append(kind)
    w, p = _scope(" AND ".join(where), tuple(params))
    sql = f"SELECT data_json FROM documents WHERE {w} ORDER BY created_at DESC"
    async with _conn() as db:
        cur = await db.execute(sql, p)
        return [GeneratedDocument.model_validate_json(r[0]) for r in await cur.fetchall()]


async def latest_document_ids(job_ids: list[str]) -> dict[str, dict[str, str]]:
    if not job_ids:
        return {}
    out: dict[str, dict[str, str]] = {}
    async with _conn() as db:
        cur = await db.execute(
            f"SELECT job_id, kind, id FROM documents WHERE job_id IN ({','.join('?' for _ in job_ids)}) ORDER BY created_at ASC",
            job_ids)
        for jid, kind, did in await cur.fetchall():
            out.setdefault(jid, {})[kind] = did
    return out


async def delete_document(doc_id: str) -> bool:
    async with _conn() as db:
        cur = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()
        return cur.rowcount > 0


def as_json(obj: Any) -> Any:
    return json.loads(obj.model_dump_json()) if hasattr(obj, "model_dump_json") else obj
