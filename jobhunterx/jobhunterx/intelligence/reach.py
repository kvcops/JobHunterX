"""
Reach — the chance that a real person actually reads this application.

Fit answers "am I right for this job?". Reach answers "will anyone see me?".
In the Indian market a public LinkedIn / Naukri / Indeed post gets hundreds
to thousands of applicants within days, so a perfectly fitting early-career
candidate is usually filtered out unread. Reach rewards the opposite
situations: a fresh post on the employer's own board, a small or
lesser-known company, a direct email route, a company known to hire
1–3 year engineers.

Every signal carries plain-language evidence. Nothing is guessed: an
applicant count is used only when the page itself shows one.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from jobhunterx.discovery import watchlist
from jobhunterx.domain.candidate import CandidateSnapshot
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import Reach, ReachSignal

# Public boards where one post collects a crowd. Seeing a job here is fine for
# discovery; applying here is usually a lottery.
CROWDED_BOARDS = {
    "linkedin.com": "LinkedIn", "naukri.com": "Naukri", "indeed.com": "Indeed", "indeed.co.in": "Indeed",
    "glassdoor.co.in": "Glassdoor", "glassdoor.com": "Glassdoor", "foundit.in": "Foundit", "monsterindia.com": "Foundit",
    "shine.com": "Shine", "timesjobs.com": "TimesJobs", "apna.co": "Apna", "freshersworld.com": "Freshersworld",
    "internshala.com": "Internshala", "hirist.tech": "Hirist", "hirist.com": "Hirist",
}
# Platforms where recruiters shortlist from a smaller pool — better than mass boards.
CURATED_BOARDS = {
    "instahyre.com": "Instahyre", "cutshort.io": "Cutshort", "wellfound.com": "Wellfound", "angel.co": "Wellfound",
    "workatastartup.com": "YC Work at a Startup", "ycombinator.com": "YC Work at a Startup",
}

_APPLICANTS = re.compile(r"(?:over\s+)?(\d[\d,]*)\+?\s+(?:applicants|applications|people\s+(?:have\s+)?applied)", re.I)
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_EMAIL_CONTEXT = re.compile(r"send|email|e-mail|mail|share|forward|resume|cv|apply|application|reach", re.I)
_EMAIL_SKIP = re.compile(r"^(no-?reply|privacy|legal|support|help|info|press|media|abuse|security|accommodations?)@", re.I)
_IMMEDIATE = re.compile(r"immediate\s+joiners?|join\s+immediately|joining\s+immediately|immediate\s+joining"
                        r"|(?:join|joining|notice(?:\s+period)?)\s+(?:of\s+|within\s+|upto\s+|up\s+to\s+|less\s+than\s+|<\s*)?(\d{1,2})\s*days", re.I)


def _host(url: str) -> str:
    h = (urlparse(url or "").hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def _board_of(job: JobPosting, table: dict[str, str]) -> Optional[str]:
    for s in job.sources or []:
        h = _host(s.url)
        for dom, name in table.items():
            if h == dom or h.endswith("." + dom):
                return name
    h = _host(job.apply_url or job.canonical_url)
    for dom, name in table.items():
        if h == dom or h.endswith("." + dom):
            return name
    return None


def application_email(job: JobPosting) -> Optional[str]:
    """An email the posting itself asks applications to be sent to (never guessed)."""
    text = job.description or ""
    for m in _EMAIL.finditer(text):
        addr = m.group(0).rstrip(".")
        if _EMAIL_SKIP.match(addr):
            continue
        window = text[max(0, m.start() - 120): m.start()]
        if _EMAIL_CONTEXT.search(window):
            return addr
    return None


def assess_reach(job: JobPosting, snapshot: Optional[CandidateSnapshot] = None,
                 now: Optional[datetime] = None) -> Reach:
    now = now or datetime.now(timezone.utc)
    signals: list[ReachSignal] = []

    def add(key: str, points: int, text: str) -> None:
        signals.append(ReachSignal(key=key, points=points, detail=text))

    # 1. Freshness — the first few days decide who gets read.
    posted = job.posted_at
    if posted:
        hours = max(0.0, (now - posted).total_seconds() / 3600)
        days = hours / 24
        if hours <= 36:
            add("fresh", 30, "Posted in the last day or so — you can be among the first applicants.")
        elif days <= 3:
            add("fresh", 22, f"Posted {days:.0f} days ago — still early.")
        elif days <= 7:
            add("fresh", 10, f"Posted {days:.0f} days ago — the crowd is arriving.")
        elif days <= 14:
            add("fresh", 0, f"Posted {days:.0f} days ago.")
        elif days <= 30:
            add("fresh", -10, f"Posted {days:.0f} days ago — most shortlists are already made.")
        else:
            add("fresh", -20, f"Posted {days:.0f} days ago — very likely already shortlisted or filled.")
    else:
        add("fresh", -3, "Posting date not shown — cannot tell how early you are.")

    # 2. Channel — where the application lands.
    crowded = _board_of(job, CROWDED_BOARDS)
    curated = _board_of(job, CURATED_BOARDS)
    first_party = bool(job.primary_source and job.primary_source.first_party)
    if first_party:
        add("channel", 15, "On the employer's own careers board — applications go straight to their recruiters.")
    elif curated:
        add("channel", 6, f"On {curated} — recruiters shortlist from a smaller pool there.")
    elif crowded:
        add("channel", -22, f"Public {crowded} listing — these usually collect hundreds to thousands of applicants. "
                            "Find the same role on the company's careers page or get a referral.")
    else:
        add("channel", 0, "Company or third-party page — crowd size unknown.")

    # 3. Visible applicant count (only when the page shows one).
    m = _APPLICANTS.search(job.description or "")
    if m:
        n = int(m.group(1).replace(",", ""))
        if n >= 200:
            add("applicants", -20, f"The page shows {n}+ applicants already.")
        elif n >= 50:
            add("applicants", -10, f"The page shows {n} applicants already.")
        else:
            add("applicants", 8, f"The page shows only {n} applicants so far.")

    # 4. Direct email route.
    email = application_email(job)
    if email:
        add("email", 12, f"The posting asks for applications at {email} — a person reads that inbox.")

    # 5. Notice period: Indian startups often want immediate joiners.
    notice = snapshot.notice_period_days if snapshot else None
    im = _IMMEDIATE.search(job.description or "")
    if im and notice:
        limit = int(im.group(1)) if im.group(1) else 0
        if limit < notice:
            want = "immediate joiners" if not im.group(1) else f"joining within {limit} days"
            add("notice", -15, f"Asks for {want}; your notice is {notice} days — likely filtered on this.")

    # 6. Company — researched watchlist data, or a mass recruiter.
    company = watchlist.find(job)
    mass = watchlist.is_mass_recruiter(job.company)
    if mass:
        add("company", -25, f"{job.company} is a mass-recruitment IT services firm — huge applicant volume, little product AI work.")
    elif company:
        comp = {"low": 12, "medium": 4, "high": -6, "very_high": -14}.get(company.competition, 0)
        crowd = {"low": "a lesser-known company — fewer people apply",
                 "medium": "moderate competition", "high": "a well-known name — many apply",
                 "very_high": "a famous brand — very heavy competition"}.get(company.competition, "")
        if crowd:
            add("company", comp, f"{company.name}: {crowd}.")
        early = {"yes": 8, "some": 3, "rare": -8}.get(company.hires_early_career)
        if early is not None:
            add("early_career", early, {"yes": "Known to hire engineers with 1–3 years.",
                                        "some": "Sometimes hires engineers with 1–3 years.",
                                        "rare": "Rarely hires engineers under 3 years."}[company.hires_early_career])
        if company.verdict == "caution" and company.red_flags:
            add("company_flags", -4, "Watch out: " + "; ".join(company.red_flags[:2]))

    score = max(0, min(100, 50 + sum(s.points for s in signals)))
    if mass:
        score = min(score, 25)          # a fresh post doesn't change who reads a bulk-hiring pipeline
    level = "high" if score >= 70 else "medium" if score >= 45 else "low"
    best = sorted([s for s in signals if s.points > 0], key=lambda s: -s.points)
    worst = sorted([s for s in signals if s.points < 0], key=lambda s: s.points)
    headline = (worst[0].detail if level == "low" and worst else best[0].detail if best else
                worst[0].detail if worst else "Not enough information to judge how crowded this is.")
    return Reach(score=score, level=level, headline=headline[:220], signals=signals,
                 application_email=email or "", watchlist_company=company.name if company else "",
                 company_verdict=company.verdict if company else "")
