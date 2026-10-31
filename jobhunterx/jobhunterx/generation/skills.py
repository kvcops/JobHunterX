"""Group the candidate's own skills into categories for documents (no fixed category list)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot, norm_term
from jobhunterx.generation.content import SkillGroup
from jobhunterx.intelligence.llm_structured import call_structured

VERSION = "skillgroups-v2"


class _Groups(BaseModel):
    groups: list[SkillGroup] = Field(default_factory=list)


_SYSTEM = """Group a candidate's skills into 3-6 clear resume categories that suit this candidate's field.
Use ONLY the skill names given, spelled exactly as given; every skill must appear in exactly one group.
A name that is itself a category heading rather than a skill (a section title copied in from the resume) is not a
skill: use it as a category name if it fits, and leave it out of the items."""


def _drop_bracketed_repeats(names: list[str]) -> list[str]:
    """'Lmod' is already in 'Environment Modules (Lmod, EasyBuild, Spack)': list it once."""
    import re
    inside = {norm_term(x) for n in names for grp in re.findall(r"\(([^)]*)\)", n) for x in re.split(r"[,/;]", grp) if x.strip()}
    return [n for n in names if "(" in n or norm_term(n) not in inside]


async def group_skills(profile: CandidateProfile, snapshot: CandidateSnapshot, *, use_llm: bool = True) -> tuple[list[SkillGroup], str]:
    names = [s.name for s in snapshot.skills] or list(profile.skills)
    seen: set[str] = set()
    names = [n for n in names if n and not (norm_term(n) in seen or seen.add(norm_term(n)))]
    names = _drop_bracketed_repeats(names)
    if not names:
        return [], ""
    groups, model = (None, "")
    if use_llm:
        # The AI decides the categories for this person's field (no fixed list). If the fast models fail or cut
        # their answer short, a second, different chain gets the same request before giving up.
        for chain in ("fast", "extraction"):
            groups, model = await call_structured(
                task="skill_groups", version=VERSION, model=_Groups, system=_SYSTEM,
                user="Skills: " + " | ".join(names), chain=chain, max_tokens=2400,
                cache_parts=(profile.content_hash(), "|".join(names)),
            )
            if groups and groups.groups:
                break
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
    titles = {norm_term(g.category) for g in out}         # a heading the AI used as a category isn't left over as a skill
    rest = [n for k, n in allowed.items() if k not in used and k not in titles]
    if not out:
        # No model answered at all: one plain list (printed without a label), never categories guessed by keywords.
        return [SkillGroup(category="Skills", items=rest)], ""
    if rest:
        out.append(SkillGroup(category="Other", items=rest))
    return out, model if groups else ""
