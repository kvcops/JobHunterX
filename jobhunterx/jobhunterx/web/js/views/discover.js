import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  startSearch, cancelSearch, setList, loadList, toggleSaved, navigate, clearJobs,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Skeleton, EmptyState, ErrorBox, ChipsInput, Tabs, Icon, Field, Notice,
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
    return html`<${EmptyState} icon="user" title="Start with your profile"
      action=${html`<${Button} variant="primary" onClick=${() => navigate('#/profile')}>Upload your resume</${Button}>`}>
      JobHunterX needs to understand your experience before it can find roles that genuinely fit you.</${EmptyState}>`;
  }
  const running = search.run && ACTIVE.has(search.run.status);
  const toggleMode = (m) => setReq((r) => ({ ...r, work_modes: r.work_modes.includes(m) ? r.work_modes.filter((x) => x !== m) : [...r.work_modes, m] }));
  return html`<section class="card launcher" aria-label="Search">
    <div class="launcher-head">
      <div>
        <h2>Find roles that fit you</h2>
        <p class="muted">${snap ? html`Searching as <strong>${snap.seniority}</strong>-level · ~${snap.professional_years} yrs · tracks: ${snap.role_families.slice(0, 3).map((f) => f.label).join(', ') || '—'}` : 'Understanding your profile…'}</p>
      </div>
      ${running
        ? html`<${Button} variant="danger" icon="stop" busy=${search.cancelling} onClick=${cancelSearch}>Stop search</${Button}>`
        : html`<${Button} variant="primary" icon="search" busy=${search.starting} onClick=${() => startSearch(req)}>Search now</${Button}>`}
    </div>
    <div class="launcher-grid">
      <${Field} label="Locations" hint="Leave empty to use your profile preferences.">
        <${ChipsInput} label="Locations" value=${req.locations} onChange=${(v) => setReq((r) => ({ ...r, locations: v }))} placeholder="Add a city…" />
      </${Field}>
      <${Field} label="Focus on roles (optional)" hint="Titles or tracks to prioritise for this run.">
        <${ChipsInput} label="Role focus" value=${req.role_focus} onChange=${(v) => setReq((r) => ({ ...r, role_focus: v }))} placeholder=${(snap && snap.target_titles[0]) || 'e.g. a title you want'} />
      </${Field}>
      <div class="field"><span class="field-label">Work mode</span>
        <div class="seg" role="group" aria-label="Work mode">
          ${WORK_MODES.map((m) => html`<button type="button" class=${`seg-btn ${req.work_modes.includes(m) ? 'on' : ''}`}
            aria-pressed=${req.work_modes.includes(m) ? 'true' : 'false'} onClick=${() => toggleMode(m)}>${WORK_MODE_LABEL[m]}</button>`)}
        </div>
        <label class="check"><input type="checkbox" checked=${req.include_international}
          onChange=${(e) => setReq((r) => ({ ...r, include_international: e.currentTarget.checked }))} /> Include roles abroad</label>
      </div>
    </div>
    ${search.startError ? html`<${ErrorBox} message=${search.startError} onRetry=${() => startSearch(search.lastRequest || req)} />` : null}
    ${snap && snap.method === 'fallback' ? html`<${Notice} tone="warning">AI understanding is unavailable, so search uses your profile fields directly. Results will be less precise.</${Notice}>` : null}
  </section>`;
}

function RunPanel() {
  const run = useStore((s) => s.search.run);
  const [open, setOpen] = useState(false);
  if (!run) return null;
  const active = ACTIVE.has(run.status);
  const c = run.counts;
  return html`<section class=${`card run-panel ${active ? 'is-active' : ''}`} aria-label="Search progress" aria-live="polite">
    <div class="run-head">
      <div class="run-title">
        ${active ? html`<span class="pulse" aria-hidden="true"></span>` : null}
        <strong>${active ? 'Searching…' : run.status === 'completed' ? 'Search complete' : `Search ${run.status}`}</strong>
        <span class="muted">started ${relTime(run.started_at)}</span>
      </div>
      <div class="run-counts">
        <span><strong>${c.recommended}</strong> recommended</span>
        <span><strong>${c.scored}</strong> analysed</span>
        <span><strong>${c.duplicates}</strong> duplicates merged</span>
        <span><strong>${c.rejected}</strong> not a fit</span>
      </div>
    </div>
    <ol class="stages">
      ${run.stages.map((st) => html`<li key=${st.key} class=${`stage st-${st.status}`} title=${st.detail}>
        <span class="stage-dot" aria-hidden="true">${st.status === 'done' ? html`<${Icon} name="check" size=${12} />` : null}</span>
        <span class="stage-label">${st.label}</span>
        <span class="sr-only">${st.status}</span>
      </li>`)}
    </ol>
    ${(() => { const cur = run.stages.find((s) => s.status === 'running'); return cur && cur.detail ? html`<p class="muted small">${cur.detail}</p>` : null; })()}
    ${run.error ? html`<${ErrorBox} message=${run.error} />` : null}
    ${run.plan ? html`<button type="button" class="link-btn" aria-expanded=${open ? 'true' : 'false'} onClick=${() => setOpen(!open)}>${open ? 'Hide' : 'Show'} search plan</button>` : null}
    ${open && run.plan ? html`<div class="plan">
      <div><span class="muted small">Titles</span><div class="chip-row">${run.plan.titles.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
      <div><span class="muted small">Locations</span><div class="chip-row">${run.plan.locations.map((t) => html`<span class="chip">${t}</span>`)}</div></div>
      <div><span class="muted small">Queries (${run.plan.queries.length})</span><ul class="queries">${run.plan.queries.map((q) => html`<li><code>${q}</code></li>`)}</ul></div>
    </div>` : null}
  </section>`;
}

export function JobCard({ job, onOpen }) {
  const pendingSave = useStore((s) => !!s.pending.save[job.id]);
  const m = job.match;
  const exp = m && m.experience;
  return html`<article class=${`job-card ${m && m.verdict === 'incompatible' ? 'is-rejected' : ''}`}>
    <button type="button" class="job-main" onClick=${() => onOpen(job.id)} aria-label=${`Open ${job.title} at ${job.company}`}>
      <${ScoreRing} score=${m ? m.score : null} verdict=${m && m.verdict} />
      <div class="job-body">
        <div class="job-title-row">
          <h3 class="job-title">${job.title || 'Untitled role'}</h3>
          ${m ? html`<${Badge} tone=${m.verdict === 'incompatible' ? 'danger' : m.verdict === 'strong' ? 'success' : m.verdict === 'good' ? 'info' : 'warning'}>${VERDICT_LABEL[m.verdict]}</${Badge}>` : html`<${Badge}>Not scored</${Badge}>`}
          ${job.match_stale ? html`<${Badge} tone="warning" title="Your profile changed since this was scored">Profile changed</${Badge}>` : null}
        </div>
        <div class="job-sub">${job.company || 'Unknown company'} · ${job.location || 'Location not stated'}${job.work_mode !== 'unknown' ? ` · ${WORK_MODE_LABEL[job.work_mode]}` : ''}</div>
        ${m && m.headline ? html`<p class="job-headline">${m.headline}</p>` : null}
        <div class="job-facts">
          ${m && m.required_total ? html`<span class="fact"><${Icon} name="check" size=${14} /> ${m.required_matched}/${m.required_total} required skills</span>` : null}
          ${exp && exp.fit !== 'unknown' ? html`<span class=${`fact tone-text-${EXPERIENCE_TONE[exp.fit]}`}>${experienceText(exp)}</span>` : null}
          ${job.salary ? html`<span class="fact">${fmtSalary(job.salary)}</span>` : null}
          <${Badge} tone=${VALIDATION_TONE[job.validation.status]}>${VALIDATION_LABEL[job.validation.status]}</${Badge}>
          ${job.source ? html`<span class="fact muted">${job.source.first_party ? 'Employer site' : humanize(job.source.kind)}${job.sources_count > 1 ? ` +${job.sources_count - 1}` : ''}</span>` : null}
          ${job.posted_at ? html`<span class="fact muted">Posted ${relTime(job.posted_at)}</span>` : null}
        </div>
      </div>
    </button>
    <button type="button" class=${`icon-btn save-btn ${job.saved ? 'on' : ''}`} aria-pressed=${job.saved ? 'true' : 'false'}
      aria-label=${job.saved ? 'Unsave job' : 'Save job'} disabled=${pendingSave} onClick=${() => toggleSaved(job.id)}>
      <${Icon} name="star" />
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
  return html`<div class="page">
    <${SearchLauncher} />
    <${RunPanel} />
    <${JobList} />
  </div>`;
}
