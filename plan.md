# Vellum OS — Career Intelligence & Application Agent (Revised Plan v2)

Complete implementation addressing all architectural feedback. Every component is designed as **best-effort with confidence scoring**, robust persistence, and proper fallback chains.

## Changes from v1 (Addressing All Feedback)

| # | Concern | Resolution |
|---|---------|------------|
| 1 | OSM `office=it` unreliable | Multi-source discovery: OSM + ddgs + curated ATS domain lists. Each source scored independently. |
| 2 | Career page search noise | URL validator/scorer: penalize LinkedIn/Glassdoor/Indeed, boost `/careers`, `/jobs`, known ATS domains (Greenhouse, Lever, Ashby, Workday). |
| 3 | ScrapeGraphAI overuse | Deterministic-first pipeline: BeautifulSoup + CSS selectors + regex → LLM fallback only when needed. |
| 4 | Regex freshness unreliable | Best-effort freshness with `confidence: float`. Check HTTP headers, meta tags, ATS-specific patterns. Never hard-discard — flag as `uncertain`. |
| 5 | Email permutation unreliable | Permutations labeled as `unverified_guesses`. No auto-send. UI shows confidence. Add MX record check. |
| 6 | Founders only targeting | Search for hiring managers, EMs, recruiters, team leads, VPs — not just founders. Role-priority ranking. |
| 7 | Browser can't bypass CAPTCHAs | Robust HITL with explicit fallback states: `needs_login`, `needs_captcha`, `needs_mfa`, `needs_manual_form`, `too_complex`. User dashboard shows queue. |
| 8 | Coarse-grained graph | Per-job pipeline: discovery graph produces job queue → each job gets its own independent validation/apply/outreach pipeline. |
| 9 | No persistence | SQLite via `aiosqlite` for jobs, profiles, agent state, tailored resumes, outreach drafts. Survives restart. |
| 10 | No retry/backoff/caching | `tenacity` for retries with exponential backoff. `diskcache` for request caching. Duplicate detection via URL hash. Semaphore-based concurrency limits per provider. |
| 11 | ChromaDB unnecessary | Removed. SQLite + FTS5 full-text search for JD matching. Embeddings only if user explicitly enables semantic search later. |
| 12 | Resume hallucination risk | Strict guardrails: original profile as ground truth, diff-based validation, no new skills/experience allowed, iterative PDF length control with binary search on bullet count. |
| 13 | Missing observability | Structured logging (`structlog`), token usage tracking per call, browser screenshots on failure, request/response tracing, failure diagnostics dashboard. |
| 14 | Best-effort confidence | Every component returns `confidence: float` (0.0-1.0). UI shows confidence badges. Low-confidence items flagged for manual review. |

## Open Questions

> [!IMPORTANT]
> **API Keys:** Your `.env` has only `GEMINI_API_KEY`. Do you have **Groq** and **Mistral** keys? System will gracefully degrade to available providers if some are missing.

> [!IMPORTANT]
> **Resume for testing:** Will you upload your own PDF, or should I include a sample for development?

---

## Proposed Changes

All files under `c:\Users\vamsi\OneDrive\Desktop\Job agent\vellum-os\`.

---

### Component 1: Project Foundation

#### [NEW] [pyproject.toml](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/pyproject.toml)
Core dependencies (no ChromaDB, no googlesearch-python):
```
fastapi, uvicorn[standard], pydantic, pydantic-settings, python-dotenv
litellm, langgraph
browser-use, playwright
ddgs                          # replaces broken googlesearch-python
geopy, overpy                 # geospatial
curl-cffi, trafilatura        # scraping
beautifulsoup4, lxml          # deterministic parsing (NEW)
scrapegraphai                 # LLM fallback only
xhtml2pdf, jinja2, pymupdf    # PDF
aiosqlite                     # persistence (replaces ChromaDB)
tenacity                      # retry with backoff (NEW)
diskcache                     # request caching (NEW)
structlog                     # structured logging (NEW)
dnspython                     # MX record verification (NEW)
```

#### [NEW] [.env.example](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/.env.example)
```env
GOOGLE_API_KEY=
GROQ_API_KEY=
MISTRAL_API_KEY=
BROWSER_USE_HEADLESS=false
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
DB_PATH=./data/vellum.db
CACHE_DIR=./data/cache
```

---

### Component 2: Configuration & Infrastructure

#### [NEW] [vellum/config/settings.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/config/settings.py)
- Pydantic `BaseSettings` with `SettingsConfigDict(env_file=".env", extra="ignore")`
- All API keys optional (graceful degradation)
- `available_providers` property that checks which keys are set
- DB path, cache dir, log level configs
- `@lru_cache` singleton

#### [NEW] [vellum/config/llm_router.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/config/llm_router.py)
- LiteLLM wrapper with auto-thinking-model detection per spec Section 4
- `THINKING_MODELS` map with parameter injection:
  - Groq `gpt-oss-*` → `reasoning_effort: "low"`
  - Mistral `magistral-*` / `mistral-large-*` → `thinking: {type: "enabled", budget_tokens: 2048}`
- **NEW: Concurrency limiter** — `asyncio.Semaphore` per provider (Gemini: 30, Groq: 30, Mistral: 30)
- **NEW: Token tracking** — logs input/output tokens per call via `structlog`
- **NEW: Fallback chain** — if primary model fails, try next available provider
- **NEW: `tenacity` retry** — exponential backoff on rate limit (429) and server errors (5xx)
- **NEW: Request caching** — `diskcache` for identical prompt+model combos (configurable TTL)
- Async `call_llm(model, messages, **kwargs)` → response

#### [NEW] [vellum/config/logging.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/config/logging.py)
- `structlog` configuration with JSON output
- Context variables: `agent_name`, `job_id`, `company`, `model`, `tokens_used`
- Console renderer for dev, JSON for production
- Token usage aggregation helper

#### [NEW] [vellum/config/database.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/config/database.py)
- `aiosqlite` connection manager
- Schema creation on startup:
  - `profiles` — candidate profiles (JSON blob + metadata)
  - `jobs` — discovered jobs with status, confidence, match_score, timestamps
  - `tailored_resumes` — PDF blobs linked to job_id
  - `outreach_drafts` — email drafts with status, confidence
  - `agent_runs` — execution logs with timestamps, token usage
  - `applied_urls` — dedup table (URL hash index for duplicate detection)
- FTS5 virtual table on `jobs.jd_text` for full-text search
- Async CRUD helpers
- **Unique constraint on `jobs.apply_url_hash`** for duplicate detection

---

### Component 3: Data Models

#### [NEW] [vellum/models.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/models.py)
All Pydantic models with confidence scoring:

```python
class CandidateProfile(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    linkedin: str
    summary: str
    skills: list[str]           # ground truth — never modified by tailoring
    experience: list[Experience]
    education: list[Education]

class JobListing(BaseModel):
    id: str                     # uuid
    company: str
    role: str
    career_page_url: str
    apply_url: str | None
    jd_text: str
    source: str                 # "osm", "ddgs", "curated"
    discovery_confidence: float # 0.0-1.0
    freshness: FreshnessResult
    validation: ValidationResult | None
    status: JobStatus           # discovered, validating, matched, applying, applied, failed, skipped

class FreshnessResult(BaseModel):
    is_fresh: bool | None       # None = uncertain
    confidence: float           # 0.0-1.0
    evidence: str               # "HTTP Last-Modified", "meta tag", "regex date", "unknown"
    detected_date: str | None

class ValidationResult(BaseModel):
    match_score: float          # 0.0-1.0
    matching_skills: list[str]
    missing_skills: list[str]
    reasoning: str
    confidence: float

class OutreachDraft(BaseModel):
    id: str
    company: str
    contact_name: str
    contact_role: str           # "Hiring Manager", "EM", "Recruiter", "Founder", etc.
    email_guesses: list[EmailGuess]
    subject: str
    body: str
    mailto_uri: str
    confidence: float
    status: str                 # "drafted", "sent", "discarded"

class EmailGuess(BaseModel):
    address: str
    pattern: str                # "first@domain", "first.last@domain", etc.
    mx_valid: bool | None       # MX record check result
    confidence: float

class HITLRequest(BaseModel):
    type: str                   # "login", "captcha", "mfa", "manual_form", "too_complex"
    job_id: str
    url: str
    screenshot_path: str | None
    message: str

class AgentEvent(BaseModel):
    agent: str
    event_type: str             # "progress", "discovery", "error", "hitl_request", "complete"
    job_id: str | None
    message: str
    data: dict | None
    timestamp: datetime
    confidence: float | None
```

---

### Component 4: Tools Layer (Deterministic-First)

#### [NEW] [vellum/tools/maps_api.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/maps_api.py)
- `geocode_location(city)` → lat/lon via `geopy.geocoders.Nominatim(user_agent="vellum-os")`
- `find_tech_companies(lat, lon, radius_km=20)` → companies via `overpy`
  - Query: `office=it` OR `office=company` OR `office=coworking` OR `building=commercial` with `name` tag
  - **Returns with `source_confidence: 0.5`** — OSM is supplementary, not primary
- Results include: name, lat, lon, website tag (if available), confidence

#### [NEW] [vellum/tools/search.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/search.py)
- **Multi-source search with scoring:**
  - `search_career_pages(company)` → uses `ddgs.DDGS().text(f"{company} careers jobs apply")`
  - **URL Scoring Pipeline (NEW):**
    - +1.0 for paths containing `/careers`, `/jobs`, `/openings`, `/apply`
    - +0.8 for known ATS domains: `greenhouse.io`, `lever.co`, `ashbyhq.com`, `workday.com`, `boards.greenhouse.io`, `jobs.lever.co`
    - -0.9 for `linkedin.com`, `glassdoor.com`, `indeed.com`, `naukri.com`
    - -0.5 for `news`, `blog`, `article` in URL
    - +0.3 for company domain match
  - Returns ranked list with confidence scores
- `search_contacts(company, location)` → searches for multiple roles:
  - Priority: "Hiring Manager" > "Engineering Manager" > "Recruiter" > "VP Engineering" > "CTO" > "Founder"
  - Uses ddgs: `f"{company} {role_title} {location} site:linkedin.com/in"`
  - Returns list of `ContactResult` with name, role, source_url, confidence
- **`diskcache` integration** — cache search results for 24 hours

#### [NEW] [vellum/tools/scrape.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/scrape.py)
- **Deterministic-first pipeline (3-tier fallback):**

  **Tier 1 — Deterministic HTML parsing (FREE, fast, no LLM):**
  - `BeautifulSoup` + `lxml` parser
  - CSS selectors for known ATS patterns:
    - Greenhouse: `div.opening a[href*="boards.greenhouse"]`
    - Lever: `div.posting a.posting-title`
    - Ashby: `a[href*="jobs.ashbyhq.com"]`
    - Workday: `a[href*="myworkdayjobs.com"]`
    - Generic: `a[href*="/apply"]`, `a[href*="/jobs/"]`, `a:contains("Apply")`
  - Regex patterns for common job link structures
  - Returns with `extraction_method: "deterministic"`, `confidence: 0.9`

  **Tier 2 — `curl_cffi` + `trafilatura` (for JD text extraction):**
  - `curl_cffi.requests.get(url, impersonate="chrome")` for Cloudflare bypass
  - `trafilatura.extract(html, include_comments=False)` for clean text
  - Returns with `extraction_method: "trafilatura"`, `confidence: 0.8`

  **Tier 3 — ScrapeGraphAI LLM fallback (expensive, last resort):**
  - Only triggered when Tier 1 finds 0 links AND page has complex JS rendering
  - Uses `SmartScraperGraph` with `gemini/gemini-3.1-flash-lite`
  - Returns with `extraction_method: "llm"`, `confidence: 0.7`

- **NEW: `extract_job_freshness(html, headers)` → `FreshnessResult`:**
  - Check 1: HTTP `Last-Modified` header → high confidence (0.9)
  - Check 2: `<meta property="article:published_time">` → high confidence (0.85)
  - Check 3: ATS-specific patterns (Greenhouse JSON-LD `datePosted`, Lever `data-qa="posting-date"`) → medium confidence (0.7)
  - Check 4: Regex date scan in visible text → low confidence (0.4)
  - Check 5: No date found → `is_fresh: None, confidence: 0.0, evidence: "unknown"`
  - **Never hard-discard.** Flag uncertain jobs for user review.

#### [NEW] [vellum/tools/email_handoff.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/email_handoff.py)
- `generate_email_permutations(first, last, domain)` → `list[EmailGuess]`
  - Patterns: `first@`, `first.last@`, `flast@`, `firstl@`, `first_last@`
  - Each labeled with `confidence` and `pattern` name
  - **NEW: MX record check** via `dns.resolver` — verify domain accepts email
  - **All results explicitly labeled `unverified_guess: True`**
- `create_mailto_uri(to, subject, body)` → encoded `mailto:` URI
- `open_mail_client(mailto_uri)` → `webbrowser.open()` wrapper
- **No auto-send ever.** User clicks "Open in Mail App" → their client opens → they click Send.

#### [NEW] [vellum/tools/pdf_render.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/pdf_render.py)
- `render_resume_pdf(profile_data, tailored_bullets)` → PDF bytes
- Jinja2 template from spec Section 6 + `xhtml2pdf.pisa.CreatePDF()`
- **NEW: Iterative length control:**
  1. Render full content → check if > 1 page
  2. If overflow: binary search on bullet count per experience entry
  3. Trim least-impactful bullets first (shortest, most generic)
  4. Re-render until exactly 1 page
  5. If still overflows after trimming all optional sections: reduce font size 10pt → 9.5pt → 9pt
- In-memory via `io.BytesIO`
- Returns PDF bytes + `page_count` assertion

#### [NEW] [vellum/tools/embeddings.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/tools/embeddings.py)
- **Minimal — optional module, not loaded by default**
- Only activated if user explicitly enables semantic search
- BGE-small-en-v1.5 via `sentence_transformers` for future use
- Not part of core pipeline (SQLite FTS5 handles search)

#### [NEW] [vellum/templates/resume.html](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/templates/resume.html)
- Exact Jinja2 + CSS template from spec Section 6
- ATS-safe, single-page, pure-CSS layout

---

### Component 5: Agent Layer (Per-Job Pipelines)

#### [NEW] [vellum/agents/extractor.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/extractor.py)
- `extract_profile(pdf_bytes)` → `CandidateProfile`
- `PyMuPDF (fitz)` with `page.get_text(sort=True)` for clean column-aware extraction
- Sends text to `gemini/gemma-4-31b` via LiteLLM with Pydantic schema as `response_format`
- **Ground truth preservation:** extracted `skills` list stored separately and never modified
- Stores profile in SQLite

#### [NEW] [vellum/agents/geo_search.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/geo_search.py)
- **Agent A — Multi-Source Company Discovery**
- **Source 1:** OSM via `maps_api` (confidence: 0.5)
- **Source 2:** ddgs search for `"{location}" tech companies hiring` (confidence: 0.6)
- **Source 3:** Curated ATS board crawl — known Greenhouse/Lever/Ashby boards for major Indian tech hubs (confidence: 0.8)
- Deduplication via company name fuzzy matching + domain matching
- For each company → `search.search_career_pages()` → URL scoring → `scrape` (deterministic-first)
- **Duplicate detection:** check `applied_urls` table before processing
- Streams `AgentEvent` updates via callback
- Inserts discovered jobs into SQLite with `status: "discovered"`

#### [NEW] [vellum/agents/validator_tailor.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/validator_tailor.py)
- **Agent C — Validation, Freshness & Tailoring (per-job)**
- **Step 1: Freshness** — `scrape.extract_job_freshness()` → `FreshnessResult`
  - If `confidence < 0.3` → flag as `uncertain`, continue processing (don't discard)
  - If confirmed stale (> 14 days, confidence > 0.7) → mark `skipped`, move to next
- **Step 2: Validation** — Groq `groq/openai/gpt-oss-120b` with structured output
  - Compare JD requirements vs profile skills/experience
  - Returns `ValidationResult` with match_score, matching/missing skills, reasoning
  - If match_score < 0.3 → mark `skipped`
- **Step 3: Tailoring** — Mistral `mistral/mistral-large-2512`
  - **STRICT GUARDRAILS (NEW):**
    - System prompt: "You may ONLY rephrase existing bullets. You MUST NOT add skills, technologies, experiences, or achievements not present in the original profile. You may reorder and emphasize, but never fabricate."
    - Post-processing validation: diff tailored bullets against original — any new proper nouns or technical terms not in original skills list → REJECT and use original
    - Token-level comparison to detect hallucinated content
  - Returns tailored bullets + validation report
- **Step 4: PDF Generation** — `pdf_render.render_resume_pdf()` with iterative length control
- Updates job in SQLite with `status: "matched"`, stores tailored PDF

#### [NEW] [vellum/agents/browser_agent.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/browser_agent.py)
- **Agent B — Browser Execution (per-job, best-effort)**
- Uses `browser_use.Agent` with `ChatLiteLLM(model="gemini/gemini-3.1-flash-lite")`
- **Robust HITL state machine (NEW):**
  ```
  start → detect_form_type
    → simple_form → fill_and_submit → upload_pdf → verify_submission → done
    → login_required → HITL("needs_login") → wait_for_user → resume
    → captcha_detected → HITL("needs_captcha") → wait_for_user → resume
    → mfa_required → HITL("needs_mfa") → wait_for_user → resume
    → complex_form → HITL("needs_manual_form") → wait_for_user → resume
    → too_complex → HITL("too_complex") → skip_with_instructions
  ```
- **Screenshot on every state transition** — saved to `data/screenshots/{job_id}/`
- **Timeout:** 120 seconds per form, then escalate to HITL
- **Error recovery:** if browser crashes → capture screenshot → send HITL with diagnostic info
- Via LangGraph `interrupt()` → WebSocket → UI Modal → `Command(resume=...)` to continue
- Updates job in SQLite with `status: "applied"` or `status: "failed"`

#### [NEW] [vellum/agents/deep_research.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/deep_research.py)
- **Agent D — Deep Research & Outreach (per-job)**
- **Contact search with role priority (NEW):**
  1. Hiring Manager for the specific team
  2. Engineering Manager
  3. Technical Recruiter
  4. VP Engineering / Head of Engineering
  5. CTO
  6. Founder (last resort, not first choice)
  - Uses `search.search_contacts()` with role-specific dorks
  - Returns best match with confidence score
- **Email permutation with verification:**
  - Generate permutations via `email_handoff`
  - MX record check — if domain has no MX → skip entirely
  - **All emails labeled as `unverified_guess`** in UI
- **Draft email** via Groq `groq/openai/gpt-oss-120b`:
  - Personalized Proof-of-Work email based on JD + profile
  - Subject line + body
  - System prompt enforces professional tone, brevity
- Stores draft in SQLite with `status: "drafted"`

#### [NEW] [vellum/agents/graph.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/agents/graph.py)
- **Two-tier LangGraph architecture (NEW):**

  **Graph 1 — Discovery Graph (runs once):**
  ```
  entry → geo_search_node → [list of JobListings in SQLite]
  ```
  - Outputs: populated `jobs` table with discovered jobs

  **Graph 2 — Per-Job Pipeline (runs per job, independently):**
  ```
  entry → validate_tailor_node
    → (if matched) → fan_out:
        → browse_apply_node (with HITL interrupts)
        → deep_research_node
    → (if skipped) → END
  ```
  - Each job gets its own `thread_id` for independent HITL state
  - `InMemorySaver` checkpointer for HITL pause/resume
  - State uses reducers for concurrent updates
  - **Worker queue:** max 3 concurrent per-job pipelines to respect rate limits

- **NEW: Job Queue Manager:**
  - Pulls discovered jobs from SQLite
  - Spawns per-job pipelines with concurrency limit (semaphore)
  - Tracks overall progress
  - Handles graceful shutdown (save state to SQLite)

---

### Component 6: API Layer

#### [NEW] [vellum/api/main.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/api/main.py)
- FastAPI app with CORS, static file mounting for `vellum/web/`
- Lifespan handler: init SQLite, init logging, init cache
- Mounts API routes + WebSocket
- Serves frontend at `/`

#### [NEW] [vellum/api/routes.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/api/routes.py)
- `POST /api/upload-resume` — Upload PDF → extract profile → store in SQLite
- `POST /api/start-search` — Start discovery graph + job queue → return run_id
- `POST /api/resume-agent` — Resume HITL: `{job_id, action: "login_done" | "captcha_solved" | "skip"}`
- `GET /api/jobs` — List jobs with filters (status, confidence, match_score)
- `GET /api/jobs/{id}` — Single job detail + tailored resume download
- `GET /api/outreach` — List outreach drafts with confidence
- `POST /api/outreach/{id}/open-mail` — Trigger `webbrowser.open(mailto:)` server-side
- `POST /api/outreach/{id}/discard` — Mark draft discarded
- `GET /api/status` — Overall run status + token usage summary
- `GET /api/screenshots/{job_id}/{filename}` — Serve browser screenshots

#### [NEW] [vellum/api/ws.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/api/ws.py)
- WebSocket at `/ws`
- Connection manager with client tracking
- Broadcasts `AgentEvent` objects in real-time:
  - Job discoveries, validation results, apply attempts, HITL requests, errors
- Heartbeat ping/pong for connection health
- Auto-reconnect support in frontend

---

### Component 7: Frontend (Dribbble-Grade UI)

#### [NEW] [vellum/web/index.html](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/web/index.html)
Three-column tabbed layout per spec Section 5.1:

```
┌──────────────────────────────────────────────────────────┐
│  Vellum OS         [ATS Auto-Apply] [Direct Outreach]    │  ← 56px top bar
├────────────┬─────────────────────────┬───────────────────┤
│  Profile   │  Job Board / Outreach   │  Live Agents      │
│  Sidebar   │  (Contextual to Tab)    │  Activity Stream  │
│  240px     │  flex-1                 │  360px            │
└────────────┴─────────────────────────┴───────────────────┘
```

**Left sidebar:**
- Resume upload with drag-and-drop
- Profile summary (extracted from resume)
- Location input for search
- "Start Career Search" CTA button
- Token usage counter
- Run statistics (jobs found, applied, outreach sent)

**Tab 1 — ATS Auto-Apply (center panel):**
- Job cards with:
  - Company name, role title
  - **Confidence badges** (discovery, freshness, match) — color-coded
  - Status indicator (discovered → validating → matched → applying → applied/failed)
  - "Needs Attention" flag for HITL items
- HITL modal overlay:
  - Shows browser screenshot
  - Clear message: "Login required", "CAPTCHA detected", "Complex form — please fill manually"
  - Buttons: "I've completed it — Resume" | "Skip this job"

**Tab 2 — Direct Outreach (center panel):**
- Outreach cards with:
  - Company, contact name + role (not just founders)
  - **Email confidence indicator** + "unverified" badge
  - MX record status
- Click → modal:
  ```
  ┌─────────────────────────────────────────────────┐
  │  ✉️ Direct Outreach: Razorpay                    │
  │                                                 │
  │  To: harsh@razorpay.com (Engineering Manager)   │
  │  ⚠️ Email unverified — domain MX valid          │
  │  Confidence: ●●●○○ Medium                       │
  │                                                 │
  │  Subject: Backend Scaling - Quick Audit         │
  │  [editable email body]                          │
  │                                                 │
  │  [ Open in Mail App ]   [ Discard ]             │
  └─────────────────────────────────────────────────┘
  ```

**Right panel — Agent Activity Stream:**
- Real-time feed of agent events via WebSocket
- Color-coded by agent (A: blue, B: green, C: orange, D: purple)
- Error events highlighted in red
- HITL requests pinned to top with action buttons

#### [NEW] [vellum/web/styles.css](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/web/styles.css)
- **Color system:**
  - Light: warm off-white `#FAFAF7` background
  - Dark: deep ink `#0A0A0B` background
  - Accent: muted terracotta `#C8553D` for CTAs
  - Confidence colors: green (high), amber (medium), red (low), gray (unknown)
- **Typography:** Inter (body) + JetBrains Mono (code/logs) from Google Fonts
- **Design tokens** via CSS custom properties for easy theming
- Dark mode toggle with `prefers-color-scheme` detection + manual override
- Glassmorphism cards: `backdrop-filter: blur(12px)`, translucent backgrounds
- Micro-animations: card hover lift, status pulse, progress shimmer
- Responsive: collapses to single column on mobile
- 56px sticky top bar with pill-shaped tab buttons

#### [NEW] [vellum/web/app.js](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/web/app.js)
- **WebSocket manager:** auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- **State management:** client-side job/outreach state synced via WebSocket events
- Tab switching with URL hash persistence (`#ats`, `#outreach`)
- Resume upload: drag-and-drop + click, with progress indicator
- Job card rendering with real-time status updates + confidence badges
- HITL modal: shows screenshot, action buttons, auto-opens when agent requests
- Outreach modal: editable email body, "Open in Mail App" triggers API call
- Activity stream: auto-scroll, max 200 entries, color-coded
- Dark mode: toggle button, persisted to `localStorage`
- Token usage counter: live update from WebSocket events
- Error toast notifications with auto-dismiss

---

### Component 8: Observability (NEW)

#### [NEW] [vellum/config/observability.py](file:///c:/Users/vamsi/OneDrive/Desktop/Job agent/vellum-os/vellum/config/observability.py)
- **Structured logging** via `structlog`:
  - Every LLM call: model, tokens_in, tokens_out, latency_ms, cache_hit
  - Every scrape: url, method (deterministic/trafilatura/llm), status, latency
  - Every agent transition: agent, from_state, to_state, job_id
  - Every error: full traceback, context, recovery action
- **Token usage aggregation:**
  - Per-model running totals
  - Per-run summaries
  - Exposed via `GET /api/status` endpoint
- **Browser screenshots:**
  - Captured on every HITL trigger
  - Captured on browser agent errors
  - Stored in `data/screenshots/{job_id}/`
  - Served via API for UI display

---

## File Tree Summary

```text
vellum-os/
├── pyproject.toml
├── .env.example
├── README.md
├── data/                          # Created at runtime
│   ├── vellum.db                  # SQLite persistence
│   ├── cache/                     # diskcache
│   └── screenshots/               # Browser screenshots
├── vellum/
│   ├── __init__.py
│   ├── models.py                  # All Pydantic models
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # BaseSettings + .env
│   │   ├── llm_router.py          # LiteLLM + thinking + retry + cache
│   │   ├── database.py            # aiosqlite + schema
│   │   ├── logging.py             # structlog config
│   │   └── observability.py       # Token tracking, screenshots
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── maps_api.py            # geopy + overpy
│   │   ├── search.py              # ddgs + URL scoring + contact search
│   │   ├── scrape.py              # BS4 → trafilatura → ScrapeGraphAI
│   │   ├── email_handoff.py       # Permutation + MX check + mailto
│   │   ├── pdf_render.py          # Jinja2 + xhtml2pdf + iterative fit
│   │   └── embeddings.py          # Optional BGE-small (not in core)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── extractor.py           # PyMuPDF → Gemma 4 → profile
│   │   ├── geo_search.py          # Multi-source discovery
│   │   ├── validator_tailor.py    # Freshness + validation + guardrailed tailoring
│   │   ├── browser_agent.py       # browser-use + HITL state machine
│   │   ├── deep_research.py       # Contact search + email draft
│   │   └── graph.py               # LangGraph: discovery + per-job pipelines
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI entry
│   │   ├── routes.py              # REST endpoints
│   │   └── ws.py                  # WebSocket stream
│   ├── web/
│   │   ├── index.html             # Tabbed layout
│   │   ├── styles.css             # Dribbble-grade theme
│   │   └── app.js                 # Frontend logic
│   └── templates/
│       └── resume.html            # ATS-safe Jinja2 template
└── tests/
    └── __init__.py
```

## Verification Plan

### Automated Tests
```bash
# 1. Install and verify project structure
cd vellum-os && pip install -e ".[dev]"

# 2. Verify settings load from .env
python -c "from vellum.config.settings import get_settings; s = get_settings(); print(f'Providers: {s.available_providers}')"

# 3. Verify database schema
python -c "import asyncio; from vellum.config.database import init_db; asyncio.run(init_db())"

# 4. Verify LLM router
python -c "from vellum.config.llm_router import get_llm_params; print(get_llm_params('groq/openai/gpt-oss-120b'))"

# 5. Start the server
python -m vellum.api.main
# → Open http://localhost:8000
```

### Manual Verification
1. Open `http://localhost:8000` — verify Dribbble-grade UI with dark mode toggle
2. Upload a resume PDF → verify profile extraction shows in sidebar
3. Enter "Bengaluru" + click "Start Career Search" → verify multi-source discovery
4. Watch activity stream → verify real-time updates with confidence badges
5. Check job cards → verify freshness/match confidence indicators
6. Trigger HITL → verify modal with screenshot appears
7. Check outreach tab → verify contact roles are diverse (not just founders)
8. Check email cards → verify "unverified" badges on email guesses
9. Click "Open in Mail App" → verify mailto opens default client
10. Restart server → verify all jobs/drafts persist from SQLite
