# JobHunterX API (v2 contract)

All endpoints live under `/api`. JSON in, JSON out. Timestamps are ISO-8601 UTC.

## Error format

Every non-2xx response has this body:

```json
{ "error": { "code": "not_found", "message": "Job not found", "details": null } }
```

Codes: `bad_request` (400), `forbidden` (403 — cross-site write blocked), `not_found` (404), `conflict` (409), `validation_error` (422),
`payload_too_large` (413), `upstream_error` (502), `internal_error` (500).

---

## Profile

The candidate profile is a first-class object. `snapshot` is derived from it
deterministically by the server (never edited by the client).

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/profile` | – | `ProfileEnvelope` (profile/snapshot may be `null`) |
| PUT | `/api/profile` | `CandidateProfile` | `ProfileEnvelope` |
| POST | `/api/profile/upload` | multipart `file` (PDF ≤ 10 MB) | `ProfileEnvelope & { extraction: { status: "ok"\|"partial"\|"failed", warnings: string[] } }` |

```ts
type ProfileEnvelope = { profile: CandidateProfile | null; snapshot: CandidateSnapshot | null; profile_hash: string | null };

type CandidateProfile = {
  name, email, phone, location, present_address, permanent_address,
  linkedin, github, portfolio, summary, suggested_role, relevant_experience: string;
  languages, skills, certifications, competitions, achievements: string[];
  experience: { role, company, location, start, end, employment_type: string; bullets: string[] }[];
  education: { degree, institution, start, end, grade, details: string }[];
  projects: { title, description, url: string; technologies: string[] }[];
  qa_memory: { expected_salary, current_ctc, expected_ctc, notice_period, work_authorization,
               requires_sponsorship, preferred_work_mode, willing_to_relocate, years_of_experience: string;
               custom_answers: Record<string,string> };
  preferences: {
    target_roles: string[]; locations: string[];
    work_modes: ("remote"|"hybrid"|"onsite")[];
    willing_to_relocate: boolean; open_to_international: boolean; home_country: string;
    min_annual_salary: number|null; salary_currency: string;   // e.g. 1200000, "INR"
    notice_period_days: number|null; employment_types: string[];
    excluded_companies: string[]; career_direction: string;
    years_experience_override: number|null;
    seniority_override: Seniority|null;
  };
};

type Seniority = "intern"|"entry"|"junior"|"mid"|"senior"|"staff"|"principal"|"unknown";

type CandidateSnapshot = {
  profile_hash: string;
  total_years: number; professional_years: number;
  years_source: "dates"|"override"|"stated"|"unknown";
  seniority: Seniority;
  role_families: { label: string; closeness: number; evidence: string }[];   // AI-derived career tracks, closeness 0–1
  target_titles: string[]; adjacent_titles: string[];
  skills: { name: string; key: string; aliases: string[]; adjacent: string[]; sources: string[]; strength: number }[];
  domains: string[];
  education_level: "none"|"diploma"|"bachelor"|"master"|"phd"|"unknown";
  locations: { city: string; region: string; country: string; aliases: string[] }[];
  home_country: string; work_modes: string[];
  open_to_international: boolean; willing_to_relocate: boolean;
  min_annual_salary: number|null; salary_currency: string; notice_period_days: number|null;
  employment_types: string[]; excluded_companies: string[]; career_direction: string;
  method: "llm"|"fallback"; llm_model: string;   // fallback = AI unavailable, lower confidence
  notes: string[];                   // how values were derived, shown in UI
};
```

Nothing in the product uses fixed lists of skills, titles or cities: role families, titles and
location names all come from the AI understanding of the candidate's own profile.
`GET /api/meta` returns `{ tracking_statuses: string[] }`.


---

## Searches (job discovery runs)

Only one run is active at a time. Starting a new run cancels the previous one.
Every job and every WebSocket event carries the `run_id` that produced it —
clients must ignore events whose `run_id` is not the run they are showing.

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/searches` | `SearchRequest` | `202 { run: SearchRun }` |
| GET | `/api/searches/current` | – | `{ run: SearchRun \| null }` (latest run, any status) |
| GET | `/api/searches/{id}` | – | `{ run: SearchRun }` |
| POST | `/api/searches/{id}/cancel` | – | `{ run: SearchRun }` |

```ts
type SearchRequest = {
  locations?: string[];          // overrides profile preferences for this run
  work_modes?: ("remote"|"hybrid"|"onsite")[];
  role_focus?: string[];         // role family keys or free-text titles
  include_international?: boolean;
  max_jobs?: number;             // default 60
};

type SearchRun = {
  id: string;
  status: "queued"|"running"|"completed"|"failed"|"cancelled";
  started_at: string; finished_at: string|null;
  stage: string;                 // key of current stage
  stages: { key: string; label: string; status: "pending"|"running"|"done"|"skipped"|"failed"; detail: string }[];
  counts: { queries: number; search_results: number; candidates: number; duplicates: number;
            fetched: number; invalid: number; scored: number; recommended: number; rejected: number };
  plan: { role_families: string[]; titles: string[]; locations: string[]; queries: string[] } | null;
  error: string|null;
  profile_hash: string;
  mode: "search"|"watch";        // "watch" = background watchlist check (see Watchlist)
  progress: RunProgress|null;    // real counts of the running stage
};

type RunProgress = {
  stage: string;                 // stage key the counts belong to (analysis reports as "match")
  done: number; total: number;   // real units: searches run, boards checked, pages read, AI reads + scores
  label: string;                 // e.g. "Company job boards: 21 of 33 checked"
};
```

Stage keys, in order: `understand`, `plan`, `discover`, `normalize`, `dedupe`,
`validate`, `extract`, `match`, `rank`.

`SearchRequest` also accepts `mode: "watch"` (used by the watcher): no web search, only the watchlist
companies' boards, only postings not stored before, at most 20 analysed per check.

---

## Setup (first run)

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/setup` | – | `{ llm_ready: boolean, llm_count: number, keys: { google, groq, mistral, tavily, exa, tinyfish, brave: boolean } }` |
| POST | `/api/setup/test-key` | `{ provider, key }` | `{ ok: boolean, message: string }` — AI keys are checked with one free "list models" call; search keys only by format |

Keys are saved with `POST /api/settings` (written to `jobhunterx/.env`). Placeholder values such as
`your_gemini_api_key` count as "no key". `POST /api/profile/upload` answers `400` while no AI key is set.
`GET /api/meta` also returns `setup`.

---

## Watchlist

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/watchlist?scope=mine\|all` | – | `{ cities, covered_cities, total, companies: WatchCompany[], status: WatchStatus }` — `mine` = companies in the active profile's cities (plus remote-India when remote is accepted) |
| POST | `/api/watchlist/check` | – | `202 { status: WatchStatus }` — runs a check now (skipped while a user search is running) |

```ts
type WatchStatus = { interval_hours: number; enabled: boolean; checking: boolean;
                     last: { status, at, run_id?, new_fits?, new_jobs?, companies? } | null };
type WatchCompany = { name; aliases; website; cities; category; what_they_do; ai_work; size; stage; careers_url;
  ats: { kind; token; verified; open_jobs; india_jobs }; hires_early_career: "yes"|"some"|"rare"|"unknown";
  early_career_evidence; role_titles_seen; reviews: { ambitionbox; ambitionbox_reviews; glassdoor; glassdoor_reviews; summary };
  red_flags: string[]; pay_signal; dsa_heavy_interviews; competition: "very_high"|"high"|"medium"|"low";
  verdict: "strong"|"good"|"caution"|"avoid"; why; sources: string[]; researched_on; board_supported: boolean };
```

The watcher runs every `WATCH_INTERVAL_HOURS` (default 4, `0` = off) while the app is open.

---

## Jobs

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/jobs?view=&run_id=&q=&work_mode=&min_score=&sort=&limit=` | – | `{ jobs: JobSummary[], counts: ViewCounts }` |
| GET | `/api/jobs/{id}` | – | `{ job: JobDetail }` |
| PUT | `/api/jobs/{id}/saved` | – | `{ job: JobSummary }` (idempotent) |
| DELETE | `/api/jobs/{id}/saved` | – | `{ job: JobSummary }` (idempotent) |
| PATCH | `/api/jobs/{id}` | `{ tracking_status: TrackingStatus }` | `{ job: JobSummary }` |
| POST | `/api/jobs/{id}/verify` | – | `{ job: JobDetail }` (re-validates live; ≤ ~20 s) |
| POST | `/api/jobs/{id}/rescore` | – | `{ job: JobDetail }` (re-match against current profile) |
| DELETE | `/api/jobs/{id}` | – | `{ ok: true }` |
| DELETE | `/api/jobs?scope=unsaved\|all` | – | `{ deleted: number }` |
| POST | `/api/jobs/{id}/apply` | – | `{ status: "started", session: ApplySession }` — checks the kit (resume, cover letter, CV), writes what is missing, then starts the browser agent; all in the background (409 if already running) |

`view`: `recommended` (default; verdict strong/good/stretch, not closed),
`fresh` (recommended and first seen in the last 48 hours — new watchlist roles land here),
`all`, `rejected` (verdict incompatible or closed/invalid), `saved`, `applied`
(tracking_status in applied/interviewing/offer).
`sort`: `chance` (default; 60 % fit + 40 % reach) | `score` (fit) | `reach` (least crowded first) | `recent`.

```ts
type ViewCounts = { recommended: number; fresh: number; all: number; rejected: number; saved: number; applied: number };

type TrackingStatus = "new"|"saved"|"preparing"|"applied"|"interviewing"|"offer"|"rejected"|"archived";

type JobSummary = {
  id: string; run_id: string|null;
  title: string; company: string;
  location: string; locations: string[]; countries: string[];
  work_mode: "remote"|"hybrid"|"onsite"|"unknown";
  employment_type: string; seniority: Seniority; role_family: string;
  posted_at: string|null; valid_through: string|null; discovered_at: string;
  apply_url: string;
  source: { name: string; kind: string; url: string; first_party: boolean } | null;
  sources_count: number;
  salary: { min: number|null; max: number|null; currency: string; period: string; raw: string } | null;
  validation: { status: "active"|"likely_active"|"unverified"|"stale"|"closed"|"invalid"; confidence: number; checked_at: string|null };
  match: MatchSummary | null;
  reach: { score: number; level: "high"|"medium"|"low"; headline: string;
           application_email: string; company_verdict: string } | null;   // chance a person reads the application
  match_stale: boolean;            // profile changed since scoring
  saved: boolean;
  tracking_status: TrackingStatus;
  pipeline_status: string;         // browser auto-apply status: discovered|applying|applied|apply_failed|needs_attention|...
  documents: { resume: string|null; cover_letter: string|null };   // latest document ids
};

type MatchSummary = {
  score: number;                   // 0–100
  verdict: "strong"|"good"|"stretch"|"weak"|"incompatible";
  headline: string;
  required_matched: number; required_total: number;
  missing_required: string[];      // first few
  experience: { required_min: number|null; required_max: number|null; candidate_years: number; fit: "under"|"within"|"over"|"unknown"; gap_years: number };
  rejected_reasons: string[];
};

type JobDetail = JobSummary & {
  description: string;            // plain text (never HTML)
  requirements: {
    required_skills: string[]; preferred_skills: string[];
    experience_min: number|null; experience_max: number|null; experience_evidence: string;
    education_level: string /* unknown|none|diploma|bachelor|master|phd */; education_mandatory: boolean; education_evidence: string;
    notice_period_max_days: number|null;
    responsibilities: string[]; requirement_lines: string[]; domain_keywords: string[];
    method: "pending"|"llm"|"fallback"; llm_model: string;   // fallback = partial analysis
  };
  validation: ValidationReport;
  match: MatchAssessment | null;
  sources: { name: string; kind: string; url: string; first_party: boolean; confidence: number; fetched_at: string }[];
  document_list: DocumentSummary[];
};

type ValidationReport = {
  status: string; confidence: number; checked_at: string|null; notes: string[];
  checks: Record<string, { status: "verified"|"inferred"|"unverified"|"unknown"|"failed"; value: string|null; evidence: string }>;
  // check keys: url_reachable, ats_confirmed, company, title, location, work_mode,
  //             posted_at, valid_through, employment_type, salary, experience, application_open
};

type MatchAssessment = {
  score: number; verdict: string; headline: string;
  hard_constraints: { key: string; label: string; status: "pass"|"warn"|"fail"|"unknown"; detail: string; hard: boolean }[];
  components: { key: string; label: string; weight: number; score: number; detail: string }[];
  strengths: string[]; gaps: string[]; unknowns: string[];
  matched_required: string[]; missing_required: string[];
  matched_preferred: string[]; missing_preferred: string[];
  experience: MatchSummary["experience"];
  rejected_reasons: string[];
  role_fit: number; role_track: string; method: "llm"|"fallback";
  profile_hash: string; engine_version: string; scored_at: string;
};
```

---

## Documents (Resume / CV / Cover letter)

Resume and CV are different documents with different generation logic:
* **Resume** — job-specific, ≤ 1 page, ATS-friendly; selects and re-orders the
  candidate's most relevant evidence for one job.
* **CV** — comprehensive, not tied to a job; includes all experience,
  projects, education, certifications, achievements; may span several pages.
* **Cover letter** — job-specific, evidence-based.

Generation is synchronous (may take up to ~60 s). The server rejects a second
concurrent generation for the same `(job_id, kind)` with 409.

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/jobs/{id}/documents` | `{ kind: "resume"\|"cover_letter" }` | `{ document: DocumentDetail }` |
| POST | `/api/documents/cv` | `{ focus?: string }` | `{ document: DocumentDetail }` |
| GET | `/api/documents?job_id=&kind=` | – | `{ documents: DocumentSummary[] }` |
| GET | `/api/documents/{id}` | – | `{ document: DocumentDetail }` |
| GET | `/api/documents/{id}/pdf` | – | `application/pdf` (attachment) |
| DELETE | `/api/documents/{id}` | – | `{ ok: true }` |

```ts
type DocumentSummary = {
  id: string; kind: "resume"|"cv"|"cover_letter"; job_id: string|null;
  title: string; focus: string; created_at: string;
  profile_hash: string; stale: boolean;          // profile changed since generation
  page_count: number; has_pdf: boolean; warnings_count: number;
  job: { title: string; company: string } | null;
};

type DocumentDetail = DocumentSummary & {
  content: ResumeContent | CoverLetterContent;
  provenance: {
    used_experience: number[]; used_projects: number[];
    omitted_experience: number[]; omitted_projects: number[];
    rewrites: { section: string; original: string; rewritten: string; accepted: boolean; reason: string }[];
    warnings: string[]; llm_model: string; llm_calls: number;
  };
};

type ResumeContent = {   // used by both resume and cv
  header: { name: string; email: string; phone: string; location: string; links: { label: string; url: string }[] };
  headline: string;                // e.g. target title
  summary: string;
  skills: { category: string; items: string[] }[];
  experience: { role: string; company: string; location: string; start: string; end: string; bullets: string[] }[];
  projects: { title: string; description: string; technologies: string[]; url: string }[];
  education: { degree: string; institution: string; start: string; end: string; grade: string; details: string }[];
  certifications: string[]; achievements: string[]; competitions: string[]; languages: string[];
};

type CoverLetterContent = { greeting: string; paragraphs: string[]; closing: string; signature: string };
```

---

## WebSocket `/ws`

Server → client JSON messages:

```ts
type WsMessage = {
  type: "search.run" | "search.progress" | "search.job" | "search.activity" | "job.updated" | "job.deleted"
      | "document.status" | "profile.updated" | "profile.upload" | "watch.status" | "watch.done" | "log" | "browser" ;
  run_id?: string; job_id?: string;
  message?: string;
  data?: any;
  ts: string;
};
```

* `search.run` — `data: { run: SearchRun }` whenever stage/status/counts change (also final status).
  `run.mode === "watch"` marks a background watchlist check — clients show it separately, not as the user's search.
* `search.progress` — `data: { progress: RunProgress, counts, mode }` each time a real unit of work finishes
  (a web search, a company board, a job page, an AI read, a score). Progress is never estimated from time.
* `search.job` — `data: { job: JobSummary }` a job was added/updated by the run.
* `search.activity` — `data: { item: { id, ts, stage, agent, kind, message, job? } }` one plain-language line
  describing what the pipeline just did (e.g. "AI Engineer at Acme is live and accepting applications").
  `kind` is `work | info | good | warn | reject | done`; `job` is `{ id, title, company, score?, verdict? }`.
  The run object also carries the latest 150 lines as `activity` (for reloads) and `total` (jobs to analyse).
* `job.updated` — `data: { job: JobSummary }` any job change outside a run (save, verify, rescore, apply status).
* `job.deleted` — `data: { ids: string[] }`.
* `document.status` — `data: { job_id, kind, status: "generating"|"ready"|"failed", document_id?, error? }`.
* `profile.updated` — `data: ProfileEnvelope`.
* `log` — `data: { level: "info"|"warn"|"error", source: string }`, `message` — activity feed line.
* `apply.session` — `data: { session: ApplySession }` every time an auto-apply session changes (status, kit, a step).
* `profile.upload` — `data: { upload: { id, status, stage: "received"|"extracting"|"understanding"|"done"|"failed", error } }`.
* `watch.status` — `data: WatchStatus` when a watchlist check starts.
* `watch.done` — `data: { status, at, run_id, new_fits, new_jobs, companies, status_info: WatchStatus }` when it ends.
* `browser` — `data` is a browser-agent event `{ agent, event_type, job_id, message }`; only `hitl_request` is sent now.

`/ws/browser`: the live view of the agent's browser. Server → client: `{type:"frame", data:<base64 jpeg>, w, h}` and
`{type:"idle"}` when the browser closes. Client → server (accepted only while the user has control or the agent is not
running): `{type:"mouse", action:"click"|"dblclick"|"move", fx, fy, button}`, `{type:"wheel", fx, fy, deltaX, deltaY}`,
`{type:"keyboard", action:"keyDown", key}`, `{type:"paste", text}` — `fx`/`fy` are 0–1 positions on the frame.

---

## Auto-apply

```ts
ApplySession {
  job_id: string; company: string; role: string; apply_url: string; person_id: string | null;
  status: "preparing"|"launching"|"running"|"paused"|"stopping"|"stopped"|"needs_you"|"applied"|"failed"|"closed";
  message: string; notice: string; result: string;
  control: "agent" | "you";        // who drives the browser right now
  live: boolean;                   // a browser is open and streaming
  url: string; title: string;      // last page
  kit: { [kind in "resume"|"cover_letter"|"cv"]?: { label, status: "checking"|"generating"|"found"|"made"|"skipped"|"failed", pages, doc_id, note } };
  steps: { n, ts, goal, actions: string[], status: "running"|"done"|"failed"|"stopped", url, repeat, note? }[];
  runs: number; started_at: string; updated_at: string;
}
```

| Method | Path | Response |
|---|---|---|
| GET | `/api/apply/current` | `{ session: ApplySession \| null }` — the live session, else the last saved one for the active profile |
| POST | `/api/apply/{job_id}/stop` | Stops immediately; browser stays open; steps saved → `{ session }` |
| POST | `/api/apply/{job_id}/take-over` | Pauses the agent, you drive → `{ session }` |
| POST | `/api/apply/{job_id}/release` | Gives control back to the agent → `{ session }` |
| POST | `/api/apply/{job_id}/continue` | Continues from the last page (reuses the open browser when there is one) → `{ status, session }` |
| POST | `/api/apply/{job_id}/close` | Closes the browser → `{ session }` |
| POST | `/api/apply/{job_id}/done` | You submitted it yourself; marks the job applied → `{ session }` |

Sessions are stored in the `apply_sessions` table; on restart, running ones become `stopped` so they can be continued.

---

## System (unchanged semantics)

`GET /api/meta`, `GET /api/status`, `GET|POST /api/settings`, `GET|POST /api/models`,
`GET /api/usage`, `GET|POST /api/pipeline-mode?mode=`, `POST /api/reset`,
`GET /api/interventions`, `POST /api/interventions/{id}/resolve`, `POST /api/interventions/{job_id}/focus`,
`GET /api/screenshots/{job_id}`. Older aliases still work: `POST /api/resume-agent {job_id, action}` (= continue / skip),
`POST /api/stop-browser` (= stop), `POST /api/browser/takeover?job_id=`, `POST /api/browser/release?job_id=`.


## Additions (profiles, providers, health)

| Method & path | Purpose |
|---|---|
| `POST /api/profile/upload?background=1` | Start reading a resume; returns `{upload}` at once. Progress arrives as `profile.upload` events (`stage`: extracting → understanding → done / failed). |
| `GET /api/profile/upload/{id}` | Upload status + result (polling fallback / after reconnect). |
| `GET /api/people` | `{people: [{id, name, headline, location, jobs, saved, has_profile, last_used_at}], active}` |
| `POST /api/people` `{name}` | Create a profile and make it active (cancels a running search). |
| `POST /api/people/{id}/activate` | Switch the active profile. Emits `people.changed`. |
| `PATCH /api/people/{id}` `{name}` / `DELETE /api/people/{id}` | Rename / delete a profile and everything it owns. |
| `GET /api/settings` | Masked keys with `*_source` (".env file" / "system environment"), provider switches, search order & strategy, tunables. |
| `POST /api/settings` | Keys, flags and `tunables` (written back to `.env`). |
| `POST /api/providers` | `{llm: {google: bool…}, search: {tavily: bool…}, search_order: [...], search_strategy: "fallback"\|"spread"\|"combine"}` |
| `GET /api/models?refresh=1` | Providers (configured / enabled / reachable), chains, catalog with limits and `reason` a model is unusable. `refresh` re-asks each provider's `/models`. |
| `GET /api/system/health` · `POST /api/system/repair` · `POST /api/system/backup` | Database checks, repairs, and a consistent backup (VACUUM INTO). |

Every jobs, documents and search-run query is scoped to the active profile.

---

## Links in the profile

`CandidateProfile` carries links as found in the resume (each `{label, url}`; `label` is the text that was on the link):

* `linkedin`, `github`, `portfolio` — the main profile links.
* `links: Link[]` — other personal pages (blog, coding or research profiles…), shown in the document header.
* `projects[].links: Link[]` — every link of a project (code, live demo, paper…); `projects[].url` is the main one.
* `item_links: {section: "certification"|"achievement"|"competition", item, label, url}[]` — a link for one entry
  (e.g. a credential page), `item` being that entry's exact text.

Generated documents expose `header.links[]`, `projects[].links[]` and `item_links{ entry text: Link[] }`; each link has
`text`, what is printed (a short address in the header, the label next to a project).

