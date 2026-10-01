"""
Resume generation — concise, job-specific, ATS-friendly, evidence-based.

1. Select (deterministic): rank every experience bullet and project by
   TF-IDF similarity to this job's requirements and responsibilities; keep
   the most relevant evidence that fits one page.
2. Tailor (one LLM call): rewrite only the *selected* bullets to foreground
   what this job cares about, write a job-specific summary, group skills.
3. Verify (deterministic): every rewritten line is fact-checked against its
   original and the profile (`generation.evidence`). Failed rewrites are
   discarded and the original line is used; the decision is recorded in
   provenance so the UI can show exactly what changed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot, norm_term
from jobhunterx.domain.documents import GeneratedDocument, Provenance, RewriteRecord
from jobhunterx.domain.job import JobPosting
from jobhunterx.generation.content import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeContent,
    SkillGroup,
    header_for,
    profile_text,
)
from jobhunterx.generation.evidence import check_free_text, check_rewrite
from jobhunterx.generation.skills import group_skills
from jobhunterx.intelligence.llm_structured import call_structured, fence
from jobhunterx.intelligence.matching import build_idf, cosine
from jobhunterx.intelligence.text import any_term_in_text

VERSION = "resume-v1"

# Layout budget for one page (a product decision, tune here).
MAX_BULLETS_PER_ROLE = 4
MAX_PROJECTS = 3


class _Bullet(BaseModel):
    id: str
    text: str


class _Tailored(BaseModel):
    summary: str = Field("", description="2-3 sentence professional summary for THIS job, third person without pronouns")
    bullets: list[_Bullet] = Field(default_factory=list, description="rewritten versions of the given bullets, same ids")


_SYSTEM = """You tailor a candidate's resume to one job without inventing anything.
Rules:
- Rewrite each given bullet so the parts most relevant to the job come first. Keep the facts identical:
  no new numbers, metrics, tools, technologies, employers, titles, scope or outcomes. If a bullet is already good, return it unchanged.
- Never add a skill or technology to a bullet that the bullet does not already mention, even if the job asks for it.
- Start bullets with a strong verb; keep each under 35 words.
- The summary may only use facts present in the candidate material. No salary, no pronouns, no buzzword stuffing.
- Return every bullet id you were given."""


def _job_text(job: JobPosting) -> str:
    r = job.requirements
    return "\n".join([job.title, *r.responsibilities, *r.requirement_lines, ", ".join(r.required_skills),
                      ", ".join(r.preferred_skills)]) or job.description[:3000]


def _select(profile: CandidateProfile, job: JobPosting, snapshot: CandidateSnapshot):
    jt = _job_text(job)
    docs = [b for e in profile.experience for b in e.bullets] + [f"{p.title} {p.description} {' '.join(p.technologies)}"
                                                                for p in profile.projects]
    idf = build_idf(docs + [job.description, jt])
    exp_sel: dict[int, list[int]] = {}
    for i, e in enumerate(profile.experience):
        ranked = sorted(range(len(e.bullets)), key=lambda k: -cosine(e.bullets[k], jt, idf))
        exp_sel[i] = sorted(ranked[:MAX_BULLETS_PER_ROLE])
    proj_rank = sorted(range(len(profile.projects)),
                       key=lambda k: -cosine(docs[len(docs) - len(profile.projects) + k], jt, idf))
    projects = proj_rank[:MAX_PROJECTS]
    return exp_sel, projects, proj_rank[MAX_PROJECTS:]


async def generate_resume(profile: CandidateProfile, snapshot: CandidateSnapshot, job: JobPosting,
                          *, use_llm: bool = True) -> GeneratedDocument:
    prov = Provenance()
    ptext = profile_text(profile)
    exp_sel, proj_sel, proj_omit = _select(profile, job, snapshot)
    prov.used_experience = list(range(len(profile.experience)))
    prov.used_projects = proj_sel
    prov.omitted_projects = proj_omit

    bullets_in = {f"e{i}b{k}": profile.experience[i].bullets[k] for i, ks in exp_sel.items() for k in ks}
    tailored = None
    if use_llm and (bullets_in or profile.summary):
        user = (
            f"Target job: {job.title} at {job.company}\n"
            f"Job requirements (third-party text):\n{fence(_job_text(job), 5000)}\n\n"
            f"Candidate's demonstrated skills: {', '.join(s.name for s in snapshot.skills[:30])}\n"
            f"Candidate summary: {profile.summary or '(none)'}\n"
            f"Experience: {snapshot.professional_years:g} years, level {snapshot.seniority.value}\n\n"
            "Bullets to tailor (id: text):\n" + "\n".join(f"{k}: {v}" for k, v in bullets_in.items())
        )
        tailored, model = await call_structured(
            task="resume_tailor", version=VERSION, model=_Tailored, system=_SYSTEM, user=user,
            chain="tailoring", max_tokens=2500, cache_parts=(profile.content_hash(), job.id, user),
        )
        if tailored:
            prov.llm_model, prov.llm_calls = model, 1
        else:
            prov.warnings.append("AI tailoring unavailable — your original bullets were used.")

    rewrites = {b.id: b.text.strip() for b in (tailored.bullets if tailored else []) if b.text and b.text.strip()}
    job_terms = job.requirements.required_skills + job.requirements.preferred_skills
    experience: list[ExperienceItem] = []
    for i, e in enumerate(profile.experience):
        out = []
        for k in exp_sel.get(i, []):
            bid, original = f"e{i}b{k}", e.bullets[k]
            new = rewrites.get(bid)
            if new and new != original:
                res = check_rewrite(new, original, ptext, forbidden_new_terms=job_terms)
                prov.rewrites.append(RewriteRecord(section=f"experience[{i}]", original=original, rewritten=new,
                                                   accepted=res.ok, reason="; ".join(res.problems)))
                out.append(new if res.ok else original)
            else:
                out.append(original)
        experience.append(ExperienceItem(role=e.role, company=e.company, location=e.location, start=e.start,
                                         end=e.end, bullets=out))

    summary = profile.summary
    if tailored and tailored.summary.strip():
        res = check_free_text(tailored.summary, ptext)
        prov.rewrites.append(RewriteRecord(section="summary", original=profile.summary, rewritten=tailored.summary,
                                           accepted=res.ok, reason="; ".join(res.problems)))
        if res.ok:
            summary = tailored.summary.strip()

    # Skills: candidate's own skills only; those the job asks for first.
    groups, gmodel = await group_skills(profile, snapshot, use_llm=use_llm)
    if gmodel:
        prov.llm_calls += 1
    wanted = [norm_term(t) for t in job_terms]

    def rank(item: str) -> int:
        forms = [item] + next((s.aliases for s in snapshot.skills if norm_term(s.name) == norm_term(item)), [])
        return 0 if any(norm_term(f) in wanted for f in forms) or any_term_in_text(forms, _job_text(job)) else 1

    skill_groups = [SkillGroup(category=g.category, items=sorted(g.items, key=rank)) for g in groups]
    skill_groups.sort(key=lambda g: min((rank(i) for i in g.items), default=1))

    projects = [ProjectItem(title=p.title, description=p.description, technologies=p.technologies, url=p.url)
                for p in (profile.projects[idx] for idx in proj_sel)]

    content = ResumeContent(
        header=header_for(profile),
        # The candidate's own title — never claim the target job's title.
        headline=profile.suggested_role or (profile.experience[0].role if profile.experience else ""),
        summary=summary,
        skills=skill_groups,
        experience=experience,
        projects=projects,
        education=[EducationItem(**e.model_dump()) for e in profile.education],
        certifications=profile.certifications,
        achievements=profile.achievements[:4],
        languages=profile.languages,
    )
    rejected = [r for r in prov.rewrites if not r.accepted]
    if rejected:
        prov.warnings.append(f"{len(rejected)} AI rewrite(s) failed fact-checking and were replaced by your original text.")
    return GeneratedDocument(kind="resume", job_id=job.id, title=f"Resume — {job.title} @ {job.company}",
                             profile_hash=profile.content_hash(), content=content.model_dump(mode="json"),
                             provenance=prov)
