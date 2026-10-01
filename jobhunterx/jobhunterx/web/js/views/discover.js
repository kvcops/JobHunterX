// Discover: a split workspace. Left = search + results list. Right = the selected job,
// or "mission control" (live pipeline / last run summary) when nothing is selected.
import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  startSearch, cancelSearch, setList, loadList, toggleSaved, navigate, clearJobs,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Skeleton, EmptyState, ErrorBox, ChipsInput, Tabs, Icon, Field, Notice, PageHead, Popover, Seg,
  Monogram, Orb, CountUp, Select, VERDICT_TONE,
} from '../components/ui.js';
import { JobDetail } from './jobdetail.js';
import {
  VERDICT_LABEL, VALIDATION_LABEL, VALIDATION_TONE, WORK_MODES, WORK_MODE_LABEL, relTime, fmtSalary,
  experienceText, EXPERIENCE_TONE, plural, humanize,
} from '../lib/format.js';
import { defaultSearchRequest } from '../state/domain.js';

const ACTIVE = new Set(['queued', 'running']);

// ---------------------------------------------------------------------------- search bar
function SearchBar() {
  const env = useStore((s) => s.profile.envelope);
  const search = useStore((s) => s.search);
  const snap = env && env.snapshot;
  const [req, setReq] = useState(() => defaultSearchRequest(snap));
  const [open, setOpen] = useState(false);
  const hash = env && env.profile_hash;
  useEffect(() => { setReq(defaultSearchRequest(snap)); }, [hash]);

  if (!env || !env.profile) {
    return html`<div class="search-box empty-profile">
      <div><strong>Start with your profile</strong><p class="muted small">JobHunterX needs to understand your experience before it can find roles that fit.</p></div>
      <${Button} variant="primary" onClick=${() => navigate('#/profile')}>Set up profile</${Button}></div>`;
  }
  const running = search.run && ACTIVE.has(search.run.status);
  const where = req.locations.length ? req.locations.join(', ') : 'Profile locations';
  const modes = req.work_modes.length ? req.work_modes.map((m) => WORK_MODE_LABEL[m]).join(' · ') : 'Any mode';
  return html`<div class="search-box">
    <div class="search-identity">
      <span class="spark-dot"><${Icon} name="spark" size=${14} /></span>
      ${snap ? html`<span>${humanize(snap.seniority)} · ~${snap.professional_years} yrs${snap.role_families[0] ? ` · ${snap.role_families[0].label}` : ''}</span>`
        : html`<span class="muted">Understanding your profile…</span>`}
    </div>
    <button type="button" class="search-summary" data-popover-anchor aria-expanded=${open ? 'true' : 'false'} onClick=${() => setOpen(!open)}>
      <span class="ss-item"><${Icon} name="pin" size=${15} />${where}</span>
      <span class="ss-item"><${Icon} name="layers" size=${15} />${modes}${req.include_international ? ' · abroad' : ''}</span>
      ${req.role_focus.length ? html`<span class="ss-item"><${Icon} name="search" size=${15} />${req.role_focus.join(', ')}</span>` : null}
      <span class="ss-edit"><${Icon} name="sliders" size=${15} /> Tune</span>
    </button>
    <${Popover} open=${open} onClose=${() => setOpen(false)} label="Search options">
      <div class="stack" style=${{ gap: '14px' }}>
        <${Field} label="Locations" hint="Leave empty to use your profile preferences.">
          <${ChipsInput} label="Locations" value=${req.locations} onChange=${(v) => setReq((r) => ({ ...r, locations: v }))} placeholder="Add a city…" />
        </${Field}>
        <${Field} label="Focus on roles (optional)">
          <${ChipsInput} label="Role focus" value=${req.role_focus} onChange=${(v) => setReq((r) => ({ ...r, role_focus: v }))} placeholder=${(snap && snap.target_titles[0]) || 'e.g. a title you want'} />
        </${Field}>
        <div class="field"><span class="field-label">Work mode</span>
          <${Seg} multi label="Work mode" options=${WORK_MODES.map((m) => [m, WORK_MODE_LABEL[m]])} value=${req.work_modes} onChange=${(v) => setReq((r) => ({ ...r, work_modes: v }))} /></div>
        <label class="switch"><input type="checkbox" checked=${req.include_international}
          onChange=${(e) => setReq((r) => ({ ...r, include_international: e.currentTarget.checked }))} /><span class="switch-ui"></span> Include roles abroad</label>
        <div class="row space"><button type="button" class="link-btn" onClick=${() => setReq(defaultSearchRequest(snap))}>Reset to profile</button>
          <${Button} size="sm" variant="primary" onClick=${() => setOpen(false)}>Done</${Button}></div>
      </div>
    </${Popover}>
    ${search.startError ? html`<${ErrorBox} message=${search.startError} onRetry=${() => startSearch(search.lastRequest || req)} />` : null}
    ${snap && snap.method === 'fallback' ? html`<${Notice} tone="warning">AI understanding is unavailable, so search uses your profile fields directly.</${Notice}>` : null}
    ${running
      ? html`<${Button} class="search-go" variant="danger" icon="stop" busy=${search.cancelling} onClick=${cancelSearch}>Stop search</${Button}>`
      : html`<${Button} class="search-go" variant="primary" busy=${search.starting} onClick=${() => { setOpen(false); startSearch(req); }}>Search now <${Icon} name="arrow" size=${16} /></${Button}>`}
  </div>`;
}

// ---------------------------------------------------------------------------- run status
function runProgress(run) {
  const active = ACTIVE.has(run.status);
  const done = run.stages.filter((st) => st.status === 'done').length;
  if (!active) return run.status === 'completed' ? 100 : Math.round((done / Math.max(1, run.stages.length)) * 100);
  return Math.min(96, Math.round(((done + 0.5) / Math.max(1, run.stages.length)) * 100));
}

function RunStrip({ onOverview }) {
  const run = useStore((s) => s.search.run);
  if (!run) return null;
  const active = ACTIVE.has(run.status);
  const cur = run.stages.find((st) => st.status === 'running');
  return html`<button type="button" class=${`run-strip ${active ? 'is-active' : ''}`} onClick=${onOverview} aria-label="Open search overview">
    <div class="row space">
      <span class="run-strip-title">${active ? html`<span class="pulse"></span>` : html`<${Icon} name="check" size=${14} />`}
        ${active ? (cur ? cur.label : 'Starting…') : run.status === 'completed' ? 'Search complete' : `Search ${run.status}`}</span>
      <span class="run-strip-counts"><strong><${CountUp} value=${run.counts.recommended} /></strong> fit · <${CountUp} value=${run.counts.scored} /> analysed</span>
    </div>
    <div class=${`beam-bar ${active ? 'is-active' : ''}`}><div style=${{ width: `${runProgress(run)}%` }}></div></div>
  </button>`;
}

function MissionControl() {
  const run = useStore((s) => s.search.run);
  const counts = useStore((s) => s.list.counts) || {};
  const firstId = useStore((s) => s.list.ids[0]);
  const [plan, setPlan] = useState(false);
  if (!run) {
    return html`<div class="mission idle">
      <${Orb} size=${170} active=${false} />
      <h2>Ready when <span class="serif">you</span> are</h2>
      <p class="muted">Each search reads every posting, verifies it is real and still open, and explains the score — including when a role is not a fit.</p>
      <div class="mission-stats">
        <div><span class="n"><${CountUp} value=${counts.recommended || 0} /></span><span class="l">recommended</span></div>
        <div><span class="n"><${CountUp} value=${counts.saved || 0} /></span><span class="l">saved</span></div>
        <div><span class="n"><${CountUp} value=${counts.applied || 0} /></span><span class="l">applied</span></div>
      </div>
    </div>`;
  }
  const active = ACTIVE.has(run.status);
  const c = run.counts;
  const cur = run.stages.find((st) => st.status === 'running');
  return html`<div class=${`mission ${active ? 'is-active' : ''}`} aria-live="polite">
    <div class="mission-hero">
      <${Orb} size=${active ? 150 : 120} active=${active} done=${run.status === 'completed'} />
      <div>
        <span class="eyebrow">${active ? 'Live' : `Finished ${relTime(run.finished_at || run.started_at)}`}</span>
        <h2>${active ? html`Discovery in <span class="serif">progress</span>` : run.status === 'completed' ? html`Search <span class="serif">complete</span>` : `Search ${run.status}`}</h2>
        <p class="muted">${active ? (cur && cur.detail) || 'Warming up…' : `${c.recommended} roles fit you out of ${c.scored} analysed. ${c.duplicates} duplicates were merged.`}</p>
        ${!active && firstId ? html`<${Button} variant="primary" onClick=${() => navigate(`#/discover/job/${encodeURIComponent(firstId)}`)}>Open best match <${Icon} name="arrow" size=${16} /></${Button}>` : null}
      </div>
    </div>
    <div class="mission-stats">
      <div class="hl"><span class="n"><${CountUp} value=${c.recommended} /></span><span class="l">recommended</span></div>
      <div><span class="n"><${CountUp} value=${c.scored} /></span><span class="l">analysed</span></div>
      <div><span class="n"><${CountUp} value=${c.duplicates} /></span><span class="l">duplicates merged</span></div>
      <div><span class="n"><${CountUp} value=${c.rejected} /></span><span class="l">not a fit</span></div>
    </div>
    <ol class="timeline" aria-label="Search progress">
      ${run.stages.map((st, i) => html`<li key=${st.key} class=${`tl st-${st.status}`} style=${{ '--i': i }}>
        <span class="tl-dot">${st.status === 'done' ? html`<${Icon} name="check" size=${11} />` : st.status === 'failed' ? html`<${Icon} name="x" size=${11} />` : null}</span>
        <span class="tl-label">${st.label}</span><span class="sr-only">${st.status}</span>
        ${st.status === 'running' && st.detail ? html`<span class="tl-detail">${st.detail}</span>` : null}
      </li>`)}
    </ol>
    ${run.error ? html`<${ErrorBox} message=${run.error} />` : null}
    ${run.plan ? html`<div class="plan-box">
      <button type="button" class="link-btn" aria-expanded=${plan ? 'true' : 'false'} onClick=${() => setPlan(!plan)}>${plan ? 'Hide' : 'Show'} search plan</button>
      ${plan ? html`<div class="plan">
        <div><div class="sec-title">Titles</div><div class="chip-row">${run.plan.titles.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
        <div><div class="sec-title">Locations</div><div class="chip-row">${run.plan.locations.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
        <div><div class="sec-title">Queries · ${run.plan.queries.length}</div><ul class="queries">${run.plan.queries.map((q) => html`<li><code>${q}</code></li>`)}</ul></div>
      </div>` : null}</div>` : null}
  </div>`;
}

// ---------------------------------------------------------------------------- job list
export function JobCard({ job, onOpen, selected, index = 0, fresh }) {
  const pendingSave = useStore((s) => !!s.pending.save[job.id]);
  const m = job.match;
  const exp = m && m.experience;
  return html`<article class=${`job-card ${m && m.verdict === 'incompatible' ? 'is-rejected' : ''} ${selected ? 'is-selected' : ''} ${fresh ? 'is-fresh' : ''}`}
      style=${{ '--i': Math.min(index, 14) }}>
    <button type="button" class="job-main" onClick=${() => onOpen(job.id)} aria-label=${`Open ${job.title} at ${job.company}`} aria-current=${selected ? 'true' : undefined}>
      <div class="job-top">
        <${Monogram} name=${job.company} />
        <div class="job-body">
          <div class="job-company">${job.company || 'Unknown company'}<span class="job-when">${job.posted_at ? relTime(job.posted_at) : relTime(job.discovered_at)}</span></div>
          <h3 class="job-title">${job.title || 'Untitled role'}</h3>
          <div class="job-sub"><span>${job.location || 'Location not stated'}</span>
            ${job.work_mode !== 'unknown' ? html`<span>${WORK_MODE_LABEL[job.work_mode]}</span>` : null}
            ${job.salary ? html`<span>${fmtSalary(job.salary)}</span>` : null}</div>
        </div>
        <${ScoreRing} score=${m ? m.score : null} verdict=${m && m.verdict} size=${48} />
      </div>
      ${m && m.headline ? html`<p class="job-headline">${m.headline}</p>` : null}
      <div class="job-facts">
        ${m ? html`<${Badge} tone=${VERDICT_TONE[m.verdict]}>${VERDICT_LABEL[m.verdict]}</${Badge}>` : html`<${Badge}>Not scored</${Badge}>`}
        <${Badge} tone=${VALIDATION_TONE[job.validation.status]}>${VALIDATION_LABEL[job.validation.status]}</${Badge}>
        ${job.match_stale ? html`<${Badge} tone="warning">Profile changed</${Badge}>` : null}
        ${m && m.required_total ? html`<span class="fact">${m.required_matched}/${m.required_total} skills</span>` : null}
        ${exp && exp.fit !== 'unknown' ? html`<span class=${`fact tone-text-${EXPERIENCE_TONE[exp.fit]}`}>${experienceText(exp)}</span>` : null}
      </div>
    </button>
    <button type="button" class=${`icon-btn save-btn ${job.saved ? 'on' : ''}`} aria-pressed=${job.saved ? 'true' : 'false'}
      aria-label=${job.saved ? 'Unsave job' : 'Save job'} disabled=${pendingSave} onClick=${() => toggleSaved(job.id)}>
      <${Icon} name="star" size=${15} />
    </button>
  </article>`;
}

function Filters() {
  const list = useStore((s) => s.list);
  const run = useStore((s) => s.search.run);
  const [q, setQ] = useState(list.q);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (q === list.q) return undefined;
    const t = setTimeout(() => setList({ q }), 300);
    return () => clearTimeout(t);
  }, [q]);
  const active = (list.work_mode ? 1 : 0) + (list.min_score ? 1 : 0) + (list.sort !== 'score' ? 1 : 0) + (list.scope === 'run' ? 1 : 0);
  return html`<div class="filter-row">
    <label class="search-field"><${Icon} name="search" size=${15} />
      <input type="search" placeholder="Filter by title, company, place" aria-label="Filter jobs" value=${q} onInput=${(e) => setQ(e.currentTarget.value)} /></label>
    <div class="pop-anchor">
      <button type="button" class=${`icon-btn filter-btn ${active ? 'on' : ''}`} data-popover-anchor aria-label="More filters" aria-expanded=${open ? 'true' : 'false'} onClick=${() => setOpen(!open)}>
        <${Icon} name="sliders" size=${16} />${active ? html`<span class="filter-count">${active}</span>` : null}</button>
      <${Popover} open=${open} onClose=${() => setOpen(false)} label="Filters" align="right">
        <div class="stack" style=${{ gap: '12px', minWidth: '240px' }}>
          ${run ? html`<label class="switch"><input type="checkbox" checked=${list.scope === 'run'}
            onChange=${(e) => setList(e.currentTarget.checked ? { scope: 'run', runId: run.id } : { scope: 'all' })} /><span class="switch-ui"></span> Latest search only</label>` : null}
          <${Field} label="Work mode">${(id) => html`<${Select} id=${id} block label="Work mode filter" value=${list.work_mode} onChange=${(v) => setList({ work_mode: v })}
            options=${[['', 'Any work mode'], ...WORK_MODES.map((m) => [m, WORK_MODE_LABEL[m]])]} />`}</${Field}>
          <${Field} label="Minimum score">${(id) => html`<${Select} id=${id} block label="Minimum score" value=${String(list.min_score || 0)} onChange=${(v) => setList({ min_score: Number(v) })}
            options=${[['0', 'Any score'], ['45', '45 and above', 'Includes stretch roles'], ['60', '60 and above', 'Good matches'], ['75', '75 and above', 'Strong matches only']]} />`}</${Field}>
          <${Field} label="Sort">${(id) => html`<${Select} id=${id} block label="Sort" value=${list.sort} onChange=${(v) => setList({ sort: v })}
            options=${[['score', 'Best match'], ['recent', 'Most recent']]} />`}</${Field}>
        </div>
      </${Popover}>
    </div>
  </div>`;
}

function JobList() {
  const list = useStore((s) => s.list);
  const byId = useStore((s) => s.jobs.byId);
  const run = useStore((s) => s.search.run);
  const streamed = useStore((s) => s.search.streamedIds);
  const route = useStore((s) => s.route);
  const counts = list.counts || {};
  const tabs = [
    { key: 'recommended', label: 'For you', count: counts.recommended },
    { key: 'all', label: 'All', count: counts.all },
    { key: 'saved', label: 'Saved', count: counts.saved },
    { key: 'applied', label: 'Applied', count: counts.applied },
    { key: 'rejected', label: 'Not a fit', count: counts.rejected },
  ];
  const jobs = list.ids.map((id) => byId[id]).filter(Boolean);
  const runActive = run && ACTIVE.has(run.status);
  const open = (id) => navigate(`#/discover/job/${encodeURIComponent(id)}`);
  const recent = new Set(streamed.slice(-3));
  return html`<div class="results" aria-label="Jobs">
    <${Tabs} label="Job views" tabs=${tabs} value=${list.view} onChange=${(v) => setList({ view: v })} size="sm" />
    <${Filters} />
    <div class="scroll job-list" aria-busy=${list.status === 'loading' ? 'true' : 'false'}>
      ${list.status === 'error' ? html`<${ErrorBox} message=${list.error} onRetry=${loadList} />` : null}
      ${list.status === 'loading' && !jobs.length ? html`<${Skeleton} rows=${5} />` : null}
      ${list.status !== 'loading' && list.status !== 'error' && !jobs.length ? (runActive
        ? html`<${EmptyState} icon="search" title="Looking for roles…">Matches appear here the moment each job is verified and analysed.</${EmptyState}>`
        : list.view === 'recommended'
          ? html`<${EmptyState} icon="spark" title="No recommendations yet">${run ? 'This search found no roles that fit well. Check “Not a fit” to see why, or tune locations and role focus.' : 'Run a search to discover roles that fit your profile.'}</${EmptyState}>`
          : html`<${EmptyState} icon="info" title="Nothing here">No jobs match these filters.</${EmptyState}>`) : null}
      ${jobs.map((j, i) => html`<${JobCard} key=${j.id} job=${j} index=${i} onOpen=${open} selected=${route.jobId === j.id} fresh=${runActive && recent.has(j.id)} />`)}
      ${jobs.length ? html`<div class="list-foot"><span>${plural(jobs.length, 'job')}</span>
        <button type="button" class="link-btn" onClick=${() => clearJobs('unsaved')}>Clear unsaved</button></div>` : null}
    </div>
  </div>`;
}

export function DiscoverView() {
  const route = useStore((s) => s.route);
  const run = useStore((s) => s.search.run);
  const active = run && ACTIVE.has(run.status);
  const overview = () => navigate('#/discover');
  // Esc closes the open job (unless a dialog or popover is handling it).
  useEffect(() => {
    if (!route.jobId) return undefined;
    const onKey = (e) => { if (e.key === 'Escape' && !document.querySelector('.overlay, .popover, .select-list')) overview(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [route.jobId]);
  return html`<div class="view view-discover">
    <${PageHead} title=${html`Roles that <span class="serif">fit</span> you`}
      sub=${active ? 'Searching now — results stream in as they are verified.' : 'Verified postings, ranked by genuine fit and explained.'} />
    <div class=${`split ${route.jobId ? 'has-detail' : ''}`}>
      <section class="pane list-pane card" aria-label="Search and results">
        <${SearchBar} />
        <${RunStrip} onOverview=${overview} />
        <${JobList} />
      </section>
      <section class="pane detail-pane card" aria-label=${route.jobId ? 'Job details' : 'Search overview'}>
        ${route.jobId ? html`<${JobDetail} key=${route.jobId} jobId=${route.jobId} onClose=${overview} />` : html`<${MissionControl} />`}
      </section>
    </div>
  </div>`;
}
