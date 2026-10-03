// Discover: a split workspace. Left = search + results list. Right = the selected job,
// or "mission control" (live pipeline / last run summary) when nothing is selected.
import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  startSearch, cancelSearch, setList, loadList, toggleSaved, navigate, clearJobs,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Skeleton, EmptyState, ErrorBox, ChipsInput, Tabs, Icon, Field, Notice, PageHead, Popover, Seg,
  Monogram, Orb, CountUp, Select, Spinner, Drawer, VERDICT_TONE,
} from '../components/ui.js';
import { JobDetail } from './jobdetail.js';
import { AgentWorld } from './agentworld.js';
import {
  VERDICT_LABEL, VALIDATION_LABEL, VALIDATION_TONE, WORK_MODES, WORK_MODE_LABEL, relTime, fmtSalary,
  experienceText, EXPERIENCE_TONE, plural, humanize, REACH_SHORT, REACH_TONE, COMPANY_VERDICT_TONE,
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
          <${ChipsInput} label="Locations" value=${req.locations} onChange=${(v) => setReq((r) => ({ ...r, locations: v }))} placeholder="Add a city…"
            suggestions=${[...((env.profile.preferences || {}).locations || []), ...(snap ? snap.locations.map((p) => p.city) : []), (env.profile.location || '').split(',')[0].trim()]} />
        </${Field}>
        <${Field} label="Focus on roles (optional)">
          <${ChipsInput} label="Role focus" value=${req.role_focus} onChange=${(v) => setReq((r) => ({ ...r, role_focus: v }))} placeholder=${(snap && snap.target_titles[0]) || 'e.g. a title you want'}
            suggestions=${snap ? [...snap.target_titles, ...snap.adjacent_titles] : []} />
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
const AGENT_META = [
  { stage: 'understand', name: 'Profile analyst', icon: 'user', h: 18 },
  { stage: 'plan', name: 'Planner', icon: 'layers', h: 262 },
  { stage: 'discover', name: 'Scout', icon: 'search', h: 205 },
  { stage: 'normalize', name: 'Reader', icon: 'doc', h: 32 },
  { stage: 'dedupe', name: 'Curator', icon: 'board', h: 292 },
  { stage: 'validate', name: 'Verifier', icon: 'shield', h: 150 },
  { stage: 'extract', name: 'Analyst', icon: 'spark', h: 340, also: ['match'] },
  { stage: 'rank', name: 'Ranker', icon: 'chart', h: 46 },
];
const AGENT_BY_STAGE = Object.fromEntries(AGENT_META.flatMap((a) => [[a.stage, a], ...(a.also || []).map((x) => [x, a])]));

// Stage groups and how much of the bar each one fills. Inside a running group the bar only moves by
// real counts the server reports (searches done, boards checked, pages read, jobs analysed) — never by time.
const PROGRESS_GROUPS = [
  { keys: ['understand'], w: 3 }, { keys: ['plan'], w: 3 }, { keys: ['discover'], w: 20 }, { keys: ['normalize'], w: 14 },
  { keys: ['dedupe'], w: 2 }, { keys: ['validate', 'extract', 'match', 'rank'], w: 58 },
];
/** Overall progress 0–100 from finished stages plus the real done/total of the running one. */
export function runProgress(run) {
  if (run.status === 'completed') return 100;
  const status = Object.fromEntries(run.stages.map((st) => [st.key, st.status]));
  const p = run.progress;
  let sum = 0;
  for (const g of PROGRESS_GROUPS) {
    if (g.keys.every((k) => status[k] === 'done' || status[k] === 'skipped')) { sum += g.w; continue; }
    if (p && p.total > 0 && g.keys.includes(p.stage)) sum += g.w * Math.min(1, p.done / p.total);
  }
  return Math.min(ACTIVE.has(run.status) ? 99 : 100, Math.round(sum));
}

function useNow(ms = 1000, on = true) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { if (!on) return undefined; const t = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(t); }, [on, ms]);
  return now;
}

function clock(sec) {
  const s = Math.max(0, Math.round(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function ago(ts, now) {
  const s = Math.max(0, (now - Date.parse(ts)) / 1000);
  if (s < 4) return 'now';
  if (s < 60) return `${Math.floor(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return relTime(ts);
}

function Elapsed({ run }) {
  const active = ACTIVE.has(run.status);
  const now = useNow(1000, active);
  const end = run.finished_at ? Date.parse(run.finished_at) : now;
  return html`<span class="elapsed">${clock((end - Date.parse(run.started_at)) / 1000)}</span>`;
}

function RunStrip({ onOverview }) {
  const run = useStore((s) => s.search.run);
  const last = useStore((s) => { const it = s.search.feed.items; return it.length ? it[it.length - 1] : null; });
  if (!run) return null;
  const active = ACTIVE.has(run.status);
  const pct = runProgress(run);
  return html`<button type="button" class=${`run-strip ${active ? 'is-active' : ''}`} onClick=${onOverview} aria-label="Open search overview">
    <div class="row space">
      <span class="run-strip-title">${active ? html`<span class="pulse"></span>` : html`<${Icon} name="check" size=${14} />`}
        ${active ? html`Searching · <${CountUp} value=${pct} />%` : run.status === 'completed' ? 'Search complete' : `Search ${run.status}`}</span>
      <span class="run-strip-counts"><strong><${CountUp} value=${run.counts.recommended} /></strong> fit · <${CountUp} value=${run.counts.scored} /> analysed</span>
    </div>
    <div class=${`beam-bar ${active ? 'is-active' : ''}`}><div style=${{ width: `${pct}%` }}></div></div>
    ${last ? html`<div class="run-strip-now" key=${last.id}><span class=${`k-dot k-${last.kind}`}></span>${last.message}</div>` : null}
  </button>`;
}

function AgentRail({ run }) {
  const speaking = useStore((s) => { const it = s.search.feed.items; return it.length ? it[it.length - 1].agent : ''; });
  const active = ACTIVE.has(run.status);
  const stateOf = (a) => {
    const sts = run.stages.filter((st) => st.key === a.stage || (a.also || []).includes(st.key)).map((st) => st.status);
    if (sts.includes('running')) return 'running';
    if (sts.includes('failed')) return 'failed';
    if (sts.length && sts.every((x) => x === 'done')) return 'done';
    if (sts.includes('skipped')) return 'skipped';
    return 'pending';
  };
  return html`<div class="agent-rail" aria-label="Agents">${AGENT_META.map((a, i) => {
    const st = stateOf(a);
    const talk = active && st === 'running' && speaking === a.name;
    return html`<div class=${`agent-chip a-${st} ${talk ? 'a-talk' : ''}`} key=${a.name} style=${{ '--h': a.h, '--i': i }} title=${`${a.name}: ${st}`}>
      <span class="agent-ava"><${Icon} name=${st === 'done' ? 'check' : a.icon} size=${13} /></span>
      <span class="agent-name">${a.name}</span>${talk ? html`<span class="typing" aria-hidden="true"><i></i><i></i><i></i></span>` : null}</div>`;
  })}</div>`;
}

function FeedItem({ it, now, live }) {
  const a = AGENT_BY_STAGE[it.stage] || { name: it.agent, icon: 'spark', h: 20 };
  const job = it.job;
  const clickable = job && job.id && it.stage === 'match';
  const body = html`<span class="feed-ava" style=${{ '--h': a.h }}><${Icon} name=${a.icon} size=${13} /></span>
    <div class="feed-body">
      <div class="feed-meta"><strong>${it.agent}</strong><span class="feed-time">${ago(it.ts, now)}</span></div>
      <div class="feed-msg">${it.kind === 'work' && live ? html`<${Spinner} size=${12} />` : html`<span class=${`k-dot k-${it.kind}`}></span>`}<span>${it.message}</span></div>
    </div>
    ${job && typeof job.score === 'number' ? html`<${ScoreRing} score=${job.score} verdict=${job.verdict} size=${34} />` : null}`;
  return clickable
    ? html`<li class=${`feed-item k-${it.kind} is-link`}><button type="button" onClick=${() => navigate(`#/discover/job/${encodeURIComponent(job.id)}`)}>${body}</button></li>`
    : html`<li class=${`feed-item k-${it.kind}`}>${body}</li>`;
}

const VIEW_KEY = 'jhx-activity-view';
function readView() { try { return localStorage.getItem(VIEW_KEY) === 'agents' ? 'agents' : 'feed'; } catch { return 'feed'; } }

function LiveFeed({ active, run }) {
  const items = useStore((s) => s.search.feed.items);
  const now = useNow(1000, true);
  const [filter, setFilter] = useState('all');
  const [view, setViewState] = useState(readView);
  const setView = (v) => { setViewState(v); try { localStorage.setItem(VIEW_KEY, v); } catch { /* storage unavailable */ } };
  const shown = items.filter((x) => filter === 'all' || (filter === 'jobs' ? x.stage === 'match' : x.kind === 'reject' || x.kind === 'warn'));
  const list = shown.slice().reverse();
  return html`<section class="feed" aria-label="Live activity">
    <div class="feed-head">
      <div class="row gap">
        <span class="feed-title">${active ? html`<span class="live-dot"></span>Live` : 'Activity'}</span>
        <div class="view-toggle" role="group" aria-label="How to show the activity">
          <button type="button" class=${view === 'feed' ? 'on' : ''} aria-pressed=${view === 'feed' ? 'true' : 'false'} onClick=${() => setView('feed')}>
            <${Icon} name="list" size=${13} /> Activity</button>
          <button type="button" class=${view === 'agents' ? 'on' : ''} aria-pressed=${view === 'agents' ? 'true' : 'false'} onClick=${() => setView('agents')}>
            <${Icon} name="user" size=${13} /> Agents at work</button>
        </div>
      </div>
      ${view === 'feed' ? html`<${Tabs} size="sm" label="Activity filter" value=${filter} onChange=${setFilter}
        tabs=${[{ key: 'all', label: 'Everything' }, { key: 'jobs', label: 'Verdicts' }, { key: 'issues', label: 'Issues' }]} />` : null}
    </div>
    ${view === 'agents' && run ? html`<${AgentWorld} run=${run} items=${items} />` : html`<ol class="feed-list" aria-live="polite">
      ${list.length ? list.map((it, k) => html`<${FeedItem} key=${it.id} it=${it} now=${now} live=${active && k === 0} />`)
        : html`<li class="feed-empty">${active ? 'Warming up…' : 'Nothing to show for this filter.'}</li>`}
    </ol>`}
  </section>`;
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
      <p class="muted">Each search reads every posting, verifies it is real and still open, and explains the score — including when a role is not a fit. You can watch every step live here.</p>
      <div class="mission-stats">
        <div><span class="n"><${CountUp} value=${counts.recommended || 0} /></span><span class="l">recommended</span></div>
        <div><span class="n"><${CountUp} value=${counts.saved || 0} /></span><span class="l">saved</span></div>
        <div><span class="n"><${CountUp} value=${counts.applied || 0} /></span><span class="l">applied</span></div>
      </div>
    </div>`;
  }
  const active = ACTIVE.has(run.status);
  const c = run.counts;
  const pct = runProgress(run);
  const idx = run.stages.findIndex((st) => st.status === 'running');
  const cur = idx >= 0 ? run.stages[idx] : null;
  return html`<div class=${`mission live ${active ? 'is-active' : ''}`}>
    <div class="mc-top">
      <div class="mc-hero">
        <${Orb} size=${92} active=${active} done=${run.status === 'completed'} />
        <div class="grow">
          <span class="eyebrow">${active ? html`Live · <${Elapsed} run=${run} />` : html`Finished in <${Elapsed} run=${run} />`}</span>
          <h2>${active ? html`Discovery in <span class="serif">progress</span>` : run.status === 'completed' ? html`Search <span class="serif">complete</span>` : `Search ${run.status}`}</h2>
          <p class="muted small" aria-live="polite">${active ? (cur ? `Step ${idx + 1} of ${run.stages.length} · ${run.progress && run.progress.label ? run.progress.label : cur.label}` : 'Starting…')
            : `${c.recommended} roles fit you out of ${c.scored} analysed · ${c.duplicates} duplicates merged`}</p>
        </div>
        <div class="mc-pct"><span class="n"><${CountUp} value=${pct} /></span><span class="u">%</span></div>
      </div>
      <div class=${`mc-bar ${active ? 'is-active' : ''}`} role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${pct}>
        <div class="mc-fill" style=${{ width: `${pct}%` }}></div>
        ${run.stages.map((st, i) => html`<span class=${`mc-tick st-${st.status}`} style=${{ left: `${((i + 1) / run.stages.length) * 100}%` }} title=${st.label}></span>`)}
      </div>
      <${AgentRail} run=${run} />
      <div class="mc-stats">
        <div class="hl"><span class="n"><${CountUp} value=${c.recommended} /></span><span class="l">recommended</span></div>
        <div><span class="n"><${CountUp} value=${c.scored} /></span><span class="l">analysed</span></div>
        <div><span class="n"><${CountUp} value=${c.duplicates} /></span><span class="l">duplicates merged</span></div>
        <div><span class="n"><${CountUp} value=${c.rejected} /></span><span class="l">not a fit</span></div>
        ${!active && firstId ? html`<${Button} size="sm" variant="primary" onClick=${() => navigate(`#/discover/job/${encodeURIComponent(firstId)}`)}>Open best match <${Icon} name="arrow" size=${15} /></${Button}>` : null}
      </div>
      ${run.error ? html`<${ErrorBox} message=${run.error} />` : null}
    </div>
    <${LiveFeed} active=${active} run=${run} />
    ${run.plan ? html`<div class="plan-box">
      <button type="button" class="link-btn" onClick=${() => setPlan(true)}>Show the exact search plan</button>
      ${plan ? html`<${Drawer} onClose=${() => setPlan(false)} label="Search plan"><div class="plan-drawer">
        <div class="row space"><h2>The exact search <span class="serif">plan</span></h2>
          <button type="button" class="icon-btn" aria-label="Close" onClick=${() => setPlan(false)}><${Icon} name="x" /></button></div>
        <p class="muted small">What this search looks for and every query it sends. Planned ${run.plan.method === 'llm' ? 'by the AI from your profile' : run.plan.method === 'watchlist' ? 'for a watchlist check' : 'from your profile'}.</p>
        <div><div class="sec-title">Titles</div><div class="chip-row">${run.plan.titles.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
        <div><div class="sec-title">Locations</div><div class="chip-row">${run.plan.locations.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
        ${run.plan.watchlist ? html`<div><div class="sec-title">Watchlist</div><p class="small">${run.plan.watchlist} researched companies' own job boards are checked directly.</p></div>` : null}
        <div><div class="sec-title">Web searches · ${run.plan.queries.length}</div><ul class="queries">${run.plan.queries.map((q) => html`<li><code>${q}</code></li>`)}</ul></div>
      </div></${Drawer}>` : null}</div>` : null}
  </div>`;
}

// ---------------------------------------------------------------------------- job list
export function JobCard({ job, onOpen, selected, index = 0, fresh }) {
  const pendingSave = useStore((s) => !!s.pending.save[job.id]);
  const m = job.match;
  const r = job.reach;
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
      ${r ? html`<div class="job-reach" title=${r.headline}>
        <${Badge} tone=${REACH_TONE[r.level]}>${REACH_SHORT[r.level]}</${Badge}>
        ${r.application_email ? html`<${Badge} tone="success">Email route</${Badge}>` : null}
        ${r.company_verdict ? html`<${Badge} tone=${COMPANY_VERDICT_TONE[r.company_verdict]}>Watchlist</${Badge}>` : null}
        <span class="job-reach-why">${r.headline}</span>
      </div>` : null}
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
  // Only filters the user set count here; "latest search only" is shown as its own chip below.
  const active = (list.work_mode ? 1 : 0) + (list.min_score ? 1 : 0) + (list.sort !== 'chance' ? 1 : 0);
  return html`<div class="filter-block"><div class="filter-row">
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
            options=${[['chance', 'Best chance', 'Fit and how likely you are to be seen'], ['score', 'Best fit'],
              ['reach', 'Least crowded', 'Fresh posts, employer boards, email routes first'], ['recent', 'Most recent']]} />`}</${Field}>
        </div>
      </${Popover}>
    </div>
  </div>
  ${list.scope === 'run' ? html`<div class="scope-note">
    <span><${Icon} name="search" size=${12} /> Showing jobs from the latest search only</span>
    <button type="button" class="link-btn small" onClick=${() => setList({ scope: 'all' })}>Show all jobs</button>
  </div>` : null}
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
    { key: 'fresh', label: 'New', count: counts.fresh },
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
