"""
Skill links — does the candidate already have a job's skill under another name, or closely related experience?

Plain matching only knows exact names and a few aliases. Real postings use other words for the same thing
("Generative AI" for "GenAI", "Large Language Models" for "LLMs") and name newer neighbours of what the candidate
does ("Agentic AI", "LangGraph", "MCP" for someone who builds LLM / RAG apps). This module asks the AI, once per
unmatched skill, whether one of the candidate's skills demonstrates it:

- same    — the same skill under another name, or a part of it the candidate clearly has → full credit
- related — real, transferable experience (an adjacent tool or the field it belongs to)   → partial credit
- none    — not shown

Skills the model does not recognise (new tools appear every month) are looked up on the web first, and the
model decides with that description in hand. Every answer is remembered on disk, so a relationship is learned
once and reused for every job and every later search.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.config.settings import get_settings
from jobhunterx.domain.candidate import CandidateSnapshot, norm_term
from jobhunterx.domain.job import JobPosting
from jobhunterx.intelligence.llm_structured import call_structured

log = get_logger("skill_links")

VERSION = "skill-links-v8"   # v8: field-neutral instructions (v7: whole profile — education, roles, projects)
BATCH = 15                    # job skills judged per AI call (small batches give steadier answers)
LOOKUPS_PER_ROUND = 6         # skills looked up on the web per resolve() call (cached afterwards)
CANDIDATE_SKILLS = 160        # candidate skills shown to the model (all of them, for nearly everyone)
WORK_EXCERPT = 3000           # characters of the candidate's own experience / project text shown with them

_store = None


def _cache():
    global _store
    if _store is None:
        from diskcache import Cache
        _store = Cache(str(get_settings().cache_full_path / "skill_links"))
    return _store


class _Link(BaseModel):
    skill: str
    known: bool = True
    relation: str = Field("none", description="same | related | none")
    via: str = Field("", description="the candidate skill that demonstrates it, exactly as listed")
    why: str = Field("", description="a few words, e.g. 'agent frameworks are built on LLMs'")


class _Links(BaseModel):
    links: list[_Link] = Field(default_factory=list)


_SYSTEM = """You compare a job's requirements with ONE candidate, like an experienced recruiter in the candidate's own
field who keeps up with how that field's tools, methods and job titles change, and who reads the whole resume — not
only its skills list. The candidate can be in any field or industry. You get the candidate's SKILLS, their EVIDENCE
(degrees, jobs held, projects, certifications) and an excerpt of their WORK (experience and project text).
For each JOB REQUIREMENT decide whether the candidate demonstrates it:
- "same": demonstrated — the same thing under another name or spelling, an abbreviation, a narrower or broader name
  the candidate clearly covers, or something their work or projects plainly show they have done.
- A BROAD AREA named in the job is "same" when the candidate has several specific skills or pieces of work inside it.
- A DEGREE or QUALIFICATION requirement is "same" when the candidate's education meets it: the same level in the same or
  a closely related subject (degree names differ by country and institution — judge the substance, not the wording);
  "or equivalent experience" is met by relevant work. Set via to that education line.
- An EXPERIENCE statement ("experience with …", "has done …") is judged against their jobs and projects.
- "related": real, transferable experience — an adjacent tool or method, another one OF THE SAME KIND, the area it
  belongs to, or the foundation it is built on — so the candidate could pick it up quickly.
- "none": no real link. Working in the same broad field is NOT enough on its own.
- A requirement listing ALTERNATIVES ("A, B or C") is met when ANY one alternative is met — judge it by the best one.
- A SOFT SKILL (communication, teamwork, problem solving…) cannot be disproved by a resume: "same", via the closest
  item of their work.
Set "via" to ONE item copied exactly from SKILLS or EVIDENCE that best supports "same" or "related"; empty for "none".
Set "known" to false only if you genuinely do not know what the requirement is (a new or niche product or term).
Return one entry for every job requirement, using its text exactly as given."""


def _key(job_skill: str, cand_hash: str) -> str:
    return f"{VERSION}|{cand_hash}|{norm_term(job_skill)}"


def _cand_skills(snap: CandidateSnapshot) -> list[str]:
    ranked = sorted(snap.skills, key=lambda s: -s.strength)
    return [s.name for s in ranked[:CANDIDATE_SKILLS]]


def _match_evidence(via: str, evidence: list[str]) -> Optional[str]:
    """An evidence line the model pointed at ("education: B.Tech, Computer Science…"), tolerant of small changes."""
    v = norm_term(via)
    if not v:
        return None
    for e in evidence:
        ne = norm_term(e)
        if v == ne or (len(v) > 6 and (v in ne or ne in v)):
            return e
    body = norm_term(via.split(":", 1)[-1])
    for e in evidence:
        if len(body) > 6 and body in norm_term(e.split(":", 1)[-1]):
            return e
    return None


def _cand_hash(names: list[str]) -> str:
    import hashlib
    return hashlib.sha1("|".join(sorted(norm_term(n) for n in names)).encode()).hexdigest()[:16]


def _literally_covered(skill: str, aliases: list[str], snap: CandidateSnapshot, index: dict, text: str) -> bool:
    """Already fully matched: by name or alias, or named in their experience text. Skills that only reach "related"
    through the fixed lists still go to the AI, which may know they are really the same thing (RAG work → "GenAI")."""
    from jobhunterx.intelligence.text import term_in_text
    forms = {norm_term(x) for x in [skill, *aliases] if x}
    if forms & index.keys():
        return True
    return bool(text) and any(len(f) > 1 and term_in_text(f, text) for f in forms)


async def _describe(skill: str) -> str:
    """A short web description of a skill the model does not know (cached for 60 days)."""
    store = _cache()
    k = f"def|{norm_term(skill)}"
    if k in store:
        return store[k]
    text = ""
    try:
        from jobhunterx.tools import deep_search
        hits = await asyncio.wait_for(deep_search.fan_out(f'"{skill}" what is it software technology'), timeout=25)
        best = sorted(hits.values(), key=lambda h: -h.score)[:4]
        text = " | ".join(re.sub(r"\s+", " ", f"{h.title}: {h.snippet}")[:260] for h in best if h.snippet)
    except Exception as exc:
        log.info("skill_lookup_failed", skill=skill, error=str(exc)[:80])
    store.set(k, text, expire=60 * 86400)
    return text


def _match_candidate(name: str, cand: list[str]) -> Optional[str]:
    """The candidate skill the model meant, tolerating case, punctuation and a dropped "(…)" part."""
    n = norm_term(name)
    if not n:
        return None
    by_norm = {norm_term(c): c for c in cand}
    if n in by_norm:
        return by_norm[n]
    bare = norm_term(re.sub(r"\(.*?\)", "", name))
    for c in cand:
        cn = norm_term(c)
        if bare and (bare == norm_term(re.sub(r"\(.*?\)", "", c)) or (len(bare) > 3 and (bare in cn or cn in bare))):
            return c
    # word overlap, singular/plural-insensitive: "LLMs" → "LLM Orchestration", "AI agent" → "Multi-Agent Systems"
    stem = lambda w: w[:-1] if len(w) > 3 and w.endswith("s") else w
    words = {stem(w) for w in re.findall(r"[a-z0-9+#.]+", bare or n) if len(w) > 1 and w not in _GENERIC}
    best = max(cand, key=lambda c: len(words & {stem(w) for w in re.findall(r"[a-z0-9+#.]+", norm_term(c))}), default=None)
    if best and words & {stem(w) for w in re.findall(r"[a-z0-9+#.]+", norm_term(best))}:
        return best
    return None


_GENERIC = {"and", "the", "of", "for", "with", "systems", "system", "development", "engineering", "tools", "framework"}


async def _judge(skills: list[str], cand: list[str], notes: dict[str, str], who: str = "",
                 evidence: Optional[list[str]] = None, work: str = "") -> dict[str, _Link]:
    out: dict[str, _Link] = {}
    evidence = evidence or []
    for i in range(0, len(skills), BATCH):
        part = skills[i:i + BATCH]
        lines = "\n".join(f"- {s}" + (f"   (web description: {notes[s][:400]})" if notes.get(s) else "") for s in part)
        user = (f"CANDIDATE: {who}\nSKILLS: {', '.join(cand)}\nEVIDENCE:\n" + "\n".join(f"- {e}" for e in evidence)
                + (f"\nWORK (excerpt):\n{work[:WORK_EXCERPT]}" if work else "") + f"\n\nJOB REQUIREMENTS:\n{lines}")
        try:
            res, used = await call_structured(task="skill_links", version=VERSION, model=_Links, system=_SYSTEM, user=user,
                                           chain="fast", max_tokens=3500, cache_parts=(user,))
            log.info("skill_links_judged", model=used, skills=len(part))
        except Exception as exc:
            log.info("skill_links_unavailable", error=str(exc)[:100])
            continue
        for link in (res.links if res else []):
            src = next((s for s in part if norm_term(s) == norm_term(link.skill)), None)
            if not src:
                continue
            rel = link.relation.strip().lower()
            via = _match_evidence(link.via, evidence) if link.via.split(":", 1)[0].strip().lower() in (
                "education", "experience", "project", "certification") else None
            via = via or _match_candidate(link.via, cand) or _match_evidence(link.via, evidence)
            if rel in ("same", "related") and not via:
                log.info("skill_link_unplaced", skill=src, via=link.via[:60])
            if rel not in ("same", "related") or not via:
                rel, via = "none", ""
            out[src] = _Link(skill=src, known=link.known, relation=rel, via=via or "", why=link.why[:120])
    return out


async def resolve(snap: CandidateSnapshot, jobs: list[JobPosting], candidate_text: str = "",
                  evidence: Optional[list[str]] = None) -> int:
    """Fill `requirements.skill_links` on each job for requirements plain matching cannot place. Returns links found.
    evidence: the candidate's degrees, jobs, projects and certifications as lines ("education: B.Tech, CSE — …"),
    so a degree or experience requirement can be met by them, not only by a skills-list entry."""
    evidence = list(evidence or [])
    cand = _cand_skills(snap)
    who = (f"{', '.join(snap.target_titles[:3]) or ', '.join(f.label for f in snap.role_families[:3])}; "
           f"~{snap.professional_years:g} years; fields: {', '.join(f.label for f in snap.role_families[:4])}")
    if not cand or not jobs:
        return 0
    chash = _cand_hash(cand + evidence)
    index = snap.skill_index()
    store = _cache()
    wanted: dict[str, None] = {}
    for p in jobs:
        req = p.requirements
        for s in dict.fromkeys([*req.required_skills, *req.preferred_skills]):
            if s and not _literally_covered(s, req.skill_aliases.get(s, []), snap, index, candidate_text):
                wanted.setdefault(s)
    known: dict[str, dict] = {}
    todo = []
    for s in wanted:
        hit = store.get(_key(s, chash))
        if hit is not None:
            known[s] = hit
        else:
            todo.append(s)
    if todo:
        judged = await _judge(todo, cand, {}, who, evidence, candidate_text)
        # Models rarely admit they don't know a new tool: anything judged "unknown" or "none" is read about on the
        # web and judged again with that description (unknown ones first; each description is cached for 60 days).
        unknown = sorted((s for s, l in judged.items() if not l.known or l.relation == "none"),
                         key=lambda s: judged[s].known)[:LOOKUPS_PER_ROUND]
        if unknown:
            notes = dict(zip(unknown, await asyncio.gather(*(_describe(s) for s in unknown))))
            notes = {s: t for s, t in notes.items() if t}
            if notes:
                judged.update(await _judge(list(notes), cand, notes, who, evidence, candidate_text))
        for s, link in judged.items():
            entry = {"relation": link.relation, "via": link.via, "why": link.why}
            store.set(_key(s, chash), entry, expire=90 * 86400)
            known[s] = entry
        log.info("skill_links", asked=len(todo), linked=sum(1 for l in judged.values() if l.relation != "none"),
                 looked_up=len(unknown))
    found = 0
    for p in jobs:
        req = p.requirements
        links = {}
        for s in dict.fromkeys([*req.required_skills, *req.preferred_skills]):
            e = known.get(s)
            if e and e.get("relation") in ("same", "related") and e.get("via"):
                links[s] = e
        req.skill_links = links
        req.links_version = VERSION
        found += len(links)
    return found

