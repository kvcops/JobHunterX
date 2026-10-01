"""Renderer-agnostic document content shapes (see docs/API.md)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from jobhunterx.domain.candidate import CandidateProfile


class Link(BaseModel):
    label: str
    url: str


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


class CoverLetterContent(BaseModel):
    greeting: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    signature: str = ""


def header_for(p: CandidateProfile) -> Header:
    links = []
    for label, url in (("LinkedIn", p.linkedin), ("GitHub", p.github), ("Portfolio", p.portfolio)):
        if url and url.lower().startswith(("http://", "https://")):
            links.append(Link(label=label, url=url))
    return Header(name=p.name, email=p.email, phone=p.phone, location=p.location, links=links)


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
