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
import re

from jobhunterx.generation.evidence import filter_sentences, snapshot_facts
from jobhunterx.generation.repair import repair_text
from jobhunterx.intelligence.llm_structured import call_structured, fence

VERSION = "cover-v2"


class GenerationUnavailable(RuntimeError):
    pass


class _Letter(BaseModel):
    greeting: str = ""
    paragraphs: list[str] = Field(default_factory=list, description="3-4 short paragraphs")
    closing: str = ""


_SYSTEM = """Write a concise, specific cover letter (under 300 words) for one job.
Use only the candidate's real experience and projects as evidence; tie each claim to a requirement of the job.
Do not invent metrics, employers, tools or achievements. Do not claim skills listed as gaps; you may express
willingness to learn them. No clichés, no salary. Address the hiring team of the company named.
Write names, degrees, numbers and skill names exactly as the candidate's material writes them (do not expand
abbreviations or convert "20k" into other forms). Talk about the job's needs in plain words; only name a technology
if the candidate's material names it. Each paragraph must read
on its own (never start one with "Furthermore" or "Additionally"). The closing is just the sign-off words
(e.g. "Sincerely,") without the name."""


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
    allowed = f"{job.company}\n{job.title}\n{snapshot_facts(snapshot)}"
    raw = [p.strip() for p in letter.paragraphs if p and p.strip()]
    checked = [filter_sentences(p, ptext, allowed_extra=allowed) for p in raw]
    problems = [x for _, probs in checked for x in probs]
    paragraphs = [kept for kept, _ in checked if kept]
    if problems:
        # one repair pass on the whole letter keeps it coherent, instead of dropping sentences
        fixed, _ = await repair_text("\n\n".join(raw), problems, ptext, allowed_extra=allowed, task="cover_letter")
        prov.llm_calls += 1
        if fixed:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", fixed) if p.strip()]
            prov.rewrites.append(RewriteRecord(section="letter", original="\n\n".join(raw), rewritten=fixed, accepted=True,
                                               reason="fixed: " + "; ".join(problems[:4])))
        else:
            for i, (para, (kept, probs)) in enumerate(zip(raw, checked)):
                if probs:
                    prov.rewrites.append(RewriteRecord(section=f"paragraph[{i}]", original="", rewritten=para,
                                                       accepted=False, reason="; ".join(probs[:4])))
            prov.warnings.append("Some sentences were removed because they stated facts not found in your profile.")
    if paragraphs:                                   # a letter never opens mid-thought
        paragraphs[0] = re.sub(r"^(?:Furthermore|Additionally|Moreover|Also|In addition),?\s+", "", paragraphs[0])
        paragraphs[0] = paragraphs[0][:1].upper() + paragraphs[0][1:]
    closing = (letter.closing or "Sincerely,").strip()
    if profile.name and closing.lower().endswith(profile.name.lower()):   # the name is printed once, as the signature
        closing = closing[: -len(profile.name)].rstrip(" ,") + ","
    content = CoverLetterContent(greeting=letter.greeting or f"Dear {job.company} hiring team,",
                                 paragraphs=paragraphs, closing=closing,
                                 signature=profile.name)
    return GeneratedDocument(kind="cover_letter", job_id=job.id, title=f"Cover letter — {job.title} @ {job.company}",
                             profile_hash=profile.content_hash(), content=content.model_dump(mode="json"),
                             provenance=prov)
