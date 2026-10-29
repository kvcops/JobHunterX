"""
Scam signals in a job posting — the frauds that target Indian freshers.

Fraud losses to cyber crime reached about ₹22,495 crore in 2025, most of it investment and "task" scams, and MHA/I4C
warned in May 2026 about fake online interviews used to collect identity and biometric data. The rules below look only
at the posting's own text and links. They are deliberately about *behaviour* (asking for money, moving the chat to
WhatsApp, paying per task, asking for documents before an interview), not about which company it is, so nothing is
hardcoded per employer.

critical → the job is never recommended (shown as "Possible scam" with the reason)
high     → shown with a clear warning; never gets the immediate-joiner boost
medium   → a caution line
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from jobhunterx.domain.job import JobPosting
from jobhunterx.domain.match import ScamCheck, ScamFlag

_RULES: list[tuple[str, str, re.Pattern, str]] = [
    ("fee", "critical", re.compile(
        r"(?i)\b(registration|training|joining|processing|security|onboarding|interview|kit|certification|placement)\s+"
        r"(fee|fees|charges?|deposit|amount)\b|\bpay\s+(?:a\s+|the\s+)?(?:refundable\s+)?(?:fee|deposit|amount)\b"
        r"|\brefundable\s+deposit\b|\b(pay|send|transfer)\b.{0,40}\b(upi|gpay|google\s*pay|phonepe|paytm)\b"),
     "Asks the applicant to pay (a fee, deposit or UPI transfer). Real employers never charge to hire you."),
    ("task_payout", "critical", re.compile(
        r"(?i)\b(per|each)\s+(task|review|like|rating|order|click)\b.{0,30}(₹|rs\.?|inr|earn|paid)"
        r"|\b(daily|instant)\s+(payout|payment|earning)s?\b|\b(like|rate|review)\s+(youtube|videos?|hotels?|products?)\b.{0,40}\bearn"
        r"|\bprepaid\s+tasks?\b|\bcomplete\s+tasks?\s+(and|to)\s+earn\b"),
     "Pays per task / like / review — the pattern of Telegram 'task' scams."),
    ("documents_early", "critical", re.compile(
        r"(?i)\b(share|send|submit|upload|provide)\b.{0,40}\b(aadhaar|aadhar|pan\s*card|bank\s+(account|details|statement)|otp|cvv|"
        r"atm\s+pin|biometric|selfie\s+with)\b|\b(anydesk|teamviewer|quick\s*support|rustdesk)\b"),
     "Asks for ID / bank details, an OTP or a remote-access app up front. Share documents only after a real offer, "
     "on the company's own HR system."),
    ("chat_apps_only", "high", re.compile(
        r"(?i)(wa\.me/|t\.me/|telegram\.me/|chat\.whatsapp\.com)|\b(contact|message|ping|dm|apply|join)\b.{0,25}\b(on|via|through)\s+"
        r"(whatsapp|telegram)\b|\bwhatsapp\s+(only|your\s+(cv|resume))\b"),
     "Moves the conversation to WhatsApp / Telegram. Real recruiters use company email or the job portal."),
    ("no_interview", "high", re.compile(
        r"(?i)\b(no|without)\s+(an?\s+)?interview\b|\bdirect\s+(selection|joining)\b|\bselected\s+without\b|\bguaranteed\s+(job|placement|selection)\b"),
     "Promises selection without an interview or a guaranteed job."),
    ("easy_money", "high", re.compile(
        r"(?i)\b(earn|income)\b.{0,25}(₹|rs\.?|inr)\s?\d[\d,]*\s*(\+\s*)?(per|/|a)\s*(day|week)\b"
        r"|\b(part[\s-]?time|home\s*based|from\s+home)\b.{0,40}\b(earn|income)\b.{0,20}(₹|rs\.?|inr)\s?\d"
        r"|\b(crypto|forex|trading|investment)\s+(job|opportunity|income)\b"),
     "Daily / weekly earning claims or 'investment job' wording — typical of fraud listings."),
    ("data_entry", "medium", re.compile(
        r"(?i)\b(copy[\s-]?paste|form[\s-]?filling|captcha\s+(typing|entry)|sms\s+sending|ad\s+posting)\b.{0,40}\b(work|job)\b"),
     "Copy-paste / form-filling / captcha 'work from home' jobs are mostly scams."),
    ("pressure", "medium", re.compile(
        r"(?i)\b(limited\s+(seats|slots)|offer\s+(valid|expires)\s+(for|in|within)\s+\d+\s*(hours?|hrs?)|pay\s+today|"
        r"confirm\s+(your\s+)?seat|last\s+\d+\s+seats)\b"),
     "Pressure tactics (limited seats, an offer that expires in hours)."),
]
_FREE_MAIL = re.compile(r"(?i)\b[\w.+-]+@(gmail|yahoo|ymail|outlook|hotmail|rediffmail|rediff|proton|protonmail|aol)\.(com|in|co\.in|me)\b")
_ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "smartrecruiters.com", "workable.com", "recruitee.com",
              "myworkdayjobs.com", "keka.com", "oraclecloud.com", "darwinbox", "zohorecruit", "freshteam.com",
              "linkedin.com", "naukri.com", "instahyre.com", "cutshort.io", "wellfound.com", "workatastartup.com",
              "ycombinator.com", "indeed.com", "foundit.in", "iimjobs.com", "hirist", "successfactors", "taleo.net",
              "icims.com", "jobvite.com", "bamboohr.com", "breezy.hr", "pyjamahr", "turbohire", "superset")


YOUNG_DAYS = 180         # younger than this: a caution
NEW_DAYS = 30            # younger than this: a warning


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def check(job: JobPosting) -> ScamCheck:
    text = " ".join([job.title or "", job.description or "", job.apply_url or ""])
    flags: list[ScamFlag] = []
    for rule, sev, rx, why in _RULES:
        if rx.search(text):
            flags.append(ScamFlag(rule=rule, severity=sev, detail=why))
    # An employer of some size that recruits from a free mailbox. Small founders do use Gmail, so only when the posting
    # claims an organisation and gives no other route.
    m = _FREE_MAIL.search(job.description or "")
    company = _norm(job.company)
    if m and company and len(company) > 3 and not job.ats:
        flags.append(ScamFlag(rule="free_mail", severity="medium",
                              detail=f"Applications go to a personal mailbox ({m.group(0)}), not a company domain."))
    # Apply link on an unrelated domain (not the company's, not a known job board / ATS).
    host = (urlparse(job.apply_url or "").hostname or "").lower()
    if host and company and len(company) > 4 and company[:5] not in _norm(host) and not any(h in host for h in _ATS_HOSTS):
        if re.search(r"(?i)(bit\.ly|tinyurl|forms\.gle|docs\.google\.com/forms|t\.me|wa\.me)", host + (job.apply_url or "")):
            flags.append(ScamFlag(rule="odd_link", severity="high",
                                  detail="The apply link is a short link, a Google Form or a chat app — not the company's site."))
    # A website registered only weeks ago (from the domain registry, looked up during validation).
    age = job.validation.checks.get("domain_age")
    days = int(age.value) if age and age.value and age.value.isdigit() else None
    if days is not None and days < YOUNG_DAYS:
        others = [f for f in flags if f.severity in ("critical", "high")]
        when = f"{days} days ago" if days != 1 else "yesterday"
        if others:          # a brand-new site that also asks for money / chats on WhatsApp is the classic fake-job setup
            flags.append(ScamFlag(rule="new_domain", severity="critical",
                                  detail=f"The website was registered {when} and the posting shows other scam signals. {age.evidence}."))
        else:
            flags.append(ScamFlag(rule="new_domain", severity="high" if days < NEW_DAYS else "medium",
                                  detail=f"The website was registered only {when}. Fake job sites are usually weeks old — "
                                         f"genuine new startups are too, so check the founders and the company before you "
                                         f"share anything. {age.evidence}."))
    order = {"critical": 3, "high": 2, "medium": 1}
    level = max((f.severity for f in flags), key=lambda s: order[s], default="none")
    return ScamCheck(level=level, flags=flags)
