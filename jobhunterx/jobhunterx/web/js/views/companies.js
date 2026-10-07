// Companies: the researched watchlist for the candidate's cities. Each company's own job board is
// checked every few hours, so new roles are caught before the public-job-board crowd arrives.
import { html, useEffect, useRef, useState } from '../lib/preact.js';
import { ReconnectingSocket } from '../lib/ws.js';
import { useStore } from '../state/store.js';
import {
  loadWatchlist, checkWatchlistNow, navigate, setList, loadMonitors, addMonitor, checkMonitor, rescoutMonitor, removeMonitor,
} from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, PageHead, Tabs, Icon, Monogram, Notice, Spinner, Portal } from '../components/ui.js';
import { CompanySection } from './jobdetail.js';
import { runProgress } from './discover.js';
import {
  COMPANY_VERDICT_LABEL, COMPANY_VERDICT_TONE, COMPETITION_LABEL, EARLY_CAREER_LABEL, relTime, humanize, plural,
} from '../lib/format.js';

const CATEGORY_LABEL = { ai_startup: 'AI startup', product: 'Product company', gcc: 'GCC (global tech centre)', ai_services_boutique: 'AI services (small)' };

function CompanyRow({ c, open, onToggle }) {
  const rv = c.reviews || {};
  return html`<article class=${`company-row card ${open ? 'is-open' : ''}`}>
    <button type="button" class="company-head" aria-expanded=${open ? 'true' : 'false'} onClick=${onToggle}>
      <${Monogram} name=${c.name} />
      <div class="grow">
        <div class="company-name">${c.name}<span class="muted small"> · ${(c.cities || []).join(', ')} · ${CATEGORY_LABEL[c.category] || humanize(c.category)}</span></div>
        <div class="muted small">${c.what_they_do}</div>
        <div class="row gap wrap" style=${{ marginTop: '6px' }}>
          <${Badge} tone=${COMPANY_VERDICT_TONE[c.verdict]}>${COMPANY_VERDICT_LABEL[c.verdict] || c.verdict}</${Badge}>
          ${c.competition ? html`<${Badge} tone=${c.competition === 'low' ? 'success' : c.competition === 'very_high' ? 'danger' : 'neutral'}>${COMPETITION_LABEL[c.competition]}</${Badge}>` : null}
          <${Badge} tone=${c.hires_early_career === 'yes' ? 'success' : c.hires_early_career === 'rare' ? 'warning' : 'neutral'}>${EARLY_CAREER_LABEL[c.hires_early_career] || 'Unknown'}</${Badge}>
          ${rv.ambitionbox ? html`<span class="fact">AmbitionBox ${rv.ambitionbox}</span>` : null}
          ${rv.glassdoor ? html`<span class="fact">Glassdoor ${rv.glassdoor}</span>` : null}
          ${c.red_flags && c.red_flags.length ? html`<span class="fact tone-text-warning">${plural(c.red_flags.length, 'red flag')}</span>` : null}
          ${c.board_supported ? html`<span class="fact tone-text-success" title="Its own job board is checked automatically">Auto-checked</span>`
            : html`<span class="fact" title="Its careers site can't be read automatically yet — open it yourself">Check manually</span>`}
        </div>
      </div>
      <${Icon} name=${open ? 'x' : 'next'} size=${16} />
    </button>
    ${open ? html`<div class="company-body"><${CompanySection} c=${c} /></div>` : null}
  </article>`;
}

const MONITOR_TONE = { ready: 'success', scouting: 'info', queued: 'neutral', failed: 'danger' };
const MONITOR_LABEL = { ready: 'Watching', scouting: 'Scouting…', queued: 'Queued', failed: 'Scout failed' };

function MonitorRow({ m, busy }) {
  const [open, setOpen] = useState(false);
  const jobs = m.jobs || [];
  const working = m.status === 'scouting' || m.status === 'queued';
  return html`<article class="monitor-row card">
    <div class="monitor-head">
      <${Monogram} name=${m.company} />
      <div class="grow">
        <div class="company-name">${m.company}<span class="muted small">${m.location ? ` · ${m.location}` : ' · all locations'}${m.keyword ? ` · “${m.keyword}”` : ''}</span></div>
        <div class="row gap wrap small" style=${{ marginTop: '4px' }}>
          <${Badge} tone=${MONITOR_TONE[m.status] || 'neutral'}>${MONITOR_LABEL[m.status] || m.status}</${Badge}>
          ${working ? html`<span class="muted monitor-step">${m.status === 'scouting' ? html`<${Spinner} size=${12} /> ` : null}${m.message}</span>` : null}
          ${m.status === 'ready' ? html`<span class="muted">via ${m.found_via || 'saved recipe'}${m.last_check_at ? ` · ${m.last_count ?? jobs.length} open · checked ${relTime(m.last_check_at)}` : ''}</span>` : null}
          ${m.status === 'failed' ? html`<span class="tone-text-danger">${m.error}</span>` : null}
        </div>
      </div>
      <div class="row gap monitor-actions">
        ${m.results_url ? html`<a class="btn btn-sm" href=${m.results_url} target="_blank" rel="noopener noreferrer" title="Open the filtered careers page"><${Icon} name="external" size=${15} /></a>` : null}
        ${m.status === 'ready' ? html`<${Button} size="sm" icon="refresh" busy=${busy} onClick=${() => checkMonitor(m.id)}>Check now</${Button}>` : null}
        ${!working ? html`<${Button} size="sm" onClick=${() => rescoutMonitor(m.id)} title="Run the Company Scout again (if the site changed)">Re-scout</${Button}>` : null}
        <${Button} size="sm" icon="trash" aria-label=${`Stop watching ${m.company}`} onClick=${() => removeMonitor(m.id)} />
      </div>
    </div>
    ${working && m.steps && m.steps.length > 1 ? html`<ul class="live-feed monitor-feed">${m.steps.slice(-4).reverse().map((s, i) => html`<li key=${i}>${s.text}</li>`)}</ul>` : null}
    ${m.status === 'ready' && jobs.length ? html`<div class="monitor-jobs">
      <button type="button" class="link-btn small" aria-expanded=${open ? 'true' : 'false'} onClick=${() => setOpen(!open)}>
        ${open ? 'Hide' : 'Show'} ${plural(jobs.length, 'open job')} found on the careers site</button>
      ${open ? html`<ul class="monitor-job-list">${jobs.map((j) => html`<li key=${j.url || j.title}>
        <a href=${j.url} target="_blank" rel="noopener noreferrer">${j.title}</a>${j.location ? html`<span class="muted small"> · ${j.location}</span>` : null}
      </li>`)}</ul>` : null}
    </div>` : null}
  </article>`;
}

/** Live picture of the Company Scout's browser (watch-only), streamed like the auto-apply view. */
function useScoutFrames(canvas) {
  const [has, setHas] = useState(false);
  useEffect(() => {
    const ctx = canvas.current.getContext('2d');
    const img = new Image();
    let pending = null; let drawing = false;
    img.onload = () => {
      if (!canvas.current) return;
      if (canvas.current.width !== img.width || canvas.current.height !== img.height) { canvas.current.width = img.width; canvas.current.height = img.height; }
      ctx.drawImage(img, 0, 0); setHas(true); drawing = false;
      if (pending) { const p = pending; pending = null; drawing = true; img.src = p; }
    };
    const sock = new ReconnectingSocket('/ws/scout', {
      onMessage: (m) => {
        if (m.type === 'idle') { setHas(false); return; }
        if (m.type !== 'frame' || typeof m.data !== 'string') return;
        const src = `data:image/jpeg;base64,${m.data}`;
        if (drawing) { pending = src; return; }          // drop stale frames instead of queueing them
        drawing = true; img.src = src;
      },
    });
    sock.connect();
    return () => sock.close();
  }, []);
  return has;
}

const WIN_KEY = 'jhx.scout.window';
const readWin = () => { try { const v = JSON.parse(localStorage.getItem(WIN_KEY) || 'null'); return v && typeof v === 'object' ? v : {}; } catch { return {}; } };
const saveWin = (v) => { try { localStorage.setItem(WIN_KEY, JSON.stringify(v)); } catch { /* private mode: not remembered */ } };
const EDGE = 8;                                   // px kept between the window and the edge of the screen

/**
 * The scout's live browser as a small floating window. It is rendered straight into <body> (a card's backdrop blur
 * would otherwise become its frame and push it off the page), always kept fully on screen, and can be minimised to a
 * title bar, made big (never taller than the screen) or dragged anywhere by its title bar. Double-click the title bar
 * to put it back in the corner. Size and place are remembered in this browser.
 */
function ScoutWindow({ m }) {
  const canvas = useRef();
  const box = useRef();
  const has = useScoutFrames(canvas);
  const [win, setWin] = useState(() => ({ mode: 'small', pos: null, ...readWin() }));   // mode: small | big | min
  const update = (patch) => setWin((cur) => { const next = { ...cur, ...patch }; saveWin(next); return next; });
  const free = () => window.innerWidth > 760;      // on phones the window is a bottom sheet, never dragged
  const keepOnScreen = (p) => {
    const el = box.current;
    if (!p || !el) return p;
    const w = el.offsetWidth, h = el.offsetHeight;
    const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;   // without scrollbars
    return { x: Math.round(Math.min(Math.max(EDGE, p.x), Math.max(EDGE, vw - w - EDGE))),
             y: Math.round(Math.min(Math.max(EDGE, p.y), Math.max(EDGE, vh - h - EDGE))) };
  };
  // whenever the window or the screen changes size, slide it back inside the screen (an effect, not a layout effect:
  // the portal draws the window in its own effect, which runs first)
  useEffect(() => {
    const fit = () => setWin((cur) => { if (!cur.pos) return cur; const p = keepOnScreen(cur.pos); return p.x === cur.pos.x && p.y === cur.pos.y ? cur : { ...cur, pos: p }; });
    fit();
    const ro = new ResizeObserver(fit); if (box.current) ro.observe(box.current);
    window.addEventListener('resize', fit);
    return () => { ro.disconnect(); window.removeEventListener('resize', fit); };
  }, [win.mode]);
  const drag = useRef(null);
  const onDown = (e) => {
    if (!free() || e.button !== 0 || (e.target.closest && e.target.closest('button'))) return;
    const r = box.current.getBoundingClientRect();
    drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top };
    e.currentTarget.setPointerCapture(e.pointerId);
    box.current.classList.add('is-dragging');
  };
  const onMove = (e) => {
    if (!drag.current) return;
    const p = keepOnScreen({ x: e.clientX - drag.current.dx, y: e.clientY - drag.current.dy });
    box.current.style.left = `${p.x}px`; box.current.style.top = `${p.y}px`;      // moved directly: no re-render per pixel
    box.current.style.right = 'auto'; box.current.style.bottom = 'auto';
    drag.current.last = p;
  };
  const onUp = () => {
    if (!drag.current) return;
    const p = drag.current.last; drag.current = null;
    box.current.classList.remove('is-dragging');
    if (p) update({ pos: p });
  };
  const steps = (m.steps || []).slice().reverse();
  const big = win.mode === 'big', min = win.mode === 'min';
  const place = win.pos && free() ? { left: `${win.pos.x}px`, top: `${win.pos.y}px`, right: 'auto', bottom: 'auto' } : {};
  return html`<${Portal}><div ref=${box} class=${`scout-window card is-${win.mode}`} style=${place} role="region"
      aria-label=${`Company Scout working on ${m.company}`}>
    <div class="scout-bar" onPointerDown=${onDown} onPointerMove=${onMove} onPointerUp=${onUp} onPointerCancel=${onUp}
      onDblClick=${(e) => { if (!(e.target.closest && e.target.closest('button'))) update({ pos: null }); }}
      title=${free() ? 'Drag to move · double-click to put it back in the corner' : ''}>
      <span class="live-dot"></span>
      <strong class="grow scout-title">Company Scout · ${m.company}${m.location ? ` · ${m.location}` : ''}</strong>
      <div class="scout-ctrls">
        <button type="button" class="icon-btn" onClick=${() => update({ mode: min ? 'small' : 'min' })}
          aria-label=${min ? 'Show the scout window' : 'Minimise the scout window'} title=${min ? 'Show' : 'Minimise'}>
          <${Icon} name=${min ? 'external' : 'minus'} size=${14} /></button>
        ${min ? null : html`<button type="button" class="icon-btn" onClick=${() => update({ mode: big ? 'small' : 'big' })}
          aria-label=${big ? 'Make the window small' : 'Make the window big'} title=${big ? 'Smaller' : 'Bigger'}>
          <${Icon} name=${big ? 'shrink' : 'enlarge'} size=${14} /></button>`}
        ${win.pos ? html`<button type="button" class="icon-btn" onClick=${() => update({ pos: null })}
          aria-label="Put the window back in the corner" title="Back to the corner"><${Icon} name="corner" size=${14} /></button>` : null}
      </div>
    </div>
    ${min ? html`<div class="scout-now muted small">${steps[0] ? steps[0].text : 'Starting the browser…'}</div>` : null}
    <div class="scout-body" hidden=${min}>
      <div class="scout-url muted small" title=${m.url || ''}>${m.url ? html`<${Icon} name="globe" size=${12} /> ${m.url}` : 'Starting the browser…'}</div>
      <div class="scout-screen">
        <canvas ref=${canvas} aria-label="Live view of the scout's browser"></canvas>
        ${has ? null : html`<div class="scout-wait"><${Spinner} size=${16} /> <span>${m.status === 'queued' ? 'Waiting for the scout…' : 'Opening the browser…'}</span></div>`}
      </div>
      <ol class="scout-steps">${steps.slice(0, big ? 6 : 3).map((st, i) => html`<li key=${steps.length - i} class=${i === 0 ? 'is-now' : ''}>${st.text}</li>`)}</ol>
    </div>
  </div></${Portal}>`;
}

/** Companies you pick yourself. The Company Scout agent opens each careers site once, sets the filters and learns how
 *  to list the jobs again — every search and watchlist check then includes them in seconds. */
function MyCompanies() {
  const s = useStore((st) => st.monitors);
  const [company, setCompany] = useState('');
  const [location, setLocation] = useState('');
  const [keyword, setKeyword] = useState('');
  const [adding, setAdding] = useState(false);
  useEffect(() => { loadMonitors(); }, []);
  const submit = async (e) => {
    e.preventDefault();
    if (company.trim().length < 2 || adding) return;
    setAdding(true);
    if (await addMonitor(company.trim(), location.trim(), keyword.trim())) { setCompany(''); setKeyword(''); }
    setAdding(false);
  };
  const active = s.items.find((m) => m.status === 'scouting');
  return html`<section class="card pad stack my-companies">
    ${active ? html`<${ScoutWindow} key=${active.id} m=${active} />` : null}
    <div>
      <h2 class="my-companies-title">Add a company to watch</h2>
      <p class="muted small">Add any company. The Company Scout agent opens its real careers site once, applies your location and role
        filters, and learns how to list those jobs. After that they are checked in seconds on every search and watchlist check.</p>
    </div>
    <form class="monitor-form" onSubmit=${submit}>
      <input id="add-company" class="input" required minLength="2" maxLength="80" placeholder="Company, e.g. Google" aria-label="Company name"
        value=${company} onInput=${(e) => setCompany(e.currentTarget.value)} />
      <input class="input" maxLength="80" placeholder="Location (optional), e.g. Hyderabad" aria-label="Location (optional)"
        value=${location} onInput=${(e) => setLocation(e.currentTarget.value)} />
      <input class="input" maxLength="80" placeholder="Role keyword (optional)" aria-label="Role keyword (optional)"
        title="Left empty, your first target role is used" value=${keyword} onInput=${(e) => setKeyword(e.currentTarget.value)} />
      <${Button} type="submit" variant="primary" icon="plus" busy=${adding} disabled=${company.trim().length < 2}>Watch</${Button}>
    </form>
    ${s.status === 'error' ? html`<${ErrorBox} message=${s.error} onRetry=${loadMonitors} />` : null}
    ${s.status === 'loading' ? html`<${Skeleton} rows=${2} />` : null}
    ${s.items.length ? html`<div class="monitor-list">${s.items.map((m) => html`<${MonitorRow} key=${m.id} m=${m} busy=${!!s.busy[m.id]} />`)}</div>`
      : s.status === 'ready' ? html`<p class="muted small">No companies yet. Try Google, Microsoft or Amazon with your city.</p>` : null}
  </section>`;
}

/** Live view of a running watchlist check — every line and number comes from the server as it happens. */
function LiveCheck({ run, feed }) {
  const pct = runProgress(run);
  const p = run.progress;
  const cur = run.stages.find((st) => st.status === 'running');
  const c = run.counts || {};
  return html`<div class="card pad live-check" aria-live="polite">
    <div class="row gap wrap">
      <span class="live-dot"></span><strong>Checking your watchlist companies now</strong>
      <span class="muted small">${p && p.label ? p.label : cur ? cur.label : 'Starting…'}</span>
      <span class="grow"></span><span class="live-pct">${pct}%</span>
    </div>
    <div class="mc-bar is-active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${pct}><div class="mc-fill" style=${{ width: `${pct}%` }}></div></div>
    <div class="row gap wrap small muted">
      <span>${c.candidates || 0} openings found</span><span>·</span><span>${c.scored || 0} analysed</span><span>·</span>
      <span class="tone-text-success">${c.recommended || 0} fit you</span>
    </div>
    ${feed && feed.length ? html`<ul class="live-feed">${feed.slice().reverse().map((it) => html`<li key=${it.id} class=${`k-${it.kind}`}>${it.message}</li>`)}</ul>` : null}
  </div>`;
}

export function CompaniesView() {
  const w = useStore((s) => s.watch);
  const [filter, setFilter] = useState('all');
  const [openName, setOpenName] = useState(null);
  const [scope, setScope] = useState('mine');
  useEffect(() => { loadWatchlist(scope); }, [scope]);
  const d = w.data;
  const st = d && d.status;
  const last = st && st.last;
  const all = (d && d.companies) || [];
  const shown = all.filter((c) => filter === 'all' || c.verdict === filter || (filter === 'low' && c.competition === 'low')
    || (filter === 'early' && c.hires_early_career === 'yes'));
  const tabs = [
    { key: 'all', label: 'All', count: all.length },
    { key: 'strong', label: 'Strong', count: all.filter((c) => c.verdict === 'strong').length },
    { key: 'early', label: 'Hires 1–3 yrs', count: all.filter((c) => c.hires_early_career === 'yes').length },
    { key: 'low', label: 'Low competition', count: all.filter((c) => c.competition === 'low').length },
    { key: 'caution', label: 'Caution', count: all.filter((c) => c.verdict === 'caution').length },
  ];
  const checking = w.checking || (st && st.checking);
  const liveRun = w.run && ['queued', 'running'].includes(w.run.status) ? w.run : null;
  return html`<div class="view view-companies">
    <${PageHead} title=${html`Companies to <span class="serif">watch</span>`}
      sub="Researched companies in your cities. Their own job boards are checked every few hours, so you can apply in the first hours — not as applicant #1,500 on LinkedIn."
      actions=${html`<${Button} icon="plus" onClick=${() => { const el = document.getElementById('add-company'); if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.focus(); } }}>Add company</${Button}>
        <${Button} variant="primary" icon="refresh" busy=${checking} onClick=${checkWatchlistNow}>${checking ? 'Checking…' : 'Check for new roles now'}</${Button}>`} />
    <${MyCompanies} />
    <div class="card pad stack">
      <div class="row gap wrap">
        ${d && d.cities && d.cities.length ? html`<span>Your cities: <strong>${d.cities.join(', ')}</strong></span>` : null}
        ${st ? html`<span class="muted small">${st.enabled ? `Auto-check every ${st.interval_hours} h while the app is open` : 'Auto-check is off (Settings → Search tuning)'}</span>` : null}
        ${last && last.at ? html`<span class="muted small">Last check ${relTime(last.at)}${last.new_fits != null ? ` · ${last.new_fits} new fitting role(s)` : ''}</span>` : null}
        ${last && last.new_fits ? html`<${Button} size="sm" onClick=${() => { setList({ view: 'fresh' }); navigate('#/discover'); }}>See new roles</${Button}>` : null}
        <span class="grow"></span>
        <${Tabs} size="sm" label="Which companies" value=${scope} onChange=${setScope} tabs=${[{ key: 'mine', label: 'My cities' }, { key: 'all', label: 'All researched' }]} />
      </div>
      ${d && scope === 'mine' && !(d.cities || []).length ? html`<${Notice} tone="warning">None of your preferred locations are covered yet. Researched cities: ${(d.covered_cities || []).join(', ')}.
        Add one of them under Profile → preferences to use the watchlist.</${Notice}>` : null}
    </div>
    ${liveRun ? html`<${LiveCheck} run=${liveRun} feed=${w.feed} />` : null}
    <${Tabs} label="Filter companies" size="sm" value=${filter} onChange=${setFilter} tabs=${tabs} />
    <div class="company-list">
      ${w.status === 'error' ? html`<${ErrorBox} message=${w.error} onRetry=${() => loadWatchlist(scope)} />` : null}
      ${w.status === 'loading' && !d ? html`<${Skeleton} rows=${6} />` : null}
      ${d && !shown.length ? html`<${EmptyState} icon="info" title="No companies here">Try another filter${scope === 'mine' ? ' or "All researched"' : ''}.</${EmptyState}>` : null}
      ${shown.map((c) => html`<${CompanyRow} key=${c.name} c=${c} open=${openName === c.name} onToggle=${() => setOpenName(openName === c.name ? null : c.name)} />`)}
    </div>
  </div>`;
}
