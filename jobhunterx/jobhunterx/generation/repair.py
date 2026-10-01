"""
One repair pass for AI-written free text (summary, cover letter).

When the fact-checker finds a few unsupported words or numbers, deleting whole
sentences can leave text that no longer reads well ("Furthermore, …" as the
opening line). Instead the AI gets one chance to rewrite the text without those
parts; the result is checked again, and only used if it passes.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from jobhunterx.generation.evidence import check_free_text
from jobhunterx.intelligence.llm_structured import call_structured, fence

VERSION = "repair-v1"


class _Fixed(BaseModel):
    text: str = ""


_SYSTEM = """You correct a piece of writing so that every fact in it is supported by the candidate's material.
- Remove or rephrase ONLY the parts named in the problems list. Do not add any new fact, number, tool or claim.
- Write names, degrees, titles and numbers exactly as the candidate's material writes them (do not expand abbreviations).
- Keep the meaning, tone, length and paragraph breaks (blank lines). The result must read naturally from the first word."""


async def repair_text(text: str, problems: list[str], material: str, *, allowed_extra: str = "",
                      task: str, chain: str = "tailoring", max_tokens: int = 1200) -> tuple[Optional[str], Optional[str]]:
    """Return (fixed text, model) when the repaired text passes the fact check, else (None, model)."""
    user = ("Problems found:\n" + "\n".join(f"- {p}" for p in problems[:10]) +
            f"\n\nCandidate material (the only allowed source of facts):\n{fence(material, 7000)}"
            + (f"\n\nAlso allowed: {allowed_extra[:1500]}" if allowed_extra else "")
            + f"\n\nText to correct:\n{fence(text, 4000)}")
    fixed, model = await call_structured(task=f"{task}_repair", version=VERSION, model=_Fixed, system=_SYSTEM, user=user,
                                         chain=chain, max_tokens=max_tokens, cache_parts=(text, "|".join(problems), material))
    if not fixed or not fixed.text.strip():
        return None, model
    res = check_free_text(fixed.text, material, allowed_extra=allowed_extra)
    return (fixed.text.strip() if res.ok else None), model
