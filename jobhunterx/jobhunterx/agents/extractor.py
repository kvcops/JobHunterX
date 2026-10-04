"""
Resume extraction: PDF → CandidateProfile.

PyMuPDF reads the text and every embedded link together with the words on it
("GitHub", "Live demo") and the lines around it, so each link can be put where
it belongs (a project, a certificate, the header). The LLM maps everything onto
the CandidateProfile schema (validated by pydantic, one repair attempt). The
resume text is fenced as untrusted data. URLs are only kept if they appear in
the PDF (text or link annotations); links the AI missed are attached to the
project or entry whose title sits next to them.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from jobhunterx.config.logging import get_logger
from jobhunterx.domain.candidate import CandidateProfile, ItemLink, Link
from jobhunterx.intelligence.llm_structured import call_structured, fence

log = get_logger("extractor")

VERSION = "profile-extract-v3"   # v3: college vs affiliating university

_SYSTEM = """You convert a resume into a structured candidate profile.
Extract ONLY what is written in the resume. Never invent or infer employers, dates, skills, metrics or links.
- experience: every job/internship with all of its bullets verbatim (light whitespace cleanup only);
  employment_type is "internship" for internships/trainee roles, otherwise "full_time", "part_time", "contract" or "freelance" if stated, else "".
- education: every degree/diploma/school with grade and details if present. `institution` is the college or school
  actually attended, exactly as written. `university` is the separate affiliating / degree-awarding university ONLY if
  the resume names one (e.g. "CVR College of Engineering, affiliated to JNTU Hyderabad" → institution "CVR College of
  Engineering", university "JNTU Hyderabad"); otherwise leave it empty. Never copy the same name into both.
- projects: every project with its technologies. Put EVERY link of the project in its `links`, each with a short
  `label` taken from the link's own text (e.g. "Code", "Live demo", "Paper", "Video"); set `url` to the main one.
- linkedin / github / portfolio: the candidate's own profile links. Other personal profiles or pages (blog, coding
  profiles, research profiles, personal sites…) go in `links` with a short label.
- item_links: a link that belongs to one certification, achievement or competition (credential, certificate,
  result page): section = "certification" | "achievement" | "competition", item = that entry's text exactly as you wrote it.
- Use the "Embedded links" list: each line is `url | text on the link | nearby lines`; the nearby lines tell you
  which project or entry a link belongs to. Skip email (mailto:) and phone (tel:) links. Never invent a URL.
- skills: every technology, tool, language, framework and method named anywhere in the resume, as written.
- certifications, achievements, competitions, languages (spoken languages) as lists.
- suggested_role: the single job title that best describes the candidate today.
- relevant_experience: a short phrase describing their experience as stated (e.g. "1.5 years in ML engineering").
- Leave qa_memory and preferences empty."""


_URL_IN_TEXT = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]{}|,;\"']+|\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+/[^\s<>()\[\]{}|,;\"']+", re.I)


def _norm_url(url: str) -> str:
    url = (url or "").strip().rstrip(".,;:)")
    if not url or url.lower().startswith(("mailto:", "tel:", "javascript:")):
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def _key(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower()).rstrip("/")


def _looks_like_url(text: str) -> bool:
    t = text.strip().lower()
    return t.startswith(("http", "www.")) or bool(re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/|$)", t))


def _clean_label(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip(" |·•-–—:")
    if not text or _looks_like_url(text) or len(text) > 40:
        return ""
    return text


async def extract_text_and_links_from_pdf(pdf_bytes: bytes) -> tuple[str, list[dict]]:
    """Text plus links: [{url, text (words on the link), near (lines around it), page, top (0-1 position)}]."""
    def _extract():
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            texts, links, seen = [], [], set()
            for pno, page in enumerate(doc):
                text = page.get_text(sort=True)
                texts.append(text)
                words = page.get_text("words")          # x0, y0, x1, y1, word, block, line, n
                lines: dict[tuple, list] = {}
                for w in words:
                    lines.setdefault((w[5], w[6]), []).append(w)
                line_boxes = [(min(w[1] for w in ws), max(w[3] for w in ws), " ".join(w[4] for w in ws)) for ws in lines.values()]
                height = page.rect.height or 1
                for link in page.get_links():
                    url = _norm_url(link.get("uri") or "")
                    if not url or _key(url) in seen:
                        continue
                    seen.add(_key(url))
                    r = link.get("from")
                    anchor = ""
                    near = ""
                    if r is not None:
                        inside = [w[4] for w in words if r.x0 - 1 <= (w[0] + w[2]) / 2 <= r.x1 + 1 and r.y0 - 1 <= (w[1] + w[3]) / 2 <= r.y1 + 1]
                        anchor = " ".join(inside)
                        around = sorted((b for b in line_boxes if b[1] >= r.y0 - 42 and b[0] <= r.y1 + 3), key=lambda b: b[0])
                        near = " / ".join(b[2] for b in around)[-220:]
                    links.append({"url": url, "text": anchor[:80], "near": near, "page": pno,
                                  "top": round((r.y0 / height) if r is not None else 1.0, 3)})
                for m in _URL_IN_TEXT.finditer(text):           # URLs written as plain text (no link annotation)
                    url = _norm_url(m.group(0))
                    if url and "@" not in m.group(0) and _key(url) not in seen:
                        seen.add(_key(url))
                        line = next((ln for ln in text.splitlines() if m.group(0) in ln), "")
                        links.append({"url": url, "text": "", "near": line.strip()[:220], "page": pno, "top": 1.0})
            return "\n\n".join(texts), links
        finally:
            doc.close()

    return await asyncio.to_thread(_extract)


def _attach_links(profile: CandidateProfile, links: list[dict]) -> CandidateProfile:
    """Keep only real URLs, label them, remove duplicates, and place links the AI missed."""
    known = {_key(x["url"]): x for x in links}

    def real(url: str) -> str:
        url = _norm_url(url)
        return url if url and _key(url) in known else ""

    profile.linkedin, profile.github, profile.portfolio = real(profile.linkedin), real(profile.github), real(profile.portfolio)
    used = {_key(u) for u in (profile.linkedin, profile.github, profile.portfolio) if u}

    def label_for(link: Link) -> str:
        return _clean_label(link.label) or _clean_label(known.get(_key(link.url), {}).get("text", ""))

    for proj in profile.projects:
        kept = []
        for link in proj.all_links():
            url = real(link.url)
            if url and _key(url) not in used:
                used.add(_key(url))
                kept.append(Link(label=label_for(Link(label=link.label, url=url)), url=url))
        proj.links, proj.url = kept, (kept[0].url if kept else "")

    entries = {"certification": profile.certifications, "achievement": profile.achievements, "competition": profile.competitions}
    item_links = []
    for il in profile.item_links:
        url = real(il.url)
        if url and _key(url) not in used and il.section in entries and il.item in entries[il.section]:
            used.add(_key(url))
            item_links.append(ItemLink(section=il.section, item=il.item, label=_clean_label(il.label) or label_for(Link(url=url)), url=url))

    extra = []
    for link in profile.links:
        url = real(link.url)
        if url and _key(url) not in used:
            used.add(_key(url))
            extra.append(Link(label=label_for(Link(label=link.label, url=url)), url=url))

    # Links the AI left out: put them next to the project / entry whose title is printed beside them.
    def where(near: str, title: str) -> int:
        """Position of the title in the nearby text (-1 if absent); later = closer to the link."""
        t = re.sub(r"\s+", " ", title or "").strip().lower()[:40]
        return near.rfind(t) if len(t) >= 4 else -1

    def closest(near: str, candidates: list) -> Any:
        scored = [(where(near, title), obj) for title, obj in candidates]
        scored = [x for x in scored if x[0] >= 0]
        return max(scored, key=lambda x: x[0])[1] if scored else None

    for k, info in known.items():
        if k in used:
            continue
        near = re.sub(r"\s+", " ", info.get("near") or "").lower()
        proj = closest(near, [(p.title, p) for p in profile.projects])
        if proj is not None:
            proj.links.append(Link(label=_clean_label(info.get("text", "")), url=info["url"]))
            proj.url = proj.url or info["url"]
            used.add(k)
            continue
        hit = closest(near, [(item, (sec, item)) for sec, items in entries.items() for item in items])
        if hit:
            item_links.append(ItemLink(section=hit[0], item=hit[1], label=_clean_label(info.get("text", "")), url=info["url"]))
            used.add(k)
        elif info.get("page") == 0 and info.get("top", 1) < 0.2:      # in the header: a personal profile
            extra.append(Link(label=_clean_label(info.get("text", "")), url=info["url"]))
            used.add(k)
    profile.links, profile.item_links = extra, item_links
    return profile


async def extract_profile(pdf_bytes: bytes) -> tuple[CandidateProfile, dict]:
    """Return (profile, extraction_info) — info: {status: ok|partial|failed, warnings: [...]}."""
    text, links = await extract_text_and_links_from_pdf(pdf_bytes)
    link_lines = [f"{x['url']} | {x['text'] or '-'} | {x['near'] or '-'}" for x in links]
    if not text.strip():
        return CandidateProfile(), {"status": "failed", "warnings": ["No text found in the PDF (is it a scanned image?)."]}
    user = "Resume text:\n" + fence(text, 30000) + ("\n\nEmbedded links:\n" + fence("\n".join(link_lines), 6000) if links else "")
    profile, model = await call_structured(task="profile_extract", version=VERSION, model=CandidateProfile,
                                           system=_SYSTEM, user=user, chain="extraction", max_tokens=8192,
                                           cache_parts=(text, "\n".join(link_lines)))
    if profile is None:
        return CandidateProfile(), {"status": "failed",
                                    "warnings": ["The AI could not read this resume right now. Please try again or fill in your profile manually."]}
    profile = _attach_links(profile, links)
    warnings = []
    if not profile.experience and not profile.projects:
        warnings.append("No experience or projects were found — please check your profile.")
    if not profile.skills:
        warnings.append("No skills were found — please add them.")
    log.info("profile_extracted", model=model, skills=len(profile.skills), experience=len(profile.experience))
    return profile, {"status": "partial" if warnings else "ok", "warnings": warnings}
