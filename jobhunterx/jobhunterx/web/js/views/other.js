// Tracker, Browser agent, Interventions, Settings.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadTracker, navigate, setTracking, loadInterventions, continueIntervention, skipIntervention, focusIntervention,
  stopBrowser, setTakeover, saveSettings, setModel, setPipelineMode, resetEverything, clearJobs, loadUsage,
} from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, PageHead, ScoreRing, Monogram, Seg } from '../components/ui.js';
import { TRACKING_LABEL, DEFAULT_TRACKING, relTime, humanize, fmtNum } from '../lib/format.js';
import { setTheme } from '../actions.js';
import { ReconnectingSocket } from '../lib/ws.js';

export function TrackerView() {
  const tr = useStore((s) => s.tracker);
  const byId = useStore((s) => s.jobs.byId);
  const route = useStore((s) => s.route);
  const statuses = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const jobs = tr.ids.map((id) => byId[id]).filter(Boolean);
  const open = (id) => navigate(`#/tracker/job/${encodeURIComponent(id)}`);
  const cols = statuses.filter((st) => st !== 'new');
  return html`<div class="view view-tracker">
    <${PageHead} title=${html`Application <span class="serif">tracker</span>`} sub="Every saved job, from shortlist to offer. Change a status to move it."
      actions=${html`<${Button} icon="refresh" busy=${tr.status === 'refreshing'} onClick=${loadTracker}>Refresh</${Button}>`} />
    ${tr.status === 'error' ? html`<${ErrorBox} message=${tr.error} onRetry=${loadTracker} />` : null}
    ${tr.status === 'ready' && !jobs.length ? html`<div class="card pane-center grow-fill"><${EmptyState} icon="star" title="Nothing tracked yet"
      action=${html`<${Button} variant="primary" onClick=${() => navigate('#/discover')}>Find roles</${Button}>`}>Save jobs with the star to track them here.</${EmptyState}></div>` : html`
    <div class="board" role="list">${cols.map((st, ci) => {
      const col = jobs.filter((j) => j.tracking_status === st);
      return html`<section class="board-col" key=${st} role="listitem" style=${{ '--i': ci }} aria-label=${TRACKING_LABEL[st] || humanize(st)}>
        <header class="board-head"><span class=${`board-dot s-${st}`}></span>${TRACKING_LABEL[st] || humanize(st)}<span class="board-count">${col.length}</span></header>
        <div class="scroll board-body">
          ${tr.status === 'loading' ? html`<${Skeleton} lines=${2} card />` : null}
          ${col.map((j) => html`<article class=${`track-card job-card ${route.jobId === j.id ? 'is-selected' : ''}`} key=${j.id}>
            <button type="button" class="job-main" onClick=${() => open(j.id)} aria-label=${`Open ${j.title} at ${j.company}`}>
              <div class="row gap"><${Monogram} name=${j.company} size=${30} /><div class="grow"><div class="job-company">${j.company}</div><strong class="track-title">${j.title}</strong></div>
                <${ScoreRing} score=${j.match ? j.match.score : null} verdict=${j.match && j.match.verdict} size=${38} /></div>
            </button>
            <select class="input input-sm" aria-label=${`Status for ${j.title}`} value=${j.tracking_status} onChange=${(e) => setTracking(j.id, e.currentTarget.value)}>
              ${statuses.map((t) => html`<option value=${t}>${TRACKING_LABEL[t] || humanize(t)}</option>`)}</select>
          </article>`)}
          ${!col.length && tr.status !== 'loading' ? html`<div class="board-empty">Empty</div>` : null}
        </div></section>`;
    })}</div>`}
  </div>`;
}

export function BrowserView() {
  const b = useStore((s) => s.browser);
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
  return html`<div class="view view-browser">
    <${PageHead} title=${html`Auto-apply <span class="serif">agent</span>`} sub="Watch the agent fill applications live. Take over any time to type or solve a CAPTCHA."
      actions=${html`<${Button} variant=${b.takeover ? 'primary' : 'secondary'} icon="hand" onClick=${() => setTakeover(!b.takeover)}>${b.takeover ? 'Release control' : 'Take over'}</${Button}>
        <${Button} variant="danger" icon="stop" onClick=${stopBrowser}>Stop</${Button}>`} />
    <div class="split split-browser">
      <div class=${`pane browser-frame ${b.takeover ? 'takeover' : ''}`}>
        ${b.url ? html`<div class="browser-url" title=${b.url}>${b.title || b.url}</div>` : null}
        <canvas ref=${canvas} tabindex="0" aria-label="Live browser view"
          onClick=${(e) => send({ type: 'mouse', action: 'click', ...coords(e), button: 0 })}
          onWheel=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'wheel', deltaX: e.deltaX, deltaY: e.deltaY }); } }}
          onKeyDown=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'keyboard', action: 'keyDown', key: e.key, text: e.key.length === 1 ? e.key : '' }); } }}
          onKeyUp=${(e) => b.takeover && send({ type: 'keyboard', action: 'keyUp', key: e.key })}></canvas>
        ${!hasFrame ? html`<div class="browser-empty"><${EmptyState} icon="globe" title="No active browser">Start “Auto-apply” on a job to see the agent here.</${EmptyState}></div>` : null}
      </div>
      <aside class="pane card steps"><div class="pane-pad"><h3 class="sec-title">Agent steps</h3></div>
        <div class="scroll pane-pad">${b.steps.length ? html`<ol class="step-log">${b.steps.map((s) => html`<li key=${s.id}><span class="muted small">${relTime(s.ts)}</span> ${s.message}</li>`)}</ol>` : html`<p class="muted">No activity yet.</p>`}</div></aside>
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
        <div style=${{ maxWidth: '340px', marginTop: '18px' }}><${Field} label="Primary search provider">${(id) => html`<select id=${id} class="input" value=${d.primary_search_provider} onChange=${(e) => saveSettings({ primary_search_provider: e.currentTarget.value })}>
          ${d.search_providers.map((p) => html`<option value=${p}>${humanize(p)}</option>`)}</select>`}</${Field}></div>
      </section>` : html`<${Skeleton} lines=${4} />`;
      case 'models': return html`<section class="set-section"><h2>AI models</h2><p class="muted small">Pick the preferred first model for each task. If it is unavailable, the next one in the chain is used automatically.</p>
        ${models.data ? html`<div class="form-grid">${Object.entries(models.data.chains).map(([key, ch]) => html`<${Field} label=${ch.name}>${(id) => html`<select id=${id} class="input" value=${ch.selected} onChange=${(e) => setModel(key, e.currentTarget.value)}>
          ${ch.options.map((m) => html`<option value=${m}>${(models.data.all_models.find((x) => x.id === m) || {}).name || m}</option>`)}</select>`}</${Field}>`)}</div>`
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
