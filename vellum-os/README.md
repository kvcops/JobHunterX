# Vellum OS — AI-Powered Job Application Agent

> **Version:** 0.1.0 | **Last Updated:** 2026-07-30 | **Status:** Active Development

---

## Overview

**Vellum OS** is an AI-powered autonomous job application agent designed for the Indian tech market. It operates as a local-first, self-hosted career intelligence system that discovers, evaluates, applies to, and reaches out to potential employers on behalf of a software engineer candidate.

### Key Features

- **Multi-source job discovery**: DuckDuckGo web search + public ATS APIs (Greenhouse, Lever, Ashby) — no paid APIs, no search keys
- **AI-powered resume tailoring**: Google XYZ formula for bullet points, role-specific summary rewriting
- **Smart contact discovery**: Multi-method email finder with MX verification
- **Automated form filling**: Browser automation with human-in-the-loop for CAPTCHAs/MFA
- **Real-time progress**: WebSocket-based live updates in the UI

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Instrument Panel UI                       │
│              (index.html + app.js + styles.css)              │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST + WebSocket
┌─────────────────────────▼───────────────────────────────────┐
│                   API Layer (FastAPI)                        │
│             routes.py + ws.py + main.py                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Agent Orchestration (LangGraph)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ geo_search  │  │ graph.py     │  │ per-job pipeline│    │
│  │ (discovery) │──│ (orchestrator)│──│ (validate/apply)│    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Tool Layer                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │web_search_      │  │ ats_api.py   │  │ career_urls.py│  │
│  │scraper.py       │  │ (Greenhouse, │  │ (URL patterns │  │
│  │(DuckDuckGo +    │  │  Lever, etc) │  │  database)    │  │
│  │ public APIs)    │  └──────────────┘  └───────────────┘  │
│  └─────────────────┘                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │ scrape.py    │  │ email_handoff│  │ pdf_render.py │    │
│  │ (BS4 + traf) │  │ (.py)        │  │ (xhtml2pdf)   │    │
│  └──────────────┘  └──────────────┘  └───────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Persistence (aiosqlite + FTS5)                  │
│  profiles │ jobs │ outreach_drafts │ agent_events            │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend** | Vanilla JS (no framework), WebSocket |
| **Agent Orchestration** | LangGraph (state machine) |
| **LLM** | LiteLLM (multi-provider routing) |
| **Search** | DuckDuckGo via `ddgs` library |
| **Scraping** | BeautifulSoup4, Trafilatura, curl-cffi |
| **Browser Automation** | browser-use (Playwright-based) |
| **PDF Generation** | xhtml2pdf, Jinja2 templates |
| **Database** | SQLite via aiosqlite + FTS5 |
| **Caching** | diskcache |
| **Resilience** | tenacity (retry), rate limiting |
| **Logging** | structlog |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js (optional, for dev tools)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vellum-os.git
cd vellum-os

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Install dev dependencies (optional)
pip install -e ".[dev]"
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: LLM_API_KEY (for AI features)
# Optional: FIRECRAWL_API_KEY, GOOGLE_API_KEY
```

### Running

```bash
# Start the server
python -m vellum.main

# Or with uvicorn directly
uvicorn vellum.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

---

## How It Works

### Step 1: Upload Resume

Upload your resume (PDF). The system extracts your profile: name, email, phone, skills, experience, education, and summary.

### Step 2: Configure Search

- **Location**: Select a city (Bengaluru, Hyderabad, Mumbai, NCR, etc.)
- **Role**: Optionally specify a role (e.g., "Python Developer", "Backend Engineer")
- **Analysis Limit**: Set max companies to analyze (default: 25)

Click **Search** to start discovery.

### Step 3: Job Discovery

The system discovers jobs using two parallel channels:

**Primary: Web Search (DuckDuckGo)**
- Searches for `"{role}" {location} site:greenhouse.io OR site:lever.co`
- Direct access to ATS job boards (no API key needed)
- Rate limiting with jitter, user-agent rotation
- Filters out aggregators (LinkedIn, Indeed, Naukri)

**Secondary: Public ATS APIs**
- Greenhouse: `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- Lever: `api.lever.co/v0/postings/{company}`
- Ashby: `api.ashbyhq.com/api/v1/job-postings/{orgId}`
- Freshteam: `YOURDOMAIN.freshteam.com/api/jobs`

**Tertiary: VC Portfolio Boards**
- Getro-powered boards (Blume Ventures, etc.)

### Step 4: AI Scoring

Jobs are scored in batches of 10:
- Location match (onsite vs remote)
- Experience fit (years, seniority)
- Skills overlap
- Role alignment
- CTC fit (if specified)

### Step 5: View Results

Browse discovered jobs in the Applications tab with match scores, company info, and apply links.

### Step 6: Apply to a Job

Click **Apply** on any job to trigger the per-job pipeline:

1. **Validate**: Re-check job freshness, deep match scoring
2. **Tailor Resume**: Rewrite summary + bullets using Google XYZ formula
3. **Generate PDF**: ATS-friendly format
4. **Find Contact**: Search for hiring manager emails
5. **Draft Email**: Cold outreach with mailto link
6. **Fill Form**: Browser automation (pauses for CAPTCHA/MFA)

---

## Project Structure

```
vellum-os/
├── vellum/
│   ├── agents/              # AI agents
│   │   ├── geo_search.py    # Job discovery (web search + ATS APIs)
│   │   ├── graph.py         # Orchestrator (discovery + per-job pipeline)
│   │   ├── career_scraper.py # Direct career page scraper
│   │   ├── job_evaluator.py # Heuristic + AI scoring
│   │   ├── validator_tailor.py # Resume tailoring
│   │   ├── contact_finder.py # Email discovery
│   │   ├── email_drafter.py # Cold email generation
│   │   ├── browser_agent.py # Form filling automation
│   │   ├── deep_research.py # Additional research
│   │   └── extractor.py     # Resume parsing
│   ├── api/
│   │   ├── routes.py        # REST endpoints
│   │   ├── ws.py            # WebSocket server
│   │   └── main.py          # FastAPI app + lifespan
│   ├── config/
│   │   ├── llm_router.py    # Multi-provider LLM routing
│   │   ├── database.py      # SQLite persistence
│   │   └── logging.py       # Structured logging
│   ├── tools/
│   │   ├── web_search_scraper.py # DuckDuckGo + ATS APIs (v2)
│   │   ├── ats_api.py       # ATS API adapters
│   │   ├── career_urls.py   # URL pattern database
│   │   ├── search.py        # Contact search
│   │   ├── scrape.py        # Web scraping
│   │   ├── email_handoff.py # Email verification
│   │   ├── pdf_render.py    # PDF generation
│   │   ├── embeddings.py    # Vector embeddings (optional)
│   │   └── maps_api.py      # Geolocation (OSM)
│   ├── web/
│   │   ├── index.html       # UI
│   │   ├── app.js           # Frontend logic
│   │   └── styles.css       # Styling
│   ├── templates/           # Jinja2 templates
│   ├── models.py            # Pydantic models
│   └── __init__.py
├── tests/                   # 112 tests (all passing)
├── company-data/            # 4000+ companies, 35+ cities
├── data/                    # Runtime data (SQLite, cache)
├── pyproject.toml           # Dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

---

## Key Components

### web_search_scraper.py (v2)

Multi-source job discovery:
- **DuckDuckGo** via `ddgs` library (free, no API key)
- **Greenhouse/Lever public APIs** (no key needed)
- Rate limiting with jitter and exponential backoff
- User-agent rotation
- URL filtering (skips aggregators)
- Page enrichment (extracts full job details)

### geo_search.py

Discovery orchestrator:
- Primary: Web search via `web_search_scraper`
- Secondary: VC Portfolio boards (Getro)
- Filters by role relevance, location, experience
- Respects analysis limit from UI

### ats_api.py

ATS API adapters for:
- Greenhouse (boards-api.greenhouse.io)
- Lever (api.lever.co)
- Ashby (api.ashbyhq.com)
- Freshteam (freshteam.com)
- Zoho Recruit
- Getro (VC portfolios)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload-resume` | Upload and parse resume |
| `POST` | `/api/start-search` | Start job discovery |
| `POST` | `/api/halt-search` | Stop running search |
| `GET` | `/api/jobs` | List discovered jobs |
| `POST` | `/api/apply` | Start per-job pipeline |
| `GET` | `/api/profile` | Get current profile |
| `WS` | `/ws` | Real-time progress updates |

---

## Configuration

### Environment Variables

```env
# Required
LLM_API_KEY=your-api-key

# Optional
FIRECRAWL_API_KEY=your-firecrawl-key
GOOGLE_API_KEY=your-google-key
EMBEDDING_PROVIDER=local  # or 'openai'
```

### LLM Provider Fallback

The system automatically falls back between providers:
1. OpenAI (primary)
2. Anthropic
3. Google Gemini
4. Local models

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_web_search_scraper.py -v

# Run with coverage
pytest tests/ --cov=vellum
```

### Code Style

- Python 3.11+ with type hints
- Pydantic v2 for data validation
- Async/await throughout
- Structured logging with structlog

---

## License

MIT License

---

## Acknowledgments

- **ddgs** — DuckDuckGo search library
- **LangGraph** — Agent orchestration
- **browser-use** — Browser automation
- **FastAPI** — Web framework
- **Trafilatura** — Web content extraction
