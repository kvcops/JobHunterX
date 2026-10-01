"""Renderer-agnostic document content shapes (see docs/API.md)."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile
from jobhunterx.domain.candidate import Project


def short_url(url: str, limit: int = 42) -> str:
    """'https://www.github.com/asha/rag/' -> 'github.com/asha/rag' (what a reader can type from a printout)."""
    text = re.sub(r"^https?://(www\.)?", "", (url or "").strip(), flags=re.I).rstrip("/")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _host(url: str) -> str:
    return short_url(url, 200).split("/", 1)[0]


class Link(BaseModel):
    label: str = ""
    url: str
    text: str = ""          # what is printed: the short address (header) or the label (projects)


class Header(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[Link] = Field(default_factory=list)


class SkillGroup(BaseModel):
    category: str
    items: list[str]


class ExperienceItem(BaseModel):
    role: str = ""
    company: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    bullets: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    title: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    url: str = ""
    links: list[Link] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    start: str = ""
    end: str = ""
    grade: str = ""
    details: str = ""


class ResumeContent(BaseModel):
    header: Header = Field(default_factory=Header)
    headline: str = ""
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    item_links: dict[str, list[Link]] = Field(default_factory=dict)   # certification / achievement text -> its links


class CoverLetterContent(BaseModel):
    greeting: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    signature: str = ""


def _web(url: str) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


def header_for(p: CandidateProfile, max_links: int = 6) -> Header:
    """Contact line: LinkedIn, GitHub, portfolio, then other profiles — printed as short addresses, clickable."""
    links: list[Link] = []
    seen: set[str] = set()
    named = [("LinkedIn", p.linkedin), ("GitHub", p.github), ("Portfolio", p.portfolio)]
    for label, url in named + [(l.label, l.url) for l in p.links]:
        key = short_url(url, 500).lower()
        if _web(url) and key not in seen:
            seen.add(key)
            links.append(Link(label=label or _host(url), url=url, text=short_url(url, 38)))
    return Header(name=p.name, email=p.email, phone=p.phone, location=p.location, links=links[:max_links])


def project_item(p: Project, max_links: int = 3) -> "ProjectItem":
    """A project with its links labelled the way the resume had them ("Code", "Live demo"), or by site."""
    links = [Link(label=l.label or _host(l.url), url=l.url, text=l.label or short_url(l.url, 34))
             for l in p.all_links() if _web(l.url)][:max_links]
    return ProjectItem(title=p.title, description=p.description, technologies=p.technologies,
                       url=links[0].url if links else "", links=links)


def item_links_for(p: CandidateProfile) -> dict[str, list[Link]]:
    out: dict[str, list[Link]] = {}
    for il in p.item_links:
        if _web(il.url) and il.item:
            out.setdefault(il.item, []).append(Link(label=il.label or _host(il.url), url=il.url, text=il.label or short_url(il.url, 34)))
    return out


def profile_text(p: CandidateProfile) -> str:
    parts = [p.name, p.summary, p.suggested_role, p.location, ", ".join(p.skills), ", ".join(p.certifications),
             ", ".join(p.achievements), ", ".join(p.competitions), ", ".join(p.languages)]
    for e in p.experience:
        parts += [e.role, e.company, e.location, *e.bullets]
    for pr in p.projects:
        parts += [pr.title, pr.description, ", ".join(pr.technologies)]
    for ed in p.education:
        parts += [ed.degree, ed.institution, ed.details, ed.grade]
    return "\n".join(x for x in parts if x)
