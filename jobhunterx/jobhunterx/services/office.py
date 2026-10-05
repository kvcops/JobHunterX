"""
The agents' office — live conversations and questions, grounded in real data.

The 3D office shows the pipeline agents as characters. Two things here use AI:

* **Break-time conversations** — two agents chat in character about what they are doing (chai, a ping-pong match,
  something one of them saw at work). The model gets their personalities, the scene, and the *real* facts of the last
  search; every number in a line must appear in those facts, or the line is dropped. Work progress is never invented.
* **Ask an agent** — the person types a question to one agent ("Why did you reject the Zoetis job?") and gets a short,
  in-character answer built only from this person's real search: counts, top matches, reasons for rejections, and the
  agent's own work log.

Both fall back gracefully: without a model, the office uses its scripted talk and the question says it cannot answer.
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
EMOTIONS = ["neutral", "happy", "laugh", "sad", "angry", "surprised", "sleepy", "love", "focused", "wink", "proud", "dizzy"]
GESTURES = ["none", "Wave", "Yes", "No", "ThumbsUp", "Jump", "Dance"]
CHAT_MIN_GAP_S = 8.0           # across the whole app: a busy office never floods the model
_last_chat = 0.0


class Line(BaseModel):
    who: int = Field(0, description="0 = the first agent, 1 = the second")
    text: str = Field("", description="what they say, at most 90 characters, natural spoken English")
    emotion: str = Field("neutral", description="one of: " + ", ".join(EMOTIONS))
    gesture: str = Field("none", description="one of: " + ", ".join(GESTURES))


class Chat(BaseModel):
    lines: list[Line] = Field(default_factory=list)
    learned: list[int] = Field(default_factory=list, description="indexes into 'a_knows_b_doesnt' that A told B about")


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


def _numbers_ok(text: str, allowed: str) -> bool:
    """Every number in a line must come from the real facts — spelled-out counts are not allowed to sneak past."""
    if _NUMBER_WORDS.search(text) and not _NUMBER_WORDS.search(allowed):
        return False
    return all(n in allowed for n in re.findall(r"\d+(?:\.\d+)?", text))


def _clean(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").replace('"', "")).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


async def chat(a: str, b: str, scene: str, a_knows: list[str], b_knows: list[str], moods: dict) -> Optional[dict]:
    """A short break-time conversation in character. None when no model is free (the office uses scripted talk)."""
    global _last_chat
    if a not in AGENTS or b not in AGENTS or a == b:
        return None
    if time.monotonic() - _last_chat < CHAT_MIN_GAP_S:
        return None
    _last_chat = time.monotonic()
    f = await facts()
    a_knows = [_clean(x, 120) for x in a_knows[:4]]
    b_knows = [_clean(x, 120) for x in b_knows[:4]]
    new_for_b = [x for x in a_knows if x not in b_knows]
    pa, pb = AGENTS[a], AGENTS[b]
    system = (
        "You write a tiny, funny, natural conversation between two AI agents who work together in a job-search office in "
        "Hyderabad. They have real personalities and feelings: they tease, laugh, complain, celebrate, get competitive. "
        "Rules: 3 to 6 lines, alternating speakers, each line at most 90 characters, spoken English with a light Indian "
        "flavour (chai, biryani, traffic) when it fits. Use ONLY the facts given for anything about jobs or the search — "
        "never invent numbers, companies, job titles or progress; write any number as digits. If A knows something B doesn't, "
        "A may tell B (gossip). "
        "Pick an emotion and a gesture for every line from the allowed lists.")
    user = json.dumps({
        "A": {"name": pa[0], "job": pa[1], "personality": pa[2], "mood": moods.get("a", "")},
        "B": {"name": pb[0], "job": pb[1], "personality": pb[2], "mood": moods.get("b", "")},
        "scene": _clean(scene, 160),
        "a_knows_b_doesnt": new_for_b,
        "real_facts": f,
        "allowed_emotions": EMOTIONS, "allowed_gestures": GESTURES,
    }, ensure_ascii=False, default=str)
    try:
        from jobhunterx.intelligence.llm_structured import call_structured
        res, model = await call_structured(task="office_chat", version="v1", model=Chat, system=system, user=user,
                                           chain="fast", max_tokens=700, use_cache=False)
    except Exception as exc:
        log.debug("office_chat_failed", error=str(exc)[:100])
        return None
    if not res or not res.lines:
        return None
    allowed = json.dumps(f, default=str) + " ".join(a_knows + b_knows) + scene
    lines = []
    for ln in res.lines[:6]:
        text = _clean(ln.text, 100)
        if not text or not _numbers_ok(text, allowed):
            continue
        lines.append({"who": 1 if ln.who == 1 else 0, "text": text,
                      "emotion": ln.emotion if ln.emotion in EMOTIONS else "neutral",
                      "gesture": ln.gesture if ln.gesture in GESTURES and ln.gesture != "none" else None})
    if len(lines) < 2:
        return None
    learned = [new_for_b[i] for i in res.learned if 0 <= i < len(new_for_b)]
    return {"lines": lines, "learned": learned, "model": model}


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
