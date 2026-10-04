// Derived data: view predicates, sorting, shape conversions. Pure functions only.

export const RECOMMENDED_VERDICTS = new Set(['strong', 'good', 'stretch']);
export const APPLIED_STATUSES = new Set(['applied', 'interviewing', 'offer']);
const DEAD_VALIDATION = new Set(['closed', 'invalid']);

/** Mirror of the server's `view` semantics (API.md) for streamed jobs. */
export function inView(job, view) {
  const verdict = job.match ? job.match.verdict : null;
  const vstatus = job.validation ? job.validation.status : null;
  switch (view) {
    case 'all': return true;
    case 'recommended': return RECOMMENDED_VERDICTS.has(verdict) && !DEAD_VALIDATION.has(vstatus);
    case 'rejected': return verdict === 'incompatible' || DEAD_VALIDATION.has(vstatus);
    case 'saved': return !!job.saved;
    case 'applied': return APPLIED_STATUSES.has(job.tracking_status);
    case 'fresh': {
      const seen = Date.parse(job.discovered_at || '');
      return RECOMMENDED_VERDICTS.has(verdict) && !DEAD_VALIDATION.has(vstatus) && !Number.isNaN(seen) && Date.now() - seen < 48 * 3600e3;
    }
    default: return true;
  }
}

export function matchesList(job, list) {
  if (!job || !inView(job, list.view)) return false;
  if (list.work_mode && job.work_mode !== list.work_mode) return false;
  if (list.min_score && (!job.match || job.match.score < list.min_score)) return false;
  const q = (list.q || '').trim().toLowerCase();
  if (q) {
    const hay = `${job.title} ${job.company} ${job.location} ${(job.locations || []).join(' ')}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
}

function ts(job) {
  const d = Date.parse(job.posted_at || job.discovered_at || '');
  return Number.isNaN(d) ? 0 : d;
}

const fit = (j) => (j.match ? j.match.score : -1);
const reach = (j) => (j.reach ? j.reach.score : 50);

export function compareJobs(sort) {
  if (sort === 'recent') return (a, b) => ts(b) - ts(a);
  if (sort === 'reach') return (a, b) => reach(b) - reach(a) || fit(b) - fit(a);
  // "chance": fit says you should apply, reach says someone will read it — mirrors the server's blend
  if (sort === 'chance') return (a, b) => (Math.max(fit(b), 0) * 0.6 + reach(b) * 0.4) - (Math.max(fit(a), 0) * 0.6 + reach(a) * 0.4) || ts(b) - ts(a);
  return (a, b) => {
    const sa = a.match ? a.match.score : -1;
    const sb = b.match ? b.match.score : -1;
    return sb - sa || ts(b) - ts(a);
  };
}

export function sortIds(ids, byId, sort) {
  const cmp = compareJobs(sort);
  return ids.filter((id) => byId[id]).sort((a, b) => cmp(byId[a], byId[b]));
}

/** Build a JobSummary-shaped match/validation from a JobDetail (detail shapes differ). */
export function summaryFromDetail(d) {
  if (!d) return null;
  const m = d.match;
  const match = m ? {
    score: m.score, verdict: m.verdict, headline: m.headline,
    required_matched: (m.matched_required || []).length,
    required_total: (m.matched_required || []).length + (m.missing_required || []).length,
    missing_required: (m.missing_required || []).slice(0, 5),
    experience: m.experience, rejected_reasons: m.rejected_reasons || [],
  } : null;
  const r = m && m.reach;
  const reachSummary = r ? {
    score: r.score, level: r.level, headline: r.headline, application_email: r.application_email, company_verdict: r.company_verdict,
  } : null;
  const v = d.validation || {};
  const { description, requirements, sources, document_list: _dl, ...rest } = d;
  return {
    ...rest,
    match,
    reach: reachSummary,
    validation: { status: v.status, confidence: v.confidence, checked_at: v.checked_at },
  };
}

// Fields of a JobSummary that are safe to copy into a cached JobDetail
// (match / validation have different shapes and must not be merged).
export const SUMMARY_SAFE_FIELDS = ['saved', 'tracking_status', 'pipeline_status', 'match_stale', 'documents', 'run_id', 'title', 'company', 'location'];

export function genKey(jobId, kind) { return `${jobId || 'cv'}:${kind}`; }

export function emptyProfile() {
  return {
    name: '', email: '', phone: '', location: '', present_address: '', permanent_address: '',
    linkedin: '', github: '', portfolio: '', summary: '', suggested_role: '', relevant_experience: '',
    languages: [], skills: [], certifications: [], competitions: [], achievements: [],
    experience: [], education: [], projects: [],
    qa_memory: {
      expected_salary: '', current_ctc: '', expected_ctc: '', notice_period: '', work_authorization: '',
      requires_sponsorship: '', preferred_work_mode: '', willing_to_relocate: '', years_of_experience: '',
      custom_answers: {},
    },
    preferences: emptyPreferences(),
  };
}

export function emptyPreferences() {
  return {
    target_roles: [], locations: [], work_modes: [], willing_to_relocate: false, open_to_international: false,
    home_country: '', min_annual_salary: null, salary_currency: 'INR', notice_period_days: null,
    employment_types: [], excluded_companies: [], career_direction: '',
    years_experience_override: null, seniority_override: null,
  };
}

/** Fill any missing keys so editors never deal with undefined. */
export function normalizeProfile(p) {
  const base = emptyProfile();
  if (!p) return base;
  const out = { ...base, ...p };
  for (const k of ['languages', 'skills', 'certifications', 'competitions', 'achievements', 'experience', 'education', 'projects']) {
    if (!Array.isArray(out[k])) out[k] = [];
  }
  out.qa_memory = { ...base.qa_memory, ...(p.qa_memory || {}) };
  if (!out.qa_memory.custom_answers || typeof out.qa_memory.custom_answers !== 'object') out.qa_memory.custom_answers = {};
  out.preferences = { ...base.preferences, ...(p.preferences || {}) };
  for (const k of ['target_roles', 'locations', 'work_modes', 'employment_types', 'excluded_companies']) {
    if (!Array.isArray(out.preferences[k])) out.preferences[k] = [];
  }
  out.experience = out.experience.map((e) => ({ role: '', company: '', location: '', start: '', end: '', employment_type: '', bullets: [], ...e, bullets: Array.isArray(e.bullets) ? e.bullets : [] }));
  out.education = out.education.map((e) => ({ degree: '', institution: '', university: '', start: '', end: '', grade: '', details: '', ...e }));
  const links = (v) => (Array.isArray(v) ? v.filter((l) => l && typeof l === 'object').map((l) => ({ label: l.label || '', url: l.url || '' })) : []);
  out.links = links(p.links);
  out.item_links = Array.isArray(p.item_links) ? p.item_links.filter((l) => l && typeof l === 'object').map((l) => ({ section: '', item: '', label: '', url: '', ...l })) : [];
  out.projects = out.projects.map((e) => {
    const pl = links(e.links);
    // older profiles have a single `url`; show it as the first link
    if (e.url && !pl.some((l) => l.url.replace(/\/$/, '') === e.url.replace(/\/$/, ''))) pl.unshift({ label: '', url: e.url });
    return { title: '', description: '', url: '', ...e, links: pl, technologies: Array.isArray(e.technologies) ? e.technologies : [] };
  });
  return out;
}

export function setIn(obj, path, value) {
  if (!path.length) return value;
  const [k, ...rest] = path;
  const copy = Array.isArray(obj) ? obj.slice() : { ...(obj || {}) };
  copy[k] = setIn(copy[k], rest, value);
  return copy;
}

export function getIn(obj, path) {
  return path.reduce((o, k) => (o === null || o === undefined ? undefined : o[k]), obj);
}

/** Default search request derived from the candidate snapshot (what the profile already says). */
export function defaultSearchRequest(snap) {
  return {
    locations: snap ? snap.locations.map((p) => p.city || p.country).filter(Boolean) : [],
    work_modes: snap ? [...snap.work_modes] : [],
    role_focus: [],
    include_international: snap ? !!snap.open_to_international : false,
  };
}
