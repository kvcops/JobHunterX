"""
The agents' office — live conversations and questions, grounded in real data.

The 3D office shows the pipeline agents as characters. Two things here use AI:

* **Break-time conversations** — two agents chat in character about what they are doing (chai, a ping-pong match,
  something one of them saw at work). The office picks the kind of chat (banter, satire about job ads, an argument,
  jealousy, a scheme, consoling) from their history and moods; lines can carry a physical beat (a stomp, a shove, a
  cartoon bonk, a high-five) and the chat can end in a make-up, someone storming off or sulking, or a chase.
  The model gets their personalities, the scene, the lines heard lately (never to be reused), and the *real* facts of
  the last search; every number in a line must appear in those facts, or the line is dropped. Work progress is never
  invented.
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
CHAT_MIN_GAP_S = 8.0           # across the whole app: a busy office never floods the model
_last_chat = 0.0


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


async def chat(a: str, b: str, scene: str, a_knows: list[str], b_knows: list[str], moods: dict, *, drama: str = "banter",
               relation: str = "", recent: Optional[list[str]] = None, working: bool = False) -> Optional[dict]:
    """A short break-time conversation in character. None when no model is free (the office uses scripted talk)."""
    global _last_chat
    if a not in AGENTS or b not in AGENTS or a == b:
        return None
    if time.monotonic() - _last_chat < CHAT_MIN_GAP_S:
        return None
    _last_chat = time.monotonic()
    f = await facts()
    drama = drama if drama in DRAMA else "banter"
    if working and drama not in ("break", "satire", "banter"):
        drama = "break"
    if drama == "satire":                  # real postings that were binned, and why: the best material there is
        f = {"recently_ruled_out": f.get("recently_ruled_out", [])}
    elif drama not in ("break", "banter"):
        f = {"note": "this scene is not about the job search; do not mention it"}
    a_knows = [_clean(x, 120) for x in a_knows[:4]]
    b_knows = [_clean(x, 120) for x in b_knows[:4]]
    new_for_b = [x for x in a_knows if x not in b_knows]
    pa, pb = AGENTS[a], AGENTS[b]
    system = (
        "You write a short scene of dialogue between two AI agents who work together in a job-search office in Hyderabad. "
        "They are characters with real feelings — they tease, get sarcastic, lose their temper, sulk, scheme, get jealous, "
        "make up. Write it like a sitcom: natural spoken English with a light Indian flavour, people interrupting each "
        "other, trailing off (…), reacting to what was just said instead of taking polite turns. Keep it playful: "
        "anger is cartoonish, a shove or a bonk is slapstick, nobody is cruel, no slurs, no real people. "
        "Rules: 3 to 7 lines, alternating speakers mostly, each line at most 90 characters, no emoji, no hashtags. "
        "The kind of scene leads; the search facts are background — mention them at most once, only when it fits. "
        "Use ONLY the facts given for anything about jobs or the search — never invent numbers, companies, job titles or "
        "progress; write any number as digits. If A knows something B doesn't, A may tell B (gossip). "
        "Tone example (do not copy): A: 'Who put my chair in the sun?' B: 'It looked cold.' A: 'It is a CHAIR.' "
        "B: 'A cold chair, though.' A: '…I am going to bonk you.' "
        "NEVER reuse a line or joke from 'heard_recently' — find a new angle. "
        "Pick an emotion, a gesture and an action (usually 'none') for every line from the allowed lists, and an ending.")
    user = json.dumps({
        "A": {"name": pa[0], "job": pa[1], "personality": pa[2], "mood": moods.get("a", "")},
        "B": {"name": pb[0], "job": pb[1], "personality": pb[2], "mood": moods.get("b", "")},
        "relationship": _clean(relation, 80) or "colleagues",
        "kind_of_scene": drama + " — " + DRAMA[drama],
        "scene": _clean(scene, 160),
        "a_knows_b_doesnt": new_for_b,
        "heard_recently": [_clean(x, 90) for x in (recent or [])[-16:]],
        "real_facts": f,
        "allowed_emotions": EMOTIONS, "allowed_gestures": GESTURES, "allowed_actions": ACTIONS,
        "allowed_endings": ENDINGS if not working else ["none", "make_up", "storm_off", "sulk"],
    }, ensure_ascii=False, default=str)
    try:
        from jobhunterx.intelligence.llm_structured import call_structured
        res, model = await call_structured(task="office_chat", version="v2", model=Chat, system=system, user=user,
                                           chain="fast", max_tokens=900, use_cache=False)
    except Exception as exc:
        log.debug("office_chat_failed", error=str(exc)[:100])
        return None
    if not res or not res.lines:
        return None
    allowed = json.dumps(f, default=str) + " ".join(a_knows + b_knows) + scene
    heard = {_clean(x, 100).lower() for x in (recent or [])}
    lines = []
    for ln in res.lines[:7]:
        text = _clean(ln.text, 100)
        if not text or not _numbers_ok(text, allowed, loose=drama != "break") or text.lower() in heard:
            continue
        lines.append({"who": 1 if ln.who == 1 else 0, "text": text,
                      "emotion": ln.emotion if ln.emotion in EMOTIONS else "neutral",
                      "gesture": ln.gesture if ln.gesture in GESTURES and ln.gesture != "none" else None,
                      "action": ln.action if ln.action in ACTIONS and ln.action != "none" else None})
    if len(lines) < 2:
        return None
    learned = [new_for_b[i] for i in res.learned if 0 <= i < len(new_for_b)]
    ending = res.ending if res.ending in ENDINGS and not (working and res.ending == "chase") else "none"
    return {"lines": lines, "learned": learned, "model": model, "ending": ending, "ending_who": 1 if res.ending_who == 1 else 0}


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
