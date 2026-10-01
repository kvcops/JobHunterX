"""
CV generation — comprehensive, career-level, NOT tailored to one job.

Differences from the resume (by design, not by filename):
  * includes every experience with all of its bullets, every project with
    technologies and links, all education, certifications, achievements,
    competitions and languages;
  * bullets are the candidate's own text (light grammar polish only, each
    polished line fact-checked like resume rewrites);
  * the summary describes the whole career and direction (optionally with a
    focus track), not one job's keywords;
  * no page limit (multi-page template), chronological completeness over brevity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.documents import GeneratedDocument, Provenance, RewriteRecord
from jobhunterx.generation.content import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeContent,
    header_for,
    profile_text,
)
from jobhunterx.generation.evidence import check_free_text, check_rewrite
from jobhunterx.generation.skills import group_skills
from jobhunterx.intelligence.llm_structured import call_structured

VERSION = "cv-v1"


class _Line(BaseModel):
    id: str
    text: str


class _CvOut(BaseModel):
    summary: str = Field("", description="4-6 sentence career summary covering the whole profile")
    polished: list[_Line] = Field(default_factory=list, description="grammar-polished bullets, same ids")


_SYSTEM = """You prepare a comprehensive academic/professional CV from a candidate's own material.
- Write a career summary (4-6 sentences) covering their experience, strongest areas, notable projects and direction.
  Use only facts present in the material. No pronouns, no salary.
- Polish each bullet for grammar and clarity ONLY. Do not shorten away detail, do not add or change facts,
  numbers, tools, scope or outcomes. Return every id."""


async def generate_cv(profile: CandidateProfile, snapshot: CandidateSnapshot, *, focus: str = "",
                      use_llm: bool = True) -> GeneratedDocument:
    prov = Provenance(used_experience=list(range(len(profile.experience))),
                      used_projects=list(range(len(profile.projects))))
    ptext = profile_text(profile)
    lines = {f"e{i}b{k}": b for i, e in enumerate(profile.experience) for k, b in enumerate(e.bullets)}
    out = None
    if use_llm:
        tracks = ", ".join(f.label for f in snapshot.role_families[:4])
        user = (f"Focus (optional): {focus or 'none — cover the whole career'}\nCareer tracks: {tracks}\n"
                f"Career direction: {profile.preferences.career_direction or '(not stated)'}\n"
                f"Profile summary: {profile.summary}\n"
                f"Projects: {' | '.join(f'{p.title}: {p.description}' for p in profile.projects)}\n"
                f"Education: {' | '.join(f'{e.degree}, {e.institution}' for e in profile.education)}\n\n"
                "Bullets (id: text):\n" + "\n".join(f"{k}: {v}" for k, v in lines.items()))
        out, model = await call_structured(task="cv", version=VERSION, model=_CvOut, system=_SYSTEM, user=user,
                                           chain="tailoring", max_tokens=3500,
                                           cache_parts=(profile.content_hash(), focus))
        if out:
            prov.llm_model, prov.llm_calls = model, 1
        else:
            prov.warnings.append("AI writing unavailable — your original text was used.")

    polished = {l.id: l.text.strip() for l in (out.polished if out else []) if l.text.strip()}
    experience = []
    for i, e in enumerate(profile.experience):
        bullets = []
        for k, original in enumerate(e.bullets):
            new = polished.get(f"e{i}b{k}")
            if new and new != original:
                res = check_rewrite(new, original, ptext)
                prov.rewrites.append(RewriteRecord(section=f"experience[{i}]", original=original, rewritten=new,
                                                   accepted=res.ok, reason="; ".join(res.problems)))
                bullets.append(new if res.ok else original)
            else:
                bullets.append(original)
        experience.append(ExperienceItem(role=e.role, company=e.company, location=e.location, start=e.start,
                                         end=e.end, bullets=bullets))

    summary = profile.summary
    if out and out.summary.strip():
        res = check_free_text(out.summary, ptext)
        prov.rewrites.append(RewriteRecord(section="summary", original=profile.summary, rewritten=out.summary,
                                           accepted=res.ok, reason="; ".join(res.problems)))
        if res.ok:
            summary = out.summary.strip()

    groups, gmodel = await group_skills(profile, snapshot, use_llm=use_llm)
    if gmodel:
        prov.llm_calls += 1
    content = ResumeContent(
        header=header_for(profile),
        headline=focus or profile.suggested_role,
        summary=summary,
        skills=groups,
        experience=experience,
        projects=[ProjectItem(title=p.title, description=p.description, technologies=p.technologies, url=p.url)
                  for p in profile.projects],
        education=[EducationItem(**e.model_dump()) for e in profile.education],
        certifications=profile.certifications,
        achievements=profile.achievements,
        competitions=profile.competitions,
        languages=profile.languages,
    )
    rejected = [r for r in prov.rewrites if not r.accepted]
    if rejected:
        prov.warnings.append(f"{len(rejected)} AI edit(s) failed fact-checking and were replaced by your original text.")
    return GeneratedDocument(kind="cv", title=f"Curriculum Vitae{' — ' + focus if focus else ''}", focus=focus,
                             profile_hash=profile.content_hash(), content=content.model_dump(mode="json"),
                             provenance=prov)
