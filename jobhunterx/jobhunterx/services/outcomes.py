"""
What happened after applying — per job and per channel, so each user learns which route works for them.

Every application records its channel, how old the posting was when applied, the experience band, whether it was a
safety-net (large IT-services) job, and whether a person was involved (referral / note to the hiring team). Every
outcome is an event with a date: a human reply, a screening call, an interview, an offer, a rejection.

The main number is **interviews per 10 targeted applications**. Benchmarks the report derives (not proven rates):
generic applications get about 3% human responses, tailored ones about 6%; the target for the targeted lane is 10%+
responses and an interview per 10-15 applications. Below 3% after 40 applications the advice switches from "apply
more" to diagnosis (docs/research/freshers-getting-shortlisted.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from jobhunterx import storage
from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import MatchAssessment

CHANNELS = ["own_site", "referral", "hiring_team", "founder_outreach", "linkedin", "job_board", "challenge",
            "it_services_test", "email", "other"]
CHANNEL_LABELS = {"own_site": "Company's own site", "referral": "Referral", "hiring_team": "Note to the hiring team",
                  "founder_outreach": "Founder outreach", "linkedin": "LinkedIn", "job_board": "Other job board",
                  "challenge": "Hiring challenge", "it_services_test": "IT-services test / drive", "email": "Email to the posting",
                  "other": "Other"}
EVENTS = ["reply", "screen", "interview", "offer", "rejected"]
# tracking statuses that imply an event
STATUS_EVENT = {"interviewing": "interview", "offer": "offer", "rejected": "rejected"}
STOP_LOSS_APPS = 40
STOP_LOSS_RATE = 0.03


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def guess_channel(posting: Optional[JobPosting], match: Optional[MatchAssessment]) -> str:
    if match is not None and match.track == "floor":
        return "it_services_test"
    src = posting.primary_source if posting else None
    if src and src.first_party:
        return "own_site"
    if src and src.name == "linkedin":
        return "linkedin"
    if match is not None and match.reach and match.reach.application_email:
        return "email"
    return "job_board" if src else "other"


def new_record(posting: Optional[JobPosting], match: Optional[MatchAssessment], channel: Optional[str],
               human_path: bool, tailored: bool) -> dict:
    age = None
    if posting is not None and posting.posted_at:
        age = round((datetime.now(timezone.utc) - posting.posted_at).total_seconds() / 86400, 1)
    return {"channel": channel if channel in CHANNELS else guess_channel(posting, match), "applied_at": _now(),
            "age_days_at_apply": age, "band": (match.experience.band if match else "") or "",
            "track": match.track if match else "main", "human_path": bool(human_path), "tailored": bool(tailored),
            "events": []}


def add_event(rec: dict, event: str) -> dict:
    if event in EVENTS and not any(e["kind"] == event for e in rec.get("events", [])):
        rec.setdefault("events", []).append({"kind": event, "at": _now()})
    return rec


def _reached(rec: dict, kinds: tuple[str, ...]) -> bool:
    return any(e["kind"] in kinds for e in rec.get("events", []))


def summarize(records: list[dict]) -> dict:
    """Per-channel and overall results, plus the stop-loss diagnosis."""
    def block(rs: list[dict]) -> dict:
        n = len(rs)
        replies = sum(1 for r in rs if _reached(r, ("reply", "screen", "interview", "offer")))
        interviews = sum(1 for r in rs if _reached(r, ("interview", "offer")))
        offers = sum(1 for r in rs if _reached(r, ("offer",)))
        return {"applied": n, "replies": replies, "interviews": interviews, "offers": offers,
                "response_rate": round(replies / n, 3) if n else None,
                "interviews_per_10": round(10 * interviews / n, 2) if n else None}

    by_channel = {}
    for ch in CHANNELS:
        rs = [r for r in records if r.get("channel") == ch]
        if rs:
            by_channel[ch] = {"label": CHANNEL_LABELS[ch], **block(rs)}
    overall = block(records)
    human = block([r for r in records if r.get("human_path")])
    direct = block([r for r in records if not r.get("human_path")])
    # how much the early-career changes found: interviews from jobs the old matcher hid (below-range years, safety net)
    unlocked = sum(1 for r in records if (r.get("band") in ("direct", "stretch") or r.get("track") == "floor")
                   and _reached(r, ("interview", "offer")))
    diagnosis: list[str] = []
    if overall["applied"] >= STOP_LOSS_APPS and (overall["response_rate"] or 0) < STOP_LOSS_RATE:
        stretch = sum(1 for r in records if r.get("band") == "stretch")
        old = [r for r in records if (r.get("age_days_at_apply") or 0) > 3]
        diagnosis.append(f"Under {int(STOP_LOSS_RATE * 100)}% replies after {overall['applied']} applications — stop adding "
                         "volume and fix the inputs first.")
        if stretch > overall["applied"] * 0.4:
            diagnosis.append(f"{stretch} of your applications were stretch roles (2+ years asked). Shift to 0-2 / 1-3 year "
                             "postings and safety-net tests.")
        if len(old) > overall["applied"] * 0.5:
            diagnosis.append(f"{len(old)} applications went to postings older than 3 days. Apply within 72 hours of posting.")
        if human["applied"] < overall["applied"] * 0.2:
            diagnosis.append("Fewer than 1 in 5 applications had a referral or a note to the hiring team. Use the referral "
                             "pack on your top jobs.")
        diagnosis.append("Check your Naukri / LinkedIn fields (experience in years and months, notice period 'Immediate', "
                         "cities, skills in the job posts' own words) and add one project that proves the core skill.")
    return {"overall": overall, "by_channel": by_channel, "with_person": human, "direct_only": direct,
            "interviews_from_unlocked_jobs": unlocked, "diagnosis": diagnosis,
            "targets": {"response_rate": 0.10, "interviews_per_10": 0.7,
                        "note": "Targets derived from the research report, not proven rates."}}


async def record_status(job_id: str, status: str, posting: Optional[JobPosting], match: Optional[MatchAssessment],
                        current: Optional[dict], channel: Optional[str] = None, human_path: Optional[bool] = None,
                        tailored: bool = False, event: Optional[str] = None) -> Optional[dict]:
    """Keep the outcome record in step with the tracker. Returns the record (None when nothing to keep yet)."""
    rec = dict(current) if current else None
    applying = status in ("applied", "interviewing", "offer") or event
    if rec is None and applying:
        rec = new_record(posting, match, channel, bool(human_path), tailored)
    if rec is None:
        return None
    if channel in CHANNELS:
        rec["channel"] = channel
    if human_path is not None:
        rec["human_path"] = bool(human_path)
    if status in STATUS_EVENT:
        add_event(rec, STATUS_EVENT[status])
    if event:
        add_event(rec, event)
    await storage.set_outcome(job_id, rec)
    return rec
