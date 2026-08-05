<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.140-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/AI-Gemma%204-4285F4?logo=google&logoColor=white" alt="Gemma 4">
  <img src="https://img.shields.io/badge/tests-85%20passing-4caf50" alt="85 tests passing">
  <img src="https://img.shields.io/badge/local%20first-100%25%20private-FF6F00" alt="Local first">
</p>

<h1 align="center">📜 Vellum OS</h1>
<h3 align="center">Careers, but make it automatic.</h3>
<p align="center">
  Upload <b>ONE resume</b>. Vellum figures out who you are, what to look for,
  finds <b>live jobs for free</b>, filters out the ones that waste your time,
  ranks the rest with AI, proves they're still open — and can even apply for you.
</p>

<div align="center">

| 🧍 You | 🤖 Vellum |
|---|---|
| Upload `Resume.pdf` | Everything else. Zero clicks. |

</div>

---

## 🎯 What is this? (in 30 seconds)

Vellum OS is a **local-first, AI-powered job-search agent** built for one very
specific person: **a software candidate who wants the right jobs, not a flood
of irrelevant ones.**

🔹 It runs **entirely on your computer** — no cloud, your data stays with you.
🔹 It works on the **free tier** of AI models (Google AI Studio, **Gemma 4**), so it costs ₹0 to run.
🔹 It only ever looks at **free, public, no-login job sources**.
🔹 It is **brutally honest** — it rejects more than it accepts, and it tells you *why*.

> 💡 **The goal was never "more jobs". It was "fewer wrong jobs."**
> You don't need 500 jobs. You need the 20 that actually fit you — and proof that those 20 are still open.

---

## ⚡ Why is this cool?

| ✨ | What Vellum does that feels like magic |
|---|---|
| 🧠 | Reads **your actual resume** and builds a *search strategy* from it (one AI call) — and your chosen city overrides the resume's |
| 🔍 | Scans **2 live free channels** — an Indian startup job feed and 6 big hiring-software (ATS) boards |
| 🚦 | Runs a **zero-cost, super-strict filter** so a fresher never sees a Senior role |
| 📊 | Ranks every survivor with AI and a written **"why this match"** reason |
| 💀 | **Checks each top job's link is still alive** before showing it; dead ones are auto-closed |
| 🧾 | Deduplicates — the same job posted on 3 sites appears once |
| 🤖 | On your click: **tailors your resume** to the job and can auto-fill the application in a real browser |
| 💸 | Respects a tiny daily AI budget (`15,000 tokens`) and **keeps working** even when it's spent |

---

## 🗺️ The Big Picture (one flow, no magic, no mermaid)

```
        📄  YOU UPLOAD ONE RESUME
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 1 · EXTRACT  (free, on your PC)        │
  │  PDF  →  your skills, experience, location   │
  │  ⭐ skills = ground truth, never rewritten    │
  └──────────────────────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 2 · PLAN  (Gemma AI, ONE call ~530 tok)│
  │  "the intelligence anchor"                   │
  │   ✅ target roles   ✅ max seniority         │
  │   ✅ years needed   ✅ cities you accept     │
  │   ✅ words that mean "reject this"           │
  └──────────────────────────────────────────────┘
                   │
                   ▼
        🔎  DISCOVERY  (all free · no login · live)
  ┌──────────────────┬───────────────────────────────┐
  │ ✅ hasjob.co     │ 🏢 ATS boards (6 kinds)       │
  │  India startups  │  Greenhouse · Ashby · Lever · │
  │  fresh, small    │  Recruitee · SmartRecruiters ·│
  │                  │  BambooHR                     │
  └──────────────────┴───────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 3 · THE GATE  (ZERO AI tokens)         │
  │  strict rules, every rejection has a reason  │
  │   ❌ "Senior Dev" → you're a fresher         │
  │   ❌ "Pune only"  → you're in Bengaluru      │
  │   ❌ "New York"   → abroad, hard-rejected     │
  └──────────────────────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 4 · STORE  (SQLite, dedupe)            │
  │  same job from 3 sources → kept ONCE         │
  └──────────────────────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 5 · SCORE  (free keyword first,        │
  │    then Gemma in batches of 10)              │
  │  🏆 best match first + a written reason      │
  └──────────────────────────────────────────────┘
                   │
                   ▼
  ┌──────────────────────────────────────────────┐
  │  STEP 6 · PROVE IT'S ALIVE  (free GET check) │
  │  🔥 live        → shown to you               │
  │  🪦 dead link   → auto-closed                │
  └──────────────────────────────────────────────┘
                   │
                   ▼
        💜 YOUR REVIEW QUEUE  (ranked, reasons visible)
                   │
                   ▼  (only when YOU click Apply)
  ┌──────────────────────────────────────────────┐
  │  STEP 7 · APPLY  (per job, automatable)      │
  │  resume tailored to that JD → real browser   │
  │  fills the application form for you          │
  └──────────────────────────────────────────────┘
```

### 🧱 The same idea as a mind-map

```
                        VELLUM OS
              ┌───────────┬───────────┬───────────┐
            🧠 PLAN     🔍 DISCOVER  🚦 GATE      📈 SCORE
              │            │            │            │
        Gemma makes   hasjob +    strict rules,  keyword sort,
        the strategy  ATS boards  zero tokens,  then Gemma 10/call
        + your city               with reasons  with reasons
              └───────────┴──────┬───────────────┘
                                 │
                              👇 WHAT PASSES
                    🧾 STORE (deduped) → 💀 LIVENESS PROOF
                                 │
                         💜 YOUR REVIEW QUEUE
                                 │
                     🤖 TAILOR + AUTO-APPLY (on click)
```

---

## 🔬 Deep dive: each step, in plain English

### 1️⃣ Extract — your resume becomes a data card
A PDF parser (`extractor`) reads your resume and builds a **Candidate Profile**:
name, contact, skills, experience, education, location.
> ⭐ **Ground truth rule:** your *skills* are never modified or invented. Ever.
> The tailoring step only *re-words experiences* — it will never add a skill you don't have.

### 2️⃣ Plan — Gemma turns that profile into a strategy
One AI call makes a **SearchPlan** — and the city you pick in the dropdown
**overrides** the plan's location list (your choice wins over the resume):

| Plan field | Example | Meaning |
|---|---|---|
| `target_roles` | `["software engineer", "sde"]` | careers to look for |
| `seniority_max` | `entry` | highest level to accept |
| `years_experience` | `1` | your experience |
| `locations` | `["Hyderabad", "Remote"]` | your chosen city + Remote |
| `reject_terms` | `["lead", "architect"]` | words ⇒ auto-reject |

Every later step runs from this one plan — so the whole system agrees on strategy.

### 3️⃣ Discovery — two live free channels
| Channel | What it is | Why it's good |
|---|---|---|
| 🌏 **hasjob.co** | Indian startup job feed (ATOM/XML) | fresh, local, small & honest |
| 🏢 **ATS boards** | Greenhouse · Ashby · Lever · Recruitee · SmartRecruiters · BambooHR — via their **public posting JSON** | real companies, structured data, full pagination (100s of jobs) |

> 🗑️ **Hacker News "Who's Hiring?" was removed** — it's global/US-heavy, so
> for an India-only candidate it mostly produced wrong-location junk. Not worth it.

Everyone (known or *found by the feeds*) lives in the **company list** (~350 and
growing). Vellum smartly "probes" only companies it hasn't checked in 24h —
so each sync stays short even as the list grows. Probing is **parallel**: a dead
website no longer slows down the good ones.

### 4️⃣ The Gate — the heart of the whole design 🚦
The Gate is a **deterministic, free, explainable** filter. It runs *before*
any AI scoring. It can only *reject*, never guess — and it always says why.

| Rule | Example | Verdict |
|---|---|---|
| Role family | *"Account Manager"* for a software candidate | ❌ reject |
| Seniority | *"Senior/Lead/Architect"* for an entry-level plan | ❌ reject |
| Location conflict | *"Pune only"* for a Bengaluru-only candidate | ❌ reject |
| Foreign location | *"New York, USA" / "London, UK"* for an India-only candidate | ❌ reject |
| Years required | *"Minimum 3 years required"* vs a 1-year candidate | ❌ reject |
| Junior markers | *"fresher / graduate / early career"* | ✅ passes |

> 📊 Measured in a live run (Bengaluru fresher profile):
> **203 jobs rejected / 68 eligible** — every rejection logged with a reason.

### 5️⃣ Store — dedupe, so you never see the same job twice
The same role is often posted on hasjob AND the company's Greenhouse board.
Vellum hashes the apply-URL **and** cross-checks *(company, role)* across sources,
keeping the **richest version** (ATS > hasjob). Result: **~51 dupes dropped**
in a single run.

### 6️⃣ Score — free first, AI second (budget-first design)
Two stages:
1. **Keyword pre-score** — `0` AI tokens; skills × role × location overlap.
2. **Gemma batch re-rank** — `10 jobs per AI call`, returns a strict `0–1` score +
   a one-line reason. Trusted order: excellent ≥ 0.8, good 0.5–0.7, weak 0.2–0.4, none 0.

🧯 **Graceful degradation:** if the daily AI budget runs out, the keyword score
still stands. Nothing breaks — the system just gets cheaper.

### 7️⃣ Liveness — prove it before you click 💀
Each sync, the **top matches** get a real HTTP check of their apply-URL:
- ✅ `200 / live` → shown as **verified live**
- ❌ `404 / "job expired"` → **status = `closed`**, hidden from your list
- ⚠️ bot-block (403) → **retried once** before calling it, so a single false
  alarm never kills a real job

Each verdict is time-stamped and stored, so the UI can say
*"verified live 3 hours ago."*

### 8️⃣ Apply — the optional, on-click finale 🤖
A careful click ("Apply") starts a **per-job pipeline**:
1. **Validate + tailor** your resume against *that specific* job description (AI bullets, strict ground truth)
2. Turn it into a **fresh PDF** exports with a clean filename (e.g. `Company_Role.pdf`)
3. Launch a **real browser** (headless, streamed live to the web UI over WebSocket/CDP) to open the form
4. Watch it fill the application for you — and you can take over anytime (HITL)

---

## 🧰 Tech stack & modules

| Corner | Tech |
|---|---|
| 🖥️ Web API | **FastAPI** + **Uvicorn** + WebSocket (live progress + browser screencast) |
| 🗄️ Storage | **SQLite** (aiosqlite) — jobs, companies, profiles, goals |
| 🧠 AI | **Gemma 4** (`gemma-4-26b-a4b-it`) via **Google AI Studio** direct call, with a persisted **budget tracker** (15k tokens/day, 30 req/min) |
| 🧭 Search | DuckDuckGo (ddgs) — lightweight, no API key dead-ends |
| 🕸️ Scraping | curl-cffi (browser-like fingerprints) + trafilatura + BeautifulSoup |
| 📄 PDF | PyMuPDF (read) + xhtml2pdf (tailored resume) |
| 🤖 Browser automation | **browser-use** + Playwright — stealth, headless, live-streamed |
| 🔁 Resilience | tenacity retries, diskcache, structlog JSON logs |
| 🧪 Tests | pytest — **85 passing**, all offline (fakes/monkeypatch, no internet) |

### 📂 Where's the code?
```
vellum-os/
├── vellum/
│   ├── api/            # FastAPI routes, WebSocket, screencast stream
│   ├── agents/         # search_planner · eligibility · job_scorer ·
│   │                   # job_sync · extractor · validator_tailor · browser_agent · graph
│   ├── tools/          # ats_client · hasjob · hn_hiring · liveness · scrape · pdf_render
│   ├── config/         # settings (.env) · gemma budget · database · logging
│   └── utils/          # json_helper · job_cleaner
├── tests/              # 90 offline tests
└── data/               # companies.csv seed · vellum.db · gemma_budget.json
```

---

## 📊 Honest, measured numbers

All measured live (Bengaluru-fresher profile) — not marketing:

| Metric | Value |
|---|---|
| 🧠 Search plan | 1 AI call · ~520 tokens (your dropdown city wins over the resume) |
| 🌏 Feeds | 12 hasjob jobs (HN removed — global junk, no longer worth it) |
| 🚦 Conductivity | **203 rejected / 68 eligible** (every rejection has a reason; foreign cities hard-rejected) |
| 🏆 AI ranking | 68 jobs, 2 batches (~3.4k tokens) |
| 💀 Liveness | 17 live / 1 gone (gone ⇒ auto-closed) |
| 🏢 ATS probe | parallel; live sweep of 163 seed companies → boards found: Razorpay 27 · Freshworks 154 · Paytm 242 · SigNoz 15 (Lever/Greenhouse/Ashby/SmartRecruiters) |
| 🧾 Dedupe | 51 duplicates dropped |
| 💰 Budget (full day) | ~4k of 15k tokens — lots of headroom |

### 💸 Budget math (brutal & honest)
> Free tier: **15,000 tokens/day**, **30 requests/min**.

| Wants AI | Always free |
|---|---|
| Plan (1 call ≈ 530) | Fetching & parsing |
| Ranking (10 jobs ≈ 650/call) | Eligibility gate |
| → ~80–150 jobs/day safely ranked | Liveness checks |
| | Keyword pre-score |

The expensive AI step only ever sees jobs that **already passed the strict gate.**

---

## 🚀 Getting started

### Prerequisites
- 🐍 **Python 3.11+**
- 🔑 A **Google AI Studio** API key (`GOOGLE_API_KEY`)*
- 🌐 Internet (for live feeds + ATS boards)

\* *Vellum degrades gracefully without it — discovery, the gate, keyword scoring
and liveness work with zero AI. You just lose plan + AI ranking.*

### Install
```bash
cd vellum-os
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### Configure
```bash
cp .env.example .env
# open .env and paste your GOOGLE_API_KEY
```
`.env` in a nutshell:
```env
GOOGLE_API_KEY=your_gemini_api_key     # the only "must" for full AI features
HOST=127.0.0.1                          # local only by default
PORT=8000
BROWSER_USE_HEADLESS=false              # show or hide the applying browser
```

### Run
```bash
python -m vellum.api.main
```
Open **http://127.0.0.1:8000** in your browser. That's it. 🎉

First run auto-loads **~163 Indian startups** (the seed index) and the sync
begins: probe → fetch → gate → store → score → prove-live. Live progress streams
to the dashboard over WebSocket.

### Run the tests
```bash
cd vellum-os
pytest tests/ -q        # 90 offline tests, no internet needed
```

---

## 🔌 API quick-reference

| Method | Endpoint | What it does |
|---|---|---|
| `POST` | `/api/upload-resume` | Upload resume PDF → extract profile |
| `POST` | `/api/start-search` | Full discovery flow (sync → score) |
| `POST` | `/api/companies/sync` | Just run the ATS sync pass |
| `GET` | `/api/jobs` | Ranked jobs (`include_closed=true` to see dead ones) |
| `GET` | `/api/jobs/{id}` | One job's full detail + freshness |
| `DELETE` | `/api/jobs` · `POST /api/jobs/clear` | Clear jobs |
| `POST` | `/api/jobs/{id}/apply` | Launch tailor + auto-apply for one job |
| `GET` | `/api/jobs/{id}/resume-pdf` | Download the tailored resume PDF |
| `GET` | `/api/companies` | Tracked companies + ATS status |
| `POST` | `/api/companies` | Add a company (probes ATS right away) |
| `GET` | `/api/budget` | Gemma budget usage live |
| `GET`/`POST` | `/api/pipeline-mode` | manual ⇄ automatic applying |
| `POST` | `/api/reset` | Full wipe + halt |
| `GET` | `/api/status` | Jobs, companies, token usage, state |
| `WS` | `/ws` · `/ws/browser` | Progress events · live browser screencast |

---

## ⚠️ Honest known limits

Nothing about this project pretends to be perfect:

- 🌏 **hasjob is small** (0–50/day, community). **ATS is the volume engine** (~350 companies), but some big ATSes —
  **Workday, FreshTeam** — expose **no public JSON**, so those companies yield 0 jobs (marked "probed", skipped next time).
- 💀 Liveness checks a **bounded set of top matches per sync** (default 40), not every job.
- 🚦 The Gate is **rule-based**: strict and explainable, not "smart". If a JD hides
  requirements in vague prose, the gate may pass it — and the **AI ranking catches it**.
- 🧠 All AI is **Gemma 4 lightweight** — cheap, free, and honest, but not a frontier
  model. The system is built to lean on deterministic logic (gate, keyword score,
  liveness) rather than trusting the model completely.
- ⚖️ It optimizes for **Bengaluru-fresher software profiles**; other profiles work but are less tuned.

---

## 🛣️ What's next (roadmap)

- [ ] 🌏 More free ATS connectors + a public-company feed to grow volume
- [ ] 📉 Smarter lossless dedupe (title-normalization edge cases)
- [ ] 🧪 Continuous weekly live-verification runs
- [ ] 🕹️ One-click auto-apply with safer form guards (captcha detection, HITL fallback)
- [ ] 📊 Analytics panel: what you applied to, response rates, re-verify staleness
- [ ] 🌐 Multi-profile support (multiple resumes per .env)
- [ ] 💬 Optional: re-add HN as an opt-in source behind a config flag (off by default)

---

## 🧠 Concept recap — the 3 words that define Vellum

| Word | Meaning here |
|---|---|
| 🔎 **Eligibility-first** | Reject the wrong stuff *before* spending any brain power. |
| 🪙 **Budget-first** | Every AI call is metered; work keeps going when the meter is empty. |
| 💜 **Prove-then-show** | Don't show a job unless we can verify it's still open. |

---

<p align="center">
  Made with 💜, a free-tier AI key, and a healthy fear of spammy job boards.<br>
  <sub>Architecture deep-dive lives in <code>architecture.md</code> (with the v4 fixes and honest numbers).</sub>
</p>