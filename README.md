<div align="center">

<img src="assets/hero_banner.jpg" alt="JobHunterX — AI Career Intelligence Agent" width="100%"/>

<br/>
<br/>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Outfit&weight=700&size=28&pause=1000&color=A855F7&center=true&vCenter=true&width=650&height=50&lines=%E2%9A%A1+JOBHUNTERX+%E2%80%94+AI+CAREER+HUNTER;Hunts%2C+Matches%2C+Tailors+%26+Applies;Stealth+Form+Auto-Fill+While+You+Sleep;6+AI+Agents+%C2%B7+3+LLM+Providers+%C2%B7+6+ATS+Boards" alt="Typing SVG" />
</p>

### 🚀 Your Autonomous AI Career Intelligence Agent That Hunts, Matches, Tailors, and Applies — While You Sleep

<br/>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" /></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.140+-009688?style=for-the-badge&logo=fastapi&logoColor=white" /></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-State_Machine-7C3AED?style=for-the-badge&logo=langchain&logoColor=white" /></a>
  <a href="https://ai.google.dev/"><img src="https://img.shields.io/badge/Gemma_4_26B-Google_AI-4285F4?style=for-the-badge&logo=google&logoColor=white" /></a>
  <a href="https://groq.com"><img src="https://img.shields.io/badge/Llama_3.3_70B-Groq-F55036?style=for-the-badge&logo=meta&logoColor=white" /></a>
  <a href="https://mistral.ai"><img src="https://img.shields.io/badge/Mistral_Large-Mistral-FF7000?style=for-the-badge&logo=mistral&logoColor=white" /></a>
  <a href="https://playwright.dev"><img src="https://img.shields.io/badge/Playwright-Stealth_Browser-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" /></a>
  <img src="https://img.shields.io/badge/Tests-85%20Passed-10B981?style=for-the-badge&logo=pytest&logoColor=white" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI_Agents-6_Specialized-purple?style=flat-square&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM_Providers-Google_·_Groq_·_Mistral-blue?style=flat-square&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/ATS_Feeds-Greenhouse_·_Lever_·_Ashby_·_SmartRecruiters-emerald?style=flat-square" />
  <img src="https://img.shields.io/badge/Indian_Tech_Hubs-16_Cities_·_4000+_Companies-orange?style=flat-square" />
</p>

<br/>

---

*Upload your resume. Pick a city. Go grab coffee.*  
*JobHunterX discovers jobs, scores them against your skills, tailors a pixel-perfect PDF resume for each one, opens a stealth Chrome browser, fills every form field, and applies — streaming every frame live to your dashboard so you can take over the keyboard whenever a CAPTCHA or login wall shows up.*

***It's the job-hunting wingman you always wished you had.***

---

</div>

<br/>

## 🖥️ Dashboard Preview

<div align="center">
<img src="assets/dashboard_preview.jpg" alt="JobHunterX Dashboard — Live Browser Canvas, Job Cards, Activity Feed" width="90%"/>
<br/>
<sub><i>Dark-mode dashboard with scored job cards, live browser canvas streaming, and real-time agent activity feed</i></sub>
</div>

<br/>

---
## ✨ Browser Agent Preview 

<div align="center">
<img src="assets/browser_agent.jpg" alt="JobHunterX Dashboard — Live Browser Canvas, Job Cards, Activity Feed" width="90%"/>
<br/>
<sub><i>live browser canvas streaming, and real-time agent activity feed</i></sub>
</div>

## 🧠 The 6-Agent Pipeline

JobHunterX isn't one monolithic script. It's a **team of 6 specialized AI agents**, orchestrated by a **LangGraph state machine**, each doing what it does best — like a Formula 1 pit crew, but for your career.

<div align="center">
<img src="assets/agent_pipeline.jpg" alt="JobHunterX — 6-Stage AI Agent Pipeline" width="90%"/>
</div>

<br/>

### Agent Breakdown

| # | Agent | Codename | What It Does | Powered By |
|:-:|:------|:---------|:-------------|:-----------|
| 🧬 | **Profile Extractor** | `extractor.py` | Parses your resume PDF (via PyMuPDF), extracts skills, experience, education, projects, LinkedIn/GitHub URLs, and builds a structured `CandidateProfile` — the ground truth that powers everything downstream. | **Gemma 4 26B** → Gemini 3.1 Flash Lite |
| 🗺️ | **Search Planner** | `search_planner.py` | Reads your profile and generates a smart `search_plan`: seniority ceiling, target roles, reject terms, and location preferences. In multi-agent mode, crafts 15–20 precision DuckDuckGo queries targeting startups and product companies while filtering out mass-hiring IT service spam. | **Gemma 4 26B** (direct Google GenAI) |
| 🕵️ | **Web Scout & ATS Scraper** | `job_search_agents.py` + `ats_client.py` | Executes search queries, scrapes ATS boards (Greenhouse, Ashby, Lever, Recruitee, SmartRecruiters, BambooHR), blacklists aggregators (LinkedIn, Indeed, Naukri, Glassdoor), deduplicates via `seen_job_urls`, runs the zero-token Eligibility Gate, and streams `job_found` events live. | **Zero-token** (pure async Python + HTTP) |
| 🎯 | **Job Evaluator** | `job_scorer.py` | Two-stage scoring: (1) **Deterministic keyword pre-filter** — skill overlap 55%, role match 20%, location 10%, freshness 5%. (2) **Gemma batch scoring** — groups top jobs into batches of 10, scores multi-dimensionally (skill fit, seniority, location, experience), and generates match reasons. | **Gemma 4 26B** (budget-aware, 15K tokens/day) |
| ✨ | **Resume Validator & Tailor** | `validator_tailor.py` | Validates freshness (URL/header checks), evaluates match score, then generates a tailored Executive Summary and transforms experience bullets using Google's XYZ action-led formula. Includes **anti-hallucination sanitizers** — no fabricated skills or made-up metrics. Renders a single-page ATS-optimized PDF via Jinja2 + xhtml2pdf with 4 iterative shrink profiles. | **Gemma 4 26B** → Gemini 3.1 Flash Lite |
| 🥷 | **Stealth Browser Agent** | `browser_agent.py` | The closer. Opens a persistent Chrome profile with anti-detection headers, fills personal details, education, work history, Q&A memory (salary, notice period, work auth), uploads the tailored PDF, and submits. Streams every browser frame live via CDP WebSocket. When it hits a login wall, CAPTCHA, or MFA — it pauses and hands you the keyboard. | **Gemini 3.1 Flash Lite** → Llama 3.3 70B (Groq) → Mistral Large → Gemma 4 27B |

<br/>

> [!TIP]
> **The Eligibility Gate** (`eligibility.py`) runs between Agents 3 and 4 as a zero-token strict filter. It rejects non-dev roles (sales, HR, marketing), foreign locations, and seniority mismatches — all without spending a single API token.

---

## 🤖 LLM Models & Provider Architecture

JobHunterX uses a **multi-provider LLM router** (`llm_router.py`) with automatic failover, per-provider rate limiting, disk caching, and concurrency semaphores. Here's every model in the system:

```mermaid
graph LR
    subgraph Google["☁️ Google AI Studio (Free Tier)"]
        G1["gemma-4-26b-a4b-it"]
        G2["gemini-3.1-flash-lite"]
        G3["gemma-4-27b-it"]
    end

    subgraph Groq["⚡ Groq (Free Tier)"]
        GR1["llama-3.3-70b-versatile"]
        GR2["gpt-oss-120b"]
        GR3["gpt-oss-20b"]
    end

    subgraph Mistral["🌀 Mistral AI (Free Tier)"]
        M1["mistral-large-latest"]
    end

    G1 -->|fallback| G2
    G2 -->|fallback| GR1
    GR1 -->|fallback| M1
    M1 -->|fallback| G3

    classDef google fill:#4285F4,stroke:#1a73e8,color:#fff,stroke-width:2px;
    classDef groq fill:#F55036,stroke:#c9302c,color:#fff,stroke-width:2px;
    classDef mistral fill:#FF7000,stroke:#cc5a00,color:#fff,stroke-width:2px;

    class G1,G2,G3 google;
    class GR1,GR2,GR3 groq;
    class M1 mistral;
```

### Fallback Chains by Task

| Chain Name | Purpose | Model Sequence |
|:-----------|:--------|:---------------|
| `fast` | Quick operations (search planning, scoring) | Gemma 4 26B → Gemini 3.1 Flash Lite |
| `reasoning` | Deep analysis (validation, match evaluation) | Gemma 4 26B → Gemini 3.1 Flash Lite |
| `tailoring` | Resume rewriting & bullet transforms | Gemma 4 26B → Gemini 3.1 Flash Lite |
| `extraction` | PDF resume parsing & profile construction | Gemma 4 26B → Gemini 3.1 Flash Lite |
| `browser` | Browser agent form-filling decisions | Gemini 3.1 Flash Lite |
| Browser fallback | When primary browser LLM fails | Llama 3.3 70B (Groq) → Mistral Large → Gemma 4 27B |

### Rate Limiting & Budget Control

#### 🟢 Google AI Studio (Free Tier)
| Model ID | RPM Limit | Min Delay | TPM Limit | RPD Limit (Requests Per Day) |
|:---------|:----------|:----------|:----------|:-----------------------------|
| **Gemma 4 26B** (`gemma-4-26b-a4b-it`) | 30 RPM | 2.0s | 16K TPM | **14,400 RPD** (14.4K req/day) |
| **Gemini 3.1 Flash Lite** (`gemini-3.1-flash-lite`) | 15 RPM | 4.0s | 250K TPM | **500 RPD** (500 req/day) |

#### ⚡ Groq Cloud (Free Tier)
| Model ID | RPM | RPD (Requests/Day) | TPM | TPD (Tokens/Day) |
|:---------|:----|:-------------------|:----|:-----------------|
| `llama-3.1-8b-instant` | 30 RPM | **14.4K RPD** | 6K TPM | 500K TPD |
| `llama-3.3-70b-versatile` | 30 RPM | **1K RPD** | 12K TPM | 100K TPD |
| `openai/gpt-oss-120b` | 30 RPM | **1K RPD** | 8K TPM | 200K TPD |
| `openai/gpt-oss-20b` | 30 RPM | **1K RPD** | 8K TPM | 200K TPD |
| `qwen/qwen3.6-27b` | 30 RPM | **1K RPD** | 8K TPM | 200K TPD |
| `meta-llama/llama-prompt-guard-2-22m/86m` | 30 RPM | **14.4K RPD** | 15K TPM | 500K TPD |

#### 🌀 Mistral AI (Updated August 2026)
| Model ID | RPS Limit | Approx RPM | TPM Limit | Category / Purpose |
|:---------|:----------|:-----------|:----------|:-------------------|
| `codestral-2508` | 2.08 RPS | ~125 RPM | 625K TPM | Code Generation & Agent Tooling |
| `codestral-embed` | 1.00 RPS | 60 RPM | 50K TPM | Code Embeddings |
| `devstral-2512` | 0.83 RPS | ~50 RPM | 1M TPM | Developer Agent Tasks |
| `labs-leanstral-1-5-1` | 0.63 RPS | ~38 RPM | 5M TPM | Experimental / High Throughput |
| `ministral-14b-2512` | 0.50 RPS | 30 RPM | 937.5K TPM | Edge / Fast Reasoning |
| `ministral-3b-2512` | 12.50 RPS | 750 RPM | 1.3M TPM | Ultra-fast Micro Decisions |
| `ministral-8b-2512` | 3.13 RPS | ~188 RPM | 625K TPM | High-Speed Lightweight Agent |
| `mistral-embed-2312` | 1.00 RPS | 60 RPM | 20M TPM | Text Embeddings |
| `mistral-large-2512` | 0.07 RPS | ~4 RPM | 250K TPM | Heavy Reasoning Fallback |
| `mistral-medium-2505` | 0.42 RPS | ~25 RPM | 375K TPM | Mid-tier Reasoning |
| `mistral-medium-2508` | 0.38 RPS | ~23 RPM | 356.25K TPM | Mid-tier Reasoning |
| `mistral-medium-latest` | 0.83 RPS | ~50 RPM | 25K TPM | General Tasks |
| `mistral-moderation-2603` | 1.67 RPS | ~100 RPM | 50K TPM | Content Moderation Guard |
| `mistral-small-2603` | 0.83 RPS | ~50 RPM | 50K TPM | Fast General Fallback |

> [!NOTE]
> **Gemma Budget System** (`gemma.py`): Enforces a hard daily cap of **14,400 requests/day** (14.4K RPD) and 30 RPM on `gemma-4-26b-a4b-it` to stay strictly within Google AI Studio's free tier. State is tracked in-memory. When the budget is exhausted, scoring gracefully degrades to the zero-token keyword pre-filter.

---

## 🌐 Web Search Architecture & Provider Modes

JobHunterX features a multi-provider web search architecture designed for high-precision job discovery, zero accidental billing, and request conservation. It supports two switchable search execution modes, controllable via the UI header toggle button (**`Web APIs: ON / OFF`**) or the `.env` configuration file (`ENABLE_WEB_SEARCH_APIS=true/false`).

```mermaid
flowchart TD
    SEARCH_REQ([🔍 User Job Search Query]) --> MODE_CHECK{"Web Search APIs Mode?"}

    MODE_CHECK -->|"ON (ENABLE_WEB_SEARCH_APIS=true)"| ROUTER["Intelligent Sequential Search Router"]
    MODE_CHECK -->|"OFF (ENABLE_WEB_SEARCH_APIS=false)"| DIRECT_SCRAPER["Direct Scraper Fallback Engine<br/>(0 API Keys Required)"]

    subgraph API_ROUTER ["⚡ SEQUENTIAL ROUTER PRIORITY"]
        ROUTER --> TF["1. TinyFish Search API<br/>(0 Credits Free Utility)"]
        TF --> QG1{"Quality Gate<br/>Pass (≥0.60)?"}
        QG1 -->|Yes| STOP1["STOP Router & Return SERP"]
        QG1 -->|Insufficient / Error| TAV["2. Tavily Search API<br/>(1,000 Free Credits/Mo)"]
        TAV --> QG2{"Quality Gate<br/>Pass (≥0.60)?"}
        QG2 -->|Yes| STOP2["STOP Router & Return SERP"]
        QG2 -->|Insufficient / Error| EXA["3. Exa AI Search API<br/>($7 / 1K searches; $10/mo ≈ 1,428/mo<br/>+ $20 new-account signup credit)"]
        EXA --> QG3{"Quality Gate<br/>Pass (≥0.60)?"}
        QG3 -->|Yes| STOP3["STOP Router & Return SERP"]
        QG3 -->|Insufficient / Error| BRV["4. Brave Search API<br/>($5/Mo Free Credit)"]
        BRV --> QG4{"Quality Gate<br/>Pass (≥0.60)?"}
        QG4 -->|Yes| STOP4["STOP Router & Return SERP"]
        QG4 -->|Insufficient / Error| DDGS_FB["5. DuckDuckGo Scraper Fallback"]
    end

    DIRECT_SCRAPER --> HYBRID_FETCH
    STOP1 --> HYBRID_FETCH
    STOP2 --> HYBRID_FETCH
    STOP3 --> HYBRID_FETCH
    STOP4 --> HYBRID_FETCH
    DDGS_FB --> HYBRID_FETCH

    subgraph HYBRID_FETCH ["📦 HYBRID FETCH PIPELINE"]
        STEP1["Safe URL Normalization<br/>(Strips utm_*, ref, source, gclid)"] --> STEP2["Lightweight Async Direct HTTP"]
        STEP2 -->|Static HTML| BS4["BeautifulSoup Local Parser"]
        STEP2 -->|JS Shell / Blocked ATS| TF_FETCH["TinyFish Fetch API<br/>(POST https://api.fetch.tinyfish.ai)"]
    end

    HYBRID_FETCH --> DEDUPE["Semantic Identity Deduplication<br/>(job_id ➔ canonical_url ➔ company+title+location)"]
    DEDUPE --> SCORE["🎯 Job Evaluator (Gemma Scoring)"]
```

### 1. Mode Comparison

| Feature / Behavior | Mode 1: Web Search APIs Mode (ON) | Mode 2: Direct Scraper Mode (OFF) |
|:-------------------|:----------------------------------|:-----------------------------------|
| **Toggle Control** | Header Button: **`Web APIs: ON`** / `.env`: `ENABLE_WEB_SEARCH_APIS=true` | Header Button: **`Web APIs: OFF`** / `.env`: `ENABLE_WEB_SEARCH_APIS=false` |
| **Search Engines Used** | **Rotating router**: TinyFish / Tavily / Exa (provider chosen per query, both 1-2 paid requests each per run via caps) + **DDGS** safety net (Optional: **Brave**) | Direct unauthenticated search scrapers + BeautifulSoup parser |
| **API Keys Required** | Optional (degrades gracefully per provider) | **0 API Keys Required** |
| **Quality Gate** | **Context-Aware Weighted SERP Quality Gate** (evaluates SERP score before calling next provider) | Direct scraping & pre-filter |
| **JS Rendering Engine** | **TinyFish Fetch API** (batching up to 10 URLs/request for Greenhouse/Lever/Ashby) | Direct HTTP parser |
| **Zero-Spend Protection** | Enforces 2-tier zero-spend circuit breaker | 100% Free / Unauthenticated |

---

### 2. Search Provider Breakdown

| Provider | API Endpoint & Method | Free Monthly Allowance | Rate Limits & Capacity | Cost Model & Safety Rules |
|:---------|:----------------------|:-----------------------|:-----------------------|:--------------------------|
| **TinyFish Search** | `GET https://api.search.tinyfish.ai` | **Unlimited 0-credit search utility** | 30 RPM default (configurable, dynamic 429 backoff) | 0 credits. Zero cost. |
| **TinyFish Fetch** | `POST https://api.fetch.tinyfish.ai` | **Unlimited 0-credit fetch utility** | 150 URLs/min (max 10 URLs per batch payload) | 0 credits. Zero cost. Used for JS-heavy ATS pages. |
| **Tavily Search** | `POST https://api.tavily.com/search` | **1,000 free API credits / month** | 100 RPM limit | 1 credit (`search_depth="basic"`). `auto_parameters` is strictly disabled under zero-spend protection. |
| **Exa AI Search** | `POST https://api.exa.ai/search` | **$10.00 / month recurring credit** ≈ **1,428 searches/month** at $7 / 1,000 searches ($0.007 each); **new accounts get a one-time $20 signup credit** ≈ **2,800 extra searches** | Dynamic 429 backoff | $0.007 / base request (≤10 results). Dynamically checks parameter cost. |
| **Brave Search** | `GET https://api.search.brave.com/res/v1/web/search` | $5.00 / month recurring credit | 50 QPS capacity | $0.005 / request. **Disabled by default** (`BRAVE_ENABLED=false`) as Brave requires linking a payment card. |
| **DuckDuckGo** | Python `ddgs` (Local Wrapper) | Unofficial scraper fallback | Adaptive backoff on 429/CAPTCHA | 0 credits. Emergency fallback when API keys are not provided or exhausted. |

---

### 🔑 Official API Key Dashboards & Setup Links

| Provider | Purpose | Free Allowance | Dashboard / API Key Link |
|:---------|:--------|:---------------|:-------------------------|
| **TinyFish** | Web Search & JS Page Fetch | Unlimited 0-Credit Utility | [TinyFish API Keys](https://agent.tinyfish.ai/api-keys) |
| **Tavily** | Primary Web Search API | 1,000 Free Credits / Month | [Tavily Dashboard](https://app.tavily.com/home) |
| **Exa AI** | Neural Web Search API | $10.00 / Month ≈ 1,428 searches (+ $20 one-time signup ≈ 2,800 more for new accounts) | [Exa AI Dashboard](https://dashboard.exa.ai/home) |
| **Brave Search** | Web Search API | $5.00 / Month Credit | [Brave Search Dashboard](https://api-dashboard.search.brave.com/app/keys) |
| **Google AI Studio** | Gemini & Gemma LLMs | 14.4k RPD / 30 RPM Free | [Google AI Studio](https://aistudio.google.com/app/api-keys) |
| **Groq** | Llama 3.3 & DeepSeek LLMs | 14.4k RPD / 30 RPM Free | [Groq Console](https://console.groq.com/keys) |
| **Mistral AI** | Mistral Large LLM | Free Tier | [Mistral AI Admin](https://admin.mistral.ai/organization/api-keys) |

---

### 3. Agent Responsibilities by Scenario

| Agent Module | Primary Role in Search & Fetch | Behavior when Web APIs = ON | Behavior when Web APIs = OFF |
|:-------------|:-------------------------------|:----------------------------|:-----------------------------|
| 🗺️ **Search Planner** (`search_planner.py`) | Query Strategist | Generates 5 targeted job search queries scoped by role & location. | Generates 5 targeted job search queries scoped by role & location. |
| 🕵️ **Web Scout & Discovery** (`job_discovery.py`) | Search Router & Orchestrator | Delegates queries to `SearchRouter` & `QualityGate`. Runs `execute_fetch_pipeline()`. | Skips Search Router. Calls direct unauthenticated scrapers & BeautifulSoup parser. |
| 🛡️ **Zero-Spend Circuit Breaker** (`zero_spend.py`) | Safety Enforcement | Evaluates `remaining_free_balance` − `worst_case_cost` $\ge 0$. Blocks request if cost is `UNKNOWN`. | Inactive (0-cost mode). |
| ⚖️ **Quality Gate** (`quality_gate.py`) | SERP Quality Evaluator | Scores SERP items ($0.30 \text{Rel} + 0.25 \text{Loc} + 0.20 \text{Fresh} + 0.15 \text{Src} + 0.10 \text{Uniq}$). Halts router when score $\ge 0.60$. | Inactive. |
| 📊 **Usage Ledger** (`usage_ledger.py`) | Ledger Tracker | Records every search and fetch attempt, native billing units, and error status in SQLite. | Records scraper fetch attempts in SQLite. |
| 🎯 **Job Evaluator** (`job_scorer.py`) | Match Scoring | Scores extracted job descriptions against skills using local Gemma LLM. | Scores extracted job descriptions against skills using local Gemma LLM. |

---

## 🔄 Pipeline Modes: Automatic vs. Manual

JobHunterX runs in two modes, switchable at any time from the dashboard or via the `/api/pipeline-mode` endpoint.

```mermaid
flowchart TD
    START([📄 Upload Resume]) --> DISCOVER
    DISCOVER["🕵️ Discover & Score Jobs"]

    DISCOVER -->|Automatic Mode| AUTO_PIPE
    DISCOVER -->|Manual Mode| MANUAL_PIPE

    subgraph AUTO ["🤖 AUTOMATIC MODE"]
        AUTO_PIPE["Auto-qualify jobs<br/>match_score ≥ 0.3"]
        AUTO_PIPE --> TAILOR_A["✨ Tailor Resume PDF"]
        TAILOR_A --> BROWSER_A["🥷 Browser Agent Applies"]
        BROWSER_A -->|CAPTCHA/Login/MFA| HITL_A["⚠️ HITL Takeover"]
        HITL_A -->|User resolves| BROWSER_A
        BROWSER_A --> DONE_A(["✅ Applied!"])
    end

    subgraph MANUAL ["👤 MANUAL MODE"]
        MANUAL_PIPE["Review scored job cards"]
        MANUAL_PIPE --> REVIEW["Inspect tailored PDF<br/>& match breakdown"]
        REVIEW -->|Click Apply| TAILOR_M["✨ Tailor Resume PDF"]
        TAILOR_M --> BROWSER_M["🥷 Browser Agent Applies"]
        BROWSER_M -->|CAPTCHA/Login/MFA| HITL_M["⚠️ HITL Takeover"]
        HITL_M -->|User resolves| BROWSER_M
        BROWSER_M --> DONE_M(["✅ Applied!"])
    end

    classDef auto fill:#7c3aed,stroke:#5b21b6,color:#fff,stroke-width:2px;
    classDef manual fill:#0891b2,stroke:#0e7490,color:#fff,stroke-width:2px;
    classDef shared fill:#1e293b,stroke:#475569,color:#e2e8f0,stroke-width:2px;
    classDef hitl fill:#f59e0b,stroke:#d97706,color:#1e293b,stroke-width:2px;

    class DISCOVER shared;
    class AUTO_PIPE,TAILOR_A,BROWSER_A,DONE_A auto;
    class MANUAL_PIPE,REVIEW,TAILOR_M,BROWSER_M,DONE_M manual;
    class HITL_A,HITL_M hitl;
```

| Feature | 🤖 Automatic Mode | 👤 Manual Mode |
|:--------|:------------------|:---------------|
| **Discovery & Scoring** | Runs automatically across all tracked companies | Same — runs automatically |
| **Application Trigger** | Jobs with `match_score ≥ 0.3` are auto-queued for apply | You review each job card and click **"Apply"** |
| **Resume Tailoring** | Happens automatically before browser launch | Happens when you trigger apply |
| **Browser Automation** | Launches immediately after tailoring | Launches only after your explicit click |
| **HITL Takeover** | Agent pauses & alerts you on login/CAPTCHA/MFA | Same behavior |
| **Best For** | Overnight autonomous job hunting | Careful, selective applications |

---

## 🛡️ Human-in-the-Loop (HITL) System

The browser agent doesn't panic when it hits a wall. It **gracefully pauses**, saves session state, captures a screenshot, and broadcasts an intervention event to your dashboard.

```mermaid
stateDiagram-v2
    [*] --> BrowserRunning: Agent starts filling forms
    BrowserRunning --> DetectObstacle: Login/CAPTCHA/MFA detected

    DetectObstacle --> SaveSession: Save browser state & screenshot
    SaveSession --> NotifyUser: Broadcast intervention event to UI
    NotifyUser --> UserTakeover: User clicks "Take Over"

    UserTakeover --> ManualControl: User controls real Chrome window
    ManualControl --> UserDone: User clicks "Continue" in dashboard

    UserDone --> BrowserRunning: Agent resumes from saved state
    BrowserRunning --> [*]: Application submitted ✅
```

| HITL Type | Trigger Condition | What Happens |
|:----------|:------------------|:-------------|
| 🔐 `LOGIN` | Sign-in / password prompts detected | Browser pauses, Chrome window stays open for manual login |
| 🤖 `CAPTCHA` | reCAPTCHA / hCaptcha / Turnstile detected | Screenshot captured, user solves in live Chrome window |
| 📱 `MFA` | OTP / 2FA / authenticator prompt | Agent waits for user to enter verification code |
| 📝 `MANUAL_FORM` | Complex custom form fields | User fills tricky fields, agent handles the rest |
| ⚠️ `TOO_COMPLEX` | Unsupported multi-page portal | Session saved, user can complete manually |

---

## 🌐 ATS Platform Support

The Web Scout agent directly scrapes these **Applicant Tracking Systems** without needing any API keys:

| Platform | Method | What It Fetches |
|:---------|:-------|:----------------|
| **Greenhouse** | Public JSON board API | Jobs with titles, locations, departments |
| **Ashby** | Public JSON board API | Full listings with descriptions |
| **Lever** | Public JSON board API | Postings with team & location data |
| **Recruitee** | Public board scraping | Career page job listings |
| **SmartRecruiters** | Public JSON API | Jobs with detailed descriptions |
| **BambooHR** | Public board API | Open positions and departments |
| **Direct Career Pages** | HTML scraping + Trafilatura | Any company career page via web discovery |

---

## 📐 Full System Architecture

```mermaid
graph TB
    subgraph Client ["🖥️ Single Page Application"]
        direction LR
        UI["Web Dashboard<br/>(HTML/JS/CSS)"]
        Canvas["Live Browser Canvas<br/>(CDP Screencast)"]
        WS_C["WebSocket Client"]
    end

    subgraph Server ["⚡ FastAPI Server"]
        direction LR
        REST["REST API Routes<br/>(/api/*)"]
        WS_S["WebSocket Manager<br/>(/ws)"]
        CDP["CDP Broadcaster<br/>(/ws/browser)"]
    end

    subgraph Pipeline ["🧠 LangGraph Agent Pipeline"]
        direction TB
        A1["🧬 Profile Extractor"]
        A2["🗺️ Search Planner"]
        A3["🕵️ Web Scout & ATS Scraper"]
        EG["🚫 Eligibility Gate"]
        A4["🎯 Job Evaluator"]
        A5["✨ Resume Validator & Tailor"]
        A6["🥷 Stealth Browser Agent"]

        A1 --> A2 --> A3 --> EG --> A4 --> A5 --> A6
    end

    subgraph Infra ["🛡️ Infrastructure"]
        direction LR
        LLM["LLM Router<br/>(LiteLLM + Fallbacks)"]
        DB[("SQLite<br/>(aiosqlite)")]
        Cache[("DiskCache<br/>+ Gemma Budget")]
        Chrome["Chromium<br/>(Persistent Profile)"]
    end

    UI --> REST
    WS_C <--> WS_S
    WS_C <--> CDP
    REST --> Pipeline
    Pipeline --> LLM
    Pipeline --> DB
    Pipeline --> Cache
    A6 --> Chrome
    Chrome --> CDP

    classDef frontend fill:#7c3aed,stroke:#5b21b6,color:#fff,stroke-width:2px;
    classDef api fill:#0891b2,stroke:#0e7490,color:#fff,stroke-width:2px;
    classDef agent fill:#059669,stroke:#047857,color:#fff,stroke-width:2px;
    classDef infra fill:#d97706,stroke:#b45309,color:#fff,stroke-width:2px;

    class UI,Canvas,WS_C frontend;
    class REST,WS_S,CDP api;
    class A1,A2,A3,EG,A4,A5,A6 agent;
    class LLM,DB,Cache,Chrome infra;
```

---

## 📁 Project Structure

```
jobhunterx/
│
├── 📂 assets/                          # README images & visual assets
│
├── 📂 data/                            # Runtime storage (gitignored)
│
├── 📂 jobhunterx/                       # Main Python package
│   ├── pyproject.toml                  # Build config & dependency spec
│   ├── requirements.txt               # Pinned dependencies
│   ├── .env.example                    # Environment variable template
│   │
│   ├── 📂 tests/                       # 85 automated tests
│   │   ├── test_api.py                 # API route tests
│   │   ├── test_ats_pagination.py      # ATS scraper pagination tests
│   │   ├── test_dedupe_freshness.py    # Job deduplication tests
│   │   ├── test_eligibility.py         # Eligibility gate tests
│   │   ├── test_gemma_budget.py        # Token budget enforcement tests
│   │   ├── test_json_helper.py         # LLM JSON parsing tests
│   │   ├── test_liveness.py            # URL liveness checker tests
│   │   └── test_resume_tailoring.py    # Resume tailor & PDF tests
│   │
│   └── 📂 vellum/                      # Application source code
│       ├── models.py                   # Pydantic models (CandidateProfile, JobPipelineState, etc.)
│       │
│       ├── 📂 agents/                  # The 6 AI agents
│       │   ├── extractor.py            # 🧬 Profile Extractor
│       │   ├── search_planner.py       # 🗺️ Search Planner
│       │   ├── job_search_agents.py    # 🕵️ Web Scout (multi-agent search)
│       │   ├── eligibility.py          # 🚫 Eligibility Gate (zero-token)
│       │   ├── job_scorer.py           # 🎯 Job Evaluator
│       │   ├── job_sync.py             # Company sync & ATS probing
│       │   ├── validator_tailor.py     # ✨ Resume Validator & Tailor
│       │   ├── browser_agent.py        # 🥷 Stealth Browser Agent
│       │   └── graph.py                # LangGraph state machine orchestrator
│       │
│       ├── 📂 api/                     # FastAPI server
│       │   ├── main.py                 # App entry point, lifespan, CDP streaming
│       │   ├── routes.py               # All REST endpoints
│       │   └── ws.py                   # WebSocket connection manager
│       │
│       ├── 📂 config/                  # Configuration & infrastructure
│       │   ├── settings.py             # Pydantic settings (.env loader)
│       │   ├── llm_router.py           # Unified LLM router (LiteLLM)
│       │   ├── gemma.py                # Gemma budget tracker (15K/day)
│       │   ├── database.py             # SQLite schema & queries (aiosqlite)
│       │   └── logging.py              # Structured logging (structlog)
│       │
│       ├── 📂 tools/                   # Scraping & utility tools
│       │   ├── ats_client.py           # ATS board scrapers (6 platforms)
│       │   ├── job_discovery.py        # DuckDuckGo search & page scraping
│       │   ├── liveness.py             # Job URL liveness verification
│       │   ├── scrape.py               # Web content extraction
│       │   └── pdf_render.py           # Jinja2 + xhtml2pdf resume renderer
│       │
│       ├── 📂 templates/              # HTML templates
│       │   └── resume.html             # ATS-optimized resume template
│       │
│       ├── 📂 utils/                   # Helpers
│       │   ├── json_helper.py          # LLM JSON response parser
│       │   └── job_cleaner.py          # Job data normalization
│       │
│       └── 📂 web/                     # Frontend SPA
│           ├── index.html              # Main dashboard page
│           ├── app.js                  # Application logic (~111KB)
│           ├── styles.css              # Styling (~98KB)
│           └── sw.js                   # Service worker
│
├── .gitignore
├── requirements.txt
└── README.md                           # You are reading this!
```

---

## ⚡ Quickstart

### Prerequisites

- **Python 3.11+**
- **At least one LLM API key** (Google AI Studio recommended — it's free)

### 1. Clone & Setup

```bash
git clone https://github.com/kvcops/jobhunterx.git
cd jobhunterx

# Create virtual environment
python -m venv .venv

# Activate (choose your OS)
.venv\Scripts\activate          # Windows PowerShell
source .venv/bin/activate       # Linux / macOS
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt --prefer-binary
playwright install chromium
```

> [!TIP]
> `--prefer-binary` tells pip to pick the newest release that ships a prebuilt wheel instead of compiling from source. The flag is also baked into `requirements.txt`, so `pip install -r requirements.txt` alone already avoids the issue.

### 3. Configure Environment

```bash
cp jobhunterx/.env.example jobhunterx/.env
```

Edit `jobhunterx/.env` with your API keys:

```env
# At minimum, set one of these (Google recommended for free tier):
GOOGLE_API_KEY=your_google_ai_studio_key
GROQ_API_KEY=your_groq_key           # Optional
MISTRAL_API_KEY=your_mistral_key     # Optional

# Application settings
BROWSER_USE_HEADLESS=true
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
```

> [!TIP]
> **Getting API keys (all free):**
> - **Google AI Studio**: [aistudio.google.com](https://aistudio.google.com/) — Create key → Use Gemma 4 & Gemini 3.1 Flash Lite
> - **Groq**: [console.groq.com](https://console.groq.com/) — Free tier with Llama 3.3 70B
> - **Mistral**: [console.mistral.ai](https://console.mistral.ai/) — Free tier with Mistral Large

### 4. Launch 🚀

```bash
cd jobhunterx
python -m jobhunterx.api.main
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** and start hunting.

---

## 🔌 API Reference

### Core Endpoints

| Method | Endpoint | What It Does |
|:------:|:---------|:-------------|
| `POST` | `/api/upload-resume` | Upload resume PDF → extract candidate profile |
| `GET` | `/api/profile` | Get current candidate profile |
| `POST` | `/api/start-search` | Launch full discovery + scoring pipeline |
| `GET` | `/api/jobs` | List all discovered & scored jobs |
| `GET` | `/api/jobs/{id}` | Get detailed job info + match breakdown |
| `POST` | `/api/jobs/{id}/apply` | Trigger per-job apply pipeline (tailor → browser) |
| `GET` | `/api/jobs/{id}/resume-pdf` | Download tailored resume PDF |
| `DELETE` | `/api/jobs/{id}` | Remove a job listing |

### Company Management

| Method | Endpoint | What It Does |
|:------:|:---------|:-------------|
| `GET` | `/api/companies` | List tracked companies with ATS status |
| `POST` | `/api/companies` | Add company → auto-probe ATS board |
| `POST` | `/api/companies/load-seed` | Import 4,000+ pre-indexed Indian startups |
| `POST` | `/api/companies/sync` | Run sync pass: probe → fetch → score → store |

### System Control

| Method | Endpoint | What It Does |
|:------:|:---------|:-------------|
| `GET/POST` | `/api/pipeline-mode` | Get or set mode (`automatic` / `manual`) |
| `GET` | `/api/budget` | View Gemma token usage (15K RPD / 30 RPM) |
| `GET` | `/api/status` | System status, job counts, token telemetry |
| `POST` | `/api/stop-browser` | Kill active browser sessions |
| `POST` | `/api/browser/takeover` | Request HITL takeover of live browser |
| `POST` | `/api/browser/release` | Release control back to agent |
| `POST` | `/api/reset` | Nuclear option — clear everything |

### WebSocket Streams

| Endpoint | What It Streams |
|:---------|:----------------|
| `/ws` | Agent logs, pipeline progress, job events, scoring updates, intervention alerts |
| `/ws/browser` | Live CDP JPEG frames (screencast) + mouse/keyboard event forwarding |

---

## 🧪 Testing

85 tests. Zero flaky. All passing.

```bash
pytest jobhunterx/tests/ -v
```

```
tests/test_api.py                 ......... (9 passed)
tests/test_ats_pagination.py      .......... (10 passed)
tests/test_dedupe_freshness.py    ........ (8 passed)
tests/test_eligibility.py         ..................... (21 passed)
tests/test_gemma_budget.py        ..... (5 passed)
tests/test_json_helper.py         .... (4 passed)
tests/test_liveness.py            ............. (13 passed)
tests/test_resume_tailoring.py    ............... (15 passed)

======================== 85 passed ========================
```

---

## 🇮🇳 Pre-Seeded Regional Data

JobHunterX ships with indexed company databases covering **16 Indian tech hubs** and **4,000+** companies:

| Hub | Companies | Hub | Companies |
|:----|:---------:|:----|:---------:|
| 🏙️ Bengaluru | 800+ | 🏙️ Chennai | 1,220+ |
| 🏙️ Hyderabad | 500+ | 🏙️ Mumbai | 1,211+ |
| 🏙️ Pune | 525+ | 🏙️ Delhi NCR | 1,070+ |
| 🏙️ Kolkata | 500+ | 🏙️ Ahmedabad | 308+ |
| 🏙️ Kochi | 100+ | 🏙️ Bhubaneswar | 200+ |
| 🏙️ Visakhapatnam | 150+ | 🏙️ Coimbatore | 100+ |
| 🏙️ Indore | 90+ | 🏙️ Chandigarh | 120+ |
| 🏙️ Jaipur | 50+ | 🏙️ Remote | ∞ |

---

## 🛡️ Stealth Browser Architecture

The browser agent doesn't show up on radar:

- **Persistent Chrome Profile** — Cookies, localStorage, and browsing history accumulate across sessions, building trust with Cloudflare and similar WAFs
- **Desktop User-Agent** — `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36`
- **Anti-Automation Flags** — `--disable-blink-features=AutomationControlled`, disabled site isolation
- **Zombie Chrome Cleanup** — Automatically kills orphan Chrome processes and clears `SingletonLock` files before each launch
- **Cloud Browser Support** — Optional cloud stealth browser integration via `BROWSER_USE_API_KEY`

---

<div align="center">

## 📜 License

**MIT License** — Build on it, fork it, make it yours.

Built with ❤️ and an unhealthy amount of caffeine for job seekers who refuse to waste time on repetitive applications.

<br/>

**⭐ Star this repo if JobHunterX saved you from the soul-crushing grind of manual job applications**

</div>
