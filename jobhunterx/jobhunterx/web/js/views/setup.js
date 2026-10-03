// First-run setup: API keys. Shown before anything else when no AI key is configured —
// without one the resume can't be read and every search would stall.
import { html, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { saveSetupKeys, testSetupKey } from '../actions.js';
import { Button, Icon, Notice, Badge } from '../components/ui.js';

const AI = [
  { id: 'google', field: 'google_api_key', name: 'Google AI Studio (Gemini / Gemma)', url: 'https://aistudio.google.com/apikey', best: true,
    why: 'Best start — reads resumes and jobs well. Free tier, no card needed.',
    steps: ['Open the link and sign in with your Google account', 'Click “Create API key”', 'Copy the key and paste it here'] },
  { id: 'groq', field: 'groq_api_key', name: 'Groq', url: 'https://console.groq.com/keys',
    why: 'Very fast free models. Adding it as a second key makes searches much quicker.',
    steps: ['Sign up (Google or email)', 'Click “Create API Key”', 'Copy it — it is shown only once'] },
  { id: 'mistral', field: 'mistral_api_key', name: 'Mistral', url: 'https://console.mistral.ai/api-keys',
    why: 'Another free backup, used when the others are busy.',
    steps: ['Sign up and choose the free “Experiment” plan (phone check)', 'Open API Keys → “Create new key”', 'Copy and paste it here'] },
];
const SEARCH = [
  { id: 'tavily', field: 'tavily_api_key', name: 'Tavily', url: 'https://app.tavily.com', why: 'Free monthly credits; good job-search results.' },
  { id: 'exa', field: 'exa_api_key', name: 'Exa', url: 'https://dashboard.exa.ai/api-keys', why: 'Free credits; finds company career pages well.' },
  { id: 'brave', field: 'brave_api_key', name: 'Brave Search', url: 'https://api-dashboard.search.brave.com/app/keys', why: 'Free monthly queries on its own index.' },
];

function KeyCard({ p, value, onChange, test, configured }) {
  const [show, setShow] = useState(false);
  return html`<div class=${`setup-key ${p.best ? 'best' : ''}`}>
    <div class="row gap wrap">
      <strong>${p.name}</strong>
      ${p.best ? html`<${Badge} tone="success">Recommended</${Badge}>` : null}
      ${configured ? html`<${Badge} tone="info">Already set</${Badge}>` : null}
      <span class="grow"></span>
      <a class="btn btn-sm btn-secondary" href=${p.url} target="_blank" rel="noopener noreferrer"><${Icon} name="external" size=${14} /><span>Get a free key</span></a>
    </div>
    <p class="muted small">${p.why}</p>
    ${p.steps ? html`<ol class="setup-steps">${p.steps.map((s) => html`<li>${s}</li>`)}</ol>` : null}
    <div class="row gap">
      <input class="input grow" type=${show ? 'text' : 'password'} autocomplete="off" spellcheck="false" aria-label=${`${p.name} API key`}
        placeholder=${configured ? 'Paste a new key to replace the current one' : 'Paste your key here'} value=${value}
        onInput=${(e) => onChange(e.currentTarget.value)} />
      <button type="button" class="icon-btn" aria-label=${show ? 'Hide key' : 'Show key'} onClick=${() => setShow(!show)}><${Icon} name="eye" size=${15} /></button>
      <${Button} size="sm" busy=${test && test.busy} disabled=${!value.trim()} onClick=${() => testSetupKey(p.id, value.trim())}>Test</${Button}>
    </div>
    ${test && !test.busy && test.message ? html`<div class=${`small ${test.ok ? 'tone-text-success' : 'error-text'}`} role="status">
      ${test.ok ? '✓ ' : '✗ '}${test.message}</div>` : null}
  </div>`;
}

export function SetupView() {
  const setup = useStore((s) => s.setup);
  const [vals, setVals] = useState({});
  const [more, setMore] = useState(false);
  const keys = (setup.data && setup.data.keys) || {};
  const tests = setup.tests || {};
  const set = (field) => (v) => setVals((x) => ({ ...x, [field]: v }));
  const entered = Object.entries(vals).filter(([, v]) => v.trim());
  const aiEntered = AI.some((p) => (vals[p.field] || '').trim()) || (setup.data && setup.data.llm_ready);
  const failed = AI.some((p) => tests[p.id] && tests[p.id].ok === false && (vals[p.field] || '').trim());
  return html`<div class="onboarding setup">
    <aside class="ob-side">
      <div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
        <span class="brand-name">JobHunter<span class="serif">X</span></span></div>
      <div class="ob-copy"><h1>First, your free <span class="serif">AI keys</span></h1>
        <p class="lead">JobHunterX uses AI to read your resume and every job. It needs at least one key — all of these are free and take about a minute each.
          Keys are saved only in your local <code>.env</code> file.</p></div>
      <ul class="setup-why">
        <li><${Icon} name="check" size=${15} /> <span><strong>One key</strong> is enough to start.</span></li>
        <li><${Icon} name="bolt" size=${15} /> <span><strong>Two or three</strong> make it much faster — free tiers allow only a few calls a minute each.</span></li>
        <li><${Icon} name="shield" size=${15} /> <span>Nothing is paid. Search works without any key (DuckDuckGo).</span></li>
      </ul>
    </aside>
    <section class="ob-main">
      <div class="card ob-card">
        <div class="ob-body">
          ${setup.error ? html`<${Notice} tone="danger">${setup.error}</${Notice}>` : null}
          <h3 class="sec-title" style=${{ margin: 0 }}>AI keys — add at least one</h3>
          ${AI.map((p) => html`<${KeyCard} key=${p.id} p=${p} value=${vals[p.field] || ''} onChange=${set(p.field)} test=${tests[p.id]} configured=${keys[p.id]} />`)}
          <button type="button" class="link-btn" aria-expanded=${more ? 'true' : 'false'} onClick=${() => setMore(!more)}>
            ${more ? 'Hide' : 'Optional:'} web search keys (better job discovery)</button>
          ${more ? html`<div class="stack">
            <p class="muted small">Optional. Without them JobHunterX uses DuckDuckGo, which is free but finds fewer postings.</p>
            ${SEARCH.map((p) => html`<${KeyCard} key=${p.id} p=${p} value=${vals[p.field] || ''} onChange=${set(p.field)} test=${tests[p.id]} configured=${keys[p.id]} />`)}
          </div>` : null}
        </div>
        <div class="ob-foot">
          <span class="muted small">${failed ? 'A key failed the test — fix it or remove it before saving.' : aiEntered ? 'Ready to save.' : 'Paste at least one AI key to continue.'}</span>
          <${Button} variant="primary" busy=${setup.saving} disabled=${!aiEntered || failed}
            onClick=${() => saveSetupKeys(Object.fromEntries(entered.map(([k, v]) => [k, v.trim()])))}>Save and continue <${Icon} name="arrow" size=${15} /></${Button}>
        </div>
      </div>
    </section>
  </div>`;
}
