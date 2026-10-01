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

// ---------------------------------------------------------------------------- tracker
// Lanes follow the application journey; "Closed" gathers rejected and archived jobs.
const LANES = [
  { key: 'saved', label: 'Saved', hint: 'Shortlisted', statuses: ['saved'], drop: 'saved' },
  { key: 'preparing', label: 'Preparing', hint: 'Tailoring documents', statuses: ['preparing'], drop: 'preparing' },
  { key: 'applied', label: 'Applied', hint: 'Waiting to hear back', statuses: ['applied'], drop: 'applied' },
  { key: 'interviewing', label: 'Interviewing', hint: 'In conversation', statuses: ['interviewing'], drop: 'interviewing' },
  { key: 'offer', label: 'Offer', hint: 'Decision time', statuses: ['offer'], drop: 'offer' },
  { key: 'closed', label: 'Closed', hint: 'Rejected or archived', statuses: ['rejected', 'archived'], drop: 'archived' },
];

function TrackCard({ job, statuses, selected, index, onOpen }) {
  const pending = useStore((s) => !!s.pending.track[job.id]);
  const [dragging, setDragging] = useState(false);
  const apply = safeUrl(job.apply_url);
  const docs = job.documents || {};
  return html`<article class=${`track-card job-card ${selected ? 'is-selected' : ''} ${dragging ? 'dragging' : ''} ${pending ? 'is-moving' : ''}`} style=${{ '--i': index }}
      draggable="true" onDragStart=${(e) => { e.dataTransfer.setData('text/x-job', job.id); e.dataTransfer.effectAllowed = 'move'; setDragging(true); }}
      onDragEnd=${() => setDragging(false)}>
    <button type="button" class="job-main" onClick=${() => onOpen(job.id)} aria-label=${`Open ${job.title} at ${job.company}`}>
      <div class="tc-top"><${Monogram} name=${job.company} size=${34} />
        <div class="grow"><div class="job-company">${job.company || 'Unknown company'}</div><strong class="track-title">${job.title}</strong></div>
        <${ScoreRing} score=${job.match ? job.match.score : null} verdict=${job.match && job.match.verdict} size=${40} /></div>
      <div class="tc-meta"><span><${Icon} name="pin" size=${12} />${job.location || 'Location not stated'}</span>
        <span>${job.posted_at ? `Posted ${relTime(job.posted_at)}` : `Found ${relTime(job.discovered_at)}`}</span></div>
    </button>
    <div class="tc-foot">
      <${Select} size="sm" label=${`Status for ${job.title}`} tone=${`s-${job.tracking_status}`} value=${job.tracking_status}
        onChange=${(v) => setTracking(job.id, v)} options=${statuses.map((t) => [t, TRACKING_LABEL[t] || humanize(t)])} />
      <div class="tc-icons">
        <span class=${`tc-doc ${docs.resume ? 'on' : ''}`} title=${docs.resume ? 'Tailored resume ready' : 'No tailored resume yet'}><${Icon} name="doc" size=${14} /></span>
        ${apply ? html`<a class="icon-btn tc-link" href=${apply} target="_blank" rel="noopener noreferrer" aria-label="Open posting" title="Open posting"><${Icon} name="external" size=${14} /></a>` : null}
      </div>
    </div>
  </article>`;
}

function Pipeline({ jobs }) {
  const total = Math.max(1, jobs.length);
  const tracked = jobs.filter((j) => j.match);
  const avg = tracked.length ? Math.round(tracked.reduce((a, j) => a + j.match.score, 0) / tracked.length) : null;
  return html`<section class="card pipeline" aria-label="Pipeline summary">
    <div class="pl-stages">${LANES.map((l, i) => {
      const n = jobs.filter((j) => l.statuses.includes(j.tracking_status)).length;
      return html`<div class=${`pl-stage s-${l.key}`} key=${l.key} style=${{ '--i': i }}>
        <div class="pl-num"><${CountUp} value=${n} /></div><div class="pl-label">${l.label}</div>
        <div class="pl-bar"><span style=${{ width: `${(n / total) * 100}%` }}></span></div></div>`;
    })}</div>
    <div class="pl-side"><div><span class="pl-big"><${CountUp} value=${jobs.length} /></span><span class="muted small">tracked</span></div>
      <div><span class="pl-big">${avg == null ? '–' : html`<${CountUp} value=${avg} />`}</span><span class="muted small">avg. match</span></div></div>
  </section>`;
}

export function TrackerView() {
  const tr = useStore((s) => s.tracker);
  const byId = useStore((s) => s.jobs.byId);
  const route = useStore((s) => s.route);
  const statuses = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const [over, setOver] = useState(null);
  const jobs = tr.ids.map((id) => byId[id]).filter(Boolean);
  const open = (id) => navigate(`#/tracker/job/${encodeURIComponent(id)}`);
  const lanes = LANES.filter((l) => statuses.includes(l.drop));
  const onDrop = (lane) => (e) => {
    e.preventDefault(); setOver(null);
    const id = e.dataTransfer.getData('text/x-job');
    const job = byId[id];
    if (job && !lane.statuses.includes(job.tracking_status)) setTracking(id, lane.drop);
  };
  return html`<div class="view view-tracker">
    <${PageHead} title=${html`Application <span class="serif">tracker</span>`} sub="Drag a card to move it along — or change its status. Every saved job lives here."
      actions=${html`<${Button} icon="refresh" busy=${tr.status === 'refreshing'} onClick=${loadTracker}>Refresh</${Button}>`} />
    ${tr.status === 'error' ? html`<${ErrorBox} message=${tr.error} onRetry=${loadTracker} />` : null}
    ${tr.status === 'ready' && !jobs.length ? html`<div class="card pane-center grow-fill"><${EmptyState} icon="star" title="Nothing tracked yet"
      action=${html`<${Button} variant="primary" onClick=${() => navigate('#/discover')}>Find roles <${Icon} name="arrow" size=${16} /></${Button}>`}>Star a job in Discover and it lands here, ready to move from shortlist to offer.</${EmptyState}></div>` : html`
    <${Pipeline} jobs=${jobs} />
    <div class="board" role="list">${lanes.map((lane, ci) => {
      const col = jobs.filter((j) => lane.statuses.includes(j.tracking_status));
      return html`<section class=${`board-col lane-${lane.key} ${over === lane.key ? 'drop-over' : ''}`} key=${lane.key} role="listitem" style=${{ '--i': ci }} aria-label=${lane.label}
          onDragOver=${(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; if (over !== lane.key) setOver(lane.key); }}
          onDragLeave=${(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setOver(null); }} onDrop=${onDrop(lane)}>
        <header class="board-head"><span class=${`board-dot s-${lane.key}`}></span>
          <div class="grow"><div class="board-title">${lane.label}</div><div class="board-hint">${lane.hint}</div></div>
          <span class="board-count">${col.length}</span></header>
        <div class="scroll board-body">
          ${tr.status === 'loading' ? html`<${Skeleton} lines=${2} card />` : null}
          ${col.map((j, i) => html`<${TrackCard} key=${j.id} job=${j} index=${i} statuses=${statuses} selected=${route.jobId === j.id} onOpen=${open} />`)}
          ${tr.status !== 'loading' ? html`<div class=${`board-drop ${col.length ? 'slim' : ''}`}>${over === lane.key ? 'Release to move here' : col.length ? 'Drop here' : 'No jobs yet · drop one here'}</div>` : null}
        </div></section>`;
    })}</div>`}
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
