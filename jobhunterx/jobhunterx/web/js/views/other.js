// Tracker, Browser agent, Interventions, Settings.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadTracker, navigate, setTracking, loadInterventions, continueIntervention, skipIntervention, focusIntervention,
  stopBrowser, setTakeover, saveSettings, setModel, setPipelineMode, resetEverything, clearJobs, loadUsage,
} from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, PageHead, ScoreRing, Monogram, Seg, Select, CountUp, Orb, Spinner } from '../components/ui.js';
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

function KeysForm({ data }) {
  const [keys, setKeys] = useState({});
  const fields = [['google_api_key', 'Google AI (Gemma / Gemini)', 'google'], ['groq_api_key', 'Groq', 'groq'], ['mistral_api_key', 'Mistral', 'mistral'],
    ['tinyfish_api_key', 'TinyFish search', 'tinyfish'], ['tavily_api_key', 'Tavily search', 'tavily'], ['exa_api_key', 'Exa search', 'exa'], ['brave_api_key', 'Brave search', 'brave']];
  const dirty = Object.values(keys).some((v) => v);
  return html`<section class="set-section"><h2>API keys</h2><p class="muted small">Keys are stored in your local .env file and never shown again in full.</p>
    <div class="form-grid">${fields.map(([k, label, n]) => html`<${Field} label=${label} hint=${data[`${n}_configured`] ? `Configured (${data[`${n}_key_masked`]})` : 'Not configured'}>
      ${(id) => html`<input id=${id} class="input" type="password" autocomplete="off" value=${keys[k] || ''} placeholder=${data[`${n}_configured`] ? 'Leave empty to keep' : 'Paste key'} onInput=${(e) => setKeys({ ...keys, [k]: e.currentTarget.value })} />`}</${Field}>`)}</div>
    <${Button} variant="primary" disabled=${!dirty} onClick=${async () => { const body = Object.fromEntries(Object.entries(keys).filter(([, v]) => v)); if (await saveSettings(body)) setKeys({}); }}>Save keys</${Button}>
  </section>`;
}

const SETTINGS_SECTIONS = [
  { key: 'keys', label: 'API keys', icon: 'key' }, { key: 'search', label: 'Search', icon: 'search' },
  { key: 'models', label: 'AI models', icon: 'spark' }, { key: 'usage', label: 'Usage', icon: 'chart' },
  { key: 'agent', label: 'Auto-apply', icon: 'globe' }, { key: 'look', label: 'Appearance', icon: 'sun' },
  { key: 'data', label: 'Data', icon: 'shield' },
];

export function SettingsView() {
  const st = useStore((s) => s.settings);
  const models = useStore((s) => s.models);
  const usage = useStore((s) => s.usage);
  const mode = useStore((s) => s.pipelineMode);
  const theme = useStore((s) => s.theme);
  const [sec, setSec] = useState('keys');
  const d = st.data;
  const body = () => {
    switch (sec) {
      case 'keys': return d ? html`<${KeysForm} data=${d} />` : st.status === 'error' ? html`<${ErrorBox} message=${st.error} />` : html`<${Skeleton} lines=${6} />`;
      case 'search': return d ? html`<section class="set-section"><h2>Search</h2>
        <label class="switch"><input type="checkbox" checked=${d.enable_web_search_apis} onChange=${(e) => saveSettings({ enable_web_search_apis: e.currentTarget.checked })} /><span class="switch-ui"></span> Use web search APIs (otherwise only the free DuckDuckGo fallback)</label>
        <label class="switch"><input type="checkbox" checked=${d.strict_zero_spend_protection} onChange=${(e) => saveSettings({ strict_zero_spend_protection: e.currentTarget.checked })} /><span class="switch-ui"></span> Zero-spend protection (never exceed free allowances)</label>
        <div style=${{ maxWidth: '340px', marginTop: '18px' }}><${Field} label="Primary search provider">${(id) => html`<${Select} id=${id} block label="Primary search provider"
          value=${d.primary_search_provider} onChange=${(v) => saveSettings({ primary_search_provider: v })} options=${d.search_providers.map((p) => [p, humanize(p)])} />`}</${Field}></div>
      </section>` : html`<${Skeleton} lines=${4} />`;
      case 'models': return html`<section class="set-section"><h2>AI models</h2><p class="muted small">Pick the preferred first model for each task. If it is unavailable, the next one in the chain is used automatically.</p>
        ${models.data ? html`<div class="form-grid">${Object.entries(models.data.chains).map(([key, ch]) => html`<${Field} label=${ch.name}>${(id) => html`<${Select} id=${id} block label=${ch.name} value=${ch.selected} onChange=${(v) => setModel(key, v)}
          options=${ch.options.map((m, i) => [m, (models.data.all_models.find((x) => x.id === m) || {}).name || m, i === 0 ? 'Default first choice' : `Fallback ${i}`])} />`}</${Field}>`)}</div>`
          : models.status === 'error' ? html`<${ErrorBox} message=${models.error} />` : html`<${Skeleton} lines=${3} />`}</section>`;
      case 'usage': return html`<section class="set-section"><div class="row space"><h2>Usage</h2><${Button} size="sm" icon="refresh" busy=${usage.status === 'refreshing'} onClick=${loadUsage}>Refresh</${Button}></div>
        ${usage.data ? html`<table class="checks"><thead><tr><th>Model</th><th>Calls</th><th>Tokens</th></tr></thead><tbody>
          ${usage.data.llm.rows.map((r) => html`<tr><td>${r.label}</td><td>${fmtNum(r.calls)}</td><td>${fmtNum(r.total_tokens)}</td></tr>`)}
          ${!usage.data.llm.rows.length ? html`<tr><td colspan="3" class="muted">No AI calls yet.</td></tr>` : null}</tbody></table>
          <p class="muted small">Gemma today: ${usage.data.gemma_budget.requests_today} / ${usage.data.gemma_budget.requests_cap} requests.</p>` : usage.status === 'error' ? html`<${ErrorBox} message=${usage.error} />` : html`<${Skeleton} lines=${3} />`}</section>`;
      case 'agent': return html`<section class="set-section"><h2>Auto-apply mode</h2>
        <${Seg} label="Pipeline mode" options=${[['manual', 'Manual'], ['automatic', 'Automatic']]} value=${mode.mode} onChange=${setPipelineMode} />
        <p class="muted small" style=${{ marginTop: '12px' }}>Manual: the agent only applies when you click Auto-apply on a job.</p></section>`;
      case 'look': return html`<section class="set-section"><h2>Appearance</h2>
        <${Seg} label="Theme" options=${[['light', 'Light'], ['dark', 'Dark']]} value=${theme} onChange=${setTheme} /></section>`;
      default: return html`<section class="set-section"><h2>Data</h2><p class="muted small">Clearing jobs keeps your profile and documents. Reset removes everything.</p>
        <div class="row gap wrap"><${Button} onClick=${() => clearJobs('unsaved')}>Clear unsaved jobs</${Button}><${Button} onClick=${() => clearJobs('all')}>Clear all jobs</${Button}>
          <${Button} variant="danger" onClick=${resetEverything}>Reset everything</${Button}></div></section>`;
    }
  };
  return html`<div class="view view-settings">
    <${PageHead} title=${html`Settings`} sub="Keys, search providers, AI model preferences and usage." />
    <div class="split split-settings">
      <nav class="pane card set-nav" aria-label="Settings sections">${SETTINGS_SECTIONS.map((x) => html`<button type="button" key=${x.key}
        class=${`set-link ${sec === x.key ? 'active' : ''}`} aria-current=${sec === x.key ? 'true' : undefined} onClick=${() => setSec(x.key)}>
        <${Icon} name=${x.icon} size=${16} />${x.label}</button>`)}</nav>
      <section class="pane card"><div class="scroll pane-pad set-body" key=${sec}>${body()}</div></section>
    </div>
  </div>`;
}
