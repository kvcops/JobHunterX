// API client for the JobHunterX v2 contract (docs/API.md).
// One request() function: JSON in/out, timeouts, AbortController support, and the
// `{ error: { code, message, details } }` error envelope surfaced as ApiError.

const DEFAULT_TIMEOUT_MS = 20_000;

const FRIENDLY = {
  bad_request: 'The request was not valid.',
  not_found: 'That item no longer exists.',
  conflict: 'That action is already in progress.',
  validation_error: 'Some fields are invalid.',
  payload_too_large: 'The file is too large.',
  upstream_error: 'An external service failed. Please try again shortly.',
  internal_error: 'Something went wrong on the server.',
};

const CODE_BY_STATUS = {
  400: 'bad_request', 404: 'not_found', 409: 'conflict', 413: 'payload_too_large',
  422: 'validation_error', 502: 'upstream_error', 500: 'internal_error',
};

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'unknown', details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function isAbortError(err) {
  return !!err && (err.name === 'AbortError' || err.code === 'aborted');
}

/** Human-readable lines from an error `details` payload (FastAPI-style list or object). */
export function describeDetails(details) {
  if (!details) return [];
  if (Array.isArray(details)) {
    return details.map((d) => {
      if (d && typeof d === 'object') {
        const loc = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : '';
        const msg = d.msg || d.message || JSON.stringify(d);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return String(d);
    });
  }
  if (typeof details === 'object') {
    return Object.entries(details).map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`);
  }
  return [String(details)];
}

export function buildQuery(params) {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {})) {
    if (v === undefined || v === null || v === '') continue;
    if (Array.isArray(v)) v.forEach((x) => usp.append(k, String(x)));
    else usp.append(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export async function request(path, {
  method = 'GET', body, form, query, signal, timeout = DEFAULT_TIMEOUT_MS,
} = {}) {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = timeout ? setTimeout(() => { timedOut = true; ctrl.abort(); }, timeout) : null;
  const forwardAbort = () => ctrl.abort();
  if (signal) {
    if (signal.aborted) ctrl.abort();
    else signal.addEventListener('abort', forwardAbort, { once: true });
  }

  const headers = { Accept: 'application/json' };
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let res;
  let text = '';
  try {
    res = await fetch(`/api${path}${buildQuery(query)}`, { method, headers, body: payload, signal: ctrl.signal });
    text = await res.text();
  } catch (err) {
    if (timedOut) {
      throw new ApiError('The server took too long to respond. Please try again.', { code: 'timeout' });
    }
    if (ctrl.signal.aborted) throw new DOMException('Request aborted', 'AbortError');
    throw new ApiError('Cannot reach the JobHunterX server. Check that it is running.', { code: 'network' });
  } finally {
    if (timer) clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', forwardAbort);
  }

  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }

  if (!res.ok) {
    const env = data && typeof data === 'object' ? data.error : null;
    const code = (env && env.code) || CODE_BY_STATUS[res.status] || 'http_error';
    const legacyDetail = data && typeof data.detail === 'string' ? data.detail : null;
    const message = (env && env.message) || legacyDetail || FRIENDLY[code] || `Request failed (HTTP ${res.status}).`;
    const details = env ? env.details ?? null : (data && Array.isArray(data.detail) ? data.detail : null);
    throw new ApiError(message, { status: res.status, code, details });
  }
  if (text && data === null) {
    throw new ApiError('The server sent an unreadable response.', { status: res.status, code: 'bad_response' });
  }
  return data;
}

const enc = encodeURIComponent;

export const api = {
  // meta / profile
  meta: (o) => request('/meta', o),
  getProfile: (o) => request('/profile', o),
  putProfile: (profile, o) => request('/profile', { method: 'PUT', body: profile, ...o }),
  uploadProfile: (file, o) => {
    const form = new FormData();
    form.append('file', file);
    // background=1: returns at once; progress arrives as `profile.upload` WebSocket events
    return request('/profile/upload', { method: 'POST', form, query: { background: 1 }, timeout: 60_000, ...o });
  },
  uploadStatus: (id, o) => request(`/profile/upload/${enc(id)}`, o),

  // people (switchable profiles)
  people: (o) => request('/people', o),
  createPerson: (name, o) => request('/people', { method: 'POST', body: { name }, ...o }),
  activatePerson: (id, o) => request(`/people/${enc(id)}/activate`, { method: 'POST', ...o }),
  renamePerson: (id, name, o) => request(`/people/${enc(id)}`, { method: 'PATCH', body: { name }, ...o }),
  deletePerson: (id, o) => request(`/people/${enc(id)}`, { method: 'DELETE', timeout: 60_000, ...o }),

  // searches
  startSearch: (req, o) => request('/searches', { method: 'POST', body: req, timeout: 30_000, ...o }),
  currentSearch: (o) => request('/searches/current', o),
  getSearch: (id, o) => request(`/searches/${enc(id)}`, o),
  cancelSearch: (id, o) => request(`/searches/${enc(id)}/cancel`, { method: 'POST', ...o }),

  // jobs
  listJobs: (query, o) => request('/jobs', { query, ...o }),
  getJob: (id, o) => request(`/jobs/${enc(id)}`, o),
  saveJob: (id, o) => request(`/jobs/${enc(id)}/saved`, { method: 'PUT', ...o }),
  unsaveJob: (id, o) => request(`/jobs/${enc(id)}/saved`, { method: 'DELETE', ...o }),
  patchJob: (id, body, o) => request(`/jobs/${enc(id)}`, { method: 'PATCH', body, ...o }),
  verifyJob: (id, o) => request(`/jobs/${enc(id)}/verify`, { method: 'POST', timeout: 45_000, ...o }),
  rescoreJob: (id, o) => request(`/jobs/${enc(id)}/rescore`, { method: 'POST', timeout: 60_000, ...o }),
  deleteJob: (id, o) => request(`/jobs/${enc(id)}`, { method: 'DELETE', ...o }),
  clearJobs: (scope, o) => request('/jobs', { method: 'DELETE', query: { scope }, ...o }),
  applyJob: (id, o) => request(`/jobs/${enc(id)}/apply`, { method: 'POST', ...o }),

  // first-run setup (API keys)
  setup: (o) => request('/setup', o),
  testKey: (provider, key, o) => request('/setup/test-key', { method: 'POST', body: { provider, key }, timeout: 30_000, ...o }),

  // watchlist (researched companies whose own job boards are checked directly)
  watchlist: (scope, o) => request('/watchlist', { query: { scope }, timeout: 45_000, ...o }),
  checkWatchlist: (o) => request('/watchlist/check', { method: 'POST', ...o }),

  // documents
  generateDocument: (jobId, kind, o) => request(`/jobs/${enc(jobId)}/documents`, { method: 'POST', body: { kind }, timeout: 120_000, ...o }),
  generateCv: (focus, o) => request('/documents/cv', { method: 'POST', body: focus ? { focus } : {}, timeout: 120_000, ...o }),
  listDocuments: (query, o) => request('/documents', { query, ...o }),
  getDocument: (id, o) => request(`/documents/${enc(id)}`, o),
  deleteDocument: (id, o) => request(`/documents/${enc(id)}`, { method: 'DELETE', ...o }),
  documentPdfUrl: (id) => `/api/documents/${enc(id)}/pdf`,

  // system
  status: (o) => request('/status', o),
  getSettings: (o) => request('/settings', o),
  postSettings: (body, o) => request('/settings', { method: 'POST', body, ...o }),
  getModels: (refresh, o) => request('/models', { query: refresh ? { refresh: 1 } : undefined, timeout: 45_000, ...o }),
  setProviders: (body, o) => request('/providers', { method: 'POST', body, ...o }),
  dbHealth: (o) => request('/system/health', o),
  dbRepair: (o) => request('/system/repair', { method: 'POST', timeout: 60_000, ...o }),
  dbBackup: (o) => request('/system/backup', { method: 'POST', timeout: 60_000, ...o }),
  setModel: (chain, modelId, o) => request('/models', { method: 'POST', body: { chain, model_id: modelId }, ...o }),
  usage: (o) => request('/usage', o),
  getPipelineMode: (o) => request('/pipeline-mode', o),
  setPipelineMode: (mode, o) => request('/pipeline-mode', { method: 'POST', query: { mode }, ...o }),
  reset: (o) => request('/reset', { method: 'POST', timeout: 30_000, ...o }),

  // browser agent / interventions
  interventions: (o) => request('/interventions', o),
  resolveIntervention: (id, status = 'resolved', o) => request(`/interventions/${enc(id)}/resolve`, { method: 'POST', query: { status }, ...o }),
  focusIntervention: (jobId, o) => request(`/interventions/${enc(jobId)}/focus`, { method: 'POST', ...o }),
  resumeAgent: (jobId, action, o) => request('/resume-agent', { method: 'POST', body: { job_id: jobId, action }, timeout: 60_000, ...o }),
  applyCurrent: (o) => request('/apply/current', o),
  // action: stop | take-over | release | continue | close | done
  applyAction: (jobId, action, o) => request(`/apply/${enc(jobId)}/${action}`, { method: 'POST', timeout: 30_000, ...o }),
  screenshotUrl: (jobId) => `/api/screenshots/${enc(jobId)}`,
};
