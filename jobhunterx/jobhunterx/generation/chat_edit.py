"""
Chat editing for resumes, CVs and cover letters.

The model never rewrites the document. It answers with a few small, named edit operations ("rewrite bullet 2 of
experience 1", "reorder this skill group", "remove that project"). Every operation is:

1. checked against a fixed whitelist and its index ranges,
2. fact-checked like generated text (no new numbers, tools, employers or links that appear nowhere in the profile, the
   current document or what the user typed),
3. applied to a COPY of the document, which must still validate as a document.

Operations that fail a check are dropped and reported with the reason; the rest are returned as a proposal. Nothing is
saved here: the app previews the proposal and the user keeps or undoes it (saving goes through the normal, validated
document update, which re-renders the PDF). Links, contact details, dates, company names and degrees can't be edited
by chat at all — there is no operation for them.

Chain `editor` (config/models.py): Gemini 3.5 Flash Lite first, then Kilo's free models; thinking is switched off for
both (config/llm_router.py, config/openai_compat.py).
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.generation.content import CoverLetterContent, ResumeContent, profile_text
from jobhunterx.generation.evidence import check_free_text, check_rewrite, numbers
from jobhunterx.intelligence.llm_structured import call_structured

log = get_logger("chat_edit")

MAX_INSTRUCTION = 600
MAX_HISTORY = 6
MAX_OPS = 8
LIMITS = {"headline": 140, "summary": 700, "bullet": 320, "project": 420, "paragraph": 900, "short": 120}
LIST_NAMES = ("achievements", "certifications", "competitions", "languages")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_URL = re.compile(r"(?i)\b(?:https?://|www\.)\S+")

OpName = Literal["set_headline", "set_summary", "rewrite_bullet", "add_bullet", "remove_bullet", "rewrite_project",
                 "remove_project", "reorder_skills", "remove_item", "rewrite_paragraph", "remove_paragraph",
                 "set_greeting", "set_closing"]


class EditOp(BaseModel):
    op: OpName
    index: Optional[int] = None          # experience / project / skill group / paragraph number (0-based)
    sub: Optional[int] = None            # bullet number inside that experience (0-based)
    list_name: str = ""                  # for remove_item: achievements | certifications | competitions | languages
    text: str = ""                       # the new wording
    items: list[str] = Field(default_factory=list)   # reorder_skills: the group's skills in the new order (none added)


class ChatEdit(BaseModel):
    reply: str = Field(default="", description="One or two plain sentences telling the user what you changed or why you could not.")
    ops: list[EditOp] = Field(default_factory=list, description="At most 8 small edits. Empty when nothing should change.")


class Change(BaseModel):
    id: int
    op: str
    label: str                  # "Experience 1 · bullet 2"
    path: str                   # dotted path the preview highlights, e.g. "experience.0.bullets.1"
    before: str = ""
    after: str = ""
    accepted: bool
    reason: str = ""


class ChatResult(BaseModel):
    reply: str
    changes: list[Change]
    content: dict[str, Any]
    model: str = ""


class ChatEditError(Exception):
    """User-facing problem (bad input, no AI available). The message is safe to show."""


_SYSTEM = f"""You are the editing assistant inside a resume builder. The user asks for a change to ONE document. You answer with a few small edit operations, never with the whole document.

Rules:
- Use only these operations. Indices are 0-based and refer to the document JSON you are given.
  set_headline(text) · set_summary(text) · rewrite_bullet(index=experience, sub=bullet, text) · add_bullet(index=experience, text) ·
  remove_bullet(index, sub) · rewrite_project(index, text = the project's description) · remove_project(index) ·
  reorder_skills(index=skill group, items = the SAME skills in a new order; you may drop some, never add) ·
  remove_item(list_name = achievements|certifications|competitions|languages, index) ·
  rewrite_paragraph(index, text) · remove_paragraph(index) · set_greeting(text) · set_closing(text)   (the last four are for cover letters)
- Keep every fact true. Do not invent numbers, tools, employers, titles, dates, links or achievements. You may use details the user states in their message. If the user asks for something that would need an invented fact, make no edit for it and say so in `reply`.
- Keep the user's voice: same tense, concrete, no buzzword padding. Keep bullets to one line where you can (under {LIMITS['bullet']} characters).
- Change only what was asked. Do not touch contact details, links, dates, company names or degrees (there is no operation for them).
- If the request is unclear or nothing should change, return no operations and ask one short question in `reply`.
- `reply` is plain text, at most two sentences. No markdown, no lists.
"""


def clean_text(text: str, limit: int) -> str:
    """One tidy line of plain text: control characters and markup characters out, whitespace collapsed, capped."""
    t = _CONTROL.sub(" ", str(text or "")).replace("<", " ").replace(">", " ")
    return re.sub(r"\s+", " ", t).strip()[:limit]


def _flat(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return "\n".join(_flat(v) for v in content.values())
    if isinstance(content, list):
        return "\n".join(_flat(v) for v in content)
    return ""


def _in_range(i: Optional[int], seq: list) -> bool:
    return isinstance(i, int) and 0 <= i < len(seq)


def _urls_ok(text: str, corpus: str) -> bool:
    return all(u.rstrip(".,;)") in corpus for u in _URL.findall(text))


class _Applier:
    """Applies one operation to a working copy; returns (Change, applied?)."""

    def __init__(self, kind: str, doc: dict, ptext: str, instruction: str):
        self.kind, self.doc = kind, doc
        self.corpus = f"{ptext}\n{_flat(doc)}\n{instruction}"      # facts the profile, the document or the user supplied
        self.ptext = ptext
        self.extra = f"{_flat(doc)}\n{instruction}"
        self.said = numbers(instruction)        # numbers the user typed themselves are theirs to use
        self.n = 0

    def _change(self, op: EditOp, label: str, path: str, before: str, after: str, ok: bool, reason: str = "") -> Change:
        self.n += 1
        return Change(id=self.n, op=op.op, label=label, path=path, before=before, after=after, accepted=ok, reason=reason)

    def _text(self, op: EditOp, label: str, path: str, before: str, limit: int, *, line: bool, required_len: int = 8) -> tuple[Change, Optional[str]]:
        after = clean_text(op.text, limit)
        if len(after) < required_len:
            return self._change(op, label, path, before, after, False, "the new text is empty or too short"), None
        if not _urls_ok(after, self.corpus):
            return self._change(op, label, path, before, after, False, "links can't be added by chat"), None
        res = (check_rewrite(after, before, self.corpus) if line and before
               else check_free_text(after, self.ptext, allowed_extra=self.extra))
        problems = [p for p in res.problems if not (p.startswith("new number '") and p.split("'")[1] in self.said)]
        if problems:
            return self._change(op, label, path, before, after, False, "; ".join(problems)), None
        return self._change(op, label, path, before, after, True), after

    def apply(self, op: EditOp) -> Change:
        d, k = self.doc, op.op
        if self.kind == "cover_letter":
            return self._letter(op)
        if k == "set_headline":
            ch, new = self._text(op, "Headline", "headline", d.get("headline", ""), LIMITS["headline"], line=False, required_len=3)
            if new is not None:
                d["headline"] = new
            return ch
        if k == "set_summary":
            ch, new = self._text(op, "Summary", "summary", d.get("summary", ""), LIMITS["summary"], line=False, required_len=20)
            if new is not None:
                d["summary"] = new
            return ch
        if k in ("rewrite_bullet", "add_bullet", "remove_bullet"):
            exp = d.get("experience", [])
            if not _in_range(op.index, exp):
                return self._change(op, "Experience", "experience", "", "", False, "that experience entry doesn't exist")
            e, label = exp[op.index], f"Experience {op.index + 1}"
            bullets = e.setdefault("bullets", [])
            if k == "add_bullet":
                if len(bullets) >= 8:
                    return self._change(op, label, f"experience.{op.index}.bullets", "", "", False, "this entry already has 8 bullets")
                ch, new = self._text(op, f"{label} · new bullet", f"experience.{op.index}.bullets.{len(bullets)}", "", LIMITS["bullet"], line=False, required_len=15)
                if new is not None:
                    bullets.append(new)
                return ch
            if not _in_range(op.sub, bullets):
                return self._change(op, label, f"experience.{op.index}.bullets", "", "", False, "that bullet doesn't exist")
            path, label = f"experience.{op.index}.bullets.{op.sub}", f"{label} · bullet {op.sub + 1}"
            if k == "remove_bullet":
                before = bullets.pop(op.sub)
                return self._change(op, label, path, before, "", True)
            ch, new = self._text(op, label, path, bullets[op.sub], LIMITS["bullet"], line=True, required_len=15)
            if new is not None:
                bullets[op.sub] = new
            return ch
        if k in ("rewrite_project", "remove_project"):
            projects = d.get("projects", [])
            if not _in_range(op.index, projects):
                return self._change(op, "Project", "projects", "", "", False, "that project doesn't exist")
            p, label, path = projects[op.index], f"Project {op.index + 1}", f"projects.{op.index}"
            if k == "remove_project":
                projects.pop(op.index)
                return self._change(op, f"{label} · {p.get('title', '')}".strip(" ·"), path, p.get("description", ""), "", True)
            ch, new = self._text(op, f"{label} · {p.get('title', '')}".strip(" ·"), f"{path}.description", p.get("description", ""), LIMITS["project"], line=True, required_len=15)
            if new is not None:
                p["description"] = new
            return ch
        if k == "reorder_skills":
            groups = d.get("skills", [])
            if not _in_range(op.index, groups):
                return self._change(op, "Skills", "skills", "", "", False, "that skill group doesn't exist")
            g = groups[op.index]
            have = {s.lower(): s for s in g.get("items", [])}
            new_items, seen = [], set()
            for s in op.items:
                key = clean_text(s, LIMITS["short"]).lower()
                if key in have and key not in seen:
                    new_items.append(have[key])
                    seen.add(key)
                elif key not in have:
                    return self._change(op, f"Skills · {g.get('category', '')}", f"skills.{op.index}", ", ".join(g["items"]), ", ".join(op.items), False,
                                        f"'{s}' isn't one of your skills in this group — chat can reorder or drop skills, not add them")
            if not new_items:
                return self._change(op, f"Skills · {g.get('category', '')}", f"skills.{op.index}", ", ".join(g["items"]), "", False, "that would empty the group")
            before = ", ".join(g["items"])
            g["items"] = new_items
            return self._change(op, f"Skills · {g.get('category', '')}", f"skills.{op.index}", before, ", ".join(new_items), True)
        if k == "remove_item":
            name = op.list_name if op.list_name in LIST_NAMES else ""
            seq = d.get(name, []) if name else []
            if not name or not _in_range(op.index, seq):
                return self._change(op, "Item", op.list_name or "list", "", "", False, "that item doesn't exist")
            before = seq.pop(op.index)
            (d.get("item_links") or {}).pop(before, None)
            return self._change(op, name.title(), f"{name}.{op.index}", before, "", True)
        return self._change(op, k, "", "", "", False, "this edit doesn't apply to a resume or CV")

    def _letter(self, op: EditOp) -> Change:
        d, k = self.doc, op.op
        paras = d.setdefault("paragraphs", [])
        if k == "rewrite_paragraph":
            if not _in_range(op.index, paras):
                return self._change(op, "Paragraph", "paragraphs", "", "", False, "that paragraph doesn't exist")
            ch, new = self._text(op, f"Paragraph {op.index + 1}", f"paragraphs.{op.index}", paras[op.index], LIMITS["paragraph"], line=False, required_len=30)
            if new is not None:
                paras[op.index] = new
            return ch
        if k == "remove_paragraph":
            if not _in_range(op.index, paras) or len(paras) <= 1:
                return self._change(op, "Paragraph", "paragraphs", "", "", False, "a cover letter needs at least one paragraph")
            before = paras.pop(op.index)
            return self._change(op, f"Paragraph {op.index + 1}", f"paragraphs.{op.index}", before, "", True)
        if k in ("set_greeting", "set_closing"):
            field = "greeting" if k == "set_greeting" else "closing"
            ch, new = self._text(op, field.title(), field, d.get(field, ""), LIMITS["short"], line=False, required_len=3)
            if new is not None:
                d[field] = new
            return ch
        return self._change(op, k, "", "", "", False, "this edit doesn't apply to a cover letter")


def validate_content(kind: str, content: dict) -> dict:
    """The document as the app stores it, or ValueError when the shape is wrong."""
    model = CoverLetterContent if kind == "cover_letter" else ResumeContent
    return model.model_validate(content).model_dump(mode="json")


async def chat_edit(kind: str, content: dict, instruction: str, profile: CandidateProfile, history: Optional[list[dict]] = None) -> ChatResult:
    instruction = clean_text(instruction, MAX_INSTRUCTION)
    if len(instruction) < 3:
        raise ChatEditError("Tell me what to change, for example “make the summary shorter”.")
    try:
        base = validate_content(kind, content)
    except Exception:
        raise ChatEditError("This document can't be edited right now. Reload it and try again.")
    turns = []
    for h in (history or [])[-MAX_HISTORY:]:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
            turns.append(f"{h['role'].upper()}: {clean_text(h.get('text', ''), 300)}")
    user = ("<document>\n" + json.dumps(base, ensure_ascii=False) + "\n</document>\n\n"
            + (("EARLIER IN THIS CHAT\n" + "\n".join(turns) + "\n\n") if turns else "")
            + f"DOCUMENT KIND: {kind}\nUSER REQUEST: {instruction}")
    res, model_used = await call_structured(task="resume_chat_edit", version="v1", model=ChatEdit, system=_SYSTEM, user=user,
                                            chain="editor", max_tokens=1500, use_cache=False)
    if res is None:
        raise ChatEditError("The AI couldn't answer just now. Try again in a moment.")
    work = copy.deepcopy(base)
    applier = _Applier(kind, work, profile_text(profile), instruction)
    changes = [applier.apply(op) for op in res.ops[:MAX_OPS]]
    try:
        final = validate_content(kind, work)
    except Exception:                         # an edit left the document in a bad shape: keep the original, say so
        log.warning("chat_edit_invalid_result", kind=kind)
        return ChatResult(reply="That change would have broken the document, so I left it as it was.", changes=[
            c.model_copy(update={"accepted": False, "reason": c.reason or "result was not a valid document"}) for c in changes],
            content=base, model=model_used)
    reply = clean_text(res.reply, 400)
    done = sum(c.accepted for c in changes)
    if changes and not done and not reply:
        reply = "I couldn't make that change without adding facts that aren't in your profile."
    if not changes and not reply:
        reply = "I didn't find anything to change. Could you say more precisely what you'd like?"
    log.info("chat_edit", kind=kind, ops=len(changes), applied=done, model=model_used)
    return ChatResult(reply=reply, changes=changes, content=final if done else base, model=model_used)
