"""
Connector — a route to a real person for the jobs that fit best.

Most applications to a public post are never read; a referral, or a short note to the right person, usually is.
For each top match the Connector:

1. **Collects real routes** — an application email the posting itself gives (never guessed), the company's careers
   page, and people searches on LinkedIn and Google: recruiters, the team that is hiring, and alumni of your own
   college at that company. They are search links: you choose the person. No profile is scraped and no address is
   invented.
2. **Drafts two short messages in your voice** — a LinkedIn connection note (LinkedIn allows 300 characters) and a
   longer email / DM — from facts in your profile and this match only: the skills you really matched, one real role or
   project. A draft that mentions a number or a skill that is not in those facts is replaced by a plain template.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, quote_plus

from pydantic import BaseModel, Field

from jobhunterx.config.logging import get_logger
from jobhunterx.discovery import watchlist
from jobhunterx.domain.candidate import CandidateProfile, CandidateSnapshot
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment
from jobhunterx.intelligence import reach

log = get_logger("connect")

NOTE_MAX = 300          # LinkedIn's limit for a connection-request note
MESSAGE_MAX = 900
TOP_JOBS = 5            # referral kits made during a search; any other job gets one on request


class Route(BaseModel):
    kind: str           # email | careers | recruiters | team | alumni | xray
    label: str
    url: str
    note: str = ""


class Connection(BaseModel):
    company: str = ""
    title: str = ""
    routes: list[Route] = Field(default_factory=list)
    note: str = ""      # LinkedIn connection note, ≤ 300 characters
    subject: str = ""
    message: str = ""
    method: str = "template"                    # llm | template
    facts: list[str] = Field(default_factory=list)   # what the drafts were allowed to say
    created_at: str = ""


class _Draft(BaseModel):
    note: str = Field("", description="LinkedIn connection note, at most 300 characters, no greeting name placeholder")
    subject: str = Field("", description="email subject, under 70 characters")
    message: str = Field("", description="email / DM body, 70-130 words, plain text, signed with the candidate's first name")


_SYS = """You write short, warm, specific outreach for a job seeker in India asking a person at a company for a referral
or a quick word with the hiring team. Rules:
- Use ONLY the facts given. Never invent achievements, numbers, companies, tools, dates or titles.
- Mention at most 3 of the matched skills, and the one real role or project given, in plain words.
- No flattery, no "I hope this finds you well", no emojis, no placeholders like [Name] — start with "Hi," or "Hi there,".
- note: one or two sentences, at most 280 characters. message: 70-130 words, ends with a thank-you and the first name.
- Polite and direct: ask for a referral or for who the right person to speak to is."""


def _first_name(name: str) -> str:
    return (name or "").strip().split(" ")[0].title() if name else ""


def _city(profile: CandidateProfile, job: JobPosting) -> str:
    for c in (job.locations or []):
        if c:
            return c
    return (profile.location or "").split(",")[0].strip()


def _college(profile: CandidateProfile) -> str:
    for e in profile.education or []:
        if e.institution:
            return e.institution
    return ""


def _highlight(profile: CandidateProfile, skills: list[str]) -> str:
    """The one real role or project that shows the most of the matched skills."""
    want = [s.lower() for s in skills]
    best, best_n = "", -1
    for x in profile.experience or []:
        text = " ".join([x.role, *x.bullets]).lower()
        n = sum(1 for s in want if s and s in text)
        if x.role and x.company and n > best_n:
            best, best_n = f"{x.role} at {x.company}", n
    for pr in profile.projects or []:
        text = " ".join([pr.title, pr.description, *pr.technologies]).lower()
        n = sum(1 for s in want if s and s in text)
        if pr.title and n > best_n:
            best, best_n = f"project “{pr.title}”", n
    return best


def _li_people(q: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={quote(q)}"


def routes_for(job: JobPosting, profile: CandidateProfile) -> list[Route]:
    company = (job.company or "").strip()
    out: list[Route] = []
    email = reach.application_email(job)
    if email:
        out.append(Route(kind="email", label=f"Email {email}", url=f"mailto:{email}",
                         note="The posting itself asks for applications at this address — a person reads it."))
    wc = watchlist.find(job)
    careers = (wc.careers_url if wc and wc.careers_url else "") or (job.apply_url or "")
    if careers:
        out.append(Route(kind="careers", label="Apply on the company's own site", url=careers,
                         note="Apply here first, then reach out — a referral points to an application that exists."))
    if not company or company.lower().startswith("unknown"):
        return out
    city = _city(profile, job)
    out.append(Route(kind="recruiters", label=f"Recruiters at {company}", url=_li_people(f"{company} talent acquisition"),
                     note="People who hire for the company — ask who handles this role."))
    team = re.sub(r"(?i)\b(senior|sr\.?|junior|jr\.?|lead|principal|staff|intern|i{1,3}|[0-9]+)\b", " ", job.title or "")
    team = re.sub(r"[\W_]+", " ", team).strip()
    if team:
        out.append(Route(kind="team", label=f"{team} people at {company}", url=_li_people(f"{company} {team}"),
                         note="Someone already doing this job — the best person to refer you."))
    college = _college(profile)
    if college:
        out.append(Route(kind="alumni", label=f"{college} alumni at {company}", url=_li_people(f"{college} {company}"),
                         note="People from your own college reply far more often."))
    xq = f'site:linkedin.com/in "{company}" (recruiter OR "talent acquisition" OR "hiring")' + (f" {city}" if city else "")
    out.append(Route(kind="xray", label="Find recruiters with Google", url=f"https://www.google.com/search?q={quote_plus(xq)}",
                     note="Google often finds recruiter profiles LinkedIn's own search hides."))
    return out


def _facts(job: JobPosting, match: Optional[MatchAssessment], profile: CandidateProfile, snap: Optional[CandidateSnapshot]):
    skills = list((match.matched_required if match else []) or [])[:4]
    if len(skills) < 2 and match:
        skills += [s for s in match.matched_preferred if s not in skills][: 3 - len(skills)]
    role = profile.suggested_role or (profile.experience[0].role if profile.experience else "")
    years = snap.total_years if snap else 0.0
    facts = {
        "candidate_first_name": _first_name(profile.name),
        "candidate_role": role,
        "years_experience": (f"{years:g}" if years >= 1 else "") if years else "",
        "matched_skills": skills,
        "real_role_or_project": _highlight(profile, skills),
        "job_title": job.title,
        "company": job.company,
        "city": _city(profile, job),
    }
    return facts


def _template(f: dict) -> _Draft:
    me = f["candidate_first_name"] or "me"
    skills = ", ".join(f["matched_skills"][:3])
    who = f["candidate_role"] or "engineer"
    exp = f" ({f['years_experience']} years)" if f["years_experience"] else ""
    note = (f"Hi, I'm {me}, a {who}{exp}" + (f" working with {skills}" if skills else "")
            + f". I'm applying for {f['job_title']} at {f['company']} — would you be open to referring me or pointing me "
              f"to the right person? Thank you!")
    body = [f"Hi,", "",
            f"I'm {me}, a {who}{exp}" + (f" with hands-on work in {skills}" if skills else "") + "."
            + (f" Most recently: {f['real_role_or_project']}." if f["real_role_or_project"] else ""),
            "",
            f"I'm applying for the {f['job_title']} role at {f['company']} and it matches what I do well. Would you be open "
            f"to referring me, or telling me who the right person to speak to is? Happy to share my resume.",
            "", "Thank you for your time,", me]
    return _Draft(note=_trim(note, NOTE_MAX), subject=f"{f['job_title']} at {f['company']} — referral request",
                  message="\n".join(body))


def _trim(text: str, n: int) -> str:
    text = re.sub(r"[ \t]+", " ", (text or "").strip())
    if len(text) <= n:
        return text
    cut = text[:n]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return (cut[:end + 1] if end > n * 0.5 else cut.rsplit(" ", 1)[0] + "…").strip()


def _honest(d: _Draft, f: dict, job: JobPosting, match: Optional[MatchAssessment]) -> bool:
    """Only facts we gave: no new numbers, no skill the candidate was found to be missing."""
    allowed = " ".join(str(v) for v in f.values())
    text = f"{d.note} {d.subject} {d.message}"
    for num in re.findall(r"\d+(?:\.\d+)?", text):
        if num not in allowed:
            return False
    missing = [*(match.missing_required if match else []), *(match.missing_preferred if match else [])]
    low = text.lower()
    for s in missing:
        s = (s or "").strip().lower()
        if len(s) > 1 and re.search(rf"(?<![\w+#]){re.escape(s)}(?![\w+#])", low) and s not in allowed.lower():
            return False
    return bool(d.note and d.message)


async def build(job: JobPosting, match: Optional[MatchAssessment], profile: CandidateProfile,
                snap: Optional[CandidateSnapshot] = None, use_llm: bool = True) -> Connection:
    f = _facts(job, match, profile, snap)
    draft, method = None, "template"
    if use_llm:
        try:
            import json
            from jobhunterx.intelligence.llm_structured import call_structured
            res, _ = await call_structured(task="connect_draft", version="v1", model=_Draft, system=_SYS,
                                           user="Facts:\n" + json.dumps(f, ensure_ascii=False, indent=1),
                                           chain="tailoring", max_tokens=700,
                                           cache_parts=(json.dumps(f, sort_keys=True),))
            if res:
                res.note, res.message = _trim(res.note, NOTE_MAX), _trim(res.message, MESSAGE_MAX)
                res.subject = _trim(res.subject, 90)
                if _honest(res, f, job, match):
                    draft, method = res, "llm"
                else:
                    log.info("connect_draft_rejected", company=job.company)
        except Exception as exc:
            log.debug("connect_draft_failed", error=str(exc)[:100])
    draft = draft or _template(f)
    facts = [x for x in [f["candidate_role"], *f["matched_skills"], f["real_role_or_project"]] if x]
    return Connection(company=job.company, title=job.title, routes=routes_for(job, profile), note=draft.note,
                      subject=draft.subject, message=draft.message, method=method, facts=facts,
                      created_at=datetime.now(timezone.utc).isoformat())
