# Vellum OS — Architecture v4 (Zero-Touch, Eligibility-First)

> The user uploads ONE resume. Everything else — search strategy, discovery,
> strict filtering, freshness proof, ranking — runs automatically.
> No company selection, no filters, no "assumed" jobs.

## The value chain (in order — each step kills waste before the next)

```
USER UPLOADS RESUME
        │
        ▼
1. SEARCH PLAN (Gemma, 1 call)          ── profile → target roles, seniority
        │                                  ceiling (entry/mid/senior), years,
        │                                  accepted cities, reject terms.
        │                                  A user-chosen location (UI dropdown)
        │                                  OVERRIDES the plan's city list.
        ▼
2. LIVE DISCOVERY (2 channels, all free/unauthenticated)
        ├─ hasjob.co ATOM feed           ── India startup job board, fresh
        └─ ATS boards (6 vendors)        ── Greenhouse/Ashby/Lever/Recruitee/
                                           SmartRecruiters/BambooHR JSON APIs
                                           (companies auto-added by feeds)
        ▼
3. ELIGIBILITY GATE (zero LLM tokens)    ── STRICT, deterministic, explains
        │                                   every rejection:
        │   • role family (sales/marketing/HR ≠ your field)
        │   • reject terms (senior/lead/architect for entry-level, ...)
        │   • location (Pune-only vs Bengaluru-only candidate → rejected;
        │     foreign cities like "New York, USA" / "London, UK" → rejected)
        │   • years required vs candidate years + seniority ceiling
        ▼
4. STORE (dedupe by apply_url hash)     ── only eligible jobs enter the DB
        ▼
5. GEMMA RANKING (budget-tracked)       ── batch 10 jobs/call, top ~80/day,
        │                                   reasons recorded (score_reason)
        ▼
6. LIVENESS PROOF (zero tokens)         ── top matches GET-checked; closed
        │                                   jobs marked status="closed"
        ▼
REVIEW QUEUE (match_score desc, reasons visible)
        ▼
validator_tailor → browser_agent (per job, on user click/auto)
```

## Why this is the honest design (vs v2/v3)

| Concern (raised in review) | v3 reality | v4 fix |
|---|---|---|
| "Senior dev shown to a fresher" | fuzzy keyword filter | **hard eligibility gate**: seniority ceiling + years math, zero tokens, rejects with a reason |
| "Jobs dumped forever, stale" | stored once, never checked | **liveness check**: top matches GET-verified each sync, closed → status=closed |
| "Wrong city suggested" | only soft boost | **location conflict = hard reject** (city aliases: Bangalore↔Bengaluru etc.) |
| "Sales/marketing junk" | scored, maybe filtered | **role-family + reject-term hard reject** |
| "Only 1 static source, static CSV" | hasjob + static seed | **2 live channels** (hasjob + ATS), seed only bootstraps first run, feeds auto-add companies |
| "Wrong city shown despite my choice" | plan city from resume only | **UI location override**: user-chosen city replaces the plan's list; foreign cities hard-rejected by the gate |
| "Gemma underused" | scored ~20 jobs | **Gemma drives the plan + ranks up to ~80/day** with per-job reasons |
| "Intelligence?" | keyword overlap | **search plan is the intelligence anchor** — Gemma decides roles/seniority/cities/rejects from the actual resume; gate + scorer all execute that plan |

## Honest numbers (measured live, fresher profile, Bengaluru)

- Plan call: ~520 tokens (1 Gemma call)
- Feeds: 12 hasjob jobs (HN "Who's Hiring" removed — global/US-heavy, was the
  main source of wrong-location junk; not worth it for an India-only candidate)
- Eligibility gate: **203 rejected / 68 eligible** — every rejection has a reason
- Gemma ranking: 68 scored in 2 batches (~3.4k tokens total, budget-tracked)
- Liveness: 18 top matches checked → **17 live / 1 gone** (gone → status=closed);
  verdicts + `liveness_checked_at` persisted in `freshness_json`
- ATS: probing is now **parallel** (per-company candidate URLs fetched at once),
  so a dead careers page no longer burns 3 × URL-timeout serially. Live sweep of
  the 163 seed companies (websites only) found boards on ~10: Razorpay/greenhouse
  27, Freshworks/SmartRecruiters 154, Paytm/lever 242, SigNoz/ashby 15,
  Livspace/recruitee 0; Workday + FreshTeam detected but have no public JSON
  (0 jobs, marked probe-probed so they aren't re-probed). Real syncs bound this
  to 60 oldest-first probes/run with 24h freshness
- Cross-source dedupe: 51 dupes dropped (ATS wins over hasjob/HN on same role)
- Probe freshness: companies stamped with `last_probed_at`; next syncs skip them
  for 24h, so runs stay bounded as the company DB grows (~350 tracked)
- Test suite: **90 tests pass** (`pytest tests/ -q`) — parse, eligibility,
  ATS pagination+probe parallelism, dedupe/freshness, liveness, API, Gemma budget,
  resume tailoring; offline via fakes/monkeypatching
- Full-day budget usage: ~4k of 15k tokens — headroom for ATS-probe jobs

## Budget math (brutal, honest)

- 15k RPD / 30 RPM. Plan = 1 call (~530). Ranking = 10 jobs/call (~650/call)
  → ~80-150 jobs/day LLM-ranked safely. Beyond that: keyword score still
  ranks, gate still filters, nothing breaks — it just gets cheaper.
- Fetching, gating, liveness: ZERO tokens. The expensive part (LLM ranking)
  only ever sees candidates that already passed the strict gate.

## Modules

| Module | Role |
|---|---|
| `agents/search_planner.py` | Gemma → search plan (roles, seniority ceiling, years, cities, reject terms) |
| `agents/eligibility.py` | Strict deterministic gate, every rejection explained |
| `tools/hasjob.py` | hasjob.co ATOM feed client |
| `tools/ats_client.py` | 6-vendor free ATS JSON clients (probe + fetch) |
| `tools/liveness.py` | Apply-URL verification (live/gone/unknown) |
| `agents/job_scorer.py` | Keyword prefilter + Gemma batch ranking with reasons |
| `agents/job_sync.py` | Orchestrates plan → discover → gate → store → rank → verify |
| `data/companies.csv` | First-run bootstrap only; feeds self-extend afterwards |

## Known honest limits

- hasjob feed is small (~0-50/day, community only). ATS probing of the ~350
  tracked companies is the volume engine; ~30-40% run free ATS boards.
- Liveness only checks a bounded set of top matches per sync (network cost; default
  `liveness_max_checks=40`, configurable), not all. Retries on 403/429/5xx so a
  single bot-block doesn't kill a live job.
- Eligibility gate is rule-based — it is *strict and explainable*, not
  "smart". If a JD hides its requirements in prose ("we expect someone who
  has shipped…"), the gate passes it and the LLM ranking catches it.
