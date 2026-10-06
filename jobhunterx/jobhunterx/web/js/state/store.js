// Single source of truth for server state + UI state.
// Immutable updates only; components subscribe with useStore(selector).
import { useState, useEffect, useRef } from '../lib/preact.js';

export function parseHash(hash = window.location.hash) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map((p) => {
    try { return decodeURIComponent(p); } catch { return p; }
  });
  const page = parts[0] || 'discover';
  const route = { page, jobId: null, docId: null };
  if ((page === 'discover' || page === 'tracker') && parts[1] === 'job' && parts[2]) route.jobId = parts[2];
  if (page === 'documents' && parts[1]) route.docId = parts[1];
  return route;
}

function readTheme() {
  try {
    const t = localStorage.getItem('jhx-theme');
    if (t === 'light' || t === 'dark') return t;
  } catch { /* storage unavailable */ }
  return 'light';   // light-first design; dark is opt-in
}

function readMotion() {
  try {
    const m = localStorage.getItem('jhx-motion');
    if (m === 'full' || m === 'reduced' || m === 'system') return m;
  } catch { /* storage unavailable */ }
  return 'full';   // animations on by default; "Follow system" is available in Settings → Appearance
}

export function initialState() {
  return {
    route: parseHash(),
    theme: readTheme(),
    // App lifecycle: booting -> (pick | onboarding | ready); 'error' when the backend cannot be reached.
    app: { phase: 'booting', error: null },
    motion: readMotion(),
    // Switchable profiles (people). `switching` holds the id being opened.
    people: { status: 'idle', items: [], active: null, error: null, switching: null },
    // One-time setup flow. `dir` drives the slide direction of step transitions.
    onboarding: { step: 'upload', dir: 1 },
    conn: 'connecting',
    meta: { status: 'idle', data: null, error: null },
    profile: {
      status: 'idle', envelope: null, error: null,
      saving: false, saveError: null, saveDetails: [],
      upload: { status: 'idle', stage: 'idle', id: null, error: null, extraction: null, fileName: '', startedAt: 0 },
    },
    search: {
      activeRunId: null, run: null, starting: false, startError: null, lastRequest: null,
      cancelling: false, cancelError: null, streamedIds: [],
      feed: { runId: null, items: [] },   // plain-language live activity of the active run
    },
    jobs: { byId: {} },
    watch: { status: 'idle', data: null, error: null, checking: false, run: null, feed: [] },   // run = live background check
    setup: { data: null, error: null, saving: false, tests: {} },   // API keys; checked before anything else
    details: {},            // jobId -> { status, job, error }
    list: {
      scope: 'all', runId: null, view: 'recommended', q: '', work_mode: '', min_score: 0, sort: 'chance',
      ids: [], counts: null, status: 'idle', error: null, hasMore: false, more: false,
    },
    pending: { save: {}, track: {}, verify: {}, rescore: {}, connect: {}, apply: {}, remove: {} },
    gen: {},                // `${jobId|'cv'}:${kind}` -> { status, error, documentId }
    docs: { status: 'idle', items: [], error: null },
    docDetails: {},         // docId -> { status, doc, error }
    tracker: { status: 'idle', ids: [], error: null },
    activity: [],
    toasts: [],
    confirm: null,
    browser: { status: 'idle', session: null, busy: '', error: null },   // session = the auto-apply run (kit, steps, control)
    interventions: { status: 'idle', items: [], error: null },
    settings: { status: 'idle', data: null, error: null },
    models: { status: 'idle', data: null, error: null },
    db: { status: 'idle', data: null, error: null },
    usage: { status: 'idle', data: null, error: null },
    pipelineMode: { status: 'idle', mode: null, error: null },
  };
}

function createStore(initial) {
  let state = initial;
  const subs = new Set();
  return {
    get: () => state,
    set(updater) {
      const next = typeof updater === 'function' ? updater(state) : { ...state, ...updater };
      if (next === state) return;
      state = next;
      subs.forEach((fn) => fn());
    },
    subscribe(fn) { subs.add(fn); return () => subs.delete(fn); },
    reset(next) { state = next; subs.forEach((fn) => fn()); },
  };
}

export const store = createStore(initialState());
export const getState = store.get;
export const setState = store.set;

/** Shallow-merge `partial` (or updater result) into top-level slice `key`. */
export function setSlice(key, partial) {
  setState((s) => ({
    ...s,
    [key]: typeof partial === 'function' ? partial(s[key], s) : { ...s[key], ...partial },
  }));
}

/** Set/replace one entry of a keyed map slice (e.g. details, gen). undefined removes. */
export function setEntry(key, id, value) {
  setState((s) => {
    const map = { ...s[key] };
    const prev = map[id];
    const next = typeof value === 'function' ? value(prev) : value;
    if (next === undefined) delete map[id];
    else map[id] = next;
    return { ...s, [key]: map };
  });
}

export function setPending(kind, id, on) {
  setState((s) => {
    const m = { ...s.pending[kind] };
    if (on) m[id] = true; else delete m[id];
    return { ...s, pending: { ...s.pending, [kind]: m } };
  });
}

/** Subscribe a component to a selected value (compared with Object.is). */
export function useStore(selector) {
  const [, force] = useState(0);
  const selRef = useRef(selector);
  selRef.current = selector;
  const valRef = useRef();
  valRef.current = selector(store.get());
  useEffect(() => {
    const check = () => {
      const next = selRef.current(store.get());
      if (!Object.is(next, valRef.current)) {
        valRef.current = next;
        force((x) => x + 1);
      }
    };
    const unsub = store.subscribe(check);
    check();
    return unsub;
  }, []);
  return valRef.current;
}
