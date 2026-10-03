"""
Company watchlist — researched employers in Indian tech cities, polled directly.

Why it exists: a public LinkedIn/Naukri post gets hundreds to thousands of
applicants, so an early-career candidate is rarely seen there. The same job
usually appears first on the employer's own ATS board. Polling those boards
every few hours puts the candidate among the first applicants.

The data (`watchlist/companies.json`) is hand-researched: what each company
really does with AI, whether it hires 1–3 year engineers, employee reviews,
red flags, and how crowded applying there is. Mass-recruitment IT services
firms are excluded on purpose (see `MASS_RECRUITERS`).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from jobhunterx.discovery import ats
from jobhunterx.domain.candidate import CandidateSnapshot, norm_term
from jobhunterx.domain.common import WorkMode
from jobhunterx.domain.job import AtsRef, JobPosting
from jobhunterx.intelligence.text import term_in_text

DATA_FILE = Path(__file__).resolve().parent.parent / "watchlist" / "companies.json"

# City name → every way a posting may write it.
CITY_FORMS: dict[str, tuple[str, ...]] = {
    "Hyderabad": ("hyderabad", "secunderabad", "cyberabad", "hitec city", "hitech city", "gachibowli", "madhapur",
                  "kondapur", "financial district", "nanakramguda", "telangana"),
    "Bengaluru": ("bengaluru", "bangalore", "blr", "karnataka", "whitefield", "koramangala", "electronic city",
                  "outer ring road", "hsr layout", "indiranagar"),
}

# Big IT-services / outsourcing employers: high-volume fresher hiring, little
# product AI work. Never recommended; jobs from them are marked as such.
MASS_RECRUITERS = (
    "tcs", "tata consultancy services", "infosys", "wipro", "hcl", "hcltech", "hcl technologies", "tech mahindra",
    "cognizant", "accenture", "capgemini", "ltimindtree", "lti mindtree", "mindtree", "mphasis", "hexaware",
    "genpact", "persistent systems", "coforge", "birlasoft", "zensar", "ntt data", "dxc technology",
    "ibm consulting", "l&t technology services", "ltts", "cyient", "sonata software", "mastek", "happiest minds",
)


class Reviews(BaseModel):
    ambitionbox: Optional[float] = None
    ambitionbox_reviews: Optional[int] = None
    glassdoor: Optional[float] = None
    glassdoor_reviews: Optional[int] = None
    summary: str = ""


class AtsInfo(BaseModel):
    kind: str = ""
    token: str = ""
    verified: bool = False
    open_jobs: Optional[int] = None
    india_jobs: Optional[int] = None


class WatchCompany(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    website: str = ""
    cities: list[str] = Field(default_factory=list)
    category: str = ""
    what_they_do: str = ""
    ai_work: str = ""
    size: str = ""
    stage: str = ""
    careers_url: str = ""
    ats: AtsInfo = Field(default_factory=AtsInfo)
    hires_early_career: str = "unknown"          # yes | some | rare | unknown
    early_career_evidence: str = ""
    role_titles_seen: list[str] = Field(default_factory=list)
    reviews: Reviews = Field(default_factory=Reviews)
    red_flags: list[str] = Field(default_factory=list)
    pay_signal: str = ""
    dsa_heavy_interviews: str = "unknown"
    competition: str = "medium"                  # very_high | high | medium | low
    verdict: str = "good"                        # strong | good | caution | avoid
    why: str = ""
    sources: list[str] = Field(default_factory=list)
    researched_on: str = ""

    @property
    def board(self) -> Optional[AtsRef]:
        """The employer's ATS board, if it is one we can read directly."""
        kind, token = self.ats.kind.lower(), self.ats.token.strip()
        if kind in ats.ADAPTERS and token:
            return AtsRef(kind=kind, token=token)
        ref = ats.parse_ats_url(self.careers_url) if self.careers_url else None
        return ref.model_copy(update={"job_id": ""}) if ref else None

    def names(self) -> set[str]:
        return {norm_term(n) for n in [self.name, *self.aliases] if n}


@lru_cache(maxsize=1)
def load() -> tuple[WatchCompany, ...]:
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    out = []
    for item in raw.get("companies", []):
        try:
            c = WatchCompany.model_validate(item)
        except ValueError:
            continue
        if not is_mass_recruiter(c.name):
            out.append(c)
    return tuple(out)


def is_mass_recruiter(company: str) -> bool:
    n = norm_term(company)
    return bool(n) and any(n == m or term_in_text(m, n) for m in MASS_RECRUITERS)


def cities_for(snap: CandidateSnapshot) -> list[str]:
    """Watchlist cities the candidate wants to work in."""
    wanted = " ; ".join(f for p in snap.locations for f in [p.city, *p.aliases] if f)
    return [city for city, forms in CITY_FORMS.items() if any(term_in_text(f, wanted) for f in forms)]


REMOTE_INDIA = "Remote India"


def for_candidate(snap: CandidateSnapshot) -> list[WatchCompany]:
    """Companies in the candidate's cities (plus remote-India employers if remote is fine), best first."""
    cities = set(cities_for(snap))
    if not cities:
        return []
    if WorkMode.REMOTE in snap.work_modes:
        cities.add(REMOTE_INDIA)
    rank = {"strong": 0, "good": 1, "caution": 2, "avoid": 9}
    picked = [c for c in load() if cities & set(c.cities) and c.verdict != "avoid"]
    return sorted(picked, key=lambda c: (rank.get(c.verdict, 5), c.competition == "very_high", c.name.lower()))


def find_board(ref: AtsRef) -> Optional[WatchCompany]:
    key = (ref.kind, ref.token.lower())
    for c in load():
        b = c.board
        if b and (b.kind, b.token.lower()) == key:
            return c
    return None


def find(job: JobPosting) -> Optional[WatchCompany]:
    """The watchlist entry for a posting's employer (by ATS board, then by name)."""
    companies = load()
    if job.ats and job.ats.token:
        hit = find_board(job.ats)
        if hit:
            return hit
    name = norm_term(job.company)
    if not name:
        return None
    for c in companies:
        if name in c.names():
            return c
    return None


def board_refs(companies: list[WatchCompany]) -> list[tuple[AtsRef, WatchCompany]]:
    out, seen = [], set()
    for c in companies:
        b = c.board
        if b and (b.kind, b.token.lower()) not in seen:
            seen.add((b.kind, b.token.lower()))
            out.append((b, c))
    return out


def public_view(c: WatchCompany) -> dict:
    return c.model_dump(mode="json") | {"board_supported": c.board is not None}
