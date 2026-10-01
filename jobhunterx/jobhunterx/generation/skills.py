"""Group the candidate's own skills into categories for documents (no fixed category list)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot, norm_term
from jobhunterx.generation.content import SkillGroup
from jobhunterx.intelligence.llm_structured import call_structured

VERSION = "skillgroups-v1"


class _Groups(BaseModel):
    groups: list[SkillGroup] = Field(default_factory=list)


_SYSTEM = """Group a candidate's skills into 3-6 clear resume categories that suit this candidate's field.
Use ONLY the skill names given, spelled exactly as given; every skill must appear in exactly one group."""


async def group_skills(profile: CandidateProfile, snapshot: CandidateSnapshot, *, use_llm: bool = True) -> tuple[list[SkillGroup], str]:
    names = [s.name for s in snapshot.skills] or list(profile.skills)
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        return [], ""
    groups, model = (None, "")
    if use_llm:
        groups, model = await call_structured(
            task="skill_groups", version=VERSION, model=_Groups, system=_SYSTEM,
            user="Skills: " + " | ".join(names), chain="fast", max_tokens=800,
            cache_parts=(profile.content_hash(), "|".join(names)),
        )
    allowed = {norm_term(n): n for n in names}
    out, used = [], set()
    for g in (groups.groups if groups else []):
        items = []
        for it in g.items:
            k = norm_term(it)
            if k in allowed and k not in used:
                used.add(k)
                items.append(allowed[k])
        if items and g.category.strip():
            out.append(SkillGroup(category=g.category.strip()[:40], items=items))
    rest = [n for k, n in allowed.items() if k not in used]
    if rest:
        out.append(SkillGroup(category="Skills" if not out else "Other", items=rest))
    return out, model if groups else ""
