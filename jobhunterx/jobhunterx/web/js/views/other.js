// Tracker, Browser agent, Interventions, Settings.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadTracker, navigate, setTracking, loadInterventions, continueIntervention, skipIntervention, focusIntervention,
  stopBrowser, setTakeover, saveSettings, setModel, setPipelineMode, resetEverything, clearJobs, loadUsage,
  loadSettings, refreshModels, setProviders, loadDbHealth, repairDb, backupDb, setMotion,
} from '../actions.js';
import { PeopleManager } from './people.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, PageHead, ScoreRing, Monogram, Seg, Select, CountUp, Orb, Spinner, Notice } from '../components/ui.js';
import { TRACKING_LABEL, DEFAULT_TRACKING, relTime, humanize, fmtNum, safeUrl } from '../lib/format.js';
import { setTheme } from '../actions.js';
import { ReconnectingSocket } from '../lib/ws.js';
import { JobDetail } from './jobdetail.js';

// ---------------------------------------------------------------------------- tracker
// Stages follow the application journey; "Closed" gathers rejected and archived jobs.
const LANES = [
  { key: 'saved', label: 'Saved', statuses: ['saved'], next: 'preparing', tip: 'Generate a tailored resume, then move it to Preparing.' },
  { key: 'preparing', label: 'Preparing', statuses: ['preparing'], next: 'applied', tip: 'Documents ready? Apply and move it to Applied.' },
  { key: 'applied', label: 'Applied', statuses: ['applied'], next: 'interviewing', tip: 'Waiting to hear back — follow up after a week.' },
  { key: 'interviewing', label: 'Interviewing', statuses: ['interviewing'], next: 'offer', tip: 'In conversation — prepare from the job requirements.' },
  { key: 'offer', label: 'Offer', statuses: ['offer'], next: null, tip: 'Decision time.' },
  { key: 'closed', label: 'Closed', statuses: ['rejected', 'archived'], next: null, tip: 'Rejected or archived.' },
];
const laneOf = (status) => LANES.find((l) => l.statuses.includes(status)) || LANES[0];

function StageBar({ jobs, value, onChange }) {
  const total = jobs.length;
  const items = [{ key: 'all', label: 'All', n: total }, ...LANES.map((l) => ({ key: l.key, label: l.label, n: jobs.filter((j) => l.statuses.includes(j.tracking_status)).length }))];
  return html`<nav class="stagebar card" aria-label="Pipeline stages">${items.map((it, i) => html`<button type="button" key=${it.key}
      class=${`stage-tab s-${it.key} ${value === it.key ? 'on' : ''}`} aria-pressed=${value === it.key ? 'true' : 'false'} style=${{ '--i': i }} onClick=${() => onChange(it.key)}>
      <span class="st-n"><${CountUp} value=${it.n} /></span>
      <span class="st-l">${it.key !== 'all' ? html`<i class="st-dot"></i>` : null}${it.label}</span>
      ${it.key !== 'all' ? html`<span class="st-bar"><span style=${{ width: `${total ? (it.n / total) * 100 : 0}%` }}></span></span>` : null}
    </button>${i > 0 && i < items.length - 1 ? html`<span class="st-arrow" aria-hidden="true"><${Icon} name="next" size=${13} /></span>` : null}`)}</nav>`;
}

function TrackRow({ job, statuses, selected, index, onOpen }) {
  const pending = useStore((s) => !!s.pending.track[job.id]);
  const lane = laneOf(job.tracking_status);
  const next = lane.next && LANES.find((l) => l.key === lane.next);
  const docs = job.documents || {};
  return html`<article class=${`track-row job-card ${selected ? 'is-selected' : ''} ${pending ? 'is-moving' : ''}`} style=${{ '--i': Math.min(index, 14) }}>
    <button type="button" class="job-main tr-main" onClick=${() => onOpen(job.id)} aria-label=${`Open ${job.title} at ${job.company}`} aria-current=${selected ? 'true' : undefined}>
      <${Monogram} name=${job.company} size=${38} />
      <div class="grow">
        <div class="job-company">${job.company || 'Unknown company'}<span class="job-when">${job.posted_at ? relTime(job.posted_at) : relTime(job.discovered_at)}</span></div>
        <strong class="track-title">${job.title}</strong>
        <div class="tr-sub"><span class=${`tc-doc ${docs.resume ? 'on' : ''}`}><${Icon} name="doc" size=${12} />${docs.resume ? 'Resume ready' : 'No resume yet'}</span>
          <span>${job.location || 'Location not stated'}</span></div>
      </div>
      <${ScoreRing} score=${job.match ? job.match.score : null} verdict=${job.match && job.match.verdict} size=${42} />
    </button>
    <div class="tr-actions">
      <${Select} size="sm" label=${`Status for ${job.title}`} tone=${`s-${job.tracking_status}`} value=${job.tracking_status}
        onChange=${(v) => setTracking(job.id, v)} options=${statuses.map((t) => [t, TRACKING_LABEL[t] || humanize(t)])} />
      ${next ? html`<button type="button" class="advance" disabled=${pending} onClick=${() => setTracking(job.id, next.key)} title=${`Move to ${next.label}`}>
        ${next.label} <${Icon} name="arrow" size=${13} /></button>` : null}
    </div>
  </article>`;
}

function TrackerOverview({ jobs }) {
  const total = jobs.length;
  const max = Math.max(1, ...LANES.map((l) => jobs.filter((j) => l.statuses.includes(j.tracking_status)).length));
  const scored = jobs.filter((j) => j.match);
  const avg = scored.length ? Math.round(scored.reduce((a, j) => a + j.match.score, 0) / scored.length) : null;
  const needResume = jobs.filter((j) => ['saved', 'preparing'].includes(j.tracking_status) && !(j.documents && j.documents.resume));
  const active = jobs.filter((j) => ['applied', 'interviewing', 'offer'].includes(j.tracking_status)).length;
  return html`<div class="tk-overview scroll">
    <div class="tk-hero"><h2>Your <span class="serif">pipeline</span></h2><p class="muted small">Select a job on the left to see its details, documents and score — or move it forward with one click.</p></div>
    <div class="tk-stats">
      <div><span class="n"><${CountUp} value=${total} /></span><span class="l">tracked</span></div>
      <div><span class="n"><${CountUp} value=${active} /></span><span class="l">in progress</span></div>
      <div><span class="n">${avg == null ? '–' : html`<${CountUp} value=${avg} />`}</span><span class="l">avg. match</span></div>
    </div>
    <div class="funnel">${LANES.map((l, i) => {
      const n = jobs.filter((j) => l.statuses.includes(j.tracking_status)).length;
      return html`<div class=${`fn-row s-${l.key}`} key=${l.key} style=${{ '--i': i }}><span class="fn-label">${l.label}</span>
        <span class="fn-track"><span class="fn-fill" style=${{ width: `${(n / max) * 100}%` }}></span></span><span class="fn-n">${n}</span></div>`;
    })}</div>
    ${needResume.length ? html`<div class="tk-todo"><div class="sec-title">Next steps</div>
      ${needResume.slice(0, 5).map((j, i) => html`<a class="todo" key=${j.id} style=${{ '--i': i }} href=${`#/tracker/job/${encodeURIComponent(j.id)}`}>
        <span class="todo-ico"><${Icon} name="spark" size=${14} /></span><span class="grow">Tailor a resume for <strong>${j.title}</strong> at ${j.company}</span><${Icon} name="arrow" size=${14} /></a>`)}
    </div>` : null}
  </div>`;
}

export function TrackerView() {
  const tr = useStore((s) => s.tracker);
  const byId = useStore((s) => s.jobs.byId);
  const route = useStore((s) => s.route);
  const statuses = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const [stage, setStage] = useState('all');
  const [q, setQ] = useState('');
  const jobs = tr.ids.map((id) => byId[id]).filter(Boolean);
  const open = (id) => navigate(`#/tracker/job/${encodeURIComponent(id)}`);
  const close = () => navigate('#/tracker');
  useEffect(() => {
    if (!route.jobId) return undefined;
    const onKey = (e) => { if (e.key === 'Escape' && !document.querySelector('.overlay, .popover, .select-list')) close(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [route.jobId]);
  const needle = q.trim().toLowerCase();
  const visible = jobs.filter((j) => (stage === 'all' || LANES.find((l) => l.key === stage).statuses.includes(j.tracking_status))
    && (!needle || `${j.title} ${j.company} ${j.location}`.toLowerCase().includes(needle)));
  const groups = (stage === 'all' ? LANES : LANES.filter((l) => l.key === stage))
    .map((l) => [l, visible.filter((j) => l.statuses.includes(j.tracking_status)).sort((a, b) => (b.match ? b.match.score : -1) - (a.match ? a.match.score : -1))])
    .filter(([, g]) => g.length);
  let k = 0;
  return html`<div class="view view-tracker">
    <${PageHead} title=${html`Application <span class="serif">tracker</span>`} sub="Every saved job, from shortlist to offer — move it forward with one click."
      actions=${html`<${Button} icon="refresh" busy=${tr.status === 'refreshing'} onClick=${loadTracker}>Refresh</${Button}>`} />
    ${tr.status === 'error' ? html`<${ErrorBox} message=${tr.error} onRetry=${loadTracker} />` : null}
    ${tr.status === 'ready' && !jobs.length ? html`<div class="card pane-center grow-fill"><${EmptyState} icon="star" title="Nothing tracked yet"
      action=${html`<${Button} variant="primary" onClick=${() => navigate('#/discover')}>Find roles <${Icon} name="arrow" size=${16} /></${Button}>`}>Star a job in Discover and it lands here, ready to move from shortlist to offer.</${EmptyState}></div>` : html`
    <${StageBar} jobs=${jobs} value=${stage} onChange=${setStage} />
    <div class=${`split split-tracker ${route.jobId ? 'has-detail' : ''}`}>
      <section class="pane list-pane card" aria-label="Tracked jobs">
        <div class="tk-tools"><label class="search-field"><${Icon} name="search" size=${15} />
          <input type="search" placeholder="Filter tracked jobs" aria-label="Filter tracked jobs" value=${q} onInput=${(e) => setQ(e.currentTarget.value)} /></label></div>
        <div class="scroll tk-list">
          ${tr.status === 'loading' ? html`<${Skeleton} rows=${4} />` : null}
          ${tr.status !== 'loading' && !groups.length ? html`<${EmptyState} icon="info" title="Nothing here">${needle ? 'No tracked jobs match this filter.' : 'No jobs at this stage yet.'}</${EmptyState}>` : null}
          ${groups.map(([lane, g]) => html`<section class="tk-group" key=${lane.key}>
            <header class=${`tk-group-head s-${lane.key}`}><i class="st-dot"></i>${lane.label}<span class="board-count">${g.length}</span><span class="tk-tip">${lane.tip}</span></header>
            ${g.map((j) => html`<${TrackRow} key=${j.id} job=${j} index=${k++} statuses=${statuses} selected=${route.jobId === j.id} onOpen=${open} />`)}
          </section>`)}
        </div>
      </section>
      <section class="pane detail-pane card" aria-label=${route.jobId ? 'Job details' : 'Pipeline overview'}>
        ${route.jobId ? html`<${JobDetail} key=${route.jobId} jobId=${route.jobId} onClose=${close} />` : html`<${TrackerOverview} jobs=${jobs} />`}
      </section>
    </div>`}
  </div>`;
}

// ---------------------------------------------------------------------------- browser agent
function agentState(b, waiting) {
  if (waiting) return { key: 'help', label: 'Needs you', tone: 'warning' };
  if (b.active) return { key: 'work', label: 'Working', tone: 'accent' };
  if (b.steps.length) return { key: 'done', label: 'Finished', tone: 'success' };
  return { key: 'idle', label: 'Idle', tone: 'neutral' };
}

export function BrowserView() {
  const b = useStore((s) => s.browser);
  const job = useStore((s) => (s.browser.jobId ? s.jobs.byId[s.browser.jobId] : null));
  const waiting = useStore((s) => s.interventions.items.length);
  const canvas = useRef();
  const sock = useRef();
  const [hasFrame, setHasFrame] = useState(false);
  useEffect(() => {
    const ctx = canvas.current.getContext('2d');
    const img = new Image();
    img.onload = () => { canvas.current.width = img.width; canvas.current.height = img.height; ctx.drawImage(img, 0, 0); setHasFrame(true); };
    sock.current = new ReconnectingSocket('/ws/browser', {
      onMessage: (m) => { if (m.type === 'frame' && typeof m.data === 'string') img.src = `data:image/jpeg;base64,${m.data}`; },
    });
    sock.current.connect();
    return () => sock.current.close();
  }, []);
  const coords = (e) => {
    const r = canvas.current.getBoundingClientRect();
    return { x: Math.round(((e.clientX - r.left) / r.width) * canvas.current.width), y: Math.round(((e.clientY - r.top) / r.height) * canvas.current.height) };
  };
  const send = (msg) => b.takeover && sock.current && sock.current.send(msg);
  const st = agentState(b, waiting);
  let host = '';
  try { host = b.url ? new URL(b.url).host : ''; } catch { host = b.url; }
  return html`<div class="view view-browser">
    <${PageHead} title=${html`Auto-apply <span class="serif">agent</span>`} sub="Watch the agent fill applications live. Take over any time to type or solve a CAPTCHA yourself." />
    <div class="split split-browser">
      <section class=${`pane browser-window ${b.takeover ? 'takeover' : ''} ${b.active ? 'is-live' : ''}`} aria-label="Live browser">
        <div class="bw-chrome">
          <span class="bw-lights" aria-hidden="true"><i></i><i></i><i></i></span>
          <div class="bw-url"><${Icon} name="shield" size=${13} /><span class="bw-host">${host || 'about:blank'}</span>
            ${b.title ? html`<span class="bw-title">${b.title}</span>` : null}</div>
          ${b.active ? html`<span class="live-pill"><i></i>Live</span>` : html`<span class="live-pill off"><i></i>Offline</span>`}
        </div>
        <div class="bw-stage">
          <canvas ref=${canvas} tabindex="0" aria-label="Live browser view" class=${hasFrame ? 'on' : ''}
            onClick=${(e) => send({ type: 'mouse', action: 'click', ...coords(e), button: 0 })}
            onWheel=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'wheel', deltaX: e.deltaX, deltaY: e.deltaY }); } }}
            onKeyDown=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'keyboard', action: 'keyDown', key: e.key, text: e.key.length === 1 ? e.key : '' }); } }}
            onKeyUp=${(e) => b.takeover && send({ type: 'keyboard', action: 'keyUp', key: e.key })}></canvas>
          ${b.takeover ? html`<div class="control-banner"><${Icon} name="hand" size=${15} /> You're in control — clicks and keys go straight to the page</div>` : null}
          ${!hasFrame ? html`<div class="bw-idle">
            <div class="bw-illus" aria-hidden="true"><${Orb} size=${150} active=${b.active} /><span class="bw-cursor"><svg width="22" height="22" viewBox="0 0 24 24"><path d="M5 3l14 7-6 2-2 6z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg></span></div>
            <h2>${b.active ? html`Connecting to the <span class="serif">browser</span>…` : html`The agent is <span class="serif">resting</span>`}</h2>
            <p class="muted">${b.active ? 'The live view appears as soon as the first page loads.' : 'Start Auto-apply on any job and you will see every click and keystroke here, live.'}</p>
            ${!b.active ? html`<ol class="bw-how"><li><span>1</span>Open a job in Discover</li><li><span>2</span>Generate its tailored resume</li><li><span>3</span>Press Auto-apply and watch</li></ol>
              <${Button} variant="primary" onClick=${() => navigate('#/discover')}>Pick a job <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          </div>` : null}
        </div>
      </section>
      <aside class="pane card agent-panel" aria-label="Agent">
        <div class="ap-head">
          <div class=${`ap-status st-${st.key}`}><span class="ap-dot"></span>${st.label}</div>
          ${job ? html`<div class="ap-job"><${Monogram} name=${job.company} size=${36} /><div class="grow"><div class="job-company">${job.company}</div>
            <strong>${job.title}</strong></div></div>` : html`<p class="muted small">No application in progress.</p>`}
          ${b.lastMessage ? html`<div class="ap-now" key=${b.lastMessage}>${b.active ? html`<${Spinner} size=${14} />` : html`<${Icon} name="check" size=${14} />`}<span>${b.lastMessage}</span></div>` : null}
          <div class="ap-controls">
            <${Button} size="sm" variant=${b.takeover ? 'primary' : 'secondary'} icon="hand" onClick=${() => setTakeover(!b.takeover)}>${b.takeover ? 'Release control' : 'Take over'}</${Button}>
            <${Button} size="sm" variant="danger" icon="stop" disabled=${!b.active} onClick=${stopBrowser}>Stop</${Button}>
          </div>
          ${waiting ? html`<a class="ap-alert" href="#/interventions"><${Icon} name="alert" size=${15} /> The agent is waiting for you <${Icon} name="arrow" size=${14} /></a>` : null}
        </div>
        <div class="ap-log-head"><span class="sec-title">Activity</span><span class="muted small">${b.steps.length} step${b.steps.length === 1 ? '' : 's'}</span></div>
        <div class="scroll ap-log">
          ${b.steps.length ? html`<ol class="timeline-v">${b.steps.map((s, i) => html`<li key=${s.id} class=${i === 0 && b.active ? 'now' : ''}>
            <span class="tv-dot"></span><div class="tv-body"><div>${s.message}</div><span class="muted small">${relTime(s.ts)}</span></div></li>`)}</ol>`
            : html`<div class="ap-empty"><${Icon} name="info" size=${16} /> Steps appear here as the agent works — page loads, fields filled, buttons pressed.</div>`}
        </div>
      </aside>
    </div></div>`;
}

export function InterventionsView() {
  const iv = useStore((s) => s.interventions);
  return html`<div class="view view-interventions">
    <${PageHead} title=${html`Needs <span class="serif">you</span>`} sub="When the agent hits a login wall, CAPTCHA or one-time code, it pauses here."
      actions=${html`<${Button} icon="refresh" busy=${iv.status === 'refreshing'} onClick=${loadInterventions}>Refresh</${Button}>`} />
    <section class="pane card"><div class="scroll pane-pad">
    ${iv.status === 'error' ? html`<${ErrorBox} message=${iv.error} onRetry=${loadInterventions} />` : null}
    ${iv.status === 'loading' ? html`<${Skeleton} rows=${3} />` : null}
    ${iv.status === 'ready' && !iv.items.length ? html`<div class="pane-center"><${EmptyState} icon="check" title="Nothing needs you">The agent is not waiting on anything.</${EmptyState}></div>` : null}
    <div class="stack">${iv.items.map((it) => html`<div class="iv-row row space wrap" key=${it.id}>
      <div><${Badge} tone="warning">${humanize(it.hitl_type)}</${Badge}> <strong>${it.role || 'Application'}</strong> <span class="muted">@ ${it.company || '—'} · ${relTime(it.created_at)}</span></div>
      <div class="row gap"><${Button} onClick=${() => focusIntervention(it)}>Show browser</${Button}>
        <${Button} variant="primary" onClick=${() => continueIntervention(it)}>Continue</${Button}>
        <${Button} onClick=${() => skipIntervention(it)}>Skip</${Button}></div></div>`)}</div>
    </div></section>
  </div>`;
}

// ---------------------------------------------------------------------------- settings
const LLM_META = {
  google: { name: 'Google AI Studio', field: 'google_api_key', hint: 'Gemma 4 31B and Gemini 3.5 Flash Lite', url: 'aistudio.google.com' },
  groq: { name: 'Groq', field: 'groq_api_key', hint: 'GPT-OSS, Kimi K2, Qwen3 — very fast', url: 'console.groq.com' },
  mistral: { name: 'Mistral', field: 'mistral_api_key', hint: 'Mistral Medium / Small / Large (latest)', url: 'console.mistral.ai' },
};
const SEARCH_META = {
  tinyfish: { name: 'TinyFish', field: 'tinyfish_api_key', hint: 'Search API — free utility credits' },
  tavily: { name: 'Tavily', field: 'tavily_api_key', hint: 'Monthly free credits; good snippets' },
  exa: { name: 'Exa', field: 'exa_api_key', hint: 'Neural search; free monthly credits' },
  brave: { name: 'Brave Search', field: 'brave_api_key', hint: 'Independent index; free monthly queries' },
  ddgs: { name: 'DuckDuckGo', field: null, hint: 'No key needed — always-available fallback' },
};
const STRATEGIES = [
  ['fallback', 'Fallback', 'Ask providers in order; the first with results answers. Fewest calls.'],
  ['spread', 'Spread', 'Rotate queries across providers so free quotas are shared.'],
  ['combine', 'Combine', 'Two providers answer every query and results merge. Widest coverage, uses more quota.'],
];
const fmtLimit = (l) => [l.rpm && `${l.rpm} RPM`, l.rpd && `${fmtNum(l.rpd)}/day`, l.tpm && `${fmtNum(l.tpm)} TPM`, l.tpd && `${fmtNum(l.tpd)} TPD`].filter(Boolean).join(' · ') || 'account limits';

function KeyField({ field, configured, masked, source, label }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState('');
  const [busy, setBusy] = useState(false);
  const save = async (v) => { setBusy(true); const ok = await saveSettings({ [field]: v }); setBusy(false); if (ok) { setEditing(false); setVal(''); } };
  if (!editing) {
    return html`<div class="key-row">
      <span class=${`key-pill ${configured ? 'on' : ''}`}><${Icon} name="key" size=${13} />${configured ? masked : 'No key'}</span>
      ${configured && source ? html`<span class="muted small">from ${source}</span>` : null}
      <${Button} size="sm" onClick=${() => setEditing(true)}>${configured ? 'Replace' : 'Add key'}</${Button}>
      ${configured ? html`<button type="button" class="link-btn small" onClick=${() => save('')}>Remove</button>` : null}
    </div>`;
  }
  return html`<div class="key-row editing">
    <input class="input" type="password" autocomplete="off" aria-label=${`${label} API key`} placeholder="Paste key" value=${val}
      onInput=${(e) => setVal(e.currentTarget.value)} onKeyDown=${(e) => { if (e.key === 'Enter' && val.trim()) save(val.trim()); if (e.key === 'Escape') setEditing(false); }} />
    <${Button} size="sm" variant="primary" busy=${busy} disabled=${!val.trim()} onClick=${() => save(val.trim())}>Save</${Button}>
    <${Button} size="sm" onClick=${() => setEditing(false)}>Cancel</${Button}>
  </div>`;
}

function Toggle({ on, onChange, label }) {
  return html`<label class="switch" title=${label}><input type="checkbox" checked=${on} aria-label=${label} onChange=${(e) => onChange(e.currentTarget.checked)} /><span class="switch-ui"></span></label>`;
}

function AiSection({ d, models }) {
  const md = models.data;
  return html`<section class="set-section">
    <div class="row space"><h2>AI providers</h2>
      <${Button} size="sm" icon="refresh" busy=${models.status === 'refreshing' || models.status === 'loading'} onClick=${refreshModels}>Check available models</${Button}></div>
    <p class="muted small">Turn a provider off to never use it. Keys are read from your .env file (or system environment) and can be changed here — they are written back to .env.</p>
    <div class="prov-list">${Object.entries(LLM_META).map(([k, m]) => {
      const st = md && md.providers[k];
      const on = d.providers.llm[k] !== false;
      return html`<div class=${`prov-card ${on ? '' : 'off'}`} key=${k}>
        <div class="prov-head"><div class="grow"><strong>${m.name}</strong><div class="muted small">${m.hint} · keys at ${m.url}</div></div>
          ${st && st.configured ? html`<span class=${`status-dot ${st.reachable === false ? 'bad' : st.reachable ? 'good' : ''}`}
            title=${st.error || ''}>${st.reachable === false ? 'Key rejected / unreachable' : st.reachable ? `${st.models_listed} models available` : 'Not checked yet'}</span>` : null}
          <${Toggle} on=${on} label=${`Use ${m.name}`} onChange=${(v) => setProviders({ llm: { [k]: v } })} /></div>
        <${KeyField} field=${m.field} label=${m.name} configured=${d[`${k}_configured`]} masked=${d[`${k}_key_masked`]} source=${d[`${k}_source`]} />
      </div>`;
    })}</div>
    <h3 class="sub-title">Model for each task</h3>
    <p class="muted small">The chosen model is tried first; if it's busy, rate limited or unavailable the next one in the list takes over automatically. Free-tier limits are shown for each model.</p>
    ${md ? html`<div class="form-grid">${Object.entries(md.chains).map(([key, ch]) => html`<${Field} label=${ch.name}>${(id) => html`<${Select} id=${id} block label=${ch.name}
        value=${ch.selected} onChange=${(v) => setModel(key, v)}
        options=${ch.options.map((mid) => { const m = md.all_models.find((x) => x.id === mid) || { name: mid, limits: {} };
          return [mid, `${m.name}${m.reason ? ` — ${m.reason}` : ''}`, fmtLimit(m.limits || {})]; })} />`}</${Field}>`)}</div>`
      : models.status === 'error' ? html`<${ErrorBox} message=${models.error} />` : html`<${Skeleton} lines=${3} />`}
  </section>`;
}

function SearchSection({ d }) {
  const order = d.providers.search_order;
  const move = (p, dir) => {
    const i = order.indexOf(p); const j = i + dir;
    if (j < 0 || j >= order.length) return;
    const next = order.slice(); [next[i], next[j]] = [next[j], next[i]];
    setProviders({ search_order: next });
  };
  return html`<section class="set-section"><h2>Web search</h2>
    <p class="muted small">Providers are asked in this order. Turn any off; DuckDuckGo needs no key and is the safety net.</p>
    <div class="field" style=${{ margin: '12px 0 16px' }}><span class="field-label">Strategy</span>
      <${Seg} label="Search strategy" options=${STRATEGIES.map(([k, l]) => [k, l])} value=${d.providers.search_strategy} onChange=${(v) => setProviders({ search_strategy: v })} />
      <span class="field-hint">${(STRATEGIES.find((x) => x[0] === d.providers.search_strategy) || STRATEGIES[0])[2]}</span></div>
    <div class="prov-list">${order.map((k, idx) => { const m = SEARCH_META[k]; if (!m) return null;
      const on = d.providers.search[k] !== false;
      return html`<div class=${`prov-card ${on ? '' : 'off'}`} key=${k}>
        <div class="prov-head"><span class="order-n">${idx + 1}</span>
          <div class="grow"><strong>${m.name}</strong><div class="muted small">${m.hint}</div></div>
          <div class="order-btns"><button type="button" class="icon-btn" aria-label=${`Move ${m.name} up`} disabled=${idx === 0} onClick=${() => move(k, -1)}><${Icon} name="back" size=${14} /></button>
            <button type="button" class="icon-btn" aria-label=${`Move ${m.name} down`} disabled=${idx === order.length - 1} onClick=${() => move(k, 1)}><${Icon} name="next" size=${14} /></button></div>
          <${Toggle} on=${on} label=${`Use ${m.name}`} onChange=${(v) => setProviders({ search: { [k]: v } })} /></div>
        ${m.field ? html`<${KeyField} field=${m.field} label=${m.name} configured=${d[`${k}_configured`]} masked=${d[`${k}_key_masked`]} source=${d[`${k}_source`]} />` : null}
      </div>`; })}</div>
    <div class="stack" style=${{ gap: '4px', marginTop: '16px' }}>
      <label class="switch"><input type="checkbox" checked=${d.enable_web_search_apis} onChange=${(e) => saveSettings({ enable_web_search_apis: e.currentTarget.checked })} /><span class="switch-ui"></span> Use keyed search APIs (off = DuckDuckGo only)</label>
      <label class="switch"><input type="checkbox" checked=${d.strict_zero_spend_protection} onChange=${(e) => saveSettings({ strict_zero_spend_protection: e.currentTarget.checked })} /><span class="switch-ui"></span> Zero-spend protection (never exceed a provider's free allowance)</label>
    </div>
  </section>`;
}

function TuningSection({ d }) {
  const [t, setT] = useState(d.tunables);
  const dirty = JSON.stringify(t) !== JSON.stringify(d.tunables);
  const num = (k, label, hint, step = 1) => html`<${Field} label=${label} hint=${hint}>${(id) => html`<input id=${id} class="input" type="number" step=${step} value=${t[k]}
    onInput=${(e) => setT({ ...t, [k]: e.currentTarget.value })} />`}</${Field}>`;
  return html`<section class="set-section"><h2>Search tuning</h2><p class="muted small">Loaded from your .env file; saving writes them back.</p>
    <div class="form-grid">
      ${num('max_jobs_per_search', 'Jobs analysed per search', '5–200. More jobs = longer searches and more AI calls.')}
      ${num('max_llm_jd_extractions_per_search', 'Deep AI reads per search', 'How many postings get a full AI read.')}
      ${num('fetch_timeout_s', 'Page fetch timeout (s)', 'How long to wait for a job page.', 0.5)}
      ${num('exa_search_num_results', 'Exa results per query', '1–50')}
      <${Field} label="Tavily depth">${(id) => html`<${Select} id=${id} block label="Tavily depth" value=${t.tavily_search_depth}
        onChange=${(v) => setT({ ...t, tavily_search_depth: v })} options=${[['basic', 'Basic', '1 credit'], ['advanced', 'Advanced', '2 credits']]} />`}</${Field}>
      <div class="field"><span class="field-label">Browser agent window</span>
        <label class="switch"><input type="checkbox" checked=${!!t.browser_use_headless} onChange=${(e) => setT({ ...t, browser_use_headless: e.currentTarget.checked })} /><span class="switch-ui"></span> Run headless (streamed here)</label></div>
    </div>
    <div class="row gap"><${Button} variant="primary" disabled=${!dirty} onClick=${() => saveSettings({ tunables: t })}>Save</${Button}>
      <${Button} disabled=${!dirty} onClick=${() => setT(d.tunables)}>Discard</${Button}></div>
  </section>`;
}

function DataSection() {
  const db = useStore((s) => s.db);
  useEffect(() => { loadDbHealth(); }, []);
  const r = db.data;
  return html`<section class="set-section"><div class="row space"><h2>Data & database</h2>
      <div class="row gap"><${Button} size="sm" icon="download" onClick=${backupDb}>Back up</${Button}>
        <${Button} size="sm" icon="refresh" busy=${db.status === 'refreshing'} onClick=${repairDb}>Check & repair</${Button}></div></div>
    <p class="muted small">The database is checked every time JobHunterX starts; damaged files are set aside and recovered automatically.</p>
    ${db.status === 'error' ? html`<${ErrorBox} message=${db.error} onRetry=${loadDbHealth} />` : null}
    ${r ? html`<div class="health">
      <div class=${`health-badge h-${r.status}`}><${Icon} name=${r.status === 'ok' ? 'check' : 'alert'} size=${16} />${r.status === 'ok' ? 'Healthy' : r.status === 'warn' ? 'Needs attention' : 'Problems found'}
        <span class="muted small">schema v${r.schema_version || '?'} · ${(r.size_bytes / 1048576).toFixed(1)} MB · ${Object.entries(r.counts || {}).map(([k, v]) => `${v} ${k.replace('_', ' ')}`).join(' · ')}</span></div>
      ${r.preflight && r.preflight.status === 'recovered' ? html`<${Notice} tone="warning">${r.preflight.detail}</${Notice}>` : null}
      <ul class="health-list">${r.checks.map((c) => html`<li key=${c.name} class=${`h-${c.status}`}><span class="h-dot"></span><strong>${c.name}</strong><span class="muted small">${c.detail}</span></li>`)}</ul>
    </div>` : db.status !== 'error' ? html`<${Skeleton} lines=${4} />` : null}
    <h3 class="sub-title">Clean up</h3>
    <div class="row gap wrap"><${Button} onClick=${() => clearJobs('unsaved')}>Clear unsaved jobs</${Button}><${Button} onClick=${() => clearJobs('all')}>Clear all jobs</${Button}>
      <${Button} variant="danger" onClick=${resetEverything}>Reset everything</${Button}></div>
  </section>`;
}

const SETTINGS_SECTIONS = [
  { key: 'ai', label: 'AI providers', icon: 'spark' }, { key: 'search', label: 'Web search', icon: 'search' },
  { key: 'tuning', label: 'Search tuning', icon: 'sliders' }, { key: 'usage', label: 'Usage', icon: 'chart' },
  { key: 'profiles', label: 'Profiles', icon: 'user' }, { key: 'agent', label: 'Auto-apply', icon: 'globe' },
  { key: 'look', label: 'Appearance', icon: 'sun' }, { key: 'data', label: 'Data', icon: 'shield' },
];

export function SettingsView() {
  const st = useStore((s) => s.settings);
  const models = useStore((s) => s.models);
  const usage = useStore((s) => s.usage);
  const mode = useStore((s) => s.pipelineMode);
  const theme = useStore((s) => s.theme);
  const motion = useStore((s) => s.motion);
  const [sec, setSec] = useState('ai');
  const d = st.data;
  const needData = ['ai', 'search', 'tuning'].includes(sec);
  const body = () => {
    if (needData && !d) return st.status === 'error' ? html`<${ErrorBox} message=${st.error} onRetry=${loadSettings} />` : html`<${Skeleton} lines=${6} />`;
    switch (sec) {
      case 'ai': return html`<${AiSection} d=${d} models=${models} />`;
      case 'search': return html`<${SearchSection} d=${d} />`;
      case 'tuning': return html`<${TuningSection} key=${JSON.stringify(d.tunables)} d=${d} />`;
      case 'usage': return html`<section class="set-section"><div class="row space"><h2>Usage</h2><${Button} size="sm" icon="refresh" busy=${usage.status === 'refreshing'} onClick=${loadUsage}>Refresh</${Button}></div>
        ${usage.data ? html`<table class="checks"><thead><tr><th>Model</th><th>Calls</th><th>Tokens</th></tr></thead><tbody>
          ${usage.data.llm.rows.map((r) => html`<tr><td>${r.label}</td><td>${fmtNum(r.calls)}</td><td>${fmtNum(r.total_tokens)}</td></tr>`)}
          ${!usage.data.llm.rows.length ? html`<tr><td colspan="3" class="muted">No AI calls yet.</td></tr>` : null}</tbody></table>
          <p class="muted small">Gemma today: ${usage.data.gemma_budget.requests_today} / ${usage.data.gemma_budget.requests_cap} requests (${usage.data.gemma_budget.model}).</p>`
          : usage.status === 'error' ? html`<${ErrorBox} message=${usage.error} />` : html`<${Skeleton} lines=${3} />`}</section>`;
      case 'profiles': return html`<${PeopleManager} />`;
      case 'agent': return html`<section class="set-section"><h2>Auto-apply mode</h2>
        <${Seg} label="Pipeline mode" options=${[['manual', 'Manual'], ['automatic', 'Automatic']]} value=${mode.mode} onChange=${setPipelineMode} />
        <p class="muted small" style=${{ marginTop: '12px' }}>Manual: the agent only applies when you click Auto-apply on a job.</p></section>`;
      case 'look': return html`<section class="set-section"><h2>Appearance</h2>
        <div class="field"><span class="field-label">Theme</span><${Seg} label="Theme" options=${[['light', 'Light'], ['dark', 'Dark']]} value=${theme} onChange=${setTheme} /></div>
        <div class="field" style=${{ marginTop: '16px' }}><span class="field-label">Motion</span>
          <${Seg} label="Motion" options=${[['full', 'Full'], ['reduced', 'Reduced'], ['system', 'Follow system']]} value=${motion} onChange=${setMotion} />
          <span class="field-hint">${motion === 'system' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
            ? 'Your system currently asks for reduced motion (Windows: Settings → Accessibility → Visual effects → Animation effects), so animations are minimal.'
            : 'Full keeps every animation; Reduced keeps only loading indicators.'}</span></div></section>`;
      default: return html`<${DataSection} />`;
    }
  };
  return html`<div class="view view-settings">
    <${PageHead} title=${html`Settings`} sub="Providers, keys, search behaviour, profiles and data — all in one place." />
    <div class="split split-settings">
      <nav class="pane card set-nav" aria-label="Settings sections">${SETTINGS_SECTIONS.map((x) => html`<button type="button" key=${x.key}
        class=${`set-link ${sec === x.key ? 'active' : ''}`} aria-current=${sec === x.key ? 'true' : undefined} onClick=${() => setSec(x.key)}>
        <${Icon} name=${x.icon} size=${16} />${x.label}</button>`)}</nav>
      <section class="pane card"><div class="scroll pane-pad set-body" key=${sec}>${body()}</div></section>
    </div>
  </div>`;
}
