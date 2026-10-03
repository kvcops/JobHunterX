// "Agents at work": the search pipeline drawn as a small office of characters.
// Every state, speech bubble and number comes from the live run (stages, progress, counts, activity) —
// the animation only shows *who* is busy; it never invents progress.
import { html, useEffect, useRef, useState } from '../lib/preact.js';
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

/** The simple desk grid — used when the device cannot run the 3D world (no WebGL). */
function AgentDesks({ run, items, states, lastLine }) {
  const c = run.counts || {};
  const p = run.progress;
  const busy = DESKS.filter((_, i) => states[i] === 'running').map((d) => d.name);
  return html`<div class="aw-office" aria-label="Agents at work">
    <div class="aw-caption" aria-hidden="true">${DESKS.map((d, i) => (states[i] === 'running'
      ? html`<span key=${d.key} style=${{ '--h': d.hue }}><strong>${d.name}:</strong> ${(p && p.label && d.stages.includes(p.stage) ? p.label : lastLine(d)) || d.role}</span>` : null))}
      ${busy.length ? null : html`<span>${states.every((x) => x === 'done') ? 'All agents finished.' : 'Waiting to start…'}</span>`}</div>
    <ol class="aw-floor">
      ${DESKS.map((d, i) => html`<${Desk} key=${d.key} desk=${d} state=${states[i]} line=${lastLine(d)}
        metric=${d.metric(c, run)} progress=${p && p.label && d.stages.includes(p.stage) ? p.label : null} />`)}
    </ol>
  </div>`;
}

const isDark = () => document.documentElement.dataset.theme === 'dark';
const reduced = () => {
  const m = document.documentElement.dataset.motion;
  if (m === 'reduced') return true;
  if (m === 'full') return false;
  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
};

/**
 * The 3D world: Three.js renders the island and characters; name tags and speech bubbles are
 * plain HTML that follows each character's head every frame (positions are written straight to
 * the elements, so following the camera never re-renders the app).
 */
function World3D({ run, items, states, lastLine }) {
  const host = useRef(null);
  const world = useRef(null);
  const tags = useRef({});
  const [mode, setMode] = useState('loading');      // loading | ready | fallback
  const [big, setBig] = useState(false);
  const c = run.counts || {};
  const p = run.progress;

  useEffect(() => {
    let alive = true;
    import('./world3d.js').then((m) => {
      if (!alive || !host.current) return;
      try {
        world.current = m.createWorld(host.current, { dark: isDark(), reducedMotion: reduced() });
      } catch (err) {
        setMode('fallback');
        return;
      }
      world.current.onFrame((pos) => {
        for (const [key, pt] of Object.entries(pos)) {
          const el = tags.current[key];
          if (!el) continue;
          el.style.transform = `translate(${pt.x.toFixed(1)}px, ${pt.y.toFixed(1)}px) translate(-50%, -100%)`;
          el.style.opacity = pt.visible ? '1' : '0';
          el.style.zIndex = String(1000 - Math.round(pt.depth * 900));
        }
      });
      setMode('ready');
    }).catch(() => setMode('fallback'));
    const mo = new MutationObserver(() => world.current && world.current.setTheme(isDark()));
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => { alive = false; mo.disconnect(); if (world.current) world.current.dispose(); world.current = null; };
  }, []);

  useEffect(() => {
    if (!world.current) return;
    world.current.update(Object.fromEntries(DESKS.map((d, i) => [STAGE_KEY[d.key], states[i]])),
      { scoredRatio: run.total ? Math.min(1, (c.scored || 0) / run.total) : 0 });
  });

  useEffect(() => {
    if (!big) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setBig(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [big]);

  if (mode === 'fallback') return html`<${AgentDesks} run=${run} items=${items} states=${states} lastLine=${lastLine} />`;
  const busy = DESKS.filter((_, i) => states[i] === 'running').map((d) => d.name);
  return html`<div class=${`aw3d ${big ? 'is-big' : ''}`} aria-label="Agents at work, in 3D">
    ${big ? html`<div class="aw3d-backdrop" onClick=${() => setBig(false)}></div>` : null}
    <div class="aw3d-frame">
      <div class="aw3d-canvas" ref=${host}></div>
      <div class="aw3d-tags" aria-hidden="true">
        ${DESKS.map((d, i) => {
          const st = states[i];
          const say = st === 'running' ? ((p && p.label && d.stages.includes(p.stage) ? p.label : lastLine(d)) || d.role)
            : st === 'done' ? (d.metric(c, run) || 'Done') : null;
          return html`<div key=${d.key} class=${`aw3d-tag is-${st}`} style=${{ '--h': d.hue, opacity: 0 }} ref=${(el) => { tags.current[STAGE_KEY[d.key]] = el; }}>
            ${say ? html`<div class="aw3d-say">${say}</div>` : st === 'pending' ? html`<div class="aw3d-zzz">z<span>z</span><span>z</span></div>` : null}
            <div class="aw3d-name"><span class="dot"></span>${d.name}</div>
          </div>`;
        })}
      </div>
      ${mode === 'loading' ? html`<div class="aw3d-loading">Building the office…</div>` : null}
      <div class="aw3d-bar">
        <span class="aw3d-hint">${busy.length ? html`<strong>${busy.join(', ')}</strong> working now` : states.every((x) => x === 'done') ? 'Everyone has finished' : 'Waiting to start'}
          <span class="muted"> · drag to look around · scroll to zoom</span></span>
        <div class="row gap">
          <button type="button" class="aw3d-btn" onClick=${() => world.current && world.current.resetView()} title="Reset the camera">Reset view</button>
          <button type="button" class="aw3d-btn" onClick=${() => setBig(!big)} aria-pressed=${big ? 'true' : 'false'}>${big ? 'Close' : 'Expand'}</button>
        </div>
      </div>
    </div>
    <p class="sr-only" aria-live="polite">${busy.length ? `${busy.join(', ')} working now. ${p && p.label ? p.label : ''}` : 'No agent is working right now.'}</p>
  </div>`;
}

// desk key -> station key in the 3D world (the Analyst desk covers the extract + match stages)
const STAGE_KEY = { understand: 'understand', plan: 'plan', discover: 'discover', normalize: 'normalize', dedupe: 'dedupe', validate: 'validate', match: 'match', rank: 'rank' };

export function AgentWorld({ run, items }) {
  const status = Object.fromEntries(run.stages.map((st) => [st.key, st.status]));
  const lastLine = (desk) => {
    for (let i = items.length - 1; i >= 0; i--) if (desk.stages.includes(items[i].stage)) return items[i].message;
    return null;
  };
  const states = DESKS.map((d) => deskState(d, status));
  return html`<${World3D} run=${run} items=${items} states=${states} lastLine=${lastLine} />`;
}
