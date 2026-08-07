"""
Kuro OS — Search Planner

Gemma turns the candidate profile into a precise search plan ONCE per sync
(one LLM call, ~800 tokens) so that every downstream step — eligibility
gate, feed filtering, ranking — operates from the same intelligent
strategy instead of hardcoded keywords.

Plan fields:
  target_roles     : role families to look for (["software engineer", "sde"])
  seniority_max    : highest seniority the candidate can credibly target
                     ("entry" | "mid" | "senior") — drives the eligibility gate
  years_experience : parsed total years (float)
  locations        : acceptable cities; "Remote" is always acceptable
  must_have        : skills that must appear (subset of profile skills)
  reject_terms     : words that disqualify a job outright ("sales", "campus")
"""

from __future__ import annotations

import json
import re
from typing import Optional

from kuro.config import gemma as g
from kuro.config.logging import get_logger

log = get_logger("search_planner")

_PLAN_SYSTEM = """You are a job-search strategist for an Indian software candidate.
Given their resume profile, build a precise search plan. Be strict and honest
about what the candidate can realistically get — do NOT inflate seniority.

Context: This is for the INDIAN job market. Focus on:
- Indian cities (Bangalore, Hyderabad, Mumbai, Pune, Chennai, Delhi NCR, etc.)
- Indian startups, product companies, SaaS companies
- Avoid mass-hiring service companies (TCS, Infosys, Wipro, Cognizant, Accenture, HCL, etc.)
- Focus on companies that actually pay well and have good growth

Rules:
- seniority_max must be the HARD CEILING the candidate can target, based on
  years_experience and role history: 0-1 yrs -> "entry", 2-4 -> "mid",
  5+ -> "senior". If the candidate is a fresher, seniority_max is "entry"
  no matter how good the projects are.
- years_experience: total years, as a number. Fresher = 0.
- target_roles: 2-5 role families, lowercase, e.g. ["software engineer", "full stack developer", "backend developer", "python developer"].
  Include specific technology-based roles if the candidate has strong skills.
- must_have: 4-8 skills from the profile that a matching job MUST touch.
- reject_terms: phrases/roles the candidate should never be shown, e.g. sales, marketing, campus ambassador, senior (when seniority_max is entry/mid).
  Always reject: sales, marketing, business development, business analyst, recruiter, HR.
- locations: the candidate's city plus 2-3 other major Indian tech cities; always include "Remote".
Return ONLY valid JSON:
{"target_roles": [...], "seniority_max": "entry", "years_experience": 0.0,
 "locations": [...], "must_have": [...], "reject_terms": [...], "reasoning": "short"}"""


def _parse_years(raw: str) -> float:
    """'3+ Years in AI/ML' → 3.0 ; 'Fresh Graduate' → 0.0"""
    s = (raw or "").lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years|yrs|year)", s)
    if m:
        return float(m.group(1))
    if re.search(r"fresh|entry|graduate|student|fresher", s):
        return 0.0
    return 0.0


def _default_plan(profile: dict) -> dict:
    """Zero-token fallback when Gemma is unavailable/budget-exhausted."""
    years = _parse_years(profile.get("relevant_experience") or "")
    seniority = "entry" if years < 2 else ("mid" if years < 5 else "senior")
    skills = (profile.get("skills") or [])[:8]
    role = (profile.get("suggested_role") or "software engineer").lower()
    reject = ["sales", "marketing", "business development", "business analyst",
              "recruiter", "hr ", "campus ambassador", "content writer",
              "internship" if years >= 1 else "x__none"]
    if seniority in ("entry", "mid"):
        reject += ["senior", "lead", "principal", "staff", "architect", "manager",
                    "director", "head of", "vp"]
    locations = [profile.get("location") or "Bengaluru"]
    if "Bengaluru" not in locations[0] and "Bangalore" not in locations[0]:
        locations.append("Bengaluru")
    locations.append("Remote")
    tech_roles = [role]
    if "engineer" in role:
        tech_roles.append("developer")
    elif "developer" in role:
        tech_roles.append("engineer")
    tech_roles.append("software engineer")
    tech_roles = list(dict.fromkeys(tech_roles))[:5]
    return {
        "target_roles": tech_roles,
        "seniority_max": seniority,
        "years_experience": years,
        "locations": [loc for loc in locations if loc],
        "must_have": [s for s in skills if s],
        "reject_terms": [r for r in reject if r != "x__none"],
        "reasoning": "fallback plan (no LLM)",
    }


def _parse_plan(text: str) -> Optional[dict]:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def build_search_plan(profile: dict) -> dict:
    """Gemma-generated search plan for this profile. Never raises."""
    plan = _default_plan(profile)
    try:
        if await g.gemma_available():
            skills = ", ".join((profile.get("skills") or [])[:25])
            user = (
                f"Profile:\n- suggested_role: {profile.get('suggested_role') or 'N/A'}\n"
                f"- relevant_experience: {profile.get('relevant_experience') or 'N/A'}\n"
                f"- location: {profile.get('location') or 'N/A'}\n"
                f"- skills: {skills}\n"
                f"- roles held: {', '.join((e.get('role') or '') for e in (profile.get('experience') or [])[:5])}\n\n"
                "Return ONLY the JSON plan."
            )
            raw = await g.call_gemma(
                system=_PLAN_SYSTEM,
                user=user,
                max_tokens=600,
                temperature=0.2,
            )
            parsed = _parse_plan(raw)
            if parsed and parsed.get("target_roles"):
                parsed["years_experience"] = float(
                    parsed.get("years_experience", 0) or 0)
                plan = parsed
                log.info("plan_built_by_gemma", seniority=plan["seniority_max"],
                         years=plan["years_experience"])
    except RuntimeError as exc:
        if "budget_exhausted" in str(exc):
            log.info("plan_fallback_budget_exhausted")
        else:
            log.warning("plan_build_failed", error=str(exc)[:150])
    except Exception as exc:
        log.warning("plan_build_failed", error=str(exc)[:150])
    return plan