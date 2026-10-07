"""
The agents' office — live conversations and questions, grounded in real data.

The 3D office shows the pipeline agents as characters. Two things here use AI:

* **Break-time conversations** — two agents chat in character (chai, a ping-pong match, a fight over the AC). The
  office picks the kind of chat (banter, satire about job ads, an argument, jealousy, a scheme, consoling) from their
  history and moods; lines can carry a physical beat (a stomp, a shove, a cartoon bonk, a high-five) and the chat can
  end in a make-up, someone storming off or sulking, or a chase. These come from a *dialogue bank*: AI writes them in
  batches every hour or two, each for one pair of agents and one kind of chat, and serving one costs no AI call.
  Facts about the real search are placeholders filled at show time; no line may carry an invented number.
* **Ask an agent** — the person types a question to one agent ("Why did you reject the Zoetis job?") and gets a short,
  in-character answer built only from this person's real search: counts, top matches, reasons for rejections, and the
  agent's own work log.

Both fall back gracefully: with an empty bank the office uses its scripted talk; without a model a question says it cannot answer.
"""

from __future__ import annotations

import json
import re
import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx import storage
from jobhunterx.config.logging import get_logger

log = get_logger("office")

AGENTS = {
    "understand": ("Profile analyst", "reads the person's resume and works out who to search for",
                   "calm, perceptive, a gentle psychologist; loves masala chai; notices how others feel"),
    "plan": ("Planner", "plans which job titles, cities and company boards to search",
             "organised and a little bossy; loves lists, whiteboards and the phrase 'action items'"),
    "discover": ("Scout", "runs out to the web and to companies' own job boards to find openings",
                 "hyper, fast-talking, wears a cap, competitive at every game, never walks when it can run"),
    "normalize": ("Reader", "opens every job page and reads the full description",
                  "bookish, round glasses, quotes job descriptions, dry introvert humour"),
    "dedupe": ("Curator", "spots the same job posted on many sites and keeps one",
               "tidy perfectionist in a bow tie; duplicates and clutter physically pain it"),
    "validate": ("Verifier", "checks every job is real and still open; bins closed and fake ones",
                 "skeptical detective in a fedora; strict about fake posts, secretly soft-hearted"),
    "match": ("Analyst", "reads what each job asks for and scores how well the person fits",
              "data nerd with big headphones; gets genuinely excited about a great fit"),
    "rank": ("Ranker", "ranks the jobs that fit and explains why",
             "showman with a tiny gold crown; loves trophies, winning and a dramatic announcement"),
    "connect": ("Connector", "finds a route to a real person at the top companies and drafts referral notes",
                "warm social butterfly with a headset; knows everyone, makes networking puns"),
}
EMOTIONS = ["neutral", "happy", "laugh", "sad", "angry", "furious", "surprised", "scared", "sleepy", "tired", "love", "focused",
            "wink", "proud", "dizzy", "jealous", "sneaky", "annoyed"]
GESTURES = ["none", "Wave", "Yes", "No", "ThumbsUp", "Jump", "Dance"]
ACTIONS = ["none", "stomp", "facepalm", "turnaway", "shove", "bonk", "highfive", "hug"]
ENDINGS = ["none", "make_up", "storm_off", "sulk", "chase"]
DRAMA = {
    "banter": "easy, funny small talk between colleagues; teasing, inside jokes, Hyderabad life (chai, biryani, traffic, cricket)",
    "break": "a quiet break while the others are still working: light jokes and complaints, nothing about search progress",
    "satire": "dry, sarcastic roasting of absurd job ads and hiring habits in India (fake 'entry level' needing 5 years, "
              "'urgent hiring' for a year, 'kindly revert', unpaid 'exposure', six interview rounds). The real postings "
              "in 'recently_ruled_out' may be joked about with their real reasons, never exaggerated; never insult people",
    "argument": "a petty argument that escalates (snacks, credit for a find, the AC, tabs vs spaces, a borrowed charger): "
                "interruptions, sarcasm, raised voices; it may get physical in a cartoon way (a stomp, a shove, one bonk) "
                "and ends with a make-up, someone storming off or sulking, or a chase",
    "jealous": "A is openly jealous of B (B won a game, got the praise, has something nicer); passive-aggressive jabs, "
               "B is smug or kind; ends in a make-up, a sulk or storming off",
    "scheme": "the two plot something mischievous together in whispers (raid the pantry, dodge a meeting, prank someone)",
    "console": "A cheers up B, who is upset after a fight; B is prickly at first, then softens",
}
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


class Line(BaseModel):
    who: int = Field(0, description="0 = the first agent, 1 = the second")
    text: str = Field("", description="what they say, at most 90 characters, natural spoken English")
    emotion: str = Field("neutral", description="one of: " + ", ".join(EMOTIONS))
    gesture: str = Field("none", description="one of: " + ", ".join(GESTURES))
    action: str = Field("none", description="a physical beat by the speaker toward the other, one of: " + ", ".join(ACTIONS))


class Chat(BaseModel):
    lines: list[Line] = Field(default_factory=list)
    learned: list[int] = Field(default_factory=list, description="indexes into 'a_knows_b_doesnt' that A told B about")
    ending: str = Field("none", description="how it ends, one of: " + ", ".join(ENDINGS))
    ending_who: int = Field(0, description="who storms off / sulks / does the chasing: 0 = A, 1 = B")


class Answer(BaseModel):
    answer: str = Field("", description="the agent's reply, at most 70 words")
    emotion: str = Field("neutral", description="one of: " + ", ".join(EMOTIONS))


async def facts() -> dict:
    """What actually happened in this person's latest search (the only numbers an agent may say)."""
    run = await storage.latest_run()
    out: dict = {"search": "none yet"}
    if run:
        c = run.get("counts") or {}
        plan = run.get("plan") or {}
        out = {
            "search_status": run.get("status"),
            "searched_titles": (plan.get("titles") or [])[:5],
            "searched_cities": (plan.get("locations") or [])[:4],
            "search_results_found": c.get("search_results", 0),
            "postings_read": c.get("candidates", 0),
            "duplicates_merged": c.get("duplicates", 0),
            "jobs_analysed": c.get("scored", 0),
            "jobs_that_fit": c.get("recommended", 0),
            "jobs_not_a_fit": c.get("rejected", 0),
        }
    top = await storage.list_rows("verdict IN ('strong', 'good', 'stretch')", order="fit_score DESC", limit=6)
    out["top_matches"] = []
    for r in top:
        p, m = storage.row_to_objects(r)
        out["top_matches"].append({"title": p.title, "company": p.company, "fit_score": r.get("fit_score"),
                                   "why": (m.headline if m else "")[:140], "has_referral_kit": bool(r.get("has_kit"))})
    rej = await storage.list_rows("verdict = 'incompatible' OR validation_status IN ('closed', 'invalid')",
                                  order="updated_at DESC", limit=5)
    out["recently_ruled_out"] = []
    for r in rej:
        p, m = storage.row_to_objects(r)
        why = (m.rejected_reasons[0] if m and m.rejected_reasons else "") or (
            "posting has closed" if p.validation.status == "closed" else "not a real job posting" if p.validation.status == "invalid" else "")
        out["recently_ruled_out"].append({"title": p.title, "company": p.company, "why": why[:140]})
    return out


_NUMBER_WORDS = re.compile(r"(?i)\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
                           r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen)s?\b")


_PROGRESS = re.compile(r"(?i)(jobs?|postings?|posts|results?|matches|fits?|roles?|applications?|boards?|searches|scored|analy[sz]ed|"
                       r"merged|duplicates|found|read|checked|binned|rejected|companies)")


def _numbers_ok(text: str, allowed: str, loose: bool = False) -> bool:
    """Every number in a line must come from the real facts — spelled-out counts are not allowed to sneak past.
    Loose (jokes about job ads): other numbers are fine unless the line talks about search progress."""
    nums = [n for n in re.findall(r"\d+(?:\.\d+)?", text) if n not in allowed]
    if loose:
        return not ((nums or (_NUMBER_WORDS.search(text) and not _NUMBER_WORDS.search(allowed))) and _PROGRESS.search(text))
    if _NUMBER_WORDS.search(text) and not _NUMBER_WORDS.search(allowed):
        return False
    return not nums


def _clean(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", _EMOJI.sub("", (s or "").replace('"', ""))).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


# ---------------------------------------------------------------------------- the dialogue bank
# Conversations are written by AI in batches and kept in the database, so a chat in the office never waits for (or
# spends) an AI call. A refill runs at most every OFFICE_BANK_REFILL_HOURS (default 1.5 h), only while no search is
# running (searches get the free AI limits first), and makes a few calls of BATCH scenes each. Every scene is written
# for one pair of agents and one kind of chat, so their personalities hold. Lines may carry placeholders that are
# filled from the latest real search when the scene is shown ({top_job}, {fits}…); a scene whose placeholder has no
# real value yet is simply not picked. The least-heard scenes are served first, and new batches keep the talk fresh.

BATCH = 8                      # scenes per AI call
CALLS_PER_REFILL = 4           # at most this many AI calls per refill
TARGET = 360                   # scenes kept ready; above it each refill replaces the most-heard ones
CAP = 480
KIND_WEIGHT = {"banter": 3, "satire": 3, "argument": 2, "break": 2, "jealous": 1, "scheme": 1, "console": 1}
PLACEHOLDERS = {
    "results": "how many search results the last search found",
    "fits": "how many jobs fit the person",
    "analysed": "how many jobs were analysed",
    "top_job": "title of the best match",
    "top_company": "company of the best match",
    "binned_job": "title of a posting that was ruled out",
    "binned_company": "its company",
    "binned_reason": "the real reason it was ruled out",
}
_PH = re.compile(r"\{(\w+)\}")
_TABLE = """CREATE TABLE IF NOT EXISTS office_scenes (
    id TEXT PRIMARY KEY, a TEXT NOT NULL, b TEXT NOT NULL, kind TEXT NOT NULL, lines_json TEXT NOT NULL,
    ending TEXT NOT NULL DEFAULT 'none', ending_who INTEGER NOT NULL DEFAULT 0, needs TEXT NOT NULL DEFAULT '',
    uses INTEGER NOT NULL DEFAULT 0, last_used REAL NOT NULL DEFAULT 0, created REAL NOT NULL)"""
_state = {"last_refill": 0.0, "running": False, "task": None}


class SceneOut(BaseModel):
    pair: int = Field(0, description="index into 'pairs' this scene is for")
    lines: list[Line] = Field(default_factory=list)
    ending: str = Field("none", description="how it ends, one of: " + ", ".join(ENDINGS))
    ending_who: int = Field(0, description="who storms off / sulks / does the chasing: 0 = A, 1 = B")


class SceneBatch(BaseModel):
    scenes: list[SceneOut] = Field(default_factory=list)


def _db():
    import aiosqlite
    from jobhunterx.config.database import get_db_path
    return aiosqlite.connect(get_db_path())


async def _ensure_table(db) -> None:
    await db.execute(_TABLE)
    await db.execute("CREATE INDEX IF NOT EXISTS office_scenes_pick ON office_scenes (kind, a, b, uses)")


def _fill_values(f: dict) -> dict:
    """Placeholder values from the latest real search (only the ones that exist)."""
    out = {}
    for k, src in (("results", "search_results_found"), ("fits", "jobs_that_fit"), ("analysed", "jobs_analysed")):
        if f.get(src):
            out[k] = str(f[src])
    if f.get("top_matches"):
        out["top_job"], out["top_company"] = f["top_matches"][0]["title"], f["top_matches"][0]["company"]
    ruled = [r for r in f.get("recently_ruled_out", []) if r.get("why")]
    if ruled:
        r = ruled[0]
        out.update(binned_job=r["title"], binned_company=r["company"], binned_reason=r["why"])
    return {k: _clean(str(v), 60) for k, v in out.items() if v}


def _norm_kind(drama: str, working: bool) -> str:
    kind = drama if drama in DRAMA else "banter"
    return "break" if working and kind not in ("break", "satire", "banter") else kind


async def chat(a: str, b: str, scene: str, a_knows: list[str], b_knows: list[str], moods: dict, *, drama: str = "banter",
               relation: str = "", recent: Optional[list[str]] = None, working: bool = False) -> Optional[dict]:
    """A break-time conversation from the dialogue bank: no AI call. None when the bank has nothing fitting yet
    (the office then uses its scripted talk)."""
    if a not in AGENTS or b not in AGENTS or a == b:
        return None
    kind = _norm_kind(drama, working)
    heard = {_clean(x, 100).lower() for x in (recent or [])}
    values = _fill_values(await facts())
    async with _db() as db:
        await _ensure_table(db)
        cur = await db.execute(
            "SELECT id, a, lines_json, ending, ending_who, needs FROM office_scenes WHERE kind = ? AND "
            "((a = ? AND b = ?) OR (a = ? AND b = ?)) ORDER BY uses ASC, last_used ASC LIMIT 12", (kind, a, b, b, a))
        rows = await cur.fetchall()
        for sid, sa, lines_json, ending, ending_who, needs in rows:
            if any(n not in values for n in needs.split(",") if n):
                continue
            lines = json.loads(lines_json)
            flip = sa != a                    # written as (b, a): swap 'who' so each agent says its own lines
            out = []
            for ln in lines:
                text = _PH.sub(lambda m: values.get(m.group(1), m.group(0)), ln["text"])
                out.append({**ln, "text": text, "who": (1 - ln["who"]) if flip else ln["who"]})
            if out and out[0]["text"].lower() in heard:
                continue
            if working and ending == "chase":
                ending = "none"
            await db.execute("UPDATE office_scenes SET uses = uses + 1, last_used = ? WHERE id = ?", (time.time(), sid))
            await db.commit()
            who = (1 - ending_who) if flip else ending_who
            return {"lines": out, "learned": [], "model": "bank", "source": "bank", "ending": ending, "ending_who": who}
    return None


async def bank_status() -> dict:
    async with _db() as db:
        await _ensure_table(db)
        cur = await db.execute("SELECT kind, COUNT(*), SUM(uses) FROM office_scenes GROUP BY kind")
        by_kind = {k: {"scenes": n, "heard": int(u or 0)} for k, n, u in await cur.fetchall()}
    every = _refill_every_s()
    nxt = max(0.0, _state["last_refill"] + every - time.time()) if _state["last_refill"] else None
    return {"scenes": sum(v["scenes"] for v in by_kind.values()), "by_kind": by_kind, "target": TARGET,
            "refilling": _state["running"], "last_refill": _state["last_refill"] or None,
            "next_refill_in_s": None if nxt is None else round(nxt), "refill_every_s": round(every)}


def _refill_every_s() -> float:
    import os
    try:
        return max(0.25, float(os.getenv("OFFICE_BANK_REFILL_HOURS", "1.5"))) * 3600
    except ValueError:
        return 1.5 * 3600


async def _plan_batch(db) -> tuple[str, list[tuple[str, str]]]:
    """The kind with the fewest scenes for its weight, and the BATCH pairs with the fewest scenes of that kind."""
    import random
    cur = await db.execute("SELECT kind, a, b, COUNT(*) FROM office_scenes GROUP BY kind, a, b")
    have: dict = {}
    for k, sa, sb, n in await cur.fetchall():
        have[(k, frozenset((sa, sb)))] = have.get((k, frozenset((sa, sb))), 0) + n
    totals = {k: sum(n for (kk, _), n in have.items() if kk == k) for k in KIND_WEIGHT}
    kind = min(KIND_WEIGHT, key=lambda k: (totals[k] / KIND_WEIGHT[k], random.random()))
    keys = list(AGENTS)
    pairs = [(x, y) for i, x in enumerate(keys) for y in keys[i + 1:]]
    random.shuffle(pairs)
    pairs.sort(key=lambda p: have.get((kind, frozenset(p)), 0))
    return kind, [p if random.random() < 0.5 else (p[1], p[0]) for p in pairs[:BATCH]]


async def _write_batch(db, kind: str, pairs: list[tuple[str, str]]) -> int:
    """One AI call: BATCH new scenes of one kind, each for its own pair of agents. Returns how many were kept."""
    import uuid
    cur = await db.execute("SELECT lines_json FROM office_scenes WHERE kind = ? ORDER BY created DESC LIMIT 40", (kind,))
    old_firsts = [json.loads(r[0])[0]["text"] for r in await cur.fetchall()]
    with_facts = kind in ("banter", "break", "satire")
    system = (
        "You write short scenes of dialogue between two AI agents who work together in a job-search office in Hyderabad. "
        "They are characters with real feelings — they tease, get sarcastic, lose their temper, sulk, scheme, get jealous, "
        "make up. Write like a sitcom: natural spoken English with a light Indian flavour, people interrupting each other, "
        "trailing off (…), reacting to what was just said instead of taking polite turns. Keep it playful: anger is "
        "cartoonish, a shove or a bonk is slapstick, nobody is cruel, no slurs, no real people or brands. "
        f"Write exactly {len(pairs)} scenes, one for each entry in 'pairs' (set 'pair' to its index), every scene different "
        "in topic and joke. Each scene: 3 to 7 lines, speakers mostly alternating (who: 0 = A of that pair, 1 = B), each "
        "line at most 90 characters, no emoji, no hashtags. Let each agent's personality and job show. "
        "Never write numbers about the job search, company names or job titles. "
        + ("For one or two scenes you MAY refer to the real latest search through placeholders written exactly like "
           "{top_job}, chosen from 'placeholders' — they are filled with real values later; never write such facts yourself. "
           if with_facts else "This kind of scene is not about the job search; do not mention it. ")
        + "Do not reuse any opening from 'openings_already_used'. Pick an emotion, a gesture and an action (usually 'none') "
          "for every line from the allowed lists, and an ending.")
    user = json.dumps({
        "kind_of_scene": kind + " — " + DRAMA[kind],
        "pairs": [{"A": {"name": AGENTS[x][0], "job": AGENTS[x][1], "personality": AGENTS[x][2]},
                   "B": {"name": AGENTS[y][0], "job": AGENTS[y][1], "personality": AGENTS[y][2]}} for x, y in pairs],
        **({"placeholders": PLACEHOLDERS} if with_facts else {}),
        "openings_already_used": [_clean(t, 90) for t in old_firsts],
        "allowed_emotions": EMOTIONS, "allowed_gestures": GESTURES, "allowed_actions": ACTIONS,
        "allowed_endings": ENDINGS if kind != "break" else ["none", "make_up", "storm_off", "sulk"],
    }, ensure_ascii=False)
    from jobhunterx.intelligence.llm_structured import call_structured
    res, model = await call_structured(task="office_bank", version="v1", model=SceneBatch, system=system, user=user,
                                       chain="fast", max_tokens=4000, use_cache=False)
    if not res:
        return 0
    seen = {t.lower() for t in old_firsts}
    kept = 0
    for sc in res.scenes:
        if not 0 <= sc.pair < len(pairs):
            continue
        lines, needs = [], set()
        for ln in sc.lines[:7]:
            text = _clean(ln.text, 100)
            names = set(_PH.findall(text))
            if not text or not names <= set(PLACEHOLDERS) or not _numbers_ok(_PH.sub("", text), "", loose=kind != "break"):
                continue
            needs |= names
            lines.append({"who": 1 if ln.who == 1 else 0, "text": text,
                          "emotion": ln.emotion if ln.emotion in EMOTIONS else "neutral",
                          "gesture": ln.gesture if ln.gesture in GESTURES and ln.gesture != "none" else None,
                          "action": ln.action if ln.action in ACTIONS and ln.action != "none" else None})
        if len(lines) < 3 or lines[0]["text"].lower() in seen:
            continue
        seen.add(lines[0]["text"].lower())
        x, y = pairs[sc.pair]
        ending = sc.ending if sc.ending in ENDINGS else "none"
        await db.execute("INSERT INTO office_scenes (id, a, b, kind, lines_json, ending, ending_who, needs, created) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (uuid.uuid4().hex, x, y, kind, json.dumps(lines, ensure_ascii=False), ending,
                          1 if sc.ending_who == 1 else 0, ",".join(sorted(needs)), time.time()))
        kept += 1
    await db.commit()
    log.info("office_bank_batch", kind=kind, kept=kept, asked=len(pairs), model=model)
    return kept


async def refill(force: bool = False) -> int:
    """Write a few batches of new scenes (skipped while a search runs, or if the last refill was recent)."""
    if not _state["last_refill"]:                 # after a restart: the newest scene tells when the last refill ran
        async with _db() as db:
            await _ensure_table(db)
            cur = await db.execute("SELECT MAX(created) FROM office_scenes")
            _state["last_refill"] = (await cur.fetchone())[0] or 0.0
    if _state["running"] or (not force and time.time() - _state["last_refill"] < _refill_every_s()):
        return 0
    run = await storage.latest_run()
    if run and run.get("status") in ("queued", "running"):
        return 0                                  # a search needs the free AI limits more than the office does
    _state["running"] = True
    added = 0
    try:
        async with _db() as db:
            await _ensure_table(db)
            cur = await db.execute("SELECT COUNT(*) FROM office_scenes")
            total = (await cur.fetchone())[0]
            calls = CALLS_PER_REFILL if total < TARGET else 1      # full bank: one batch keeps it fresh
            for i in range(calls):
                kind, pairs = await _plan_batch(db)
                try:
                    added += await _write_batch(db, kind, pairs)
                except Exception as exc:              # no free model right now: try again at the next refill
                    log.info("office_bank_batch_failed", error=str(exc)[:120])
                    break
            cur = await db.execute("SELECT COUNT(*) FROM office_scenes")
            extra = (await cur.fetchone())[0] - (CAP if total < TARGET else TARGET)
            if extra > 0:                             # retire the most-heard scenes first
                await db.execute("DELETE FROM office_scenes WHERE id IN (SELECT id FROM office_scenes "
                                 "ORDER BY uses DESC, created ASC LIMIT ?)", (extra,))
                await db.commit()
    finally:
        _state["running"] = False
        _state["last_refill"] = time.time()
    return added


def start_refills() -> None:
    """Background loop: the first refill a minute after start (so startup stays fast), then every refill period.
    A run that was skipped because a search was running is retried 10 minutes later."""
    import asyncio
    if _state["task"]:
        return

    async def loop() -> None:
        await asyncio.sleep(60)
        while True:
            try:
                before = _state["last_refill"]
                await refill()
                wait = _refill_every_s() if _state["last_refill"] != before else 600
            except Exception as exc:
                log.warning("office_bank_refill_failed", error=str(exc)[:160])
                wait = 600
            await asyncio.sleep(wait)
    _state["task"] = asyncio.create_task(loop())


async def ask(agent: str, question: str) -> dict:
    """The person asks one agent a question; the answer uses only this person's real search data."""
    if agent not in AGENTS:
        return {"answer": "I don't work here!", "emotion": "surprised"}
    name, job, persona = AGENTS[agent]
    f = await facts()
    run = await storage.latest_run()
    stages = {"understand": ["understand"], "plan": ["plan"], "discover": ["discover"], "normalize": ["normalize"],
              "dedupe": ["dedupe"], "validate": ["validate"], "match": ["extract", "match"], "rank": ["rank"],
              "connect": ["connect"]}[agent]
    mine = [it.get("message", "") for it in (run or {}).get("activity", []) if it.get("stage") in stages][-14:]
    system = (f"You are the {name} in JobHunterX, an AI job-search office. Your job: {job}. Personality: {persona}. "
              "Answer the person's question in character, warm and specific, at most 70 words. Use ONLY the data given "
              "(the person's latest search and your own work log). If the data does not answer it, say so honestly and "
              "suggest where in the app to look. Never invent jobs, companies, numbers or reasons.")
    user = json.dumps({"question": _clean(question, 300), "latest_search": f, "my_work_log": mine,
                       "allowed_emotions": EMOTIONS}, ensure_ascii=False, default=str)
    try:
        from jobhunterx.intelligence.llm_structured import call_structured
        res, _ = await call_structured(task="office_ask", version="v1", model=Answer, system=system, user=user,
                                       chain="fast", max_tokens=500, use_cache=False)
    except Exception as exc:
        log.debug("office_ask_failed", error=str(exc)[:100])
        res = None
    if not res or not res.answer:
        return {"answer": "My AI brain is resting right now — no model is free. Try again in a minute!", "emotion": "sleepy",
                "ok": False}
    text = _clean(res.answer, 520)
    if not _numbers_ok(text, json.dumps(f, default=str) + " ".join(mine) + question):
        text = re.sub(r"\d+(?:\.\d+)?", "some", text)   # a number not in the data is never shown as fact
    return {"answer": text, "emotion": res.emotion if res.emotion in EMOTIONS else "neutral", "ok": True}
