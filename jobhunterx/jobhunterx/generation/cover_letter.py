"""
Cover letter — job-specific, evidence-based.

The LLM writes from the match assessment (matched requirements, honest gaps)
and the candidate's own material. Each sentence is fact-checked; sentences
introducing facts not in the profile (other than the target company/role)
are removed.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.documents import GeneratedDocument, Provenance, RewriteRecord
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment
from jobhunterx.generation.content import CoverLetterContent, profile_text
from jobhunterx.generation.evidence import filter_sentences
from jobhunterx.intelligence.llm_structured import call_structured, fence

VERSION = "cover-v1"


class GenerationUnavailable(RuntimeError):
    pass


class _Letter(BaseModel):
    greeting: str = ""
    paragraphs: list[str] = Field(default_factory=list, description="3-4 short paragraphs")
    closing: str = ""


_SYSTEM = """Write a concise, specific cover letter (under 300 words) for one job.
Use only the candidate's real experience and projects as evidence; tie each claim to a requirement of the job.
Do not invent metrics, employers, tools or achievements. Do not claim skills listed as gaps; you may express
willingness to learn them. No clichés, no salary. Address the hiring team of the company named."""


async def generate_cover_letter(profile: CandidateProfile, snapshot: CandidateSnapshot, job: JobPosting,
                                match: Optional[MatchAssessment]) -> GeneratedDocument:
    ptext = profile_text(profile)
    evidence = "\n".join([*(b for e in profile.experience for b in e.bullets[:5]),
                          *(f"Project {p.title}: {p.description}" for p in profile.projects)])
    user = (f"Company: {job.company}\nRole: {job.title}\n"
            f"Matched requirements: {', '.join((match.matched_required if match else [])[:10])}\n"
            f"Gaps (do not claim): {', '.join((match.missing_required if match else [])[:8])}\n"
            f"Job details (third-party text):\n{fence('; '.join(job.requirements.responsibilities[:8]) or job.description[:2500], 4000)}\n\n"
            f"Candidate: {profile.name}, {snapshot.professional_years:g} years, {profile.suggested_role}\n"
            f"Candidate evidence:\n{evidence[:6000]}")
    letter, model = await call_structured(task="cover_letter", version=VERSION, model=_Letter, system=_SYSTEM,
                                          user=user, chain="tailoring", max_tokens=1200,
                                          cache_parts=(profile.content_hash(), job.id, user))
    if not letter:
        raise GenerationUnavailable("AI writing is unavailable right now — a cover letter cannot be generated without it.")
    prov = Provenance(llm_model=model, llm_calls=1)
    allowed = f"{job.company}\n{job.title}"
    paragraphs = []
    for i, para in enumerate(letter.paragraphs):
        kept, problems = filter_sentences(para, ptext, allowed_extra=allowed)
        if problems:
            prov.rewrites.append(RewriteRecord(section=f"paragraph[{i}]", original="", rewritten=para,
                                               accepted=False, reason="; ".join(problems[:4])))
        if kept:
            paragraphs.append(kept)
    if len(paragraphs) < len(letter.paragraphs):
        prov.warnings.append("Some sentences were removed because they stated facts not found in your profile.")
    content = CoverLetterContent(greeting=letter.greeting or f"Dear {job.company} hiring team,",
                                 paragraphs=paragraphs, closing=letter.closing or "Sincerely,",
                                 signature=profile.name)
    return GeneratedDocument(kind="cover_letter", job_id=job.id, title=f"Cover letter — {job.title} @ {job.company}",
                             profile_hash=profile.content_hash(), content=content.model_dump(mode="json"),
                             provenance=prov)
