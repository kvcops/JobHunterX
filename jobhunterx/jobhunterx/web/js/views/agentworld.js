// "Agents at work": the search pipeline drawn as a small office of characters.
// Every state, speech bubble and number comes from the live run (stages, progress, counts, activity) —
// the animation only shows *who* is busy; it never invents progress.
import { html } from '../lib/preact.js';
import { Icon } from '../components/ui.js';

const DESKS = [
  { key: 'understand', stages: ['understand'], name: 'Profile analyst', role: 'Reads your profile', icon: 'user', hue: 18, act: 'type',
    metric: (c) => null },
  { key: 'plan', stages: ['plan'], name: 'Planner', role: 'Plans the searches', icon: 'list', hue: 265, act: 'type',
    metric: (c, run) => (run.plan ? `${run.plan.queries.length} searches planned` : null) },
  { key: 'discover', stages: ['discover'], name: 'Scout', role: 'Searches job sites & company boards', icon: 'search', hue: 205, act: 'walk',
    metric: (c) => (c.search_results ? `${c.search_results} results found` : null) },
  { key: 'normalize', stages: ['normalize'], name: 'Reader', role: 'Opens every job page', icon: 'doc', hue: 160, act: 'read',
    metric: (c) => (c.candidates ? `${c.candidates} postings read` : null) },
  { key: 'dedupe', stages: ['dedupe'], name: 'Curator', role: 'Merges duplicate posts', icon: 'layers', hue: 40, act: 'type',
    metric: (c) => (c.duplicates ? `${c.duplicates} duplicates merged` : null) },
  { key: 'validate', stages: ['validate'], name: 'Verifier', role: 'Checks each job is real & open', icon: 'shield', hue: 140, act: 'stamp',
    metric: (c) => (c.invalid ? `${c.invalid} fake / closed removed` : null) },
  { key: 'match', stages: ['extract', 'match'], name: 'Analyst', role: 'Reads requirements & scores fit', icon: 'spark', hue: 330, act: 'think',
    metric: (c, run) => (run.total ? `${c.scored} of ${run.total} scored` : null) },
  { key: 'rank', stages: ['rank'], name: 'Ranker', role: 'Ranks & explains', icon: 'chart', hue: 28, act: 'cheer',
    metric: (c) => (c.recommended ? `${c.recommended} fit you` : null) },
];

function deskState(desk, status) {
  const st = desk.stages.map((k) => status[k]).filter(Boolean);
  if (st.includes('failed')) return 'failed';
  if (st.includes('running')) return 'running';
  if (st.length && st.every((x) => x === 'done' || x === 'skipped')) return 'done';
  return 'pending';
}

/** A tiny person in SVG. Parts carry classes so CSS can make them walk, type, read, stamp or cheer. */
function Person({ hue }) {
  return html`<svg class="aw-person" viewBox="0 0 60 84" aria-hidden="true" style=${{ '--h': hue }}>
    <ellipse class="aw-shadow" cx="30" cy="80" rx="15" ry="3" />
    <g class="aw-leg aw-leg-l"><rect x="22" y="54" width="7" height="22" rx="3.5" /></g>
    <g class="aw-leg aw-leg-r"><rect x="31" y="54" width="7" height="22" rx="3.5" /></g>
    <rect class="aw-body" x="17" y="26" width="26" height="32" rx="11" />
    <g class="aw-arm aw-arm-l"><rect x="10" y="29" width="7" height="22" rx="3.5" /></g>
    <g class="aw-arm aw-arm-r"><rect x="43" y="29" width="7" height="22" rx="3.5" /></g>
    <circle class="aw-head" cx="30" cy="15" r="10" />
    <path class="aw-hair" d="M20 14 Q21 3 30 4 Q40 3 40 14 Q36 8 30 9 Q24 8 20 14 Z" />
    <circle class="aw-eye" cx="26.5" cy="16" r="1.2" /><circle class="aw-eye" cx="33.5" cy="16" r="1.2" />
  </svg>`;
}

function Desk({ desk, state, line, metric, progress }) {
  const bubble = state === 'running' ? (progress || line || desk.role) : state === 'done' ? (metric || 'Done') : state === 'failed' ? 'Hit a problem' : null;
  return html`<li class=${`aw-desk is-${state} act-${desk.act}`} style=${{ '--h': desk.hue }}>
    <div class="aw-stage">
      ${bubble ? html`<div class="aw-bubble" title=${bubble}>${bubble}</div>` : html`<div class="aw-zzz" aria-hidden="true">z<span>z</span><span>z</span></div>`}
      ${state === 'running' ? html`<span class="aw-paper p1" aria-hidden="true"></span><span class="aw-paper p2" aria-hidden="true"></span><span class="aw-paper p3" aria-hidden="true"></span>` : null}
      <div class="aw-walker"><${Person} hue=${desk.hue} /></div>
      <div class="aw-table" aria-hidden="true"><span class="aw-prop"><${Icon} name=${desk.icon} size=${14} /></span></div>
      ${state === 'done' ? html`<span class="aw-check" aria-hidden="true"><${Icon} name="check" size=${12} /></span>` : null}
    </div>
    <div class="aw-name"><strong>${desk.name}</strong><span>${state === 'running' ? 'working now' : state === 'done' ? 'finished' : state === 'failed' ? 'stopped' : 'waiting'}</span></div>
    ${metric && state !== 'pending' ? html`<div class="aw-metric">${metric}</div>` : null}
  </li>`;
}

export function AgentWorld({ run, items }) {
  const status = Object.fromEntries(run.stages.map((st) => [st.key, st.status]));
  const c = run.counts || {};
  const p = run.progress;
  const lastLine = (desk) => {
    for (let i = items.length - 1; i >= 0; i--) if (desk.stages.includes(items[i].stage)) return items[i].message;
    return null;
  };
  const states = DESKS.map((d) => deskState(d, status));
  const busy = DESKS.filter((_, i) => states[i] === 'running').map((d) => d.name);
  return html`<div class="aw-office" aria-label="Agents at work">
    <p class="sr-only" aria-live="polite">${busy.length ? `${busy.join(', ')} working now. ${p && p.label ? p.label : ''}` : 'No agent is working right now.'}</p>
    <div class="aw-caption" aria-hidden="true">${DESKS.map((d, i) => (states[i] === 'running'
      ? html`<span key=${d.key} style=${{ '--h': d.hue }}><strong>${d.name}:</strong> ${(p && p.label && d.stages.includes(p.stage) ? p.label : lastLine(d)) || d.role}</span>` : null))}
      ${busy.length ? null : html`<span>${states.every((x) => x === 'done') ? 'All agents finished.' : 'Waiting to start…'}</span>`}</div>
    <ol class="aw-floor">
      ${DESKS.map((d, i) => html`<${Desk} key=${d.key} desk=${d} state=${states[i]} line=${lastLine(d)}
        metric=${d.metric(c, run)} progress=${p && p.label && d.stages.includes(p.stage) ? p.label : null} />`)}
    </ol>
  </div>`;
}
