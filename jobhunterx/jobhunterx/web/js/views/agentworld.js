// "Agents at work": the search pipeline drawn as a small office of characters.
// Every state, speech bubble and number comes from the live run (stages, progress, counts, activity) —
// the animation only shows *who* is busy; it never invents progress.
import { html, useEffect, useRef, useState } from '../lib/preact.js';
import { Icon } from '../components/ui.js';
import { api } from '../lib/api.js';

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
  { key: 'connect', stages: ['connect'], name: 'Connector', role: 'Finds a real person & drafts referral notes', icon: 'user', hue: 92, act: 'type',
    metric: (c, run) => { const st = (run.stages || []).find((x) => x.key === 'connect'); return st && st.status === 'done' && st.detail ? st.detail : null; } },
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

const ROOMS = [['all', 'Whole office'], ['work', 'Work floor'], ['meeting', 'Meeting room'], ['pantry', 'Pantry'], ['server', 'Server room'], ['game', 'Game room'], ['garden', 'Garden']];
const WHERE = { work: 'on the work floor', pantry: 'in the pantry', server: 'in the server room', meet: 'in the meeting room', hall: 'in the hallway', game: 'in the game room', garden: 'in the garden' };
const EMOJI = { neutral: '🙂', happy: '😊', laugh: '😂', sad: '😢', angry: '😤', surprised: '😮', sleepy: '😴', love: '😍', focused: '🧐', wink: '😉', proud: '😎', dizzy: '😵', tired: '🥱', scared: '😱' };
const AI_KEY = 'jhx.office.ai';
const readAI = () => { try { return localStorage.getItem(AI_KEY) !== '0'; } catch { return true; } };
const KIND_WORD = { work: 'work', chat: 'chat', ai: 'live AI chat', play: 'play', think: 'thinking', ask: 'answer', memory: 'memory' };
const LOG_KEEP = 80;

/**
 * The 3D world: Three.js renders the office and the robots; name tags and speech bubbles are plain HTML that follows
 * each robot's head every frame (positions are written straight to the elements, so the app never re-renders for it).
 * Work lines come from the real run; "chat" lines are the robots' break-time talk and are marked as such in the log.
 */
function World3D({ run, items, states, lastLine }) {
  const host = useRef(null);
  const world = useRef(null);
  const tags = useRef({});
  const where = useRef({});
  const logEnd = useRef(null);
  const [mode, setMode] = useState('loading');      // loading | ready | fallback
  const [big, setBig] = useState(false);
  const [follow, setFollow] = useState(true);
  const [room, setRoom] = useState('all');
  const [showLog, setShowLog] = useState(false);
  const [log, setLog] = useState([]);
  const [selected, setSelected] = useState(null);
  const [said, setSaid] = useState({});             // agent key -> { text, until, kind }: what each robot is saying now
  const [ai, setAI] = useState(readAI);
  const [ask, setAsk] = useState('');
  const [asking, setAsking] = useState(false);
  const [qa, setQA] = useState({});                  // agent key -> [{ q, a }]
  const [, tick] = useState(0);
  const c = run.counts || {};

  useEffect(() => {
    let alive = true;
    let seq = 0;
    const onSay = (key, text, secs, kind = 'work') => {
      if (kind !== 'memory') setSaid((cur) => ({ ...cur, [key]: { text, until: Date.now() + secs * 1000, kind } }));
      if (kind !== 'think') setLog((cur) => [...cur, { id: ++seq, key, text, kind, at: new Date() }].slice(-LOG_KEEP));
      setTimeout(() => alive && tick((n) => n + 1), secs * 1000 + 50);
    };
    const onSelect = (key) => alive && setSelected(key);
    const talk = (body) => api.officeChat(body).catch(() => null);
    import('./world3d.js')
      .then((m) => m.createWorld(host.current, { dark: isDark(), reducedMotion: reduced(), onSay, onSelect, talk }))
      .then((w) => {
        if (!alive) { w.dispose(); return; }
        world.current = w;
        w.setAI(readAI());
        w.onFrame((pos) => {
          for (const [key, pt] of Object.entries(pos)) {
            const prev = where.current[key];
            where.current[key] = pt;
            const el = tags.current[key];
            if (!el) continue;
            el.style.transform = `translate(${pt.x.toFixed(1)}px, ${pt.y.toFixed(1)}px) translate(-50%, -100%)`;
            el.style.opacity = pt.visible ? '1' : '0';
            el.style.zIndex = String(1000 - Math.round(pt.depth * 900));
            if (!prev || prev.expr !== pt.expr || !el.dataset.emo) { const em = el.querySelector('.aw3d-emo'); if (em) { em.textContent = EMOJI[pt.expr] || ''; el.dataset.emo = '1'; } }
          }
        });
        setMode('ready');
      })
      .catch((err) => { console.warn('3D office unavailable', err); if (alive) setMode('fallback'); });      // no WebGL, or the model could not load
    const mo = new MutationObserver(() => world.current && world.current.setTheme(isDark()));
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => { alive = false; mo.disconnect(); if (world.current) world.current.dispose(); world.current = null; };
  }, []);

  // live run -> world: stage states and real numbers every render; new activity lines become scenes
  useEffect(() => {
    const w = world.current;
    if (!w) return;
    w.update(Object.fromEntries(DESKS.map((d, i) => [STAGE_KEY[d.key], states[i]])),
      { scoredRatio: run.total ? Math.min(1, (c.scored || 0) / run.total) : 0, counts: c, status: run.status, total: run.total || 0 });
    const active = ['queued', 'running'].includes(run.status);
    const justFinished = run.finished_at && Date.now() - Date.parse(run.finished_at) < 30000;
    const young = run.started_at && Date.now() - Date.parse(run.started_at) < 180000;
    w.feed(items, run.id, !active, young && (active || justFinished) ? 'all' : (active || justFinished));
  });
  useEffect(() => { if (world.current) world.current.setFollow(follow); }, [follow, mode]);
  useEffect(() => { if (showLog && logEnd.current) logEnd.current.scrollIntoView({ block: 'end' }); }, [log, showLog]);
  // the selected robot's card shows where it is and how it feels; refresh that twice a second while a card is open
  useEffect(() => {
    if (!selected) return undefined;
    const t = setInterval(() => tick((n) => n + 1), 500);
    return () => clearInterval(t);
  }, [selected]);

  useEffect(() => {
    if (!big) return undefined;
    const onKey = (e) => { if (e.key === 'Escape' && !(e.target && e.target.closest && e.target.closest('input'))) { if (selected) world.current && world.current.select(null); else setBig(false); } };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [big, selected]);

  if (mode === 'fallback') return html`<${AgentDesks} run=${run} items=${items} states=${states} lastLine=${lastLine} />`;
  const now = Date.now();
  const busy = DESKS.filter((_, i) => states[i] === 'running').map((d) => d.name);
  const goRoom = (r) => { setRoom(r); if (world.current) world.current.view(r); };
  const selIdx = selected ? DESKS.findIndex((d) => STAGE_KEY[d.key] === selected) : -1;
  const selDesk = selIdx >= 0 ? DESKS[selIdx] : null;
  const selLines = selDesk ? items.filter((it) => selDesk.stages.includes(it.stage)).slice(-3).reverse() : [];
  const selWhere = selected && where.current[selected];
  const selMetric = selDesk ? selDesk.metric(c, run) : null;
  const selInfo = selected && world.current ? world.current.info(selected) : null;
  const deskOf = (key) => DESKS.find((d) => STAGE_KEY[d.key] === key) || DESKS[0];
  const stateWord = (st) => (st === 'running' ? 'working now' : st === 'done' ? 'finished' : st === 'failed' ? 'stopped' : 'waiting');
  const toggleAI = () => { const on = !ai; setAI(on); try { localStorage.setItem(AI_KEY, on ? '1' : '0'); } catch { /* ignore */ } if (world.current) world.current.setAI(on); };
  async function sendAsk(e) {
    e.preventDefault();
    const q = ask.trim();
    if (!q || !selected || asking) return;
    const key = selected;
    setAsking(true); setAsk('');
    if (world.current) world.current.thinking(key, true);
    try {
      const r = await api.officeAsk({ agent: key, question: q });
      if (world.current) { world.current.thinking(key, false); world.current.speak(key, r.answer, r.emotion, Math.min(14, 4 + r.answer.length / 20)); }
      setQA((cur) => ({ ...cur, [key]: [...(cur[key] || []), { q, a: r.answer }].slice(-4) }));
    } catch {
      if (world.current) { world.current.thinking(key, false); world.current.speak(key, 'I could not reach the server — try again?', 'sad', 4); }
    } finally {
      setAsking(false);
    }
  }
  const meter = (label, v, tone) => html`<div class="aw3d-meter"><span>${label}</span><i><b class=${tone} style=${{ width: `${Math.round((v || 0) * 100)}%` }}></b></i></div>`;
  const sayBody = (say) => (say.kind === 'think' && say.text === '…' ? html`<span class="aw3d-dots"><i></i><i></i><i></i></span>` : say.text);
  return html`<div class=${`aw3d ${big ? 'is-big' : ''}`} aria-label="Agents at work, in 3D">
    ${big ? html`<div class="aw3d-backdrop" onClick=${() => setBig(false)}></div>` : null}
    <div class="aw3d-frame">
      <div class="aw3d-canvas" ref=${host}></div>
      <div class="aw3d-tags" aria-hidden="true">
        ${DESKS.map((d, i) => {
          const st = states[i];
          const key = STAGE_KEY[d.key];
          const say = said[key] && said[key].until > now ? said[key] : null;
          const cls = ['aw3d-tag', `is-${st}`, say ? 'talking' : '', selected === key ? 'is-selected' : ''].join(' ');
          return html`<div key=${d.key} class=${cls} style=${{ '--h': d.hue, opacity: 0 }} ref=${(el) => { tags.current[key] = el; }}>
            ${say ? html`<div class=${`aw3d-say is-${say.kind}`}>${sayBody(say)}${say.kind === 'ai' ? html`<span class="aw3d-ai" title="Live AI conversation">AI</span>` : null}</div>` : null}
            <div class="aw3d-name"><span class="aw3d-emo"></span>${d.name}<span class="dot"></span></div>
          </div>`;
        })}
      </div>
      ${mode === 'loading' ? html`<div class="aw3d-loading"><span class="aw3d-spin"></span>Opening the office…</div>` : null}
      <div class="aw3d-rooms" role="group" aria-label="Go to a room">
        ${ROOMS.map(([k, label]) => html`<button type="button" key=${k} class="aw3d-chip" aria-pressed=${room === k ? 'true' : 'false'} onClick=${() => goRoom(k)}>${label}</button>`)}
      </div>
      ${showLog ? html`<aside class="aw3d-log" aria-label="Office talk">
        <div class="aw3d-log-head"><div><strong>Office talk</strong><span class="muted small">work updates, chats, games and gossip</span></div>
          <button type="button" class="aw3d-x" aria-label="Close" onClick=${() => setShowLog(false)}>×</button></div>
        <ol class="aw3d-log-list">
          ${log.length ? log.map((l) => { const d = deskOf(l.key); return html`<li key=${l.id} class=${`is-${l.kind}`} style=${{ '--h': d.hue }}>
            <span class="who"><span class="dot"></span>${d.name}<span class="when">${KIND_WORD[l.kind] || l.kind} · ${l.at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></span>
            <span class="what">${l.text}</span></li>`; })
            : html`<li class="aw3d-log-empty">Nothing said yet. The agents report every real step of a search, and chat, play and gossip on their breaks.</li>`}
          <li ref=${logEnd} class="aw3d-log-end" aria-hidden="true"></li>
        </ol></aside>` : null}
      ${selDesk ? html`<div class="aw3d-card" style=${{ '--h': selDesk.hue }} role="dialog" aria-label=${selDesk.name}>
        <div class="aw3d-card-head"><span class="aw3d-card-emo">${selInfo ? EMOJI[selInfo.expr] || '🙂' : '🙂'}</span><strong>${selDesk.name}</strong>
          <span class=${`aw3d-state is-${states[selIdx]}`}>${stateWord(states[selIdx])}</span>
          <button type="button" class="aw3d-x" aria-label="Close" onClick=${() => world.current && world.current.select(null)}>×</button></div>
        <p class="aw3d-card-role">${selDesk.role}${selWhere ? html`<span class="muted"> · ${selInfo && selInfo.doing ? `${selInfo.doing} ` : selWhere.chatting ? 'chatting ' : selWhere.seated ? 'sitting ' : ''}${WHERE[selWhere.where] || ''}</span>` : null}</p>
        ${selMetric ? html`<div class="aw3d-card-metric">${selMetric}</div>` : null}
        ${selInfo ? html`<div class="aw3d-meters">${meter('Mood', selInfo.mood.joy, 'joy')}${meter('Energy', selInfo.mood.energy, 'energy')}${meter('Stress', selInfo.mood.stress, 'stress')}</div>` : null}
        ${selLines.length ? html`<ul class="aw3d-card-lines">${selLines.map((it) => html`<li key=${it.id}>${it.message}</li>`)}</ul>` : null}
        ${selInfo && selInfo.memories.length ? html`<div class="aw3d-mem"><span class="aw3d-sub">Remembers</span><ul>${selInfo.memories.slice(0, 4).map((m, i) => html`<li key=${i}>${m.text}${m.from ? html`<em> — heard from ${m.from}</em>` : null}</li>`)}</ul></div>` : null}
        ${selInfo && (selInfo.best || selInfo.rival) ? html`<div class="aw3d-friends">${selInfo.best ? html`<span>💛 Best friend: <strong>${selInfo.best.name}</strong></span>` : null}${selInfo.rival ? html`<span>⚔️ Rival: <strong>${selInfo.rival.name}</strong> (${selInfo.rival.rec})</span>` : null}</div>` : null}
        ${(qa[selected] || []).length ? html`<ul class="aw3d-qa">${qa[selected].slice(-2).map((x, i) => html`<li key=${i}><span class="q">${x.q}</span><span class="a">${x.a}</span></li>`)}</ul>` : null}
        <form class="aw3d-ask" onSubmit=${sendAsk}>
          <input type="text" value=${ask} maxLength="300" placeholder=${`Ask the ${selDesk.name} something…`} onInput=${(e) => setAsk(e.target.value)} disabled=${asking} aria-label=${`Ask the ${selDesk.name}`} />
          <button type="submit" class="aw3d-btn" disabled=${asking || !ask.trim()}>${asking ? '…' : 'Ask'}</button>
        </form>
        <div class="aw3d-card-actions">
          <button type="button" class="aw3d-btn" onClick=${() => world.current && world.current.poke(selected)}>👉 Poke</button>
          <button type="button" class="aw3d-btn" onClick=${() => world.current && world.current.rest(selected)}>☕ Send on a break</button>
        </div>
      </div>` : null}
      <div class="aw3d-bar">
        <span class="aw3d-hint">${busy.length ? html`<strong>${busy.join(', ')}</strong> working now` : states.every((x) => x === 'done') ? 'Everyone has finished — break time' : 'No search running — the team is on a break'}
          <span class="muted"> · click a robot · drag to look around · scroll to zoom</span></span>
        <div class="row gap">
          <button type="button" class="aw3d-btn" aria-pressed=${ai ? 'true' : 'false'} onClick=${toggleAI} title="Let the agents chat live with a free AI model on their breaks">${ai ? '✨ AI chats on' : 'AI chats off'}</button>
          <button type="button" class="aw3d-btn" aria-pressed=${showLog ? 'true' : 'false'} onClick=${() => setShowLog(!showLog)}>Office talk${log.length ? ` · ${log.length}` : ''}</button>
          <button type="button" class="aw3d-btn" aria-pressed=${follow ? 'true' : 'false'} onClick=${() => setFollow(!follow)}
            title="Move the camera to wherever agents are working together">${follow ? '● Following the action' : 'Follow the action'}</button>
          <button type="button" class="aw3d-btn" onClick=${() => { setRoom('all'); if (world.current) world.current.resetView(); }} title="Reset the camera">Reset view</button>
          <button type="button" class="aw3d-btn" onClick=${() => setBig(!big)} aria-pressed=${big ? 'true' : 'false'}>${big ? 'Close' : 'Expand'}</button>
        </div>
      </div>
    </div>
    <p class="sr-only" aria-live="polite">${busy.length ? `${busy.join(', ')} working now.` : 'No agent is working right now.'}</p>
  </div>`;
}

// desk key -> station key in the 3D world (the Analyst desk covers the extract + match stages)
const STAGE_KEY = { understand: 'understand', plan: 'plan', discover: 'discover', normalize: 'normalize', dedupe: 'dedupe', validate: 'validate', match: 'match', rank: 'rank', connect: 'connect' };

export function AgentWorld({ run, items }) {
  const status = Object.fromEntries(run.stages.map((st) => [st.key, st.status]));
  const lastLine = (desk) => {
    for (let i = items.length - 1; i >= 0; i--) if (desk.stages.includes(items[i].stage)) return items[i].message;
    return null;
  };
  const states = DESKS.map((d) => deskState(d, status));
  return html`<${World3D} run=${run} items=${items} states=${states} lastLine=${lastLine} />`;
}
