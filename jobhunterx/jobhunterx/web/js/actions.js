// All side effects live here. Components call actions; actions update the store.
// Rules: every async flow has explicit status; late responses never overwrite newer
// ones (sequence numbers + AbortController); WS events are filtered by run id.
import { api, ApiError, isAbortError } from './lib/api.js';
import { ReconnectingSocket } from './lib/ws.js';
import {
  getState, setState, setSlice, setEntry, setPending, parseHash, initialState,
} from './state/store.js';
import { matchesList, sortIds, summaryFromDetail, SUMMARY_SAFE_FIELDS, genKey } from './state/domain.js';

const prefersReducedMotion = () => {
  const m = document.documentElement.dataset.motion;
  if (m === 'reduced') return true;
  if (m === 'full') return false;
  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
};
export function setMotion(motion) {
  setState((s) => ({ ...s, motion }));
  try { localStorage.setItem('jhx-motion', motion); } catch { /* ignore */ }
}
/** Run a state change inside a View Transition when the browser supports it (pure enhancement). */
export function withTransition(apply) {
  if (!document.startViewTransition || prefersReducedMotion() || document.hidden) { apply(); return; }
  // Preact renders on a microtask after the store changes; resolve after it so the new DOM is captured.
  document.startViewTransition(() => { apply(); return new Promise((r) => setTimeout(r, 0)); });
}

// ---------------------------------------------------------------------------
// Toasts, confirm, activity
// ---------------------------------------------------------------------------
let toastSeq = 0;
export async function copyText(text, what = 'Copied') {
  try {
    await navigator.clipboard.writeText(text);
    toast(`${what} — paste it anywhere.`, 'success', 2500);
  } catch {
    toast('Could not copy — select the text and copy it yourself.', 'warning');
  }
}
export function toast(message, tone = 'info', ms = 4500) {
  const id = ++toastSeq;
  setState((s) => ({ ...s, toasts: [...s.toasts, { id, message, tone, ms }].slice(-4) }));
  setTimeout(() => dismissToast(id), ms);
}
export function dismissToast(id) {
  setState((s) => ({ ...s, toasts: s.toasts.filter((t) => t.id !== id) }));
}
export function errorText(err) {
  if (err instanceof ApiError) return err.message;
  return (err && err.message) || 'Something went wrong.';
}
export function confirmAction(opts) {
  return new Promise((resolve) => setState((s) => ({ ...s, confirm: { ...opts, resolve } })));
}
export function closeConfirm(result) {
  const c = getState().confirm;
  setState((s) => ({ ...s, confirm: null }));
  if (c) c.resolve(result);
}
function activity(message, level = 'info', source = 'app') {
  setState((s) => ({ ...s, activity: [{ id: Date.now() + Math.random(), ts: new Date().toISOString(), message, level, source }, ...s.activity].slice(0, 200) }));
}

// ---------------------------------------------------------------------------
// Routing & theme
// ---------------------------------------------------------------------------
export function navigate(hash) {
  if (window.location.hash !== hash) window.location.hash = hash;
  else setSlice('route', parseHash());
}
export function initRouting() {
  window.addEventListener('hashchange', () => {
    const route = parseHash();
    const prev = getState().route;
    const apply = () => setState((s) => ({ ...s, route }));
    if (prev.page !== route.page && getState().app.phase === 'ready') withTransition(apply); else apply();
    onRoute(route);
  });
  onRoute(getState().route);
}
function onRoute(route) {
  if (route.jobId) loadDetail(route.jobId);
  if (route.page === 'documents') { loadDocuments(); if (route.docId) loadDocument(route.docId); }
  if (route.page === 'tracker') loadTracker();
  if (route.page === 'interventions' || route.page === 'browser') loadInterventions();
  if (route.page === 'browser') loadApplySession();
  if (route.page === 'settings') { loadSettings(); loadModels(); loadUsage(); loadPipelineMode(); loadPeople().catch(() => {}); }
}
export function setTheme(theme) {
  setState((s) => ({ ...s, theme }));
  try { localStorage.setItem('jhx-theme', theme); } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Jobs cache helpers
// ---------------------------------------------------------------------------
function upsertJobs(summaries) {
  setState((s) => {
    const byId = { ...s.jobs.byId };
    const details = { ...s.details };
    for (const j of summaries) {
      byId[j.id] = { ...(byId[j.id] || {}), ...j };
      const d = details[j.id];
      if (d && d.job) {
        const merged = { ...d.job };
        for (const f of SUMMARY_SAFE_FIELDS) if (f in j) merged[f] = j[f];
        details[j.id] = { ...d, job: merged };
      }
    }
    return { ...s, jobs: { byId }, details };
  });
}
function reconcileListMembership(job) {
  setState((s) => {
    const list = s.list;
    if (list.status !== 'ready' && list.status !== 'loading') return s;
    const inRunScope = list.scope !== 'run' || job.run_id === list.runId;
    const should = inRunScope && matchesList(job, list);
    const has = list.ids.includes(job.id);
    if (should === has) {
      return has ? { ...s, list: { ...list, ids: sortIds(list.ids, s.jobs.byId, list.sort) } } : s;
    }
    const ids = should ? sortIds([...list.ids, job.id], s.jobs.byId, list.sort) : list.ids.filter((x) => x !== job.id);
    return { ...s, list: { ...list, ids } };
  });
}
function removeJobs(ids) {
  setState((s) => {
    const byId = { ...s.jobs.byId };
    const details = { ...s.details };
    ids.forEach((id) => { delete byId[id]; delete details[id]; });
    return { ...s, jobs: { byId }, details, list: { ...s.list, ids: s.list.ids.filter((x) => !ids.includes(x)) },
      tracker: { ...s.tracker, ids: s.tracker.ids.filter((x) => !ids.includes(x)) } };
  });
}

// ---------------------------------------------------------------------------
// App lifecycle & one-time onboarding
// ---------------------------------------------------------------------------
// The step is remembered so a reload in the middle of setup resumes where the user was.
const ONB_KEY = 'jhx-onboarding';
const ONB_STEPS = ['upload', 'review', 'prefs', 'pay', 'launch'];
function readOnb() { try { return localStorage.getItem(ONB_KEY); } catch { return null; } }
function writeOnb(v) { try { if (v) localStorage.setItem(ONB_KEY, v); else localStorage.removeItem(ONB_KEY); } catch { /* ignore */ } }

export function setOnboardingStep(step) {
  if (!ONB_STEPS.includes(step)) return;
  const cur = getState().onboarding.step;
  writeOnb(step);
  setSlice('onboarding', { step, dir: ONB_STEPS.indexOf(step) >= ONB_STEPS.indexOf(cur) ? 1 : -1 });
}
/** Leave setup. With a request, the first search starts immediately. */
export function finishOnboarding({ search = null, to = '#/discover' } = {}) {
  writeOnb(null);
  withTransition(() => {
    setSlice('app', { phase: 'ready' });
    if (window.location.hash !== to) window.location.hash = to;
  });
  if (search) startSearch(search);
}
function decidePhase() {
  const p = getState().profile;
  if (p.status === 'error' && !p.envelope) { setSlice('app', { phase: 'error', error: p.error }); return; }
  const hasProfile = !!(p.envelope && p.envelope.profile);
  const pending = readOnb();
  if (!hasProfile) {
    setSlice('onboarding', { step: 'upload', dir: 1 });
    setSlice('app', { phase: 'onboarding', error: null });
  } else if (pending && pending !== 'upload' && ONB_STEPS.includes(pending)) {
    setSlice('onboarding', { step: pending, dir: 1 });
    setSlice('app', { phase: 'onboarding', error: null });
  } else {
    setSlice('app', { phase: 'ready', error: null });
  }
}
export async function retryBoot() {
  setSlice('app', { phase: 'booting', error: null });
  await startSession();
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------
let profileCtrl = null;
export async function loadProfile() {
  profileCtrl?.abort();
  profileCtrl = new AbortController();
  setSlice('profile', { status: getState().profile.envelope ? 'refreshing' : 'loading', error: null });
  try {
    const env = await api.getProfile({ signal: profileCtrl.signal, timeout: 90_000 });
    setSlice('profile', { status: 'ready', envelope: env });
  } catch (err) {
    if (isAbortError(err)) return;
    setSlice('profile', { status: 'error', error: errorText(err) });
  }
}
let uploadPoll = null;
function finishUpload(up, result) {
  clearInterval(uploadPoll); uploadPoll = null;
  if (getState().profile.upload.id !== up.id) return;        // a newer upload replaced this one
  if (up.status === 'failed') {
    setSlice('profile', (p) => ({ ...p, upload: { ...p.upload, status: 'error', stage: 'failed', error: up.error || 'Could not read the resume.' } }));
    return;
  }
  const { extraction, ...env } = result || {};
  setSlice('profile', (p) => ({ ...p, status: 'ready', envelope: result ? env : p.envelope,
    upload: { ...p.upload, status: 'done', stage: 'done', error: null, extraction: extraction || null } }));
  loadPeople();
  const partial = extraction && extraction.status === 'partial';
  if (getState().app.phase === 'onboarding') setOnboardingStep('review');
  toast(partial ? 'Resume read — please review the highlighted gaps.' : 'Resume read successfully.', partial ? 'warning' : 'success');
}
/** Background upload: the server answers at once and streams stages; we also poll in case a WS event is missed. */
export async function uploadResume(file) {
  if (!file) return;
  if (getState().profile.upload.status === 'uploading') return;
  setSlice('profile', (p) => ({ ...p, upload: { status: 'uploading', stage: 'sending', id: null, error: null, extraction: null, fileName: file.name, startedAt: Date.now() } }));
  try {
    const { upload } = await api.uploadProfile(file);
    setSlice('profile', (p) => ({ ...p, upload: { ...p.upload, id: upload.id, stage: upload.stage } }));
    clearInterval(uploadPoll);
    uploadPoll = setInterval(async () => {
      const cur = getState().profile.upload;
      if (cur.id !== upload.id || cur.status !== 'uploading') { clearInterval(uploadPoll); return; }
      try {
        const res = await api.uploadStatus(upload.id);
        onUploadEvent(res.upload, res.result);
      } catch { /* transient — keep polling */ }
    }, 5000);
  } catch (err) {
    setSlice('profile', (p) => ({ ...p, upload: { ...p.upload, status: 'error', stage: 'failed', error: errorText(err) } }));
  }
}
function onUploadEvent(up, result) {
  const cur = getState().profile.upload;
  if (!up || cur.id !== up.id || cur.status !== 'uploading') return;
  if (up.status === 'done' || up.status === 'failed') {
    if (up.status === 'done' && !result) {   // WS event carries no payload: fetch the result once
      api.uploadStatus(up.id).then((r) => finishUpload(r.upload, r.result)).catch(() => finishUpload(up, null));
      return;
    }
    finishUpload(up, result);
  } else {
    setSlice('profile', (p) => ({ ...p, upload: { ...p.upload, stage: up.stage } }));
  }
}

export async function saveProfile(profile, { quiet = false } = {}) {
  if (getState().profile.saving) return false;
  setSlice('profile', { saving: true, saveError: null, saveDetails: [] });
  try {
    const env = await api.putProfile(profile, { timeout: 90_000 });
    setSlice('profile', { saving: false, status: 'ready', envelope: env });
    if (!quiet) toast('Profile saved. Matches will refresh on the next search or rescore.', 'success');
    return true;
  } catch (err) {
    setSlice('profile', { saving: false, saveError: errorText(err), saveDetails: (err.details || []).map((d) => d.msg ? `${(d.loc || []).slice(1).join('.')}: ${d.msg}` : String(d)) });
    return false;
  }
}

// ---------------------------------------------------------------------------
// Search runs
// ---------------------------------------------------------------------------
const FEED_KEEP = 150;
/** Merge activity lines (by increasing id) into the feed of `runId`; a new run starts a fresh feed. */
function mergeFeed(runId, items) {
  if (!items || !items.length) return;
  setSlice('search', (sr) => {
    const base = sr.feed.runId === runId ? sr.feed.items : [];
    const last = base.length ? base[base.length - 1].id : 0;
    const add = items.filter((x) => x.id > last);
    if (!add.length && sr.feed.runId === runId) return sr;
    return { ...sr, feed: { runId, items: [...base, ...add].slice(-FEED_KEEP) } };
  });
}
export async function startSearch(req) {
  const s = getState().search;
  if (s.starting) return;
  setSlice('search', { starting: true, startError: null, lastRequest: req });
  try {
    const { run } = await api.startSearch(req);
    setSlice('search', { starting: false, activeRunId: run.id, run, streamedIds: [], feed: { runId: run.id, items: run.activity || [] } });
    setList({ scope: 'run', runId: run.id });
    activity(`Search started (${run.id.slice(0, 8)})`, 'info', 'search');
  } catch (err) {
    setSlice('search', { starting: false, startError: errorText(err) });
  }
}
export async function cancelSearch() {
  const { activeRunId, cancelling } = getState().search;
  if (!activeRunId || cancelling) return;
  setSlice('search', { cancelling: true, cancelError: null });
  try {
    const { run } = await api.cancelSearch(activeRunId);
    if (getState().search.activeRunId === run.id) setSlice('search', { run });
  } catch (err) {
    setSlice('search', { cancelError: errorText(err) });
  } finally {
    setSlice('search', { cancelling: false });
  }
}
async function loadCurrentRun() {
  try {
    const { run } = await api.currentSearch();
    if (!run) return;
    if (run.mode === 'watch') {                 // a background watchlist check is not the user's search
      if (['queued', 'running'].includes(run.status)) onWatchRun(run);
      return;
    }
    const active = getState().search.activeRunId;
    if (!active || active === run.id) { setSlice('search', { activeRunId: run.id, run }); mergeFeed(run.id, run.activity); }
  } catch { /* non-fatal */ }
}

// ---------------------------------------------------------------------------
// Job list (sequenced; a slower old response can never overwrite a newer one)
// ---------------------------------------------------------------------------
let listSeq = 0;
let listCtrl = null;
export function setList(partial) {
  setSlice('list', partial);
  loadList();
}
function listQuery(l, extra = {}) {
  return { view: l.view, q: l.q, work_mode: l.work_mode, min_score: l.min_score || '', sort: l.sort,
    run_id: l.scope === 'run' ? l.runId : '', ...extra };
}
// Tab counts while jobs stream in: one small request at most every ~1.5 s, same filters as the list.
let countsTimer = null;
function refreshCountsSoon() {
  if (countsTimer) return;
  countsTimer = setTimeout(async () => {
    countsTimer = null;
    try {
      const res = await api.listJobs(listQuery(getState().list, { limit: 1 }));
      setSlice('list', { counts: res.counts });
    } catch { /* the next full load corrects it */ }
  }, 1500);
}
// The list arrives in pages: the first one at once, the next when you scroll near the end (see loadMoreList).
const PAGE = 100;
export async function loadList() {
  const seq = ++listSeq;
  listCtrl?.abort();
  listCtrl = new AbortController();
  const l = getState().list;
  setSlice('list', { status: 'loading', error: null });
  try {
    const res = await api.listJobs(listQuery(l, { limit: PAGE }), { signal: listCtrl.signal });
    if (seq !== listSeq) return;
    upsertJobs(res.jobs);
    setSlice('list', { status: 'ready', ids: res.jobs.map((j) => j.id), counts: res.counts, hasMore: !!res.has_more, more: false });
  } catch (err) {
    if (isAbortError(err) || seq !== listSeq) return;
    setSlice('list', { status: 'error', error: errorText(err) });
  }
}
export async function loadMoreList() {
  const l = getState().list;
  if (!l.hasMore || l.more || l.status !== 'ready') return;
  const seq = listSeq;
  setSlice('list', { more: true });
  try {
    const res = await api.listJobs(listQuery(l, { limit: PAGE, offset: l.ids.length }), { signal: listCtrl?.signal });
    if (seq !== listSeq) return;                                  // filters changed meanwhile: that load wins
    upsertJobs(res.jobs);
    const have = new Set(getState().list.ids);
    setSlice('list', { ids: [...getState().list.ids, ...res.jobs.map((j) => j.id).filter((id) => !have.has(id))],
      counts: res.counts, hasMore: !!res.has_more, more: false });
  } catch (err) {
    if (seq === listSeq) setSlice('list', { more: false, hasMore: !isAbortError(err) && l.hasMore });
  }
}

// ---------------------------------------------------------------------------
// Job detail & actions
// ---------------------------------------------------------------------------
const detailCtrl = {};
export async function loadDetail(jobId, { silent = false } = {}) {
  detailCtrl[jobId]?.abort();
  const ctrl = new AbortController();
  detailCtrl[jobId] = ctrl;
  if (!silent) setEntry('details', jobId, (d) => ({ ...(d || {}), status: d && d.job ? 'refreshing' : 'loading', error: null }));
  try {
    const { job } = await api.getJob(jobId, { signal: ctrl.signal });
    if (detailCtrl[jobId] !== ctrl) return;
    setEntry('details', jobId, { status: 'ready', job, error: null });
    upsertJobs([summaryFromDetail(job)]);
  } catch (err) {
    if (isAbortError(err)) return;
    setEntry('details', jobId, (d) => ({ ...(d || {}), status: 'error', error: errorText(err) }));
  }
}
export async function toggleSaved(jobId) {
  const s = getState();
  if (s.pending.save[jobId]) return;
  const job = s.jobs.byId[jobId] || (s.details[jobId] && s.details[jobId].job);
  if (!job) return;
  const want = !job.saved;
  setPending('save', jobId, true);
  upsertJobs([{ id: jobId, saved: want }]);
  try {
    const res = want ? await api.saveJob(jobId) : await api.unsaveJob(jobId);
    upsertJobs([res.job]);
    reconcileListMembership(getState().jobs.byId[jobId]);
  } catch (err) {
    upsertJobs([{ id: jobId, saved: !want }]);
    toast(`Could not ${want ? 'save' : 'unsave'} the job: ${errorText(err)}`, 'danger');
  } finally {
    setPending('save', jobId, false);
  }
}
export async function setTracking(jobId, status) {
  if (getState().pending.track[jobId]) return;
  const prev = getState().jobs.byId[jobId]?.tracking_status;
  setPending('track', jobId, true);
  upsertJobs([{ id: jobId, tracking_status: status }]);
  try {
    const res = await api.patchJob(jobId, { tracking_status: status });
    upsertJobs([res.job]);
    reconcileListMembership(getState().jobs.byId[jobId]);
  } catch (err) {
    upsertJobs([{ id: jobId, tracking_status: prev }]);
    toast(`Could not update status: ${errorText(err)}`, 'danger');
  } finally {
    setPending('track', jobId, false);
  }
}
async function detailAction(kind, jobId, call, okMsg) {
  if (getState().pending[kind][jobId]) return;
  setPending(kind, jobId, true);
  try {
    const { job } = await call(jobId);
    setEntry('details', jobId, { status: 'ready', job, error: null });
    upsertJobs([summaryFromDetail(job)]);
    reconcileListMembership(getState().jobs.byId[jobId]);
    if (okMsg) toast(okMsg, 'success');
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    setPending(kind, jobId, false);
  }
}
export const verifyJob = (id) => detailAction('verify', id, api.verifyJob, 'Posting re-checked.');
export const connectJob = (id) => detailAction('connect', id, api.connectJob, 'Referral kit ready.');
export const rescoreJob = (id) => detailAction('rescore', id, api.rescoreJob, 'Match updated for your current profile.');
export async function deleteJob(jobId) {
  if (getState().pending.remove[jobId]) return;
  if (!(await confirmAction({ title: 'Remove this job?', body: 'It will be removed from all lists. Generated documents for it are kept.', confirm: 'Remove', tone: 'danger' }))) return;
  setPending('remove', jobId, true);
  try {
    await api.deleteJob(jobId);
    removeJobs([jobId]);
    if (getState().route.jobId === jobId) navigate(`#/${getState().route.page}`);
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    setPending('remove', jobId, false);
  }
}
export async function clearJobs(scope) {
  const label = scope === 'all' ? 'all jobs' : 'unsaved jobs';
  if (!(await confirmAction({ title: `Clear ${label}?`, body: scope === 'all' ? 'Every discovered job (including saved and tracked ones) will be deleted.' : 'Saved and tracked jobs are kept.', confirm: 'Clear', tone: 'danger' }))) return;
  try {
    const { deleted } = await api.clearJobs(scope);
    toast(`Removed ${deleted} jobs.`, 'success');
    setState((s) => ({ ...s, jobs: { byId: {} }, details: {} }));
    loadList();
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}
export async function autoApply(jobId) {
  if (getState().pending.apply[jobId]) return;
  const cur = getState().browser.session;
  if (cur && cur.job_id === jobId && ['needs_you', 'stopped'].includes(cur.status)) {
    navigate('#/browser');
    return;
  }
  if (!(await confirmAction({
    title: 'Apply with the browser agent?',
    body: 'First we check your resume, cover letter and CV for this job and write any that are missing (resume on one page). Then the agent opens the application right inside the Auto-apply tab — you can watch, stop, or take over any time.',
    confirm: 'Check documents & start',
  }))) return;
  setPending('apply', jobId, true);
  try {
    const { session } = await api.applyJob(jobId);
    if (session) setSlice('browser', { status: 'ready', session, error: null });
    navigate('#/browser');
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    setPending('apply', jobId, false);
  }
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
export async function generateDocument(jobId, kind) {
  const key = genKey(jobId, kind);
  if (getState().gen[key]?.status === 'generating') return;
  setEntry('gen', key, { status: 'generating', error: null, documentId: null, startedAt: Date.now() });
  try {
    const { document } = await api.generateDocument(jobId, kind);
    setEntry('gen', key, { status: 'ready', error: null, documentId: document.id });
    setEntry('docDetails', document.id, { status: 'ready', doc: document, error: null });
    upsertJobs([{ id: jobId, documents: { ...(getState().jobs.byId[jobId]?.documents || {}), [kind]: document.id } }]);
    loadDocuments();
    if (getState().details[jobId]) loadDetail(jobId, { silent: true });
  } catch (err) {
    setEntry('gen', key, { status: 'failed', error: errorText(err), documentId: null });
  }
}
export async function generateCv(focus) {
  const key = genKey(null, 'cv');
  if (getState().gen[key]?.status === 'generating') return;
  setEntry('gen', key, { status: 'generating', error: null, documentId: null, focus, startedAt: Date.now() });
  try {
    const { document } = await api.generateCv(focus);
    setEntry('gen', key, { status: 'ready', error: null, documentId: document.id });
    setEntry('docDetails', document.id, { status: 'ready', doc: document, error: null });
    loadDocuments();
    navigate(`#/documents/${document.id}`);
  } catch (err) {
    setEntry('gen', key, { status: 'failed', error: errorText(err), documentId: null, focus });
  }
}
let docsSeq = 0;
export async function loadDocuments() {
  const seq = ++docsSeq;
  setSlice('docs', (d) => ({ ...d, status: d.items.length ? 'refreshing' : 'loading', error: null }));
  try {
    const { documents } = await api.listDocuments({});
    if (seq !== docsSeq) return;
    setSlice('docs', { status: 'ready', items: documents });
  } catch (err) {
    if (seq !== docsSeq) return;
    setSlice('docs', { status: 'error', error: errorText(err) });
  }
}
export async function loadDocument(docId) {
  if (getState().docDetails[docId]?.status === 'ready') return;
  setEntry('docDetails', docId, { status: 'loading', doc: null, error: null });
  try {
    const { document } = await api.getDocument(docId);
    setEntry('docDetails', docId, { status: 'ready', doc: document, error: null });
  } catch (err) {
    setEntry('docDetails', docId, { status: 'error', doc: null, error: errorText(err) });
  }
}
export async function deleteDocument(docId) {
  if (!(await confirmAction({ title: 'Delete this document?', body: 'The PDF and its history will be removed.', confirm: 'Delete', tone: 'danger' }))) return;
  try {
    await api.deleteDocument(docId);
    setEntry('docDetails', docId, undefined);
    loadDocuments();
    if (getState().route.docId === docId) navigate('#/documents');
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}

// ---------------------------------------------------------------------------
// Tracker (saved + tracked jobs)
// ---------------------------------------------------------------------------
let trackerSeq = 0;
export async function loadTracker() {
  const seq = ++trackerSeq;
  setSlice('tracker', (t) => ({ ...t, status: t.ids.length ? 'refreshing' : 'loading', error: null }));
  try {
    const res = await api.listJobs({ view: 'saved', sort: 'recent', limit: 500 });
    if (seq !== trackerSeq) return;
    upsertJobs(res.jobs);
    setSlice('tracker', { status: 'ready', ids: res.jobs.map((j) => j.id) });
  } catch (err) {
    if (seq !== trackerSeq) return;
    setSlice('tracker', { status: 'error', error: errorText(err) });
  }
}

// ---------------------------------------------------------------------------
// Watchlist (researched companies; their own job boards are checked every few hours)
// ---------------------------------------------------------------------------
let watchSeq = 0;
export async function loadWatchlist(scope = 'mine') {
  const seq = ++watchSeq;
  setSlice('watch', (w) => ({ ...w, status: w.data ? 'refreshing' : 'loading', error: null }));
  try {
    const data = await api.watchlist(scope);
    if (seq !== watchSeq) return;
    setSlice('watch', { status: 'ready', data, scope, checking: !!(data.status && data.status.checking) });
  } catch (err) {
    if (seq !== watchSeq) return;
    setSlice('watch', { status: 'error', error: errorText(err) });
  }
}
export async function checkWatchlistNow() {
  setSlice('watch', { checking: true });
  try {
    await api.checkWatchlist();
    toast('Checking your watchlist companies for new roles…', 'info');
  } catch (err) {
    setSlice('watch', { checking: false });
    toast(errorText(err), 'danger');
  }
}
// A background watchlist check streams the same events as a search; it gets its own live panel
// (Companies page + sidebar dot) instead of taking over the Discover screen.
const WATCH_FEED_KEEP = 6;
function onWatchRun(run) {
  setSlice('watch', (w) => ({ ...w, checking: ['queued', 'running'].includes(run.status), run,
    feed: w.run && w.run.id === run.id ? w.feed : (run.activity || []).slice(-WATCH_FEED_KEEP) }));
}
function isWatchEvent(msg) {
  const w = getState().watch;
  return !!(msg.run_id && w.run && w.run.id === msg.run_id);
}
function onWatchDone(d) {
  setSlice('watch', (w) => ({ ...w, checking: false, run: w.run ? { ...w.run, status: d.status || 'completed' } : null,
    data: w.data ? { ...w.data, status: d.status_info || w.data.status } : w.data }));
  if (getState().route.page === 'companies') loadWatchlist(getState().watch.scope || 'mine');
  if (d.status === 'busy' || d.status === 'already_checking') return;
  if (d.new_fits > 0) {
    toast(`${d.new_fits} new role${d.new_fits === 1 ? '' : 's'} at watchlist companies fit you — see the "New" tab. Apply early.`, 'success', 12000);
  } else if (d.status === 'completed') {
    activity(`Watchlist checked (${d.companies || 0} companies): no new roles that fit right now`, 'info', 'watch');
  }
  loadList();
}

// ---------------------------------------------------------------------------
// Companies you watch yourself — the Company Scout agent finds each careers site and its filters once
// ---------------------------------------------------------------------------
function upsertMonitor(m) {
  if (!m) return;
  setSlice('monitors', (s) => {
    const items = s.items.some((x) => x.id === m.id) ? s.items.map((x) => (x.id === m.id ? m : x)) : [m, ...s.items];
    return { ...s, items };
  });
}
function monitorBusy(id, on) {
  setSlice('monitors', (s) => ({ ...s, busy: { ...s.busy, [id]: on } }));
}
export async function loadMonitors() {
  setSlice('monitors', (s) => ({ ...s, status: s.items.length ? 'refreshing' : 'loading', error: null }));
  try {
    const res = await api.monitors();
    setSlice('monitors', { status: 'ready', items: res.monitors || [] });
  } catch (err) {
    setSlice('monitors', { status: 'error', error: errorText(err) });
  }
}
export async function addMonitor(company, location, keyword) {
  try {
    const res = await api.addMonitor({ company, location, keyword });
    upsertMonitor(res.monitor);
    toast(res.monitor.status === 'ready' ? `${company} is ready — it was scouted before`
      : `The Company Scout is finding ${company}'s careers site. This takes about a minute.`, 'info', 6000);
    return true;
  } catch (err) {
    toast(errorText(err), 'danger');
    return false;
  }
}
export async function checkMonitor(id) {
  monitorBusy(id, true);
  try {
    upsertMonitor((await api.checkMonitor(id)).monitor);
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    monitorBusy(id, false);
  }
}
export async function rescoutMonitor(id) {
  try {
    upsertMonitor((await api.rescoutMonitor(id)).monitor);
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}
export async function removeMonitor(id) {
  try {
    await api.deleteMonitor(id);
    setSlice('monitors', (s) => ({ ...s, items: s.items.filter((x) => x.id !== id) }));
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}
function onMonitorUpdated(m) {
  const before = getState().monitors.items.find((x) => x.id === m.id);
  upsertMonitor(m);
  if (before && before.status !== m.status && m.status === 'ready' && before.status === 'scouting') {
    toast(`${m.company}: ${m.message}`, 'success', 8000);
  } else if (before && before.status !== m.status && m.status === 'failed') {
    toast(`${m.company}: ${m.error || 'scouting failed'}`, 'danger', 9000);
  }
}

// ---------------------------------------------------------------------------
// Settings, models, usage, pipeline mode, reset
// ---------------------------------------------------------------------------
async function loadInto(slice, call) {
  setSlice(slice, (v) => ({ ...v, status: v.data ? 'refreshing' : 'loading', error: null }));
  try {
    setSlice(slice, { status: 'ready', data: await call() });
  } catch (err) {
    setSlice(slice, { status: 'error', error: errorText(err) });
  }
}
export const loadSettings = () => loadInto('settings', () => api.getSettings());
export const loadModels = () => loadInto('models', () => api.getModels());
export const refreshModels = () => loadInto('models', () => api.getModels(true));
export const loadDbHealth = () => loadInto('db', () => api.dbHealth());
export async function repairDb() {
  setSlice('db', { status: 'refreshing' });
  try {
    const data = await api.dbRepair();
    setSlice('db', { status: 'ready', data });
    toast(data.status === 'ok' ? 'Database is healthy.' : 'Checks finished — see the details.', data.status === 'ok' ? 'success' : 'warning');
  } catch (err) { setSlice('db', { status: 'error', error: errorText(err) }); }
}
export async function backupDb() {
  try {
    const { path } = await api.dbBackup();
    toast(`Backup saved: ${path.split(/[\\/]/).pop()}`, 'success', 7000);
  } catch (err) { toast(errorText(err), 'danger'); }
}
export async function setProviders(body) {
  try {
    const data = await api.setProviders(body);
    setSlice('settings', { status: 'ready', data });
    if (body.llm) loadModels();
  } catch (err) { toast(errorText(err), 'danger'); }
}
export const loadUsage = () => loadInto('usage', () => api.usage());
export async function saveSettings(body) {
  try {
    const data = await api.postSettings(body);
    setSlice('settings', { status: 'ready', data });
    toast('Settings saved.', 'success');
    // a new key triggers a server-side model check; pick up the result shortly after
    if (Object.keys(body).some((k) => k.endsWith('_api_key'))) setTimeout(loadModels, 3000);
    return true;
  } catch (err) {
    toast(errorText(err), 'danger');
    return false;
  }
}
export async function setModel(chain, modelId) {
  try {
    const { config } = await api.setModel(chain, modelId);
    setSlice('models', { status: 'ready', data: config });
    toast('Model preference updated.', 'success');
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}
export async function loadPipelineMode() {
  try {
    const { mode } = await api.getPipelineMode();
    setSlice('pipelineMode', { status: 'ready', mode });
  } catch (err) {
    setSlice('pipelineMode', { status: 'error', error: errorText(err) });
  }
}
export async function setPipelineMode(mode) {
  try {
    const res = await api.setPipelineMode(mode);
    setSlice('pipelineMode', { status: 'ready', mode: res.mode });
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}
export async function resetEverything() {
  if (!(await confirmAction({ title: 'Reset everything?', body: 'This deletes your profile, all jobs, documents and caches. This cannot be undone.', confirm: 'Reset everything', tone: 'danger', typeToConfirm: 'RESET' }))) return;
  try {
    await api.reset();
    writeOnb(null);
    window.location.hash = '#/discover';
    window.location.reload();
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}

// ---------------------------------------------------------------------------
// Browser agent & interventions
// ---------------------------------------------------------------------------
export async function loadInterventions() {
  setSlice('interventions', (v) => ({ ...v, status: v.items.length ? 'refreshing' : 'loading', error: null }));
  try {
    const { interventions } = await api.interventions();
    setSlice('interventions', { status: 'ready', items: interventions });
  } catch (err) {
    setSlice('interventions', { status: 'error', error: errorText(err) });
  }
}
// An intervention stays listed until the application is really finished: submitted (by the agent or
// marked done by you) or dismissed. Taking over or continuing keeps it here.
export async function continueIntervention(item) {
  try {
    const { session } = await api.applyAction(item.job_id, 'continue');
    if (session) setSlice('browser', { status: 'ready', session });
    navigate('#/browser');
  } catch (err) { toast(errorText(err), 'danger'); }
  loadInterventions();
}
export async function markInterventionApplied(item) {
  try {
    const { session } = await api.applyAction(item.job_id, 'done');
    if (session) setSlice('browser', { status: 'ready', session });
    toast('Marked as applied 🎉', 'success');
  } catch (err) { toast(errorText(err), 'danger'); }
  loadInterventions();
}
export async function skipIntervention(item) {
  try {
    await api.resolveIntervention(item.id, 'skipped');
    toast('Dismissed — it no longer waits for you.', 'info');
  } catch (err) { toast(errorText(err), 'danger'); }
  loadInterventions();
}
export async function focusIntervention(item) {
  try {
    const { session } = await api.applyAction(item.job_id, 'take-over');
    if (session) setSlice('browser', { status: 'ready', session });
  } catch { /* the browser may be closed; the Auto-apply tab still shows the saved run */ }
  navigate('#/browser');
}
export async function loadApplySession() {
  setSlice('browser', (b) => ({ ...b, status: b.session ? 'refreshing' : 'loading', error: null }));
  try {
    const { session } = await api.applyCurrent();
    setSlice('browser', { status: 'ready', session: session || null });
  } catch (err) {
    setSlice('browser', { status: 'error', error: errorText(err) });
  }
}
const APPLY_DONE_TEXT = { stop: null, 'take-over': 'You have control — click and type right in the view.', release: 'Handed back to the agent.',
  continue: 'Continuing from where it stopped…', close: 'Browser closed.', done: 'Marked as applied 🎉' };
export async function applyControl(action) {
  const s = getState().browser.session;
  if (!s || getState().browser.busy) return;
  setSlice('browser', { busy: action });
  try {
    const { session } = await api.applyAction(s.job_id, action);
    if (session) setSlice('browser', { session });
    if (APPLY_DONE_TEXT[action]) toast(APPLY_DONE_TEXT[action], action === 'done' ? 'success' : 'info');
    if (action === 'continue' || action === 'done') loadInterventions();
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    setSlice('browser', { busy: '' });
  }
}
function onApplySession(session) {
  if (!session) return;
  const s = getState();
  if (session.person_id && s.people.active && session.person_id !== s.people.active) return;
  const prev = s.browser.session;
  setSlice('browser', { status: 'ready', session });
  const changed = !prev || prev.job_id !== session.job_id || prev.status !== session.status;
  if (!changed) return;
  loadInterventions();                         // keep the Interventions list in step with every status change
  if (session.status === 'applied') toast(`Applied to ${session.company || 'the job'} 🎉`, 'success', 7000);
  if (session.status === 'needs_you') toast(session.notice || 'The agent needs your help.', 'warning', 8000);
  if (session.status === 'failed') toast(session.notice || 'The agent could not finish.', 'danger', 8000);
}
function handleBrowserEvent(ev) {
  // Step-by-step progress now arrives as `apply.session`; only the "needs you" nudge is still a browser event.
  if (ev && ev.event_type === 'hitl_request') loadInterventions();
}

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------
let socket = null;
function onMessage(msg) {
  const s = getState();
  switch (msg.type) {
    case 'search.run': {
      const run = msg.data && msg.data.run;
      if (!run) return;
      if (run.mode === 'watch') { onWatchRun(run); return; }
      if (s.search.activeRunId && run.id !== s.search.activeRunId) return;   // stale run
      if (!s.search.activeRunId && s.search.starting) return;                 // response will carry it
      const wasActive = s.search.run && ['queued', 'running'].includes(s.search.run.status);
      setSlice('search', { activeRunId: run.id, run });
      mergeFeed(run.id, run.activity);
      if (wasActive && ['completed', 'failed', 'cancelled'].includes(run.status)) {
        activity(`Search ${run.status}: ${run.counts.recommended} recommended, ${run.counts.rejected} not a fit`, run.status === 'failed' ? 'error' : 'info', 'search');
        loadList();
      }
      return;
    }
    case 'search.job': {
      const job = msg.data && msg.data.job;
      if (job && isWatchEvent(msg)) {                                        // new watchlist role: show it live
        upsertJobs([job]);
        reconcileListMembership(getState().jobs.byId[job.id]);
        refreshCountsSoon();
        return;
      }
      if (!job || msg.run_id !== s.search.activeRunId) return;               // stale run
      upsertJobs([job]);
      setSlice('search', (sr) => ({ ...sr, streamedIds: sr.streamedIds.includes(job.id) ? sr.streamedIds : [...sr.streamedIds, job.id] }));
      refreshCountsSoon();
      reconcileListMembership(getState().jobs.byId[job.id]);
      return;
    }
    case 'search.progress': {
      const d = msg.data || {};
      if (isWatchEvent(msg)) {
        setSlice('watch', (w) => ({ ...w, run: { ...w.run, progress: d.progress, counts: d.counts || w.run.counts } }));
        return;
      }
      if (!msg.run_id || msg.run_id !== s.search.activeRunId || !s.search.run) return;   // stale run
      setSlice('search', (sr) => ({ ...sr, run: { ...sr.run, progress: d.progress, counts: d.counts || sr.run.counts } }));
      return;
    }
    case 'search.activity': {
      const item = msg.data && msg.data.item;
      if (item && isWatchEvent(msg)) {
        setSlice('watch', (w) => ({ ...w, feed: [...(w.feed || []), item].slice(-WATCH_FEED_KEEP) }));
        return;
      }
      if (!item || !msg.run_id || msg.run_id !== s.search.activeRunId) return;   // stale run
      mergeFeed(msg.run_id, [item]);
      return;
    }
    case 'job.updated': {
      const job = msg.data && msg.data.job;
      if (!job) return;
      upsertJobs([job]);
      reconcileListMembership(getState().jobs.byId[job.id]);
      return;
    }
    case 'job.deleted': {
      const ids = (msg.data && msg.data.ids) || [];
      if (ids.length) removeJobs(ids); else loadList();
      return;
    }
    case 'document.status': {
      const d = msg.data || {};
      if (d.status === 'ready' || d.status === 'failed') loadDocuments();
      return;
    }
    case 'profile.updated':
      if (msg.data && getState().app.phase !== 'pick') setSlice('profile', { status: 'ready', envelope: msg.data });
      return;
    case 'profile.upload':
      onUploadEvent(msg.data && msg.data.upload, null);
      return;
    case 'people.changed': {
      const active = msg.data && msg.data.active;
      loadPeople().catch(() => {});
      // another tab switched profile: follow it so this tab never shows a mix of two people
      if (active && active !== s.people.active && s.app.phase === 'ready') choosePerson(active);
      return;
    }
    case 'log':
      activity(msg.message || '', (msg.data && msg.data.level) || 'info', (msg.data && msg.data.source) || 'server');
      return;
    case 'browser':
      handleBrowserEvent(msg.data);
      return;
    case 'apply.session':
      onApplySession(msg.data && msg.data.session);
      return;
    case 'watch.status':
      setSlice('watch', { checking: !!(msg.data && msg.data.checking) });
      return;
    case 'watch.done':
      onWatchDone(msg.data || {});
      return;
    case 'monitor.updated':
      if (msg.data && msg.data.monitor) onMonitorUpdated(msg.data.monitor);
      return;
    default:
  }
}
export function connectSocket() {
  socket = new ReconnectingSocket('/ws', {
    onMessage,
    onStatus: (conn) => setState((s) => ({ ...s, conn })),
    onOpen: (isReconnect) => {
      if (isReconnect) { loadCurrentRun(); loadList(); if (getState().route.page === 'browser') loadApplySession(); }
    },
  });
  socket.connect();
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// People (switchable profiles) and session start
// ---------------------------------------------------------------------------
const PICK_KEY = 'jhx-picked';   // per browser session: which profile the user chose
function readPicked() { try { return sessionStorage.getItem(PICK_KEY); } catch { return null; } }
function writePicked(id) { try { if (id) sessionStorage.setItem(PICK_KEY, id); else sessionStorage.removeItem(PICK_KEY); } catch { /* ignore */ } }

export async function loadPeople() {
  setSlice('people', (p) => ({ ...p, status: p.items.length ? 'refreshing' : 'loading', error: null }));
  try {
    const { people, active } = await api.people();
    setSlice('people', { status: 'ready', items: people, active });
    return { people, active };
  } catch (err) {
    setSlice('people', { status: 'error', error: errorText(err) });
    throw err;
  }
}

/** Forget everything that belongs to the previous person (jobs, runs, documents…). */
function resetPersonState() {
  const fresh = initialState();
  listSeq++; docsSeq++; trackerSeq++;
  listCtrl?.abort();
  setState((s) => ({
    ...s,
    profile: fresh.profile, search: fresh.search, jobs: fresh.jobs, details: fresh.details, list: fresh.list,
    pending: fresh.pending, gen: fresh.gen, docs: fresh.docs, docDetails: fresh.docDetails, tracker: fresh.tracker,
  }));
}

async function loadSessionData() {
  await Promise.all([loadProfile(), loadCurrentRun()]);
  decidePhase();
  const run = getState().search.run;
  if (run && ['queued', 'running'].includes(run.status)) setSlice('list', { scope: 'run', runId: run.id });
  loadList();
  loadDocuments();
  if (getState().route.page === 'tracker') loadTracker();
}

// ---------------------------------------------------------------------------
// First-run setup: without an AI key nothing works, so it is asked for before anything else
// ---------------------------------------------------------------------------
async function loadSetup() {
  const data = await api.setup();
  setSlice('setup', { data, error: null });
  return data;
}
export async function testSetupKey(provider, key) {
  setSlice('setup', (s) => ({ ...s, tests: { ...s.tests, [provider]: { busy: true } } }));
  try {
    const res = await api.testKey(provider, key);
    setSlice('setup', (s) => ({ ...s, tests: { ...s.tests, [provider]: { busy: false, ok: res.ok, message: res.message } } }));
  } catch (err) {
    setSlice('setup', (s) => ({ ...s, tests: { ...s.tests, [provider]: { busy: false, ok: false, message: errorText(err) } } }));
  }
}
export async function saveSetupKeys(keys) {
  setSlice('setup', { saving: true, error: null });
  try {
    if (Object.keys(keys).length) await api.postSettings(keys);
    const data = await loadSetup();
    setSlice('setup', { saving: false });
    if (!data.llm_ready) { setSlice('setup', { error: 'No working AI key yet — paste at least one AI key.' }); return; }
    toast('Keys saved. Next: your resume.', 'success');
    setSlice('app', { phase: 'booting' });
    await startSession();
  } catch (err) {
    setSlice('setup', { saving: false, error: errorText(err) });
  }
}

export async function startFree(keys = {}) {
  setSlice('setup', { saving: true, error: null });
  try {
    if (Object.keys(keys).length) await api.postSettings(keys);
    await api.setupFree();
    await loadSetup();
    setSlice('setup', { saving: false });
    toast('Using free Kilo models. Next: your resume.', 'success');
    setSlice('app', { phase: 'booting' });
    await startSession();
  } catch (err) {
    setSlice('setup', { saving: false, error: errorText(err) });
  }
}

async function startSession() {
  try {
    const setup = await loadSetup();
    if (!setup.llm_ready) { setSlice('app', { phase: 'setup', error: null }); return; }
  } catch (err) {
    setSlice('app', { phase: 'error', error: errorText(err) });
    return;
  }
  let people;
  try {
    ({ people } = await loadPeople());
  } catch (err) {
    setSlice('app', { phase: 'error', error: errorText(err) });
    return;
  }
  if (!people.length) {                     // first run ever: straight to setup
    setSlice('profile', { status: 'ready', envelope: { profile: null, snapshot: null, profile_hash: null } });
    decidePhase();
    return;
  }
  const active = getState().people.active;
  if (!readPicked() || readPicked() !== active) {   // returning user: ask which profile to open
    setSlice('app', { phase: 'pick', error: null });
    return;
  }
  await loadSessionData();
}

export async function choosePerson(id) {
  if (getState().people.switching) return;
  setSlice('people', { switching: id });
  try {
    if (getState().people.active !== id) await api.activatePerson(id);
    writePicked(id);
    setSlice('people', { active: id });
    resetPersonState();
    setSlice('app', { phase: 'booting' });   // set synchronously: a deferred transition could land after 'ready'
    await loadSessionData();
    loadPeople();
  } catch (err) {
    toast(errorText(err), 'danger');
  } finally {
    setSlice('people', { switching: null });
  }
}

/** Back to "Who's searching?" — e.g. from onboarding, to switch, add or delete a profile. */
export async function openPicker() {
  try { await loadPeople(); } catch { /* the picker shows what it has */ }
  withTransition(() => setSlice('app', { phase: 'pick', error: null }));
}

export async function createPerson(name = '') {
  try {
    const { active, people } = await api.createPerson(name || 'New profile');
    writePicked(active);
    writeOnb('upload');
    setSlice('people', { items: people, active });
    resetPersonState();
    setSlice('profile', { status: 'ready', envelope: { profile: null, snapshot: null, profile_hash: null } });
    withTransition(() => { setSlice('onboarding', { step: 'upload', dir: 1 }); setSlice('app', { phase: 'onboarding' }); });
  } catch (err) {
    toast(errorText(err), 'danger');
  }
}

export async function renamePerson(id, name) {
  try {
    const { people } = await api.renamePerson(id, name);
    setSlice('people', { items: people });
  } catch (err) { toast(errorText(err), 'danger'); }
}

export async function deletePerson(id) {
  const person = getState().people.items.find((p) => p.id === id);
  if (!(await confirmAction({ title: `Delete “${person ? person.name : 'this profile'}”?`,
    body: 'Its resume, jobs, tracker and documents are deleted. Other profiles are not affected.', confirm: 'Delete profile', tone: 'danger', typeToConfirm: 'DELETE' }))) return;
  const wasActive = getState().people.active === id;
  try {
    const { people, active } = await api.deletePerson(id);
    setSlice('people', { items: people, active });
    toast('Profile deleted.', 'success');
    if (wasActive) {
      writePicked(null);
      resetPersonState();
      await startSession();
    }
  } catch (err) { toast(errorText(err), 'danger'); }
}

export async function boot() {
  connectSocket();
  initRouting();
  api.meta().then((m) => setSlice('meta', { status: 'ready', data: m })).catch(() => {});
  await startSession();
}
