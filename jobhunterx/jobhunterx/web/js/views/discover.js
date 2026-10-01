import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  startSearch, cancelSearch, setList, loadList, toggleSaved, navigate, clearJobs,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Skeleton, EmptyState, ErrorBox, ChipsInput, Tabs, Icon, Field, Notice, PageHero, VERDICT_TONE,
} from '../components/ui.js';
import {
  VERDICT_LABEL, VALIDATION_LABEL, VALIDATION_TONE, WORK_MODES, WORK_MODE_LABEL, relTime, fmtSalary,
  experienceText, EXPERIENCE_TONE, plural, humanize,
} from '../lib/format.js';

const ACTIVE = new Set(['queued', 'running']);

function SearchLauncher() {
  const env = useStore((s) => s.profile.envelope);
  const search = useStore((s) => s.search);
  const snap = env && env.snapshot;
  const defaults = () => ({
    locations: snap ? snap.locations.map((p) => p.city || p.country).filter(Boolean) : [],
    work_modes: snap ? snap.work_modes : [],
    role_focus: [],
    include_international: snap ? snap.open_to_international : false,
  });
  const [req, setReq] = useState(defaults);
  const hash = env && env.profile_hash;
  useEffect(() => { setReq(defaults()); }, [hash]);

  if (!env || !env.profile) {
    return html`<section class="card"><${EmptyState} icon="user" title="Start with your profile"
      action=${html`<${Button} variant="primary" onClick=${() => navigate('#/profile')}>Upload your resume</${Button}>`}>
      JobHunterX needs to understand your experience before it can find roles that genuinely fit you.</${EmptyState}></section>`;
  }
  const running = search.run && ACTIVE.has(search.run.status);
  const toggleMode = (m) => setReq((r) => ({ ...r, work_modes: r.work_modes.includes(m) ? r.work_modes.filter((x) => x !== m) : [...r.work_modes, m] }));
  return html`<section class="card prompt" aria-label="Search">
    <div class="prompt-head">
      <h2>What should JobHunterX look for?</h2>
      ${snap ? html`<div class="identity">
        <span class="chip">${humanize(snap.seniority)} level</span>
        <span class="chip">~${snap.professional_years} yrs</span>
        ${snap.role_families.slice(0, 2).map((f) => html`<span class="chip soft">${f.label}</span>`)}
      </div>` : html`<span class="muted small">Understanding your profile…</span>`}
    </div>
    <div class="prompt-body">
      <${Field} label="Locations" hint="Leave empty to use your profile preferences.">
        <${ChipsInput} label="Locations" value=${req.locations} onChange=${(v) => setReq((r) => ({ ...r, locations: v }))} placeholder="Add a city…" />
      </${Field}>
      <${Field} label="Focus on roles (optional)" hint="Titles or tracks to prioritise for this run.">
        <${ChipsInput} label="Role focus" value=${req.role_focus} onChange=${(v) => setReq((r) => ({ ...r, role_focus: v }))} placeholder=${(snap && snap.target_titles[0]) || 'e.g. a title you want'} />
      </${Field}>
    </div>
    ${search.startError ? html`<div style=${{ padding: '0 24px 16px' }}><${ErrorBox} message=${search.startError} onRetry=${() => startSearch(search.lastRequest || req)} /></div>` : null}
    ${snap && snap.method === 'fallback' ? html`<div style=${{ padding: '0 24px 16px' }}><${Notice} tone="warning">AI understanding is unavailable, so search uses your profile fields directly. Results will be less precise.</${Notice}></div>` : null}
    <div class="prompt-foot">
      <div class="row gap wrap">
        <div class="seg" role="group" aria-label="Work mode">
          ${WORK_MODES.map((m) => html`<button type="button" class=${`seg-btn ${req.work_modes.includes(m) ? 'on' : ''}`}
            aria-pressed=${req.work_modes.includes(m) ? 'true' : 'false'} onClick=${() => toggleMode(m)}>${WORK_MODE_LABEL[m]}</button>`)}
        </div>
        <label class="check"><input type="checkbox" checked=${req.include_international}
          onChange=${(e) => setReq((r) => ({ ...r, include_international: e.currentTarget.checked }))} /> Include roles abroad</label>
      </div>
      ${running
        ? html`<${Button} variant="danger" icon="stop" busy=${search.cancelling} onClick=${cancelSearch}>Stop search</${Button}>`
        : html`<${Button} variant="primary" size="lg" busy=${search.starting} onClick=${() => startSearch(req)}>Search now <${Icon} name="arrow" size=${16} /></${Button}>`}
    </div>
  </section>`;
}

function RunPanel() {
  const run = useStore((s) => s.search.run);
  const [open, setOpen] = useState(false);
  if (!run) return null;
  const active = ACTIVE.has(run.status);
  const c = run.counts;
  const done = run.stages.filter((st) => st.status === 'done').length;
  const cur = run.stages.find((st) => st.status === 'running');
  const pct = Math.round((Math.max(0, done - (active ? 0 : 1)) / Math.max(1, run.stages.length - 1)) * 100);
  return html`<section class=${`card pipeline-card ${active ? 'is-active' : ''}`} aria-label="Search progress" aria-live="polite">
    <div class="run-head">
      <div class="run-title">
        ${active ? html`<span class="pulse" aria-hidden="true"></span>` : null}
        <strong>${active ? 'Discovery in progress' : run.status === 'completed' ? 'Search complete' : `Search ${run.status}`}</strong>
        <span class="muted small">started ${relTime(run.started_at)}</span>
      </div>
      ${run.plan ? html`<button type="button" class="link-btn" aria-expanded=${open ? 'true' : 'false'} onClick=${() => setOpen(!open)}>${open ? 'Hide' : 'Show'} search plan</button>` : null}
    </div>
    <div class="track-bar" aria-hidden="true"><div style=${{ width: `${active ? Math.min(100, pct) : run.status === 'completed' ? 100 : pct}%` }}></div></div>
    <ol class="stages">
      ${run.stages.map((st) => html`<li key=${st.key} class=${`stage st-${st.status}`} title=${st.detail}>
        <span class="stage-dot" aria-hidden="true">${st.status === 'done' ? html`<${Icon} name="check" size=${11} />` : null}</span>
        <span class="stage-label">${st.label}</span>
        <span class="sr-only">${st.status}</span>
      </li>`)}
    </ol>
    ${cur && cur.detail ? html`<p class="stage-detail">${cur.detail}</p>` : null}
    <div class="counters">
      <div class="counter hl"><span class="n">${c.recommended}</span><span class="l">recommended</span></div>
      <div class="counter"><span class="n">${c.scored}</span><span class="l">analysed</span></div>
      <div class="counter"><span class="n">${c.duplicates}</span><span class="l">duplicates merged</span></div>
      <div class="counter"><span class="n">${c.rejected}</span><span class="l">not a fit</span></div>
    </div>
    ${run.error ? html`<div style=${{ marginTop: '14px' }}><${ErrorBox} message=${run.error} /></div>` : null}
    ${open && run.plan ? html`<div class="plan">
      <div><div class="sec-title">Titles</div><div class="chip-row">${run.plan.titles.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
      <div><div class="sec-title">Locations</div><div class="chip-row">${run.plan.locations.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
      <div><div class="sec-title">Queries · ${run.plan.queries.length}</div><ul class="queries">${run.plan.queries.map((q) => html`<li><code>${q}</code></li>`)}</ul></div>
    </div>` : null}
  </section>`;
}

export function JobCard({ job, onOpen }) {
  const pendingSave = useStore((s) => !!s.pending.save[job.id]);
  const m = job.match;
  const exp = m && m.experience;
  const initial = ((job.company || '?').trim()[0] || '?').toUpperCase();
  return html`<article class=${`job-card ${m && m.verdict === 'incompatible' ? 'is-rejected' : ''}`}>
    <button type="button" class="job-main" onClick=${() => onOpen(job.id)} aria-label=${`Open ${job.title} at ${job.company}`}>
      <div class="job-top">
        <span class="monogram" aria-hidden="true">${initial}</span>
        <div class="job-body">
          <div class="job-company">${job.company || 'Unknown company'}</div>
          <h3 class="job-title">${job.title || 'Untitled role'}</h3>
          <div class="job-sub"><span>${job.location || 'Location not stated'}</span>
            ${job.work_mode !== 'unknown' ? html`<span>${WORK_MODE_LABEL[job.work_mode]}</span>` : null}
            ${job.salary ? html`<span>${fmtSalary(job.salary)}</span>` : null}</div>
        </div>
      </div>
      ${m && m.headline ? html`<p class="job-headline">${m.headline}</p>` : null}
      <div class="job-meta">
        <div class="stack" style=${{ gap: '8px' }}>
          <div class="row gap wrap">
            ${m ? html`<${Badge} tone=${VERDICT_TONE[m.verdict]}>${VERDICT_LABEL[m.verdict]}</${Badge}>` : html`<${Badge}>Not scored</${Badge}>`}
            <${Badge} tone=${VALIDATION_TONE[job.validation.status]}>${VALIDATION_LABEL[job.validation.status]}</${Badge}>
            ${job.match_stale ? html`<${Badge} tone="warning">Profile changed</${Badge}>` : null}
          </div>
          <div class="job-facts">
            ${m && m.required_total ? html`<span class="fact">${m.required_matched}/${m.required_total} required skills</span>` : null}
            ${exp && exp.fit !== 'unknown' ? html`<span class=${`fact tone-text-${EXPERIENCE_TONE[exp.fit]}`}>${experienceText(exp)}</span>` : null}
          </div>
        </div>
        <${ScoreRing} score=${m ? m.score : null} verdict=${m && m.verdict} />
      </div>
    </button>
    <div class="job-foot">
      <span>${job.source ? `${job.source.first_party ? 'Employer site' : humanize(job.source.kind)}${job.sources_count > 1 ? ` · +${job.sources_count - 1} sources` : ''}` : 'Source unknown'}</span>
      <span>${job.posted_at ? `Posted ${relTime(job.posted_at)}` : `Found ${relTime(job.discovered_at)}`}</span>
    </div>
    <button type="button" class=${`icon-btn save-btn ${job.saved ? 'on' : ''}`} aria-pressed=${job.saved ? 'true' : 'false'}
      aria-label=${job.saved ? 'Unsave job' : 'Save job'} disabled=${pendingSave} onClick=${() => toggleSaved(job.id)}>
      <${Icon} name="star" size=${16} />
    </button>
  </article>`;
}

function JobList() {
  const list = useStore((s) => s.list);
  const byId = useStore((s) => s.jobs.byId);
  const run = useStore((s) => s.search.run);
  const route = useStore((s) => s.route);
  const [q, setQ] = useState(list.q);
  useEffect(() => {
    if (q === list.q) return undefined;
    const t = setTimeout(() => setList({ q }), 300);
    return () => clearTimeout(t);
  }, [q]);
  const counts = list.counts || {};
  const tabs = [
    { key: 'recommended', label: 'Recommended', count: counts.recommended },
    { key: 'all', label: 'All', count: counts.all },
    { key: 'saved', label: 'Saved', count: counts.saved },
    { key: 'applied', label: 'Applied', count: counts.applied },
    { key: 'rejected', label: 'Not a fit', count: counts.rejected },
  ];
  const jobs = list.ids.map((id) => byId[id]).filter(Boolean);
  const runActive = run && ACTIVE.has(run.status);
  const open = (id) => navigate(`#/${route.page}/job/${encodeURIComponent(id)}`);
  return html`<section class="results" aria-label="Jobs">
    <div class="results-toolbar">
      <${Tabs} label="Job views" tabs=${tabs} value=${list.view} onChange=${(v) => setList({ view: v })} />
      <div class="filters">
        ${list.scope === 'run' && run ? html`<button type="button" class="chip chip-btn on" onClick=${() => setList({ scope: 'all' })}
          title="Show jobs from all searches">This search only <${Icon} name="x" size=${12} /></button>`
          : run ? html`<button type="button" class="chip chip-btn" onClick=${() => setList({ scope: 'run', runId: run.id })}>Latest search only</button>` : null}
        <input class="input search-input" type="search" placeholder="Filter by title, company, place" aria-label="Filter jobs" value=${q} onInput=${(e) => setQ(e.currentTarget.value)} />
        <select class="input" aria-label="Work mode filter" value=${list.work_mode} onChange=${(e) => setList({ work_mode: e.currentTarget.value })}>
          <option value="">Any work mode</option>
          ${WORK_MODES.map((m) => html`<option value=${m}>${WORK_MODE_LABEL[m]}</option>`)}
        </select>
        <select class="input" aria-label="Minimum score" value=${String(list.min_score || 0)} onChange=${(e) => setList({ min_score: Number(e.currentTarget.value) })}>
          <option value="0">Any score</option><option value="45">45+</option><option value="60">60+</option><option value="75">75+</option>
        </select>
        <select class="input" aria-label="Sort" value=${list.sort} onChange=${(e) => setList({ sort: e.currentTarget.value })}>
          <option value="score">Best match</option><option value="recent">Most recent</option>
        </select>
      </div>
    </div>
    ${list.status === 'error' ? html`<${ErrorBox} message=${list.error} onRetry=${loadList} />` : null}
    ${list.status === 'loading' && !jobs.length ? html`<div class="job-grid">${[0, 1, 2, 3].map(() => html`<${Skeleton} card lines=${3} />`)}</div>` : null}
    ${list.status !== 'loading' && list.status !== 'error' && !jobs.length ? (runActive
      ? html`<${EmptyState} icon="search" title="Looking for roles…">Matches will appear here as soon as each job has been verified and analysed.</${EmptyState}>`
      : list.view === 'recommended'
        ? html`<${EmptyState} icon="search" title="No recommended roles yet">${run ? 'This search found no roles that fit your profile well. Check "Not a fit" to see why, or broaden locations and role focus.' : 'Run a search to discover roles that fit your profile.'}</${EmptyState}>`
        : html`<${EmptyState} icon="info" title="Nothing here">No jobs match these filters.</${EmptyState}>`) : null}
    ${jobs.length ? html`<div class="job-grid" aria-busy=${list.status === 'loading' ? 'true' : 'false'}>
      ${jobs.map((j) => html`<${JobCard} key=${j.id} job=${j} onOpen=${open} />`)}</div>` : null}
    ${jobs.length ? html`<div class="list-foot muted small">${plural(jobs.length, 'job')} shown
      <button type="button" class="link-btn" onClick=${() => clearJobs('unsaved')}>Clear unsaved jobs</button></div>` : null}
  </section>`;
}

export function DiscoverView() {
  const run = useStore((s) => s.search.run);
  const active = run && ACTIVE.has(run.status);
  const announce = active ? 'Search running — results stream in as they are verified'
    : run && run.status === 'completed' ? `Last search: ${run.counts.recommended} recommended · ${run.counts.rejected} not a fit`
      : 'Career intelligence, not keyword search';
  return html`<div class="page">
    <${PageHero} center announce=${announce} title=${html`Roles that <span class="serif">genuinely</span> fit you`}
      lead="JobHunterX reads every posting, checks it is real and open, and explains exactly why it fits — or why it doesn't." />
    <${SearchLauncher} />
    <${RunPanel} />
    <${JobList} />
  </div>`;
}
