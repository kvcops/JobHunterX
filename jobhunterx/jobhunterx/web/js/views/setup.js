// First-run setup: API keys. Shown before anything else when no AI key is configured and the user
// has not chosen Kilo's free models — without AI the resume can't be read and every search would stall.
// Layout rule: the whole form fits on one screen — compact rows, no inner scrolling.
import { html, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { saveSetupKeys, testSetupKey, startFree } from '../actions.js';
import { Button, Icon, Notice, Badge } from '../components/ui.js';

const AI = [
  { id: 'google', field: 'google_api_key', name: 'Google AI Studio', sub: 'Gemini · Gemma', url: 'https://aistudio.google.com/apikey', best: true,
    how: 'Sign in with Google → “Create API key” → copy. Free, no card.' },
  { id: 'nvidia', field: 'nvidia_api_key', name: 'NVIDIA NIM', sub: '40 requests/min', url: 'https://build.nvidia.com/settings/api-keys',
    how: 'Sign in at build.nvidia.com → “Generate API Key” → copy. Free, no card.' },
  { id: 'groq', field: 'groq_api_key', name: 'Groq', sub: 'very fast', url: 'https://console.groq.com/keys',
    how: 'Sign up → “Create API Key” → copy (shown only once).' },
];
const MORE = [
  { id: 'mistral', field: 'mistral_api_key', name: 'Mistral', url: 'https://console.mistral.ai/api-keys' },
  { id: 'tavily', field: 'tavily_api_key', name: 'Tavily', url: 'https://app.tavily.com' },
  { id: 'exa', field: 'exa_api_key', name: 'Exa', url: 'https://dashboard.exa.ai/api-keys' },
  { id: 'brave', field: 'brave_api_key', name: 'Brave', url: 'https://api-dashboard.search.brave.com/app/keys' },
];

function TestResult({ test }) {
  if (!test || test.busy || !test.message) return null;
  return html`<div class=${`setup-result small ${test.ok ? 'tone-text-success' : 'error-text'}`} role="status">
    <${Icon} name=${test.ok ? 'check' : 'alert'} size=${13} /> ${test.message}</div>`;
}

function KeyRow({ p, value, onChange, test, configured }) {
  const [show, setShow] = useState(false);
  return html`<div class=${`setup-row ${p.best ? 'best' : ''} ${test && test.ok ? 'ok' : ''}`}>
    <div class="setup-row-head">
      <div class="setup-name"><strong>${p.name}</strong><span class="muted small">${p.sub}</span>
        ${p.best ? html`<${Badge} tone="success">Start here</${Badge}>` : null}
        ${configured ? html`<${Badge} tone="info">Saved</${Badge}>` : null}</div>
      <a class="setup-link" href=${p.url} target="_blank" rel="noopener noreferrer">Get a free key <${Icon} name="external" size=${13} /></a>
    </div>
    <div class="muted small setup-how">${p.how}</div>
    <div class="setup-input">
      <input class="input" type=${show ? 'text' : 'password'} autocomplete="off" spellcheck="false" aria-label=${`${p.name} API key`}
        placeholder=${configured ? 'Paste a new key to replace the saved one' : 'Paste your key here'} value=${value}
        onInput=${(e) => onChange(e.currentTarget.value)} />
      <button type="button" class="icon-btn" aria-label=${show ? 'Hide key' : 'Show key'} onClick=${() => setShow(!show)}><${Icon} name="eye" size=${15} /></button>
      <${Button} size="sm" busy=${test && test.busy} disabled=${!value.trim()} onClick=${() => testSetupKey(p.id, value.trim())}>Test</${Button}>
    </div>
    <${TestResult} test=${test} />
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
  const aiEntered = [...AI, MORE[0]].some((p) => (vals[p.field] || '').trim()) || (setup.data && setup.data.llm_ready);
  const failed = [...AI, ...MORE].some((p) => tests[p.id] && tests[p.id].ok === false && (vals[p.field] || '').trim());
  return html`<div class="onboarding setup">
    <aside class="ob-side">
      <div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
        <span class="brand-name">JobHunter<span class="serif">X</span></span></div>
      <div class="ob-copy"><h1>First, your free <span class="serif">AI</span></h1>
        <p class="lead">JobHunterX uses AI to read your resume and every job. Start free with no key,
          or add a free key — each takes about a minute.</p></div>
      <ul class="setup-why">
        <li><${Icon} name="check" size=${15} /> <span><strong>No key</strong> works: Kilo's free models. <strong>One key</strong> is faster and private.</span></li>
        <li><${Icon} name="bolt" size=${15} /> <span><strong>Two or three</strong> make searches much faster — each free plan allows only a few calls a minute.</span></li>
        <li><${Icon} name="shield" size=${15} /> <span>Saved only on your computer, in <code>jobhunterx/.env</code>. Nothing is paid.</span></li>
      </ul>
    </aside>
    <section class="ob-main">
      <div class=${`card setup-card ${more ? 'more' : ''}`}>
        <div class="setup-card-head">
          <h2>Start free, or add a key</h2>
          <p class="muted small">Click “Get a free key”, copy it, paste it below. Use “Test” to check it works.</p>
        </div>
        ${setup.error ? html`<${Notice} tone="danger">${setup.error}</${Notice}>` : null}
        <div class="setup-free">
          <div class="grow"><strong>No key? Start free with Kilo</strong>
            <span class="muted small">Free AI models, no sign-up. Slower when busy, and these free models may use your prompts
              (resume text, job posts) to train — add a key below if that matters to you.</span></div>
          <${Button} busy=${setup.saving} onClick=${() => startFree(Object.fromEntries(entered.map(([k, v]) => [k, v.trim()])))}>Start free <${Icon} name="arrow" size=${14} /></${Button}>
        </div>
        <div class="setup-rows">
          ${AI.map((p) => html`<${KeyRow} key=${p.id} p=${p} value=${vals[p.field] || ''} onChange=${set(p.field)} test=${tests[p.id]} configured=${keys[p.id]} />`)}
        </div>
        <div class="setup-search">
          <button type="button" class="link-btn small" aria-expanded=${more ? 'true' : 'false'} onClick=${() => setMore(!more)}>
            <${Icon} name=${more ? 'x' : 'plus'} size=${13} /> ${more ? 'Hide' : 'Optional:'} Mistral and web search keys (free Deep Search works without one)</button>
          ${more ? html`<div class="setup-search-grid">
            ${MORE.map((p) => html`<label class="setup-mini" key=${p.id}>
              <span class="row gap"><strong class="small">${p.name}</strong>${keys[p.id] ? html`<${Badge} tone="info">Saved</${Badge}>` : null}
                <a class="setup-link small" href=${p.url} target="_blank" rel="noopener noreferrer" aria-label=${`Get a free ${p.name} key`} title="Get a free key"><span class="lbl">Get key</span> <${Icon} name="external" size=${12} /></a></span>
              <input class="input" type="password" autocomplete="off" spellcheck="false" aria-label=${`${p.name} API key`} placeholder="Optional"
                value=${vals[p.field] || ''} onInput=${(e) => set(p.field)(e.currentTarget.value)} />
            </label>`)}
          </div>` : null}
        </div>
        <div class="setup-foot">
          <span class="muted small">${failed ? 'A key failed the test — fix it or clear it first.' : aiEntered ? 'Ready — you can add more keys later in Settings.' : 'Paste an AI key, or start free above.'}</span>
          <${Button} variant="primary" busy=${setup.saving} disabled=${!aiEntered || failed}
            onClick=${() => saveSetupKeys(Object.fromEntries(entered.map(([k, v]) => [k, v.trim()])))}>Save and continue <${Icon} name="arrow" size=${15} /></${Button}>
        </div>
      </div>
    </section>
  </div>`;
}
