// All side effects live here. Components call actions; actions update the store.
// Rules: every async flow has explicit status; late responses never overwrite newer
// ones (sequence numbers + AbortController); WS events are filtered by run id.
import { api, ApiError, isAbortError } from './lib/api.js';
import { ReconnectingSocket } from './lib/ws.js';
import {
  getState, setState, setSlice, setEntry, setPending, parseHash,
} from './state/store.js';
import { matchesList, sortIds, summaryFromDetail, SUMMARY_SAFE_FIELDS, genKey } from './state/domain.js';

const prefersReducedMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
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
  if (route.page === 'settings') { loadSettings(); loadModels(); loadUsage(); loadPipelineMode(); }
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
const ONB_STEPS = ['upload', 'review', 'prefs', 'launch'];
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
  await loadProfile();
  decidePhase();
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
export async function uploadResume(file) {
  if (!file) return;
  if (getState().profile.upload.status === 'uploading') return;
  setSlice('profile', (p) => ({ ...p, upload: { status: 'uploading', error: null, extraction: null, fileName: file.name } }));
  try {
    const res = await api.uploadProfile(file);
    const { extraction, ...env } = res;
    setSlice('profile', (p) => ({ ...p, status: 'ready', envelope: env, upload: { status: 'done', error: null, extraction, fileName: file.name } }));
    const partial = extraction && extraction.status === 'partial';
    if (getState().app.phase === 'onboarding') setOnboardingStep('review');
    toast(partial ? 'Resume read — please review the highlighted gaps.' : 'Resume read successfully.', partial ? 'warning' : 'success');
  } catch (err) {
    setSlice('profile', (p) => ({ ...p, upload: { status: 'error', error: errorText(err), extraction: null, fileName: file.name } }));
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
export async function loadList() {
  const seq = ++listSeq;
  listCtrl?.abort();
  listCtrl = new AbortController();
  const l = getState().list;
  setSlice('list', { status: 'loading', error: null });
  try {
    const res = await api.listJobs({
      view: l.view, q: l.q, work_mode: l.work_mode, min_score: l.min_score || '', sort: l.sort,
      run_id: l.scope === 'run' ? l.runId : '',
    }, { signal: listCtrl.signal });
    if (seq !== listSeq) return;
    upsertJobs(res.jobs);
    setSlice('list', { status: 'ready', ids: res.jobs.map((j) => j.id), counts: res.counts });
  } catch (err) {
    if (isAbortError(err) || seq !== listSeq) return;
    setSlice('list', { status: 'error', error: errorText(err) });
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
  if (!(await confirmAction({ title: 'Start the browser agent?', body: 'A browser will open the application form and fill it using your profile and this job\'s tailored resume. You can watch and take over at any time.', confirm: 'Start applying' }))) return;
  setPending('apply', jobId, true);
  try {
    await api.applyJob(jobId);
    toast('Browser agent started — watch it in "Browser agent".', 'success');
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
  setEntry('gen', key, { status: 'generating', error: null, documentId: null });
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
  setEntry('gen', key, { status: 'generating', error: null, documentId: null, focus });
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
export const loadUsage = () => loadInto('usage', () => api.usage());
export async function saveSettings(body) {
  try {
    const data = await api.postSettings(body);
    setSlice('settings', { status: 'ready', data });
    toast('Settings saved.', 'success');
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
export async function continueIntervention(item) {
  try {
    await api.resumeAgent(item.job_id, 'done');
    await api.resolveIntervention(item.id, 'resolved');
    toast('Agent resumed.', 'success');
  } catch (err) { toast(errorText(err), 'danger'); }
  loadInterventions();
}
export async function skipIntervention(item) {
  try {
    await api.resumeAgent(item.job_id, 'skip');
    await api.resolveIntervention(item.id, 'skipped');
  } catch (err) { toast(errorText(err), 'danger'); }
  loadInterventions();
}
export async function focusIntervention(item) {
  try { await api.focusIntervention(item.job_id); } catch (err) { toast(errorText(err), 'danger'); }
}
export async function stopBrowser() {
  try {
    await api.stopBrowser();
    setSlice('browser', { active: false, takeover: false });
    toast('Browser agent stopped.', 'info');
  } catch (err) { toast(errorText(err), 'danger'); }
}
export async function setTakeover(on) {
  const jobId = getState().browser.jobId;
  try {
    if (on) await api.takeover(jobId); else await api.release(jobId);
    setSlice('browser', { takeover: on });
  } catch (err) { toast(errorText(err), 'danger'); }
}
function handleBrowserEvent(ev) {
  if (!ev || typeof ev !== 'object') return;
  const type = ev.event_type;
  const data = ev.data || {};
  if (type === 'browser_step' || type === 'progress') {
    setSlice('browser', (b) => ({
      ...b, active: true, jobId: ev.job_id || b.jobId,
      url: data.url || b.url, title: data.title || b.title,
      lastMessage: ev.message || b.lastMessage,
      steps: ev.message ? [{ id: Date.now() + Math.random(), message: ev.message, ts: new Date().toISOString() }, ...b.steps].slice(0, 60) : b.steps,
    }));
  } else if (type === 'hitl_request') {
    toast('The browser agent needs your help (login/CAPTCHA). Open "Interventions".', 'warning', 8000);
    loadInterventions();
  } else if (type === 'complete' || type === 'error') {
    setSlice('browser', (b) => ({ ...b, active: false, lastMessage: ev.message || b.lastMessage }));
  }
  if (ev.job_id && type === 'job_status_changed' && data.status) upsertJobs([{ id: ev.job_id, pipeline_status: data.status }]);
  if (ev.message) activity(ev.message, type === 'error' ? 'error' : 'info', ev.agent || 'browser');
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
      if (!job || msg.run_id !== s.search.activeRunId) return;               // stale run
      upsertJobs([job]);
      setSlice('search', (sr) => ({ ...sr, streamedIds: sr.streamedIds.includes(job.id) ? sr.streamedIds : [...sr.streamedIds, job.id] }));
      reconcileListMembership(getState().jobs.byId[job.id]);
      return;
    }
    case 'search.activity': {
      const item = msg.data && msg.data.item;
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
      if (msg.data) setSlice('profile', { status: 'ready', envelope: msg.data });
      return;
    case 'log':
      activity(msg.message || '', (msg.data && msg.data.level) || 'info', (msg.data && msg.data.source) || 'server');
      return;
    case 'browser':
      handleBrowserEvent(msg.data);
      return;
    default:
  }
}
export function connectSocket() {
  socket = new ReconnectingSocket('/ws', {
    onMessage,
    onStatus: (conn) => setState((s) => ({ ...s, conn })),
    onOpen: (isReconnect) => {
      if (isReconnect) { loadCurrentRun(); loadList(); }
    },
  });
  socket.connect();
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
export async function boot() {
  connectSocket();
  initRouting();
  await Promise.all([loadProfile(), loadCurrentRun(), api.meta().then((m) => setSlice('meta', { status: 'ready', data: m })).catch(() => {})]);
  decidePhase();
  const run = getState().search.run;
  if (run && ['queued', 'running'].includes(run.status)) setSlice('list', { scope: 'run', runId: run.id });
  loadList();
  loadDocuments();
}
