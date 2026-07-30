# Vellum OS — Core Logic Redesign: Complete Issue Analysis & Solution

> **Date:** July 30, 2026  
> **Status:** Analysis Complete — Implementation Pending  
> **Scope:** Complete overhaul of job discovery, validation, and apply flow

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Flow — What's Actually Happening](#2-current-flow--whats-actually-happening)
3. [Root Cause Analysis — Why It's Broken](#3-root-cause-analysis--why-its-broken)
4. [The Correct Architecture](#4-the-correct-architecture)
5. [Phase 1: Direct Career Page Scraping (Replace DuckDuckGo)](#5-phase-1-direct-career-page-scraping)
6. [Phase 2: Experience & Quality Filtering](#6-phase-2-experience--quality-filtering)
7. [Phase 3: Batch LLM Relevancy Scoring](#7-phase-3-batch-llm-relevancy-scoring)
8. [Phase 4: Applications Tab — Apply-on-Click Flow](#8-phase-4-applications-tab--apply-on-click-flow)
9. [Phase 5: Email Finding — Multi-Method Approach](#9-phase-5-email-finding--multi-method-approach)
10. [Phase 6: LinkedIn Filtering & Exclusion Rules](#10-phase-6-linkedin-filtering--exclusion-rules)
11. [Phase 7: Third-Party ATS Exclusion List](#11-phase-7-third-party-ats-exclusion-list)
12. [Implementation Plan — File-by-File Changes](#12-implementation-plan--file-by-file-changes)
13. [Edge Cases & Scenarios](#13-edge-cases--scenarios)
14. [Research Findings Summary](#14-research-findings-summary)

---

## 1. Executive Summary

### The Problem (One Sentence)
We are using DuckDuckGo/Google search to randomly find job links from the internet, getting expired postings, third-party aggregator spam, and irrelevant results — when we already have a **static list of 4000+ real company names** and **working ATS API adapters** for Greenhouse, Lever, Ashby, Freshteam, and Zoho.

### The Fix (One Sentence)
For each company in our static list, **hit their actual career page or ATS API directly** using the role keywords from the parsed resume, filter by experience level, score relevancy via LLM, show results in the Applications tab, and only trigger PDF generation + email + browser agent **when the user clicks Apply**.

### Key Metrics to Improve
| Metric | Current | Target |
|--------|---------|--------|
| Job source | DuckDuckGo random search | Direct company career pages + ATS APIs |
| Expired job rate | ~40-60% | <5% |
| Third-party/aggregator noise | ~30-50% | 0% |
| Relevancy scoring | Per-job LLM call (slow) | Batch 3-5 jobs per LLM call |
| Apply trigger | Auto (wasteful) | User-click only |
| Email finding | Basic permutation only | Multi-method waterfall |

---

## 2. Current Flow — What's Actually Happening

### 2.1 The Discovery Pipeline (`geo_search.py`)

```
Channel 0: ats_api.fetch_hub_ats_jobs() — ✅ GOOD (hits ATS APIs directly)
Channel 0.5: ats_api.fetch_getro_vc_jobs() — ✅ OK (VC portfolio boards)
Channel 1: search.fetch_hasjob_jobs() — ⚠️ RSS feed, limited quality
Channel 2: search.search_wellfound_instahyre_jobs() — ❌ Third-party platforms
Channel 3: search.search_direct_ats_jobs() — ❌ DuckDuckGo site: search (unreliable)
Channel 4: search.search_unadvertised_social_posts() — ⚠️ LinkedIn/X dorks (hit or miss)
```

**The core issue:** Channels 2, 3, and 4 rely on DuckDuckGo (`ddgs` library) to search for jobs. This produces:
- Expired job postings (no freshness guarantee)
- Third-party aggregator links (Indeed, Glassdoor, Naukri — all in PENALTY_DOMAINS)
- Random blog posts about "top 10 jobs in Bangalore"
- Irrelevant role matches
- Staffing agency posts

### 2.2 The Search Tool (`search.py`)

```python
# search_direct_ats_jobs() — THE BIGGEST PROBLEM
queries = [
    f'"{role}" "{location}" site:boards.greenhouse.io',
    f'"{role}" "{location}" site:jobs.lever.co',
    f'"{role}" "{location}" site:jobs.ashbyhq.com',
    ...
]
# Uses DDGS to search — returns random indexed pages, not actual job listings
```

This is fundamentally broken because:
1. DuckDuckGo indexes career **pages**, not individual job listings
2. Results include "About Us" pages, blog posts, and category pages
3. No way to filter by experience level, freshness, or applicant count
4. Rate limited and unreliable

### 2.3 The Job Evaluator (`job_evaluator.py`)

```python
# Heuristic pre-filter — OK but incomplete
# Batch LLM evaluation — Good but runs on garbage input
```

The evaluator is well-designed but processes **bad input** from the discovery phase. No amount of evaluation can fix jobs that were never relevant.

### 2.4 The Apply Flow (`graph.py`)

```
Current: run_full_search() → discovery → batch_score → per-job pipelines (validate_only)
```

The `validate_only` mode is correct — it validates/tailors but doesn't auto-apply. However:
- The full pipeline still runs validation LLM calls on every discovered job
- PDF generation happens in `validator_tailor.run()` even before user clicks Apply
- This wastes LLM tokens and compute on jobs the user may never want

### 2.5 The Company Data (`ats_api.py`)

```python
TECH_HUB_STARTUPS = {
    "hyderabad": ["100ms", "1mg", "24-frames-factory", ...],  # 400+ companies
    "bengaluru": ["abb", "abbott", "accenture", ...],          # 400+ companies
    "mumbai": [...],                                           # 400+ companies
}
```

**This is GOLD** — a curated list of real companies. But `fetch_hub_ats_jobs()` only queries a random subset with ATS API calls. It doesn't iterate through the full list systematically.

---

## 3. Root Cause Analysis — Why It's Broken

### Issue 1: Wrong Discovery Strategy
**Current:** Search the internet for jobs → get random results  
**Correct:** For each company in our list → check their career page directly

### Issue 2: Third-Party Platform Dependency
**Current:** Searches Wellfound, Instahyre, LinkedIn posts via DuckDuckGo  
**Correct:** Only use direct company career pages and public ATS APIs

### Issue 3: No Experience Pre-Filtering
**Current:** Discovery gets all jobs → evaluator checks experience later  
**Correct:** Extract experience from JD during discovery → filter immediately

### Issue 4: PDF Generation Too Early
**Current:** `validator_tailor.run()` generates PDF for every validated job  
**Correct:** Only generate PDF when user clicks Apply

### Issue 5: No LinkedIn Quality Filtering
**Current:** No filtering for Easy Apply, 100+ applicants, promoted jobs  
**Correct:** Detect and exclude low-quality LinkedIn postings

### Issue 6: Email Finding is Weak
**Current:** Only basic permutation + MX check  
**Correct:** Multi-method waterfall: permutations → Google dorks → GitHub → contact page scraping → SMTP verification

### Issue 7: DuckDuckGo is Unreliable
**Current:** DDGS is the primary search engine  
**Correct:** Use direct HTTP requests to known ATS endpoints (no search engine needed)

---

## 4. The Correct Architecture

### 4.1 New Discovery Flow

```
For each company in TECH_HUB_STARTUPS[location]:
  1. Try ATS API directly (Greenhouse → Lever → Ashby → Freshteam → Zoho)
     - If found: filter by role keywords + experience level
     - If not found: try company career page URL patterns
  
  2. Try company career page URL patterns:
     - careers.{company}.com
     - {company}.com/careers
     - {company}.com/jobs
     - Check for JSON-LD JobPosting structured data
     - Check for RSS/Atom feeds
  
  3. For each job found:
     a. Extract experience requirement from JD text (regex + LLM)
     b. Compare against user profile experience level
     c. If experience matches: add to candidate list
     d. If no experience mentioned: include (permissive)
  
  4. Batch candidate jobs (3-5 at a time) → LLM relevancy scoring
     - Returns: match_score, matching_skills, missing_skills, reasoning
  
  5. Display scored jobs in Applications tab
     - User sees: company, role, match_score, JD snippet
     - NO PDF generated yet
     - NO email drafted yet
     - NO browser agent launched

When user clicks "Apply" on a job:
  1. Generate tailored resume PDF (validator_tailor)
  2. Find company email (contact_finder with new multi-method)
  3. Draft outreach email (email_drafter)
  4. Launch browser agent (browser_agent)
```

### 4.2 New File Structure

```
vellum/
├── agents/
│   ├── career_scraper.py        # NEW: Direct career page scraper
│   ├── ats_fetcher.py           # NEW: Systematic ATS API fetcher  
│   ├── experience_filter.py     # NEW: JD experience extraction + filtering
│   ├── job_evaluator.py         # MODIFIED: Batch LLM scoring (keep)
│   ├── contact_finder.py        # MODIFIED: Multi-method email finding
│   ├── validator_tailor.py      # MODIFIED: Only runs on Apply click
│   ├── email_drafter.py         # MODIFIED: Only runs on Apply click
│   ├── browser_agent.py         # MODIFIED: Only runs on Apply click
│   └── graph.py                 # MODIFIED: New flow orchestration
├── tools/
│   ├── search.py                # MODIFIED: Remove DDGS job search
│   ├── scrape.py                # KEEP: curl_cffi + trafilatura
│   ├── ats_api.py               # KEEP: All ATS adapters
│   ├── email_handoff.py         # MODIFIED: Add SMTP verification
│   └── career_urls.py           # NEW: Career page URL pattern database
```

---

## 5. Phase 1: Direct Career Page Scraping

### 5.1 ATS API Priority Order

For each company slug, try in this order:

| Priority | ATS | API Endpoint | Auth | Reliability |
|----------|-----|-------------|------|-------------|
| 1 | Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | None | ★★★★★ |
| 2 | Lever | `api.lever.co/v0/postings/{slug}?mode=json` | None | ★★★★★ |
| 3 | Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | None | ★★★★☆ |
| 4 | Freshteam | `{slug}.freshteam.com/jobs.json` | None | ★★★☆☆ |
| 5 | Zoho | `{slug}.zohorecruit.in/careers` | None | ★★☆☆☆ |
| 6 | SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings` | None* | ★★★☆☆ |
| 7 | Workday | `{slug}.wd1.myworkdayjobs.com/wday/cxs/{slug}/{site}/jobs` | None** | ★★☆☆☆ |

*SmartRecruiters requires the customer to enable public feed  
**Workday internal JSON endpoint (undocumented, varies by tenant)

### 5.2 Career Page URL Patterns

When no ATS API works, try these URL patterns:

```python
CAREER_URL_PATTERNS = [
    "https://careers.{slug}.com",
    "https://careers.{slug}.com/jobs",
    "https://{slug}.com/careers",
    "https://{slug}.com/jobs",
    "https://{slug}.com/openings",
    "https://{slug}.com/positions",
    "https://{slug}.com/hiring",
    "https://www.{slug}.com/careers",
    "https://boards.greenhouse.io/{slug}",
    "https://jobs.lever.co/{slug}",
    "https://jobs.ashbyhq.com/{slug}",
]
```

### 5.3 JSON-LD Extraction from Career Pages

Many career pages embed Schema.org `JobPosting` structured data:

```python
# Parse <script type="application/ld+json"> from career page HTML
{
    "@type": "JobPosting",
    "title": "Senior Software Engineer",
    "datePosted": "2026-07-15",
    "validThrough": "2026-08-15",          # EXPIRED IF PAST
    "employmentType": "FULL_TIME",
    "hiringOrganization": {"name": "Acme Corp"},
    "jobLocation": {"address": {"addressLocality": "Bengaluru"}},
    "description": "<p>We are looking for...</p>",
    "baseSalary": {"currency": "INR", "value": {"minValue": 1500000, "maxValue": 2500000}},
    "directApply": true
}
```

### 5.4 Implementation: `career_scraper.py`

```python
"""
New Agent: Career Page Scraper
For each company in our list → try ATS APIs → try career page URLs → extract jobs
"""

async def scrape_company_jobs(company_slug: str, role_keywords: str, location: str) -> list[dict]:
    """Scrape jobs from a company's career page or ATS API."""
    
    # Step 1: Try ATS APIs in priority order
    for ats_fetcher in [fetch_greenhouse, fetch_lever, fetch_ashby, fetch_freshteam, fetch_zoho]:
        jobs = await ats_fetcher(company_slug)
        if jobs:
            # Filter by role keywords
            matched = filter_by_role(jobs, role_keywords)
            # Filter by experience
            matched = filter_by_experience(matched, user_experience)
            # Filter by location
            matched = filter_by_location(matched, location)
            return matched
    
    # Step 2: Try career page URL patterns
    for url_pattern in CAREER_URL_PATTERNS:
        url = url_pattern.format(slug=company_slug)
        try:
            page = await fetch_page(url)
            if page.get("status") == 200:
                # Try JSON-LD extraction first
                jobs = extract_jsonld_jobs(page["html"], company_slug)
                if jobs:
                    return filter_jobs(jobs, role_keywords, location)
                
                # Try HTML link extraction
                jobs = extract_job_links(page["html"], url, company_slug)
                if jobs:
                    return filter_jobs(jobs, role_keywords, location)
        except Exception:
            continue
    
    return []  # Company has no discoverable career page
```

---

## 6. Phase 2: Experience & Quality Filtering

### 6.1 Experience Extraction from JD

```python
# Regex patterns to extract experience requirements
EXPERIENCE_PATTERNS = [
    r'(\d+)[\s\-]+(?:to|[-])\s*(\d+)\s*(?:\+\s*)?years?',
    r'(\d+)\s*(?:\+\s*)?years?\s*(?:of\s+)?(?:experience|exp)',
    r'minimum\s*(?:of\s*)?(\d+)\s*years?',
    r'at\s*least\s*(\d+)\s*years?',
    r'senior.*?(\d+)\s*years?',
    r'junior.*?(\d+)\s*years?',
    r'experience.*?:\s*(\d+)',
]

# Also check for level indicators
LEVEL_INDICATORS = {
    "intern": 0,
    "trainee": 0,
    "fresher": 0,
    "junior": 1,
    "mid-level": 3,
    "senior": 5,
    "lead": 7,
    "principal": 10,
    "staff": 10,
    "director": 12,
    "vp": 15,
    "cto": 15,
}
```

### 6.2 Filtering Rules

```python
def should_include_job(job: dict, user_profile: dict) -> tuple[bool, str]:
    """Determine if a job should be included based on experience and quality."""
    
    user_experience = parse_experience(user_profile.get("relevant_experience", "0"))
    jd_text = job.get("jd_text", "")
    
    # Rule 1: Extract experience from JD
    required_exp = extract_experience(jd_text)
    
    # Rule 2: If no experience mentioned, include (permissive)
    if required_exp is None:
        return True, "no_experience_specified"
    
    # Rule 3: If experience requirement <= user's experience, include
    if required_exp <= user_experience:
        return True, f"experience_match ({required_exp}y <= {user_experience}y)"
    
    # Rule 4: If experience requirement > user's experience, exclude
    return False, f"experience_mismatch ({required_exp}y > {user_experience}y)"
```

### 6.3 Freshness Check

```python
def is_job_fresh(job: dict, max_age_days: int = 14) -> bool:
    """Check if a job posting is still fresh."""
    
    # Check validThrough from JSON-LD
    if job.get("valid_through"):
        if datetime.fromisoformat(job["valid_through"]) < datetime.now():
            return False  # Expired
    
    # Check datePosted
    if job.get("date_posted"):
        posted = datetime.fromisoformat(job["date_posted"])
        if (datetime.now() - posted).days > max_age_days:
            return False  # Too old
    
    # Check HTTP status of apply URL
    if job.get("apply_url"):
        try:
            resp = requests.head(job["apply_url"], timeout=5)
            if resp.status_code == 404:
                return False  # Dead link
        except:
            pass
    
    return True
```

---

## 7. Phase 3: Batch LLM Relevancy Scoring

### 7.1 Batch Scoring (3-5 jobs per LLM call)

```python
BATCH_SCORING_PROMPT = """You are an expert job-matching AI. Score each job against the candidate profile.

Candidate:
- Name: {name}
- Target Role: {target_role}
- Experience: {experience} years
- Skills: {skills}
- Expected CTC: {expected_ctc}

Jobs to score:
{jobs_block}

For EACH job, return:
- match_score: 0.0-1.0 (how well it matches)
- experience_match: true/false
- skills_match: percentage of matching skills
- reason: 1-sentence explanation

Return JSON array of objects, one per job:
[{"match_score": 0.85, "experience_match": true, "skills_match": 0.7, "reason": "..."}]

Return valid JSON only."""
```

### 7.2 Scoring Criteria

| Factor | Weight | How to Score |
|--------|--------|-------------|
| Role alignment | 30% | Title contains target role keywords |
| Skills overlap | 25% | JD skills vs candidate skills |
| Experience match | 20% | Required exp <= candidate exp |
| Location match | 15% | Target city or remote |
| CTC alignment | 10% | If mentioned, within range |

---

## 8. Phase 4: Applications Tab — Apply-on-Click Flow

### 8.1 Current Flow (BROKEN)

```
Discovery → Validation (LLM) → Tailoring (LLM) → PDF Generation → 
→ Contact Search (LLM) → Email Draft (LLM) → Browser Agent
```

**Problem:** All of this runs automatically before the user even sees the job.

### 8.2 New Flow (CORRECT)

```
Discovery → Experience Filter → Batch LLM Scoring → Display in UI
                                                          ↓
                                              User clicks "Apply"
                                                          ↓
                              ┌─────────────────────────────────────────┐
                              │  1. Generate tailored resume PDF        │
                              │  2. Find company email (multi-method)   │
                              │  3. Draft outreach email                │
                              │  4. Launch browser agent (if needed)    │
                              └─────────────────────────────────────────┘
```

### 8.3 UI State Machine

```
Job Card States:
  discovered → scored → user_reviewing → applying → applied/needs_attention/failed
  
Only when state = "user_reviewing" and user clicks Apply:
  → state = "applying"
  → Run: validator_tailor → contact_finder → email_drafter → browser_agent
  → state = "applied" or "needs_attention"
```

### 8.4 Database Schema Changes

```sql
-- Add columns to jobs table
ALTER TABLE jobs ADD COLUMN experience_required REAL;
ALTER TABLE jobs ADD COLUMN experience_matched BOOLEAN DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN is_fresh BOOLEAN DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN date_posted TEXT;
ALTER TABLE jobs ADD COLUMN valid_through TEXT;
ALTER TABLE jobs ADD COLUMN ats_source TEXT;
ALTER TABLE jobs ADD COLUMN company_domain TEXT;

-- Track what's been generated on-demand
ALTER TABLE jobs ADD COLUMN pdf_generated BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN email_drafted BOOLEAN DEFAULT FALSE;
ALTER TABLE jobs ADD COLUMN contact_found BOOLEAN DEFAULT FALSE;
```

---

## 9. Phase 5: Email Finding — Multi-Method Approach

### 9.1 Method Priority (Waterfall)

| Priority | Method | Reliability | Cost | Speed |
|----------|--------|------------|------|-------|
| 1 | ATS apply page email | ★★★★★ | Free | Fast |
| 2 | Company contact page scraping | ★★★★☆ | Free | Fast |
| 3 | Email permutation + MX verify | ★★★★☆ | Free | Fast |
| 4 | Google dorking for emails | ★★★☆☆ | Free | Medium |
| 5 | GitHub commit email extraction | ★★☆☆☆ | Free | Medium |
| 6 | LinkedIn profile email | ★★★☆☆ | Free | Slow |
| 7 | WHOIS/RDAP lookup | ★☆☆☆☆ | Free | Fast |
| 8 | Social media bio extraction | ★★☆☆☆ | Free | Medium |

### 9.2 Implementation: Enhanced `contact_finder.py`

```python
async def find_company_email(company: str, role: str, domain: str = "") -> dict:
    """Multi-method email finding waterfall."""
    
    results = {
        "contacts": [],
        "email_guesses": [],
        "company_domain": domain,
        "method_used": "",
    }
    
    # Method 1: Check ATS apply page for recruiter email
    ats_email = await extract_ats_recruiter_email(company)
    if ats_email:
        results["email_guesses"].append(ats_email)
        results["method_used"] = "ats_page"
        return results
    
    # Method 2: Scrape company contact/about page
    contact_page_emails = await scrape_contact_page(domain)
    if contact_page_emails:
        results["email_guesses"].extend(contact_page_emails)
        results["method_used"] = "contact_page"
    
    # Method 3: Email permutation + MX verification
    if not results["email_guesses"]:
        # Find a contact name first
        contact = await find_hiring_contact(company, role)
        if contact:
            permutations = generate_email_permutations(
                contact["name"].split()[0],
                contact["name"].split()[-1] if len(contact["name"].split()) > 1 else "",
                domain
            )
            verified = await verify_emails_with_smtp(permutations)
            results["email_guesses"].extend(verified)
            results["contacts"].append(contact)
            results["method_used"] = "permutation"
    
    # Method 4: Google dorking
    if not results["email_guesses"]:
        dork_emails = await google_dork_for_emails(company, domain)
        if dork_emails:
            results["email_guesses"].extend(dork_emails)
            results["method_used"] = "google_dork"
    
    # Method 5: GitHub commit emails
    if not results["email_guesses"]:
        gh_emails = await extract_github_emails(company)
        if gh_emails:
            results["email_guesses"].extend(gh_emails)
            results["method_used"] = "github"
    
    return results
```

### 9.3 SMTP Email Verification

```python
async def verify_email_smtp(email: str) -> bool:
    """Verify if an email exists via SMTP handshake (no email sent)."""
    import smtplib
    import dns.resolver
    
    domain = email.split("@")[1]
    
    # Step 1: Check MX records
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(mx_records[0].exchange).rstrip(".")
    except:
        return False
    
    # Step 2: SMTP handshake
    try:
        with smtplib.SMTP(mx_host, 25, timeout=10) as smtp:
            smtp.helo("verify.local")
            smtp.mail("verify@verify.local")
            code, _ = smtp.rcpt(email)
            return code == 250
    except:
        return False
```

### 9.4 Google Dork Patterns for Email Discovery

```python
EMAIL_DORK_PATTERNS = [
    '"@" + "{domain}" site:linkedin.com',
    '"@" + "{domain}" filetype:pdf',
    '"@" + "{domain}" filetype:docx',
    'site:{domain} "contact" OR "email" OR "reach us"',
    '"{company}" "email" "recruiter" site:linkedin.com',
    '"{company}" "{role}" "email me" OR "send resume"',
    'site:github.com "@{domain}"',
    '"{company}" "press" email site:prnewswire.com OR site:businesswire.com',
]
```

### 9.5 GitHub Commit Email Extraction

```python
async def extract_github_emails(company: str) -> list[dict]:
    """Extract emails from GitHub organization member commits."""
    
    # Step 1: Find company's GitHub org
    org_url = f"https://api.github.com/orgs/{company_slug}"
    org_data = await fetch_json(org_url)
    if not org_data:
        return []
    
    # Step 2: Get recent commits from public repos
    repos_url = f"https://api.github.com/orgs/{company_slug}/repos?sort=updated&per_page=5"
    repos = await fetch_json(repos_url)
    
    emails = []
    for repo in (repos or []):
        commits_url = f"https://api.github.com/repos/{company_slug}/{repo['name']}/commits?per_page=5"
        commits = await fetch_json(commits_url)
        for commit in (commits or []):
            author = commit.get("commit", {}).get("author", {})
            email = author.get("email", "")
            name = author.get("name", "")
            if email and email != f"noreply@github.com" and company_slug.lower() in email:
                emails.append({"email": email, "name": name, "source": "github"})
    
    return emails[:5]  # Limit
```

### 9.6 Contact Page URL Patterns

```python
CONTACT_PAGE_PATTERNS = [
    "https://{domain}/contact",
    "https://{domain}/contact-us",
    "https://{domain}/get-in-touch",
    "https://{domain}/about",
    "https://{domain}/about/team",
    "https://{domain}/about/leadership",
    "https://{domain}/team",
    "https://{domain}/people",
    "https://{domain}/our-team",
]
```

---

## 10. Phase 6: LinkedIn Filtering & Exclusion Rules

### 10.1 LinkedIn Quality Filters

```python
def is_linkedin_low_quality(job: dict) -> tuple[bool, str]:
    """Check if a LinkedIn job posting is low quality."""
    
    # Rule 1: Easy Apply (high volume, low signal)
    if job.get("is_easy_apply"):
        return True, "easy_apply"
    
    # Rule 2: Too many applicants (>100)
    applicant_count = parse_applicant_count(job.get("applicant_count_text", ""))
    if applicant_count and applicant_count > 100:
        return True, f"too_many_applicants ({applicant_count})"
    
    # Rule 3: Promoted listing (usually spam)
    if job.get("is_promoted"):
        return True, "promoted_listing"
    
    # Rule 4: Staffing agency
    STAFFING_KEYWORDS = [
        "staffing", "recruiting", "talent agency", "consulting group",
        "manpower", "randstad", "adecco", "teamlease", "quess",
    ]
    company_lower = job.get("company", "").lower()
    if any(kw in company_lower for kw in STAFFING_KEYWORDS):
        return True, "staffing_agency"
    
    # Rule 5: Too old (>14 days)
    if job.get("posted_at"):
        try:
            posted = datetime.fromisoformat(job["posted_at"])
            if (datetime.now() - posted).days > 14:
                return True, "stale_posting"
        except:
            pass
    
    return False, "quality_ok"
```

### 10.2 LinkedIn URL Parameters for Filtering

```
# Best practice URL to avoid noise:
https://www.linkedin.com/jobs/search/
  ?keywords={role}
  &location={location}
  &f_TPR=r604800      # Past week only
  &f_RJ=0             # Remove reposts
  &f_JT=F             # Full-time only
  &f_AL=false         # Exclude Easy Apply (if parameter available)
  &sortBy=DD          # Most recent first
```

### 10.3 LinkedIn JSON-LD Fields Available

| Field | Use |
|-------|-----|
| `validThrough` | Detect expired postings |
| `datePosted` | Calculate age |
| `employmentType` | Filter by job type |
| `jobLocation` | Location matching |
| `baseSalary` | CTC filtering |
| `totalJobOpenings` | Multiple positions = higher priority |
| `directApply` | True = direct apply (not Easy Apply) |

---

## 11. Phase 7: Third-Party ATS Exclusion List

### 11.1 Domains to EXCLUDE (Never Scrape)

```python
EXCLUDED_DOMAINS = {
    # Job aggregators (useless — just repostings)
    "linkedin.com",           # Easy Apply spam, 100+ applicants
    "indeed.com",             # Aggregator, expired posts
    "glassdoor.com",          # Aggregator, salary bait
    "naukri.com",             # Indian aggregator, volume spam
    "monster.com",            # Aggregator
    "internshala.com",        # Student-focused, low quality
    "ambitionbox.com",        # Aggregator
    "jooble.org",             # Aggregator
    "ziprecruiter.com",       # Aggregator
    "simplyhired.com",        # Aggregator
    "careerjet.com",          # Aggregator
    "talent.com",             # Aggregator
    "jobrapido.com",          # Aggregator
    "adzuna.com",             # Aggregator
    "jora.com",               # Aggregator
    "foundit.in",             # Aggregator
    "shine.com",              # Aggregator
    "timesjobs.com",          # Aggregator
    "cutshort.io",            # Aggregator
    "instahyre.com",          # Third-party platform
    "hirect.in",              # Third-party platform
    "apna.co",                # Third-party platform
    "wellfound.com",          # Third-party platform (AngelList)
    
    # Third-party ATS platforms (NOT direct company pages)
    "greenhouse.io",          # Third-party ATS (but we use their API)
    "lever.co",               # Third-party ATS (but we use their API)
    "ashbyhq.com",            # Third-party ATS (but we use their API)
    "smartrecruiters.com",    # Third-party ATS (but we use their API)
    "bamboohr.com",           # Third-party ATS
    "recruitee.com",          # Third-party ATS
    "breezy.hr",              # Third-party ATS
    "workable.com",           # Third-party ATS
    "jobvite.com",            # Third-party ATS
    "icims.com",              # Third-party ATS
    "myworkdayjobs.com",      # Third-party ATS (Workday)
    
    # Staffing agencies
    "randstad.com",
    "adecco.com",
    "manpowergroup.com",
    "teamlease.com",
    "quess.in",
    "collabera.com",
}
```

### 11.2 Exception: ATS APIs Are OK

We EXCLUDE these domains from **web scraping** but still use their **public APIs**:
- Greenhouse API: `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- Lever API: `api.lever.co/v0/postings/{slug}?mode=json`
- Ashby API: `api.ashbyhq.com/posting-api/job-board/{slug}`
- Freshteam API: `{slug}.freshteam.com/jobs.json`

The difference: APIs return structured, fresh data. Web scraping returns random indexed pages.

---

## 12. Implementation Plan — File-by-File Changes

### 12.1 NEW FILES

#### `vellum/agents/career_scraper.py` (NEW — ~300 lines)
```python
"""
Career Page Scraper — Direct company career page discovery
For each company in our list → try ATS APIs → try career page URLs → extract jobs
"""
```

**Responsibilities:**
- Iterate through company list for user's location
- Try ATS APIs in priority order
- Try career page URL patterns
- Extract JSON-LD structured data
- Extract job links from HTML
- Return structured job listings

#### `vellum/tools/career_urls.py` (NEW — ~100 lines)
```python
"""
Career page URL pattern database
Maps company slugs to known career page URLs
"""
```

**Responsibilities:**
- Store career page URL patterns
- Store ATS detection patterns
- Provide fallback URL generation

### 12.2 MODIFIED FILES

#### `vellum/agents/geo_search.py` (MODIFY — Major Rewrite)
**Changes:**
- Remove Channels 2, 3, 4 (DuckDuckGo-based search)
- Keep Channels 0, 0.5 (direct ATS APIs)
- Add new Channel: systematic career page scraping
- Add experience pre-filtering
- Add freshness pre-filtering

**New flow:**
```python
async def run(state: dict) -> dict:
    """Agent A: Systematic career page discovery."""
    
    location = state.get("location", "Bengaluru")
    profile = state.get("profile", {})
    role = state.get("role") or "software engineer"
    user_experience = parse_experience(profile.get("relevant_experience", "0"))
    
    # Get company list for this location
    company_list = TECH_HUB_STARTUPS.get(_normalise_city(location), [])
    
    jobs = []
    for company_slug in company_list:
        # Try ATS APIs
        ats_jobs = await try_all_ats_apis(company_slug, role, location)
        
        # Try career page URLs
        if not ats_jobs:
            career_jobs = await try_career_pages(company_slug, role, location)
            ats_jobs = career_jobs
        
        # Filter by experience
        for job in ats_jobs:
            included, reason = should_include_job(job, profile)
            if included:
                jobs.append(job)
        
        # Limit to avoid too many LLM calls
        if len(jobs) >= 50:
            break
    
    # Batch LLM scoring
    scored_jobs = await batch_score_jobs(jobs, profile, location)
    
    # Store in DB
    for job in scored_jobs:
        await db.insert_job(job)
    
    return {"discovered_jobs": scored_jobs}
```

#### `vellum/agents/job_evaluator.py` (MODIFY — Minor Changes)
**Changes:**
- Add experience extraction from JD text
- Add freshness scoring
- Keep batch LLM evaluation (already good)

#### `vellum/agents/validator_tailor.py` (MODIFY — Critical Change)
**Changes:**
- DO NOT run during discovery phase
- ONLY run when user clicks Apply
- Move PDF generation to a separate function called on Apply

```python
# BEFORE (runs during discovery):
async def run(state: dict) -> dict:
    # freshness check → validation → tailoring → PDF generation
    
# AFTER (runs only on Apply click):
async def run_on_apply(state: dict) -> dict:
    # Only runs when user clicks Apply
    # freshness check → validation → tailoring → PDF generation
```

#### `vellum/agents/contact_finder.py` (MODIFY — Major Enhancement)
**Changes:**
- Add multi-method email finding waterfall
- Add SMTP email verification
- Add Google dorking for emails
- Add GitHub commit email extraction
- Add contact page scraping

#### `vellum/agents/graph.py` (MODIFY — Flow Restructure)
**Changes:**
- New discovery flow: scrape → filter → score → display
- Apply-on-click: validate → contact → email → browser
- Remove auto-validation during discovery

```python
# New graph structure:
def build_discovery_graph():
    """Discovery: scrape → filter → score → display"""
    graph = StateGraph(DiscoveryState)
    graph.add_node("scrape", career_scraper.run)
    graph.add_node("filter", experience_filter.run)
    graph.add_node("score", batch_scorer.run)
    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "filter")
    graph.add_edge("filter", "score")
    graph.add_edge("score", END)
    return graph.compile()

def build_apply_pipeline():
    """Apply: validate → contact → email → browser"""
    graph = StateGraph(JobPipelineState)
    graph.add_node("validate_tailor", validator_tailor.run)
    graph.add_node("find_contacts", contact_finder.run)
    graph.add_node("draft_email", email_drafter.run)
    graph.add_node("browse_apply", browser_agent.run)
    graph.set_entry_point("validate_tailor")
    graph.add_edge("validate_tailor", "find_contacts")
    graph.add_edge("find_contacts", "draft_email")
    graph.add_edge("draft_email", "browse_apply")
    graph.add_edge("browse_apply", END)
    return graph.compile()
```

#### `vellum/tools/search.py` (MODIFY — Remove DDGS Job Search)
**Changes:**
- Remove `search_direct_ats_jobs()` (uses DDGS, unreliable)
- Remove `search_wellfound_instahyre_jobs()` (third-party platforms)
- Keep `search_contacts()` (for contact finding)
- Keep `verify_email_mx()` (for email verification)
- Keep `score_career_url()` (for URL quality scoring)

#### `vellum/tools/ats_api.py` (KEEP — No Changes)
**Status:** Already well-implemented. All 5 ATS adapters work correctly.

#### `vellum/tools/email_handoff.py` (MODIFY — Add SMTP Verification)
**Changes:**
- Add SMTP email verification function
- Add catch-all domain detection
- Enhance email permutation patterns

### 12.3 API Changes

#### `vellum/api/routes.py` (MODIFY)
**Changes:**
- Add `/api/jobs/{job_id}/apply` endpoint (triggers full pipeline)
- Modify `/api/search` to use new discovery flow
- Add `/api/jobs/{job_id}/generate-pdf` endpoint (on-demand PDF)

```python
@router.post("/api/jobs/{job_id}/apply")
async def apply_to_job(job_id: str):
    """User clicked Apply — trigger full pipeline."""
    result = await graph.run_single_job_apply(job_id)
    return result

@router.post("/api/jobs/{job_id}/generate-pdf")
async def generate_resume_pdf(job_id: str):
    """Generate tailored resume PDF on demand."""
    job = await db.get_job(job_id)
    profile = await db.get_latest_profile()
    pdf_bytes = await validator_tailor.generate_tailored_pdf(job, profile)
    return Response(content=pdf_bytes, media_type="application/pdf")
```

#### `vellum/api/ws.py` (MODIFY)
**Changes:**
- Add WebSocket events for Apply status updates
- Add progress events for email finding

---

## 13. Edge Cases & Scenarios

### 13.1 Company Has No Career Page
**Scenario:** Small startup with no website or ATS  
**Solution:** Skip company, log warning, continue to next

### 13.2 Company Uses Uncommon ATS
**Scenario:** ATS not in our adapter list (e.g., Breezy, Recruitee)  
**Solution:** Try career page URL patterns → HTML link extraction → JSON-LD extraction

### 13.3 All Jobs at Company Are Expired
**Scenario:** Company has career page but no current openings  
**Solution:** Skip company, log "no_current_openings", continue

### 13.4 JD Has No Experience Mentioned
**Scenario:** Job posting doesn't specify years of experience  
**Solution:** Include job (permissive), let LLM scoring determine fit

### 13.5 JD Has Ambiguous Experience
**Scenario:** "3-5 years" or "senior level" without number  
**Solution:** Parse level indicators (senior=5yr), include if within range

### 13.6 Company Domain Can't Be Found
**Scenario:** Can't determine company website for email permutation  
**Solution:** Generate likely domain (`{slug}.com`), try MX check, fallback to "apply only"

### 13.7 Email Verification Returns Catch-All
**Scenario:** Company domain accepts any email (catch-all)  
**Solution:** Include email guesses with warning "catch-all domain, unverified"

### 13.8 Browser Agent Hits CAPTCHA
**Scenario:** ATS website has Cloudflare protection  
**Solution:** Pause browser, show HITL intervention card, user solves manually

### 13.9 Multiple Roles at Same Company
**Scenario:** Company has 10 openings matching the role  
**Solution:** Show all, but prioritize by match score. User can Apply to multiple.

### 13.10 User Location Doesn't Match Any Company
**Scenario:** User searches for "Mysore" but no companies in list  
**Solution:** Show "no_companies_found" message, suggest nearby cities

### 13.11 Rate Limiting from ATS APIs
**Scenario:** Too many requests to Greenhouse/Lever  
**Solution:** Implement 1-second delay between requests, respect robots.txt

### 13.12 LinkedIn Jobs Mixed with Direct Applications
**Scenario:** Some jobs are LinkedIn Easy Apply, others are direct  
**Solution:** Mark source clearly, filter out Easy Apply, prioritize direct applications

### 13.13 User Profile Has Zero Experience
**Scenario:** Fresh graduate with no work experience  
**Solution:** Include jobs requiring 0-2 years, exclude senior/staff roles

### 13.14 Company Uses Multiple ATS Platforms
**Scenario:** Different departments use different ATS  
**Solution:** Try all ATS adapters, deduplicate by job title + location

### 13.15 Job Posting in Different Language
**Scenario:** JD is in Hindi, Tamil, or other non-English language  
**Solution:** Skip non-English postings, log "non_english_jd"

---

## 14. Research Findings Summary

### 14.1 ATS API Endpoints (Verified Working)

| ATS | Endpoint | Auth | Content |
|-----|----------|------|---------|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | None | Full JD HTML inline |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json` | None | Full JD plain text |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | None | Full JD HTML |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings` | None* | Full JD |
| Freshteam | `{slug}.freshteam.com/jobs.json` | None | Full JD HTML |

### 14.2 Email Finding Methods (Ranked by Reliability)

| Method | Reliability | Cost | Notes |
|--------|------------|------|-------|
| ATS apply page email | ★★★★★ | Free | Often shows recruiter email |
| Contact page scraping | ★★★★☆ | Free | `careers@`, `hr@` common |
| Email permutation + MX | ★★★★☆ | Free | Need contact name first |
| Google dorking | ★★★☆☆ | Free | Public indexed emails |
| GitHub commits | ★★☆☆☆ | Free | Developers only |
| LinkedIn profile | ★★★☆☆ | Free | Contact Info section |
| WHOIS/RDAP | ★☆☆☆☆ | Free | Post-GDPR, mostly redacted |
| Social media bio | ★★☆☆☆ | Free | Business accounts only |

### 14.3 LinkedIn Filtering Parameters

| Parameter | Purpose | Value |
|-----------|---------|-------|
| `f_TPR` | Time posted | `r604800` (past week) |
| `f_RJ` | Remove reposts | `0` |
| `f_JT` | Job type | `F` (full-time) |
| `f_AL` | Easy Apply | `true` to include, post-filter to exclude |
| `sortBy` | Sort order | `DD` (most recent) |

### 14.4 JSON-LD `validThrough` for Expiry Detection

Most major ATS platforms embed `validThrough` in their job posting JSON-LD. If this date is in the past, the job is expired. This is the most reliable way to detect expired postings without HTTP checks.

### 14.5 SMTP Verification Limitations

- **Catch-all domains** (15-28% of B2B domains) accept any address — SMTP always returns 250
- Some servers block port 25 or rate-limit SMTP queries
- IP reputation matters — residential IPs may get blocked
- **Best practice:** Combine SMTP verification with catch-all detection

---

## Appendix A: Company List Usage

The `TECH_HUB_STARTUPS` dictionary in `ats_api.py` contains 4000+ company slugs across 35+ Indian cities. This is the primary data source for discovery. Instead of searching the internet randomly, we iterate through this list and check each company's career page directly.

**Current usage:** `fetch_hub_ats_jobs()` randomly samples 30 companies and tries ATS APIs.  
**New usage:** Iterate through ALL companies in the user's target city, try all ATS adapters, then try career page URLs.

## Appendix B: LLM Token Budget

| Operation | Tokens per Call | Calls per Job | Total per Job |
|-----------|----------------|---------------|---------------|
| Batch scoring (5 jobs) | ~2000 | 1 | ~400 (amortized) |
| Validation | ~1500 | 1 | ~1500 |
| Summary tailoring | ~1000 | 1 | ~1000 |
| Bullet tailoring | ~1500 | 2 | ~3000 |
| Contact extraction | ~1000 | 1 | ~1000 |
| Email drafting | ~1500 | 1 | ~1500 |
| **Total per applied job** | | | **~8,400** |

**For 50 discovered jobs, 10 applied:** ~84,000 tokens total (well within free tier limits)

## Appendix C: Testing Strategy

1. **Unit tests:** Test each ATS adapter with known company slugs
2. **Integration tests:** Test full discovery → scoring pipeline
3. **Manual testing:** Verify email finding with 10 real companies
4. **Edge case testing:** Test with companies that have no career page, expired jobs, catch-all domains

---

*This document is the complete analysis and implementation plan. All changes should be implemented in the order specified in Section 12.*
