// Tracker, Browser agent, Interventions, Settings.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadTracker, navigate, setTracking, loadInterventions, continueIntervention, skipIntervention, focusIntervention,
  stopBrowser, setTakeover, saveSettings, setModel, setPipelineMode, resetEverything, clearJobs, loadUsage,
} from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, Notice } from '../components/ui.js';
import { JobCard } from './discover.js';
import { TRACKING_LABEL, DEFAULT_TRACKING, relTime, humanize, fmtNum } from '../lib/format.js';
import { ReconnectingSocket } from '../lib/ws.js';

export function TrackerView() {
  const tr = useStore((s) => s.tracker);
  const byId = useStore((s) => s.jobs.byId);
  const statuses = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const jobs = tr.ids.map((id) => byId[id]).filter(Boolean);
  const open = (id) => navigate(`#/tracker/job/${encodeURIComponent(id)}`);
  return html`<div class="page">
    <div class="row space"><h1>Application tracker</h1><${Button} icon="refresh" onClick=${loadTracker}>Refresh</${Button}></div>
    ${tr.status === 'error' ? html`<${ErrorBox} message=${tr.error} onRetry=${loadTracker} />` : null}
    ${tr.status === 'loading' ? html`<${Skeleton} lines=${4} />` : null}
    ${tr.status === 'ready' && !jobs.length ? html`<${EmptyState} icon="star" title="Nothing tracked yet">Save jobs with the star to track them through your application pipeline.</${EmptyState}>` : null}
    <div class="board">${statuses.filter((st) => st !== 'new').map((st) => {
      const col = jobs.filter((j) => j.tracking_status === st);
      return col.length ? html`<section class="board-col" key=${st}><h2 class="group-title">${TRACKING_LABEL[st] || humanize(st)} <span class="muted">${col.length}</span></h2>
        ${col.map((j) => html`<div class="tracked" key=${j.id}><${JobCard} job=${j} onOpen=${open} />
          <select class="input input-sm" aria-label=${`Status for ${j.title}`} value=${j.tracking_status} onChange=${(e) => setTracking(j.id, e.currentTarget.value)}>
            ${statuses.map((t) => html`<option value=${t}>${TRACKING_LABEL[t] || humanize(t)}</option>`)}</select></div>`)}</section>` : null;
    })}</div>
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
  return html`<div class="page">
    <div class="row space wrap"><div><h1>Browser agent</h1><p class="muted">Watch the agent fill applications. Take over to type or solve a CAPTCHA yourself.</p></div>
      <div class="row gap"><${Button} variant=${b.takeover ? 'primary' : 'secondary'} icon="hand" onClick=${() => setTakeover(!b.takeover)}>${b.takeover ? 'Release control' : 'Take over'}</${Button}>
        <${Button} variant="danger" icon="stop" onClick=${stopBrowser}>Stop</${Button}></div></div>
    <div class="browser-layout">
      <div class=${`browser-frame ${b.takeover ? 'takeover' : ''}`}>
        ${b.url ? html`<div class="browser-url" title=${b.url}>${b.title || b.url}</div>` : null}
        <canvas ref=${canvas} tabindex="0" aria-label="Live browser view"
          onClick=${(e) => send({ type: 'mouse', action: 'click', ...coords(e), button: 0 })}
          onWheel=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'wheel', deltaX: e.deltaX, deltaY: e.deltaY }); } }}
          onKeyDown=${(e) => { if (b.takeover) { e.preventDefault(); send({ type: 'keyboard', action: 'keyDown', key: e.key, text: e.key.length === 1 ? e.key : '' }); } }}
          onKeyUp=${(e) => b.takeover && send({ type: 'keyboard', action: 'keyUp', key: e.key })}></canvas>
        ${!hasFrame ? html`<div class="browser-empty"><${EmptyState} icon="globe" title="No active browser">Start “Auto-apply” on a job to see the agent here.</${EmptyState}></div>` : null}
      </div>
      <aside class="card steps"><h3 class="sec-title">Agent steps</h3>
        ${b.steps.length ? html`<ol>${b.steps.map((s) => html`<li key=${s.id}><span class="muted small">${relTime(s.ts)}</span> ${s.message}</li>`)}</ol>` : html`<p class="muted">No activity yet.</p>`}</aside>
    </div></div>`;
}

export function InterventionsView() {
  const iv = useStore((s) => s.interventions);
  return html`<div class="page">
    <div class="row space"><h1>Interventions</h1><${Button} icon="refresh" onClick=${loadInterventions}>Refresh</${Button}></div>
    <p class="muted">When the agent hits a login wall, CAPTCHA or one-time code, it pauses here. Solve it in the browser, then continue.</p>
    ${iv.status === 'error' ? html`<${ErrorBox} message=${iv.error} onRetry=${loadInterventions} />` : null}
    ${iv.status === 'loading' ? html`<${Skeleton} lines=${3} />` : null}
    ${iv.status === 'ready' && !iv.items.length ? html`<${EmptyState} icon="check" title="Nothing needs you">The agent is not waiting on anything.</${EmptyState}>` : null}
    <div class="stack">${iv.items.map((it) => html`<div class="card row space wrap" key=${it.id}>
      <div><${Badge} tone="warning">${humanize(it.hitl_type)}</${Badge}> <strong>${it.role || 'Application'}</strong> <span class="muted">@ ${it.company || '—'} · ${relTime(it.created_at)}</span></div>
      <div class="row gap"><${Button} onClick=${() => focusIntervention(it)}>Show browser</${Button}>
        <${Button} variant="primary" onClick=${() => continueIntervention(it)}>Continue</${Button}>
        <${Button} onClick=${() => skipIntervention(it)}>Skip</${Button}></div></div>`)}</div>
  </div>`;
}

function KeysForm({ data }) {
  const [keys, setKeys] = useState({});
  const fields = [['google_api_key', 'Google AI (Gemma / Gemini)', 'google'], ['groq_api_key', 'Groq', 'groq'], ['mistral_api_key', 'Mistral', 'mistral'],
    ['tinyfish_api_key', 'TinyFish search', 'tinyfish'], ['tavily_api_key', 'Tavily search', 'tavily'], ['exa_api_key', 'Exa search', 'exa'], ['brave_api_key', 'Brave search', 'brave']];
  const dirty = Object.values(keys).some((v) => v);
  return html`<section class="card"><h2>API keys</h2><p class="muted small">Keys are stored in your local .env file and never shown again in full.</p>
    <div class="form-grid">${fields.map(([k, label, n]) => html`<${Field} label=${label} hint=${data[`${n}_configured`] ? `Configured (${data[`${n}_key_masked`]})` : 'Not configured'}>
      ${(id) => html`<input id=${id} class="input" type="password" autocomplete="off" value=${keys[k] || ''} placeholder=${data[`${n}_configured`] ? 'Leave empty to keep' : 'Paste key'} onInput=${(e) => setKeys({ ...keys, [k]: e.currentTarget.value })} />`}</${Field}>`)}</div>
    <${Button} variant="primary" disabled=${!dirty} onClick=${async () => { const body = Object.fromEntries(Object.entries(keys).filter(([, v]) => v)); if (await saveSettings(body)) setKeys({}); }}>Save keys</${Button}>
  </section>`;
}

export function SettingsView() {
  const st = useStore((s) => s.settings);
  const models = useStore((s) => s.models);
  const usage = useStore((s) => s.usage);
  const mode = useStore((s) => s.pipelineMode);
  const d = st.data;
  return html`<div class="page">
    <h1>Settings</h1>
    ${st.status === 'error' ? html`<${ErrorBox} message=${st.error} />` : null}
    ${d ? html`<${KeysForm} data=${d} />
    <section class="card"><h2>Search</h2>
      <label class="check"><input type="checkbox" checked=${d.enable_web_search_apis} onChange=${(e) => saveSettings({ enable_web_search_apis: e.currentTarget.checked })} /> Use web search APIs (otherwise only the free DuckDuckGo fallback)</label>
      <label class="check"><input type="checkbox" checked=${d.strict_zero_spend_protection} onChange=${(e) => saveSettings({ strict_zero_spend_protection: e.currentTarget.checked })} /> Zero-spend protection (never exceed free allowances)</label>
      <${Field} label="Primary search provider">${(id) => html`<select id=${id} class="input" value=${d.primary_search_provider} onChange=${(e) => saveSettings({ primary_search_provider: e.currentTarget.value })}>
        ${d.search_providers.map((p) => html`<option value=${p}>${humanize(p)}</option>`)}</select>`}</${Field}>
    </section>` : html`<${Skeleton} lines=${4} />`}
    <section class="card"><h2>AI models</h2><p class="muted small">Pick the preferred first model for each task. If it is unavailable, the next one in the chain is used automatically.</p>
      ${models.data ? html`<div class="form-grid">${Object.entries(models.data.chains).map(([key, ch]) => html`<${Field} label=${ch.name}>${(id) => html`<select id=${id} class="input" value=${ch.selected} onChange=${(e) => setModel(key, e.currentTarget.value)}>
        ${ch.options.map((m) => html`<option value=${m}>${(models.data.all_models.find((x) => x.id === m) || {}).name || m}</option>`)}</select>`}</${Field}>`)}</div>`
        : models.status === 'error' ? html`<${ErrorBox} message=${models.error} />` : html`<${Skeleton} lines=${3} />`}
    </section>
    <section class="card"><div class="row space"><h2>Usage</h2><${Button} size="sm" icon="refresh" onClick=${loadUsage}>Refresh</${Button}></div>
      ${usage.data ? html`<table class="checks"><thead><tr><th>Model</th><th>Calls</th><th>Tokens</th></tr></thead><tbody>
        ${usage.data.llm.rows.map((r) => html`<tr><td>${r.label}</td><td>${fmtNum(r.calls)}</td><td>${fmtNum(r.total_tokens)}</td></tr>`)}
        ${!usage.data.llm.rows.length ? html`<tr><td colspan="3" class="muted">No AI calls yet.</td></tr>` : null}</tbody></table>
        <p class="muted small">Gemma today: ${usage.data.gemma_budget.requests_today} / ${usage.data.gemma_budget.requests_cap} requests.</p>` : usage.status === 'error' ? html`<${ErrorBox} message=${usage.error} />` : html`<${Skeleton} lines=${3} />`}
    </section>
    <section class="card"><h2>Browser agent mode</h2>
      <div class="seg" role="group" aria-label="Pipeline mode">${['manual', 'automatic'].map((m) => html`<button type="button" class=${`seg-btn ${mode.mode === m ? 'on' : ''}`} aria-pressed=${mode.mode === m ? 'true' : 'false'} onClick=${() => setPipelineMode(m)}>${humanize(m)}</button>`)}</div>
      <p class="muted small">Manual: the agent only applies when you click Auto-apply on a job.</p></section>
    <section class="card danger-zone"><h2>Data</h2>
      <div class="row gap wrap"><${Button} onClick=${() => clearJobs('unsaved')}>Clear unsaved jobs</${Button}><${Button} onClick=${() => clearJobs('all')}>Clear all jobs</${Button}>
        <${Button} variant="danger" onClick=${resetEverything}>Reset everything</${Button}></div></section>
  </div>`;
}
