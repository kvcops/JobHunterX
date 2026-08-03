# Vellum OS — Architecture v3 (Zero-Touch Job Engine)

> Fully automatic: the user uploads ONE resume. Nothing else.
> No company selection, no dropdowns, no filters. Discovery, probing,
> scoring and the review queue all run by themselves.

## The core insight

ATS boards want to be read: Greenhouse, Ashby, Lever, Recruitee,
SmartRecruiters and BambooHR all publish free, unauthenticated JSON APIs of
their open jobs. Search engines block bots; ATS APIs don't. So:

- **Discovery sources, ranked:**
  1. **hasjob.co ATOM feed** (live, India-focused startup job board) —
     fresh jobs + the startups that posted them, every sync. Companies found
     here are auto-added to the company DB. (~New companies: 0 synonyms)
  2. **Seed index** (`data/companies.csv`, 163 Indian startups) — auto-loaded
     into the DB on the first sync. No user action ever required.
  3. **User-added companies** (optional power feature; never required).
- **Matching is resume-first.** Keyword prefilter (zero tokens) narrows to
  plausible matches, then Gemma batch-scores them vs the profile.
- **LLM is used ONLY where needed** (scoring, tailoring, parsing).
  Only Gemma via Google AI Studio (`gemma-4-26b-a4b-it`), hard budget
  tracker (15k RPD / 30 RPM). No other API keys, no web-search APIs.

## Data flow (fully automatic)

```
USER UPLOADS RESUME  ──►  /api/upload-resume  → profile in DB
                                  │
                                  ▼
      /api/start-search  (single trigger, no inputs)
                                  │
                     ┌────────────┴─────────────┐
                     ▼                          ▼
   seed CSV auto-load          hasjob.co ATOM feed fetch
   (only if DB empty)          (fresh startup jobs + companies)
                     │                          │
                     └──────────┬───────────────┘
                                ▼
              companies table (seed + auto-discovered)
                                ▼
        ats_client.probe(company)      # parallel (6-way semaphore)
                                ▼
        ats_client.fetch_jobs(company)  # free JSON API per ATS
                                ▼
        normalize → dedupe by apply_url hash → store
                                ▼
        job_scorer.score_batch(jobs, profile) # keyword prefilter
                                               # → Gemma batch (10/call)
                                ▼
        review queue (match_score desc)
                                ▼
        validator_tailor → browser_agent   # per job, on click/auto
```

## Modules

| Module | Purpose |
|---|---|
| `config/gemma.py` | Direct Gemma call via `google.genai` + budget tracker (15k RPD / 30 RPM), disk-persisted |
| `tools/ats_client.py` | Unified free ATS JSON clients (probe + fetch), 6 ATS vendors |
| `tools/hasjob.py` | Live hasjob.co ATOM feed client — automatic startup discovery |
| `agents/job_sync.py` | Engine: seed bootstrap + feed discovery + parallel ATS probe → fetch → dedupe → score → store |
| `agents/job_scorer.py` | Keyword prefilter + Gemma batch scoring, budget-aware |
| `data/companies.csv` | Seed list of Indian startups (auto-loaded, not user-facing) |
| `agents/extractor.py` | Resume PDF → structured profile (kept) |
| `agents/validator_tailor.py` | Per-job resume tailoring (kept) |
| `agents/browser_agent.py` | Automated application filling (kept) |

## Honest constraints

- hasjob.co feed is community-posting only (no recruiters/placement
  agencies) → high signal for real Indian startup jobs, ~0-50 jobs per day.
- ATS boards are the bulk source; discovery rate depends on how many tracked
  companies run Greenhouse/Ashby/Lever-class boards (~30% of seed list).
- Gemma free tier: 15k RPD / 30 RPM. Batch scoring = 10 jobs/LLM call.
  Budget tracker pauses LLM scoring (never fetching) at the RPD cap; the
  keyword score keeps the queue usable until the next UTC day.