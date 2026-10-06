// Tracker, Browser agent, Interventions, Settings.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadTracker, navigate, setTracking, loadInterventions, continueIntervention, skipIntervention, focusIntervention, markInterventionApplied,
  applyControl, saveSettings, setModel, setPipelineMode, resetEverything, clearJobs, loadUsage,
  loadSettings, refreshModels, setProviders, loadDbHealth, repairDb, backupDb, setMotion,
} from '../actions.js';
import { PeopleManager } from './people.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, PageHead, ScoreRing, Monogram, Seg, Select, CountUp, Orb, Spinner, Notice, reduced } from '../components/ui.js';
import { api } from '../lib/api.js';
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
      <${ScoreRing} score=${job.match ? job.match.score : null} verdict=${job.match && job.match.verdict} size=${42} animate=${false} />
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

// ---------------------------------------------------------------------------- browser agent (auto-apply)
const PHASES = [
  { key: 'kit', label: 'Documents' }, { key: 'open', label: 'Open browser' },
  { key: 'fill', label: 'Fill the form' }, { key: 'submit', label: 'Submit' },
];
const STATUS_META = {
  idle: { label: 'Idle', tone: 'neutral' }, preparing: { label: 'Getting documents ready', tone: 'accent' },
  launching: { label: 'Opening the browser', tone: 'accent' }, running: { label: 'Working', tone: 'accent' },
  paused: { label: 'You are driving', tone: 'info' }, stopping: { label: 'Stopping…', tone: 'warning' },
  stopped: { label: 'Stopped — progress saved', tone: 'warning' }, needs_you: { label: 'Needs you', tone: 'warning' },
  applied: { label: 'Applied', tone: 'success' }, failed: { label: 'Could not finish', tone: 'danger' },
  closed: { label: 'Browser closed', tone: 'neutral' },
};
const WORKING = ['preparing', 'launching', 'running', 'stopping'];

function phaseIndex(sess) {
  if (!sess) return -1;
  const st = sess.status;
  if (st === 'applied') return 4;
  if (st === 'preparing') return 0;
  if (st === 'launching') return 1;
  if (st === 'needs_you') return 3;
  const kit = Object.values(sess.kit || {});
  const kitDone = kit.length && kit.every((k) => !['checking', 'generating'].includes(k.status)) && !kit.some((k) => k.status === 'failed');
  if (!sess.steps || !sess.steps.length) return kitDone || sess.runs ? 1 : 0;
  return 2;
}

function PhaseStepper({ sess }) {
  const at = phaseIndex(sess);
  const halted = sess && ['stopped', 'failed', 'needs_you', 'closed'].includes(sess.status);
  return html`<ol class="phases" aria-label="Progress">${PHASES.map((p, i) => {
    const state = i < at ? 'done' : i === at ? (halted ? 'halt' : 'now') : 'todo';
    return html`<li key=${p.key} class=${`ph ph-${state}`}><span class="ph-dot">${state === 'done' ? html`<${Icon} name="check" size=${12} />`
      : state === 'halt' ? html`<${Icon} name=${sess.status === 'failed' ? 'x' : 'stop'} size=${10} />` : i + 1}</span><span class="ph-label">${p.label}</span></li>`;
  })}</ol>`;
}

const KIT_ORDER = ['resume', 'cover_letter', 'cv'];
const KIT_STATE = {
  checking: { text: 'Checking…', icon: null }, generating: { text: 'Writing…', icon: null },
  found: { text: 'Ready', icon: 'check' }, made: { text: 'Written now', icon: 'spark' },
  skipped: { text: 'Skipped', icon: 'x' }, failed: { text: 'Failed', icon: 'alert' },
};
function KitList({ kit }) {
  const keys = KIT_ORDER.filter((k) => kit && kit[k]);
  if (!keys.length) return null;
  const settled = keys.every((k) => !['checking', 'generating', 'failed'].includes(kit[k].status));
  if (settled) {
    return html`<div class="kit-compact">${keys.map((k) => {
      const it = kit[k]; const ok = it.status !== 'skipped';
      const chip = html`<${Icon} name=${ok ? 'check' : 'x'} size=${12} />${it.label}${it.pages ? html`<em>${it.pages}p</em>` : null}`;
      return it.doc_id ? html`<a key=${k} class=${`kit-chip ${ok ? 'ok' : 'off'} ${it.pages > 1 ? 'long' : ''}`} href=${api.documentPdfUrl(it.doc_id)} target="_blank" rel="noopener" title=${`${it.note || ''} — open PDF`}>${chip}</a>`
        : html`<span key=${k} class=${`kit-chip ${ok ? 'ok' : 'off'}`} title=${it.note || ''}>${chip}</span>`;
    })}</div>`;
  }
  return html`<ul class="kit">${keys.map((k) => {
    const it = kit[k]; const m = KIT_STATE[it.status] || KIT_STATE.checking;
    const busy = it.status === 'checking' || it.status === 'generating';
    return html`<li key=${k} class=${`kit-row k-${it.status}`}>
      <span class="kit-ic">${busy ? html`<${Spinner} size=${14} />` : html`<${Icon} name=${m.icon} size=${14} />`}</span>
      <span class="grow"><strong>${it.label}</strong><span class="muted small">${it.note || m.text}</span></span>
      ${it.pages ? html`<span class=${`kit-pages ${it.pages === 1 ? 'one' : ''}`}>${it.pages} page${it.pages === 1 ? '' : 's'}</span>` : null}
      ${it.doc_id ? html`<a class="kit-open" href=${api.documentPdfUrl(it.doc_id)} target="_blank" rel="noopener" title="Open PDF"><${Icon} name="eye" size=${15} /></a>` : null}
    </li>`;
  })}</ul>`;
}

const VERB_ICON = [['Click', 'cursor'], ['Type', 'type'], ['Upload', 'upload'], ['Open', 'globe'], ['Choose', 'list'], ['Look', 'list'],
  ['Scroll', 'scroll'], ['Press', 'type'], ['Wait', 'refresh'], ['Read', 'eye'], ['Go back', 'back'], ['Switch', 'layers'], ['Finish', 'check']];
const verbIcon = (a) => (VERB_ICON.find(([v]) => a.startsWith(v)) || [null, 'bolt'])[1];

function StepLog({ steps, live }) {
  const box = useRef();
  const last = steps.length ? `${steps[steps.length - 1].n}:${steps[steps.length - 1].repeat}:${steps[steps.length - 1].status}` : '';
  useEffect(() => { if (box.current) box.current.scrollTo({ top: box.current.scrollHeight, behavior: reduced() ? 'auto' : 'smooth' }); }, [last]);
  if (!steps.length) return html`<div class="ap-log"><div class="ap-empty"><${Icon} name="info" size=${16} /> Each step appears here in plain words — what the agent is trying, what it clicked and typed, and whether it worked.</div></div>`;
  return html`<div class="scroll ap-log" ref=${box}><ol class="steps">${steps.map((s) => html`<li key=${s.n} class=${`step s-${s.status} ${live && s.status === 'running' ? 'is-now' : ''}`}>
    <span class="step-n">${s.status === 'running' && live ? html`<${Spinner} size=${13} />` : s.status === 'done' ? html`<${Icon} name="check" size=${12} />`
      : s.status === 'failed' ? html`<${Icon} name="x" size=${12} />` : s.n}</span>
    <div class="step-body">
      <div class="step-goal">${s.goal || 'Looking at the page'}${s.repeat > 1 ? html`<span class="step-rep" title="Tried this more than once">×${s.repeat}</span>` : null}</div>
      ${s.actions && s.actions.length ? html`<div class="step-acts">${s.actions.map((a, i) => html`<span class="act" key=${i}><${Icon} name=${verbIcon(a)} size=${12} />${a}</span>`)}</div>` : null}
      ${s.note ? html`<div class="step-note">${s.note}</div>` : null}
    </div></li>`)}</ol></div>`;
}

function useLiveFrames(canvas) {
  const [frame, setFrame] = useState(false);
  const sock = useRef();
  useEffect(() => {
    const ctx = canvas.current.getContext('2d');
    const img = new Image();
    let pending = null; let drawing = false;
    img.onload = () => {
      if (canvas.current.width !== img.width || canvas.current.height !== img.height) { canvas.current.width = img.width; canvas.current.height = img.height; }
      ctx.drawImage(img, 0, 0); setFrame(true); drawing = false;
      if (pending) { const p = pending; pending = null; drawing = true; img.src = p; }
    };
    const sendSize = () => {
      const r = canvas.current && canvas.current.parentElement.getBoundingClientRect();
      if (r && r.width > 0) sock.current && sock.current.send({ type: 'viewport', w: Math.round(r.width), h: Math.round(r.height) });
    };
    let t = 0;
    const ro = new ResizeObserver(() => { clearTimeout(t); t = setTimeout(sendSize, 350); });
    ro.observe(canvas.current.parentElement);
    sock.current = new ReconnectingSocket('/ws/browser', {
      onOpen: sendSize,
      onMessage: (m) => {
        if (m.type === 'idle') { setFrame(false); return; }
        if (m.type !== 'frame' || typeof m.data !== 'string') return;
        const src = `data:image/jpeg;base64,${m.data}`;
        if (drawing) { pending = src; return; }          // drop stale frames instead of queueing them
        drawing = true; img.src = src;
      },
    });
    sock.current.connect();
    return () => { ro.disconnect(); clearTimeout(t); sock.current.close(); };
  }, []);
  return [frame, (msg) => sock.current && sock.current.send(msg)];
}

export function BrowserView() {
  const b = useStore((s) => s.browser);
  const waiting = useStore((s) => s.interventions.items.length);
  const sess = b.session;
  const canvas = useRef();
  const [hasFrame, send] = useLiveFrames(canvas);
  const status = sess ? sess.status : 'idle';
  const meta = STATUS_META[status] || STATUS_META.idle;
  const working = WORKING.includes(status) || status === 'paused';
  const youDrive = !!sess && sess.control === 'you';
  const canType = !!sess && sess.live && (youDrive || !WORKING.includes(status));
  const showFrame = hasFrame && sess && sess.live;
  const pos = (e) => { const r = canvas.current.getBoundingClientRect(); return { fx: (e.clientX - r.left) / r.width, fy: (e.clientY - r.top) / r.height }; };
  const input = (msg) => canType && send(msg);
  let host = '';
  try { host = sess && sess.url ? new URL(sess.url).host : ''; } catch { host = sess.url; }
  const steps = (sess && sess.steps) || [];
  const busy = b.busy;
  const ctl = (action, label, opts = {}) => html`<${Button} size="sm" variant=${opts.variant || 'secondary'} icon=${opts.icon}
    busy=${busy === action} disabled=${!!busy && busy !== action} onClick=${() => applyControl(action)}>${label}</${Button}>`;

  let controls = null;
  if (sess) {
    if (['preparing', 'launching', 'running'].includes(status)) {
      controls = html`${ctl('stop', 'Stop now', { variant: 'danger', icon: 'stop' })}
        ${status !== 'preparing' ? ctl('take-over', 'Take over', { icon: 'hand' }) : null}`;
    } else if (status === 'paused') {
      controls = html`${ctl('release', 'Give back to agent', { variant: 'primary', icon: 'play' })}${ctl('stop', 'Stop', { variant: 'danger', icon: 'stop' })}`;
    } else if (['stopped', 'needs_you', 'failed'].includes(status)) {
      controls = html`${ctl('continue', 'Continue', { variant: 'primary', icon: 'play' })}
        ${sess.live && !youDrive ? ctl('take-over', 'Take over', { icon: 'hand' }) : null}
        ${ctl('done', 'I submitted it', { icon: 'check' })}
        ${sess.live ? ctl('close', 'Close browser', { icon: 'x' }) : null}`;
    } else if (status === 'applied' || status === 'closed') {
      controls = html`<${Button} size="sm" variant="primary" icon="search" onClick=${() => navigate('#/discover')}>Find the next job</${Button}>
        ${status === 'closed' ? ctl('continue', 'Start again', { icon: 'refresh' }) : null}
        ${sess.live ? ctl('close', 'Close browser', { icon: 'x' }) : null}`;
    }
  }

  return html`<div class="view view-browser">
    <h1 class="sr-only">Auto-apply agent</h1>
    <div class="split split-browser">
      <section class=${`pane browser-window ${youDrive ? 'takeover' : ''} ${showFrame && working ? 'is-live' : ''}`} aria-label="Live browser">
        <div class="bw-chrome">
          <span class="bw-lights" aria-hidden="true"><i></i><i></i><i></i></span>
          <div class="bw-url"><${Icon} name="shield" size=${13} /><span class="bw-host">${host || (sess ? sess.company || 'Preparing' : 'Waiting for a job')}</span>
            ${sess && sess.title ? html`<span class="bw-title">${sess.title}</span>` : null}</div>
          ${showFrame ? html`<span class=${`live-pill ${youDrive ? 'you' : ''}`}><i></i>${youDrive ? 'You' : working ? 'Live' : 'Open'}</span>`
            : html`<span class="live-pill off"><i></i>${sess && WORKING.includes(status) ? 'Starting' : 'Offline'}</span>`}
        </div>
        <div class="bw-stage">
          <canvas ref=${canvas} tabindex="0" aria-label="Live browser view" class=${`${showFrame ? 'on' : ''} ${canType ? 'interactive' : ''}`}
            onMouseDown=${(e) => { canvas.current.focus(); }}
            onClick=${(e) => input({ type: 'mouse', action: 'click', button: 0, ...pos(e) })}
            onDblClick=${(e) => input({ type: 'mouse', action: 'dblclick', button: 0, ...pos(e) })}
            onWheel=${(e) => { if (canType) { e.preventDefault(); input({ type: 'wheel', deltaX: e.deltaX, deltaY: e.deltaY, ...pos(e) }); } }}
            onKeyDown=${(e) => { if (canType && !e.metaKey && !(e.ctrlKey && e.key !== 'v')) { e.preventDefault(); input({ type: 'keyboard', action: 'keyDown', key: e.key }); } }}
            onPaste=${(e) => { if (canType) { e.preventDefault(); input({ type: 'paste', text: e.clipboardData.getData('text') }); } }}></canvas>
          ${showFrame && youDrive ? html`<div class="control-banner"><${Icon} name="hand" size=${15} /> You're driving — click and type right here. Press “Give back” when done.</div>` : null}
          ${showFrame && !youDrive && working ? html`<div class="watch-banner"><${Icon} name="eye" size=${14} /> Watching the agent</div>` : null}
          ${!showFrame ? html`<div class="bw-idle">
            <div class="bw-illus" aria-hidden="true"><${Orb} size=${150} active=${WORKING.includes(status)} done=${status === 'applied'} />
              ${status === 'idle' ? html`<span class="bw-cursor"><svg width="22" height="22" viewBox="0 0 24 24"><path d="M5 3l14 7-6 2-2 6z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg></span>` : null}</div>
            ${!sess ? html`<h2>The agent is <span class="serif">resting</span></h2>
              <p class="muted">Press Auto-apply on any job. You'll see every click and keystroke right here — no extra windows.</p>
              <${Button} variant="primary" onClick=${() => navigate('#/discover')}>Pick a job <${Icon} name="arrow" size=${16} /></${Button}>`
            : status === 'preparing' ? html`<h2>Getting your <span class="serif">documents</span> ready</h2><p class="muted">${sess.message}</p>`
            : status === 'launching' ? html`<h2>Opening a private <span class="serif">browser</span>…</h2><p class="muted">The live view appears as soon as the page loads.</p>`
            : status === 'applied' ? html`<h2>Application <span class="serif">sent</span> 🎉</h2><p class="muted">${sess.company} · ${sess.role}</p>`
            : html`<h2>${meta.label}</h2><p class="muted">${sess.live ? 'Waiting for the next frame…' : 'The browser is closed. Your steps are saved — press Continue to pick up from the last page.'}</p>`}
          </div>` : null}
        </div>
      </section>
      <aside class="pane card agent-panel" aria-label="Agent">
        <div class="ap-head">
          <div class="ap-top"><h2 class="ap-title">Auto-apply <span class="serif">agent</span></h2>
            <div class=${`ap-status tone-${meta.tone} ${WORKING.includes(status) ? 'is-working' : ''}`}><span class="ap-dot"></span>${meta.label}</div></div>
          ${sess ? html`<div class="ap-job"><${Monogram} name=${sess.company} size=${30} /><div class="grow"><div class="job-company">${sess.company}${sess.runs > 1 ? html` · run ${sess.runs}` : ''}</div>
            <strong>${sess.role}</strong></div>${sess.apply_url ? html`<a class="icon-btn" href=${safeUrl(sess.apply_url)} target="_blank" rel="noopener" title="Open the posting"><${Icon} name="external" size=${15} /></a>` : null}</div>
            <${PhaseStepper} sess=${sess} />` : html`<ol class="ap-guide"><li><span>1</span><div><strong>Pick a job</strong><small>Open any job in Discover and press Auto-apply</small></div></li>
              <li><span>2</span><div><strong>Documents first</strong><small>Resume (1 page), cover letter and CV are checked and written if missing</small></div></li>
              <li><span>3</span><div><strong>Watch it apply</strong><small>The browser shows here — stop or take over any time</small></div></li></ol>
              <div class="ap-tips"><span class="sec-title">Good to know</span>
                <div><${Icon} name="stop" size=${14} /><span><strong>Stop</strong> is instant — every step is saved</span></div>
                <div><${Icon} name="hand" size=${14} /><span><strong>Take over</strong> for a CAPTCHA, login or tricky field</span></div>
                <div><${Icon} name="play" size=${14} /><span><strong>Continue</strong> picks up from the last page, even after a restart</span></div>
                <div><${Icon} name="shield" size=${14} /><span>Nothing is invented — every document is fact-checked</span></div></div>`}
          ${sess && sess.message && WORKING.includes(status) ? html`<div class="ap-now" key=${sess.message}><${Spinner} size=${14} /><span>${sess.message}</span></div>` : null}
          ${sess && sess.notice ? html`<${Notice} tone=${status === 'failed' ? 'warning' : 'info'}>${sess.notice}</${Notice}>` : null}
          ${controls ? html`<div class="ap-controls">${controls}</div>` : null}
          ${waiting && status !== 'needs_you' ? html`<a class="ap-alert" href="#/interventions"><${Icon} name="alert" size=${15} /> ${waiting} application${waiting === 1 ? '' : 's'} waiting for you <${Icon} name="arrow" size=${14} /></a>` : null}
        </div>
        ${sess && sess.kit && Object.keys(sess.kit).length ? html`<div class="ap-sec"><span class="sec-title">Application kit</span><${KitList} kit=${sess.kit} /></div>` : null}
        ${sess ? html`<div class="ap-log-head"><span class="sec-title">What the agent did</span><span class="muted small">${steps.length} step${steps.length === 1 ? '' : 's'}</span></div>
        <${StepLog} steps=${steps} live=${status === 'running'} />` : null}
      </aside>
    </div></div>`;
}

const IV_STATE = {
  needs_you: ['Waiting for you', 'warning'], stopped: ['Stopped — waiting for you', 'warning'], paused: ['You have control', 'info'],
  running: ['Agent is continuing…', 'info'], launching: ['Agent is starting…', 'info'], closed: ['Browser closed — still unfinished', 'neutral'],
  failed: ['Agent stopped — still unfinished', 'danger'],
};
function ivState(item, session) {
  if (!session || session.job_id !== item.job_id) return ['Waiting for you', 'warning'];
  if (session.control === 'you' && session.live) return ['You have control', 'info'];
  return IV_STATE[session.status] || ['Waiting for you', 'warning'];
}

export function InterventionsView() {
  const iv = useStore((s) => s.interventions);
  const session = useStore((s) => s.browser.session);
  return html`<div class="view view-interventions">
    <${PageHead} title=${html`Needs <span class="serif">you</span>`} sub="Applications the agent could not finish — a login wall, CAPTCHA, one-time code, or you stopped it. Each stays here until it is submitted or you dismiss it."
      actions=${html`<${Button} icon="refresh" busy=${iv.status === 'refreshing'} onClick=${loadInterventions}>Refresh</${Button}>`} />
    <section class="pane card"><div class="scroll pane-pad">
    ${iv.status === 'error' ? html`<${ErrorBox} message=${iv.error} onRetry=${loadInterventions} />` : null}
    ${iv.status === 'loading' ? html`<${Skeleton} rows=${3} />` : null}
    ${iv.status === 'ready' && !iv.items.length ? html`<div class="pane-center"><${EmptyState} icon="check" title="Nothing needs you">The agent is not waiting on anything.</${EmptyState}></div>` : null}
    <div class="stack">${iv.items.map((it) => { const [state, tone] = ivState(it, session); return html`<div class="iv-row row space wrap" key=${it.id}>
      <div class="stack" style=${{ gap: '4px' }}>
        <div><${Badge} tone="warning">${humanize(it.hitl_type)}</${Badge}> <strong>${it.role || 'Application'}</strong> <span class="muted">@ ${it.company || '—'} · ${relTime(it.created_at)}</span></div>
        <div class="small"><${Badge} tone=${tone}>${state}</${Badge}></div>
      </div>
      <div class="row gap wrap"><${Button} onClick=${() => focusIntervention(it)}>Take over</${Button}>
        <${Button} variant="primary" onClick=${() => continueIntervention(it)}>Let the agent continue</${Button}>
        <${Button} icon="check" onClick=${() => markInterventionApplied(it)}>Mark as applied</${Button}>
        <button type="button" class="link-btn small" onClick=${() => skipIntervention(it)}>Dismiss</button></div></div>`; })}</div>
    </div></section>
  </div>`;
}

// ---------------------------------------------------------------------------- settings
const LLM_META = {
  google: { name: 'Google AI Studio', field: 'google_api_key', hint: 'Gemma 4 31B and Gemini 3.5 Flash Lite', url: 'aistudio.google.com' },
  kilo: { name: 'Kilo Gateway', field: 'kilo_api_key', hint: 'Free models with no key — Nemotron 3 Super, Laguna S, Ling Flash · 200 requests/hour per model', url: 'kilo.ai (key optional)',
    free: true, note: 'Free models may use your prompts (resume text, job posts) to train. Turn off if that matters to you.' },
  nvidia: { name: 'NVIDIA NIM', field: 'nvidia_api_key', hint: 'Nemotron Nano 3, GPT-OSS 20B, GLM Flash, DeepSeek Flash · 40 requests/min', url: 'build.nvidia.com' },
  groq: { name: 'Groq', field: 'groq_api_key', hint: 'GPT-OSS, Kimi K2, Qwen3 — very fast', url: 'console.groq.com' },
  mistral: { name: 'Mistral', field: 'mistral_api_key', hint: 'Mistral Medium / Small / Large (latest)', url: 'console.mistral.ai' },
};
const SEARCH_META = {
  tinyfish: { name: 'TinyFish', field: 'tinyfish_api_key', hint: 'Search API — free utility credits' },
  tavily: { name: 'Tavily', field: 'tavily_api_key', hint: 'Monthly free credits; good snippets' },
  exa: { name: 'Exa', field: 'exa_api_key', hint: 'Neural search; free monthly credits' },
  brave: { name: 'Brave Search', field: 'brave_api_key', hint: 'Independent index; free monthly queries' },
  deep: { name: 'Deep Search', field: null, hint: 'No key — asks 6 free engines at once, opens careers pages for real postings, AI ranks the results' },
  ddgs: { name: 'DuckDuckGo', field: null, hint: 'No key needed — always-available fallback' },
};
const STRATEGIES = [
  ['smart', 'Smart', 'Free Deep Search and one keyed provider answer every query together; results are merged and ranked by AI. Best results.'],
  ['fallback', 'Fallback', 'Ask providers in order; the first with results answers. Fewest calls.'],
  ['spread', 'Spread', 'Rotate queries across providers so free quotas are shared.'],
  ['combine', 'Combine', 'Two providers answer every query and results merge. Widest coverage, uses more quota.'],
];
const fmtLimit = (l) => [l.rpm && `${l.rpm} RPM`, l.rph && `${l.rph}/hour`, l.rpd && `${fmtNum(l.rpd)}/day`, l.tpm && `${fmtNum(l.tpm)} TPM`, l.tpd && `${fmtNum(l.tpd)} TPD`].filter(Boolean).join(' · ') || 'account limits';

function KeyField({ field, configured, masked, source, label }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState('');
  const [busy, setBusy] = useState(false);
  const save = async (v) => { setBusy(true); const ok = await saveSettings({ [field]: v }); setBusy(false); if (ok) { setEditing(false); setVal(''); } };
  if (!editing) {
    return html`<div class="key-row">
      <span class=${`key-pill ${configured ? 'on' : ''}`}><${Icon} name="key" size=${13} />${configured ? masked : 'No key'}</span>
      ${configured && source ? html`<span class="muted small">from ${source}</span>` : null}
      <${Button} size="sm" onClick=${() => setEditing(true)}>${configured ? 'Replace' : 'Add key'}</${Button}>
      ${configured ? html`<button type="button" class="link-btn small" onClick=${() => save('')}>Remove</button>` : null}
    </div>`;
  }
  return html`<div class="key-row editing">
    <input class="input" type="password" autocomplete="off" aria-label=${`${label} API key`} placeholder="Paste key" value=${val}
      onInput=${(e) => setVal(e.currentTarget.value)} onKeyDown=${(e) => { if (e.key === 'Enter' && val.trim()) save(val.trim()); if (e.key === 'Escape') setEditing(false); }} />
    <${Button} size="sm" variant="primary" busy=${busy} disabled=${!val.trim()} onClick=${() => save(val.trim())}>Save</${Button}>
    <${Button} size="sm" onClick=${() => setEditing(false)}>Cancel</${Button}>
  </div>`;
}

function Toggle({ on, onChange, label }) {
  return html`<label class="switch" title=${label}><input type="checkbox" checked=${on} aria-label=${label} onChange=${(e) => onChange(e.currentTarget.checked)} /><span class="switch-ui"></span></label>`;
}

function AiSection({ d, models }) {
  const md = models.data;
  return html`<section class="set-section">
    <div class="row space"><h2>AI providers</h2>
      <${Button} size="sm" icon="refresh" busy=${models.status === 'refreshing' || models.status === 'loading'} onClick=${refreshModels}>Check available models</${Button}></div>
    <p class="muted small">Turn a provider off to never use it. Keys are read from your .env file (or system environment) and can be changed here — they are written back to .env.</p>
    <div class="prov-list">${Object.entries(LLM_META).map(([k, m]) => {
      const st = md && md.providers[k];
      const on = d.providers.llm[k] !== false;
      return html`<div class=${`prov-card ${on ? '' : 'off'}`} key=${k}>
        <div class="prov-head"><div class="grow"><strong>${m.name}</strong><div class="muted small">${m.hint} · keys at ${m.url}</div></div>
          ${st && st.configured ? html`<span class=${`status-dot ${st.reachable === false ? 'bad' : st.reachable ? 'good' : ''}`}
            title=${st.error || ''}>${st.reachable === false ? 'Key rejected / unreachable' : st.reachable ? `${st.models_listed} models available` : 'Not checked yet'}</span>` : null}
          <${Toggle} on=${on} label=${`Use ${m.name}`} onChange=${(v) => setProviders({ llm: { [k]: v } })} /></div>
        ${m.free ? html`<div class="row gap small"><${Badge} tone="success">Works without a key</${Badge}><span class="muted">${m.note}</span></div>`
          : html`<${KeyField} field=${m.field} label=${m.name} configured=${d[`${k}_configured`]} masked=${d[`${k}_key_masked`]} source=${d[`${k}_source`]} />`}
      </div>`;
    })}</div>
    <h3 class="sub-title">Model for each task</h3>
    <p class="muted small">The chosen model is tried first; if it's busy, rate limited or unavailable the next one in the list takes over automatically. Free-tier limits are shown for each model.</p>
    ${md ? html`<div class="form-grid">${Object.entries(md.chains).map(([key, ch]) => html`<${Field} label=${ch.name}>${(id) => html`<${Select} id=${id} block label=${ch.name}
        value=${ch.selected} onChange=${(v) => setModel(key, v)}
        options=${ch.options.map((mid) => { const m = md.all_models.find((x) => x.id === mid) || { name: mid, limits: {} };
          return [mid, `${m.name}${m.reason ? ` — ${m.reason}` : ''}`, fmtLimit(m.limits || {})]; })} />`}</${Field}>`)}</div>`
      : models.status === 'error' ? html`<${ErrorBox} message=${models.error} />` : html`<${Skeleton} lines=${3} />`}
  </section>`;
}

function SearchSection({ d }) {
  const order = d.providers.search_order;
  const move = (p, dir) => {
    const i = order.indexOf(p); const j = i + dir;
    if (j < 0 || j >= order.length) return;
    const next = order.slice(); [next[i], next[j]] = [next[j], next[i]];
    setProviders({ search_order: next });
  };
  return html`<section class="set-section"><h2>Web search</h2>
    <p class="muted small">Providers are asked in this order. Turn any off; Deep Search and DuckDuckGo need no key and are the safety net.</p>
    <div class="field" style=${{ margin: '12px 0 16px' }}><span class="field-label">Strategy</span>
      <${Seg} label="Search strategy" options=${STRATEGIES.map(([k, l]) => [k, l])} value=${d.providers.search_strategy} onChange=${(v) => setProviders({ search_strategy: v })} />
      <span class="field-hint">${(STRATEGIES.find((x) => x[0] === d.providers.search_strategy) || STRATEGIES[0])[2]}</span></div>
    <div class="prov-list">${order.map((k, idx) => { const m = SEARCH_META[k]; if (!m) return null;
      const on = d.providers.search[k] !== false;
      return html`<div class=${`prov-card ${on ? '' : 'off'}`} key=${k}>
        <div class="prov-head"><span class="order-n">${idx + 1}</span>
          <div class="grow"><strong>${m.name}</strong><div class="muted small">${m.hint}</div></div>
          <div class="order-btns"><button type="button" class="icon-btn" aria-label=${`Move ${m.name} up`} disabled=${idx === 0} onClick=${() => move(k, -1)}><${Icon} name="back" size=${14} /></button>
            <button type="button" class="icon-btn" aria-label=${`Move ${m.name} down`} disabled=${idx === order.length - 1} onClick=${() => move(k, 1)}><${Icon} name="next" size=${14} /></button></div>
          <${Toggle} on=${on} label=${`Use ${m.name}`} onChange=${(v) => setProviders({ search: { [k]: v } })} /></div>
        ${m.field ? html`<${KeyField} field=${m.field} label=${m.name} configured=${d[`${k}_configured`]} masked=${d[`${k}_key_masked`]} source=${d[`${k}_source`]} />` : null}
      </div>`; })}</div>
    <div class="stack" style=${{ gap: '4px', marginTop: '16px' }}>
      <label class="switch"><input type="checkbox" checked=${d.enable_web_search_apis} onChange=${(e) => saveSettings({ enable_web_search_apis: e.currentTarget.checked })} /><span class="switch-ui"></span> Use keyed search APIs (off = free Deep Search + DuckDuckGo only)</label>
      <label class="switch"><input type="checkbox" checked=${d.strict_zero_spend_protection} onChange=${(e) => saveSettings({ strict_zero_spend_protection: e.currentTarget.checked })} /><span class="switch-ui"></span> Zero-spend protection (never exceed a provider's free allowance)</label>
    </div>
  </section>`;
}

function TuningSection({ d }) {
  const [t, setT] = useState(d.tunables);
  const dirty = JSON.stringify(t) !== JSON.stringify(d.tunables);
  const num = (k, label, hint, step = 1) => html`<${Field} label=${label} hint=${hint}>${(id) => html`<input id=${id} class="input" type="number" step=${step} value=${t[k]}
    onInput=${(e) => setT({ ...t, [k]: e.currentTarget.value })} />`}</${Field}>`;
  return html`<section class="set-section"><h2>Search tuning</h2><p class="muted small">Loaded from your .env file; saving writes them back.</p>
    <div class="form-grid">
      ${num('max_jobs_per_search', 'Jobs analysed per search', '5–200. More jobs = longer searches and more AI calls.')}
      ${num('max_llm_jd_extractions_per_search', 'Deep AI reads per search', 'How many postings get a full AI read.')}
      ${num('watch_interval_hours', 'Watchlist check (hours)', 'How often your watchlist companies are checked for new roles while the app is open. 0 = off.', 0.5)}
      ${num('fetch_timeout_s', 'Page fetch timeout (s)', 'How long to wait for a job page.', 0.5)}
      ${num('exa_search_num_results', 'Exa results per query', '1–50')}
      <${Field} label="Tavily depth">${(id) => html`<${Select} id=${id} block label="Tavily depth" value=${t.tavily_search_depth}
        onChange=${(v) => setT({ ...t, tavily_search_depth: v })} options=${[['basic', 'Basic', '1 credit'], ['advanced', 'Advanced', '2 credits']]} />`}</${Field}>
    </div>
    <div class="row gap"><${Button} variant="primary" disabled=${!dirty} onClick=${() => saveSettings({ tunables: t })}>Save</${Button}>
      <${Button} disabled=${!dirty} onClick=${() => setT(d.tunables)}>Discard</${Button}></div>
  </section>`;
}

function AgentSection({ d, mode }) {
  const t0 = d.tunables;
  const [t, setT] = useState(t0);
  const dirty = JSON.stringify(t) !== JSON.stringify(t0);
  const sw = (k, label, hint) => html`<div class="set-toggle"><div><strong>${label}</strong><span class="muted small">${hint}</span></div>
    <label class="switch"><input type="checkbox" checked=${!!t[k]} onChange=${(e) => setT({ ...t, [k]: e.currentTarget.checked })} /><span class="switch-ui"></span></label></div>`;
  return html`<section class="set-section"><h2>Auto-apply</h2>
    <p class="muted small">How the browser agent works: <strong>1</strong> check your documents → <strong>2</strong> write what is missing → <strong>3</strong> fill the form live in the Auto-apply tab.</p>
    <h3 class="sub-title">Documents to attach</h3>
    <div class="set-toggles">
      <div class="set-toggle is-fixed"><div><strong>Resume</strong><span class="muted small">Always attached. Tailored to the job and kept to one page.</span></div><${Badge} tone="success">Always</${Badge}></div>
      ${sw('apply_with_cover_letter', 'Cover letter', 'Written for the job and uploaded when the form has a place for it.')}
      ${sw('apply_with_cv', 'CV', 'Your longer, general career story — used when a form asks for a CV.')}
    </div>
    <h3 class="sub-title">Agent behaviour</h3>
    <div class="form-grid">
      <${Field} label="Most steps per run" hint="10–150. The agent stops and asks you if it needs more.">${(id) => html`<input id=${id} class="input" type="number" min="10" max="150" value=${t.browser_max_steps}
        onInput=${(e) => setT({ ...t, browser_max_steps: e.currentTarget.value })} />`}</${Field}>
      <${Field} label="Pause between steps (s)" hint="A small pause looks more human and stays inside free AI limits.">${(id) => html`<input id=${id} class="input" type="number" min="0" max="20" step="0.5" value=${t.browser_step_delay_s}
        onInput=${(e) => setT({ ...t, browser_step_delay_s: e.currentTarget.value })} />`}</${Field}>
    </div>
    <div class="set-toggles">${sw('browser_show_window', 'Also show a separate Chrome window', 'Off = the browser is shown only inside the app (recommended). Turn on just for debugging.')}</div>
    <div class="row gap"><${Button} variant="primary" disabled=${!dirty} onClick=${() => saveSettings({ tunables: t })}>Save</${Button}>
      <${Button} disabled=${!dirty} onClick=${() => setT(t0)}>Discard</${Button}></div>
    <h3 class="sub-title">When to apply</h3>
    <${Seg} label="Pipeline mode" options=${[['manual', 'Only when I press Auto-apply'], ['automatic', 'Automatically for strong matches']]} value=${mode.mode} onChange=${setPipelineMode} />
  </section>`;
}

const PROVIDER_NAMES = { google: 'Google', kilo: 'Kilo (free)', nvidia: 'NVIDIA NIM', groq: 'Groq', mistral: 'Mistral' };
const SEARCH_NAMES = { tinyfish: 'TinyFish', tavily: 'Tavily', exa: 'Exa', brave: 'Brave Search', deep: 'Deep Search (free)', ddgs: 'DuckDuckGo (free)' };

function UsageBody({ u }) {
  const rows = u.llm.rows;
  const total = rows.reduce((a, r) => a + r.calls, 0) || 1;
  const search = u.web_search.providers.filter((p) => p.calls);
  return html`<p class="muted small">Each task asks its first model; when that model is busy (free tiers allow only a few calls a minute),
      the call goes straight to the next free model in the chain — so backups appear here once searches run several things at once.
      Answers served from the cache are not counted.</p>
    <table class="checks"><thead><tr><th>Model</th><th>Provider</th><th>Calls</th><th>Share</th><th>Tokens</th></tr></thead><tbody>
      ${rows.map((r) => html`<tr><td>${r.label}</td><td class="muted">${PROVIDER_NAMES[r.provider] || r.provider || '—'}</td><td>${fmtNum(r.calls)}</td>
        <td>${Math.round((r.calls / total) * 100)}%</td><td>${fmtNum(r.total_tokens)}</td></tr>`)}
      ${!rows.length ? html`<tr><td colspan="5" class="muted">No AI calls yet.</td></tr>` : null}</tbody></table>
    <h3 class="sub-title">Web search</h3>
    <table class="checks"><thead><tr><th>Provider</th><th>Calls</th><th>This month</th><th>Last used</th></tr></thead><tbody>
      ${search.map((p) => html`<tr><td>${SEARCH_NAMES[p.name] || p.name}</td><td>${fmtNum(p.calls)}</td><td>${fmtNum(p.calls_this_month || 0)}</td>
        <td class="muted">${p.last_used ? relTime(p.last_used.replace(' ', 'T') + 'Z') : '—'}</td></tr>`)}
      ${!search.length ? html`<tr><td colspan="4" class="muted">No web searches yet.</td></tr>` : null}</tbody></table>
    <p class="muted small">Gemma today: ${u.gemma_budget.requests_today} / ${u.gemma_budget.requests_cap} requests (${u.gemma_budget.model}).</p>`;
}

function SettingsOverview({ d }) {
  if (!d) return null;
  const llm = ['google', 'kilo', 'nvidia', 'groq', 'mistral'];
  const search = d.search_providers || [];
  const on = (kind, p) => !d.providers || !d.providers[kind] || d.providers[kind][p] !== false;
  const llmReady = llm.filter((p) => (p === 'kilo' || d[`${p}_configured`]) && on('llm', p)).length;
  const searchReady = search.filter((p) => (p === 'ddgs' || p === 'deep' || d[`${p}_configured`]) && on('search', p)).length;
  const item = (ok, label, value) => html`<div class=${`ov-item ${ok ? 'ok' : 'warn'}`}><span class="ov-dot"></span><span class="grow">${label}</span><strong>${value}</strong></div>`;
  return html`<div class="set-overview">
    ${item(llmReady > 0, 'AI providers', `${llmReady}/${llm.length}`)}
    ${item(searchReady > 0, 'Web search', `${searchReady}/${search.length}`)}
    ${item(true, 'Auto-apply', d.tunables && d.tunables.browser_show_window ? 'window + in-app' : 'in-app')}
  </div>`;
}

function DataSection() {
  const db = useStore((s) => s.db);
  useEffect(() => { loadDbHealth(); }, []);
  const r = db.data;
  return html`<section class="set-section"><div class="row space"><h2>Data & database</h2>
      <div class="row gap"><${Button} size="sm" icon="download" onClick=${backupDb}>Back up</${Button}>
        <${Button} size="sm" icon="refresh" busy=${db.status === 'refreshing'} onClick=${repairDb}>Check & repair</${Button}></div></div>
    <p class="muted small">The database is checked every time JobHunterX starts; damaged files are set aside and recovered automatically.</p>
    ${db.status === 'error' ? html`<${ErrorBox} message=${db.error} onRetry=${loadDbHealth} />` : null}
    ${r ? html`<div class="health">
      <div class=${`health-badge h-${r.status}`}><${Icon} name=${r.status === 'ok' ? 'check' : 'alert'} size=${16} />${r.status === 'ok' ? 'Healthy' : r.status === 'warn' ? 'Needs attention' : 'Problems found'}
        <span class="muted small">schema v${r.schema_version || '?'} · ${(r.size_bytes / 1048576).toFixed(1)} MB · ${Object.entries(r.counts || {}).map(([k, v]) => `${v} ${k.replace('_', ' ')}`).join(' · ')}</span></div>
      ${r.preflight && r.preflight.status === 'recovered' ? html`<${Notice} tone="warning">${r.preflight.detail}</${Notice}>` : null}
      <ul class="health-list">${r.checks.map((c) => html`<li key=${c.name} class=${`h-${c.status}`}><span class="h-dot"></span><strong>${c.name}</strong><span class="muted small">${c.detail}</span></li>`)}</ul>
    </div>` : db.status !== 'error' ? html`<${Skeleton} lines=${4} />` : null}
    <h3 class="sub-title">Clean up</h3>
    <div class="row gap wrap"><${Button} onClick=${() => clearJobs('unsaved')}>Clear unsaved jobs</${Button}><${Button} onClick=${() => clearJobs('all')}>Clear all jobs</${Button}>
      <${Button} variant="danger" onClick=${resetEverything}>Reset everything</${Button}></div>
  </section>`;
}

const SETTINGS_SECTIONS = [
  { key: 'ai', label: 'AI providers', icon: 'spark' }, { key: 'search', label: 'Web search', icon: 'search' },
  { key: 'tuning', label: 'Search tuning', icon: 'sliders' }, { key: 'usage', label: 'Usage', icon: 'chart' },
  { key: 'profiles', label: 'Profiles', icon: 'user' }, { key: 'agent', label: 'Auto-apply', icon: 'globe' },
  { key: 'look', label: 'Appearance', icon: 'sun' }, { key: 'data', label: 'Data', icon: 'shield' },
];

export function SettingsView() {
  const st = useStore((s) => s.settings);
  const models = useStore((s) => s.models);
  const usage = useStore((s) => s.usage);
  const mode = useStore((s) => s.pipelineMode);
  const theme = useStore((s) => s.theme);
  const motion = useStore((s) => s.motion);
  const [sec, setSec] = useState('ai');
  const d = st.data;
  const needData = ['ai', 'search', 'tuning', 'agent'].includes(sec);
  const body = () => {
    if (needData && !d) return st.status === 'error' ? html`<${ErrorBox} message=${st.error} onRetry=${loadSettings} />` : html`<${Skeleton} lines=${6} />`;
    switch (sec) {
      case 'ai': return html`<${AiSection} d=${d} models=${models} />`;
      case 'search': return html`<${SearchSection} d=${d} />`;
      case 'tuning': return html`<${TuningSection} key=${JSON.stringify(d.tunables)} d=${d} />`;
      case 'usage': return html`<section class="set-section"><div class="row space"><h2>Usage</h2><${Button} size="sm" icon="refresh" busy=${usage.status === 'refreshing'} onClick=${loadUsage}>Refresh</${Button}></div>
        ${usage.data ? html`<${UsageBody} u=${usage.data} />`
          : usage.status === 'error' ? html`<${ErrorBox} message=${usage.error} />` : html`<${Skeleton} lines=${3} />`}</section>`;
      case 'profiles': return html`<${PeopleManager} />`;
      case 'agent': return html`<${AgentSection} key=${JSON.stringify(d.tunables)} d=${d} mode=${mode} />`;
      case 'look': return html`<section class="set-section"><h2>Appearance</h2>
        <div class="field"><span class="field-label">Theme</span><${Seg} label="Theme" options=${[['light', 'Light'], ['dark', 'Dark']]} value=${theme} onChange=${setTheme} /></div>
        <div class="field" style=${{ marginTop: '16px' }}><span class="field-label">Motion</span>
          <${Seg} label="Motion" options=${[['full', 'Full'], ['reduced', 'Reduced'], ['system', 'Follow system']]} value=${motion} onChange=${setMotion} />
          <span class="field-hint">${motion === 'system' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
            ? 'Your system currently asks for reduced motion (Windows: Settings → Accessibility → Visual effects → Animation effects), so animations are minimal.'
            : 'Full keeps every animation; Reduced keeps only loading indicators.'}</span></div></section>`;
      default: return html`<${DataSection} />`;
    }
  };
  return html`<div class="view view-settings">
    <${PageHead} title=${html`Settings`} sub="Providers, keys, search behaviour, profiles and data — all in one place." />
    <div class="split split-settings">
      <nav class="pane card set-nav" aria-label="Settings sections">${SETTINGS_SECTIONS.map((x) => html`<button type="button" key=${x.key}
        class=${`set-link ${sec === x.key ? 'active' : ''}`} aria-current=${sec === x.key ? 'true' : undefined} onClick=${() => setSec(x.key)}>
        <${Icon} name=${x.icon} size=${16} />${x.label}</button>`)}<${SettingsOverview} d=${d} /></nav>
      <section class="pane card"><div class="scroll pane-pad set-body" key=${sec}>${body()}</div></section>
    </div>
  </div>`;
}
