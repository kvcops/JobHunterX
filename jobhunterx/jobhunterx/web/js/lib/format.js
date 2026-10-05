// Pure formatting / domain helpers. No DOM, no state.

export const STAGE_KEYS = ['understand', 'plan', 'discover', 'normalize', 'dedupe', 'validate', 'extract', 'match', 'rank', 'connect'];
export const STAGE_LABELS = {
  understand: 'Understand profile', plan: 'Plan search', discover: 'Discover', normalize: 'Normalize',
  dedupe: 'De-duplicate', validate: 'Validate', extract: 'Extract requirements', match: 'Match', rank: 'Rank',
};

export const VERDICTS = ['strong', 'good', 'stretch', 'weak', 'incompatible'];
export const VERDICT_LABEL = {
  strong: 'Strong match', good: 'Good match', stretch: 'Stretch', weak: 'Weak match', incompatible: 'Incompatible',
};

export const VALIDATION_LABEL = {
  active: 'Verified active', likely_active: 'Likely active', unverified: 'Unverified',
  stale: 'Possibly stale', closed: 'Closed', invalid: 'Invalid',
};
export const VALIDATION_TONE = {
  active: 'success', likely_active: 'info', unverified: 'neutral', stale: 'warning', closed: 'danger', invalid: 'danger',
};

export const CHECK_LABEL = {
  url_reachable: 'Posting URL reachable', ats_confirmed: 'Confirmed on company ATS', company: 'Company',
  title: 'Title', location: 'Location', work_mode: 'Work mode', posted_at: 'Posted date',
  valid_through: 'Valid through', employment_type: 'Employment type', salary: 'Salary',
  experience: 'Experience requirement', application_open: 'Accepting applications',
};
export const CHECK_STATUS_LABEL = {
  verified: 'Verified', inferred: 'Inferred', unverified: 'Unverified', unknown: 'Unknown', failed: 'Failed',
};
export const CHECK_STATUS_TONE = {
  verified: 'success', inferred: 'info', unverified: 'neutral', unknown: 'unknown', failed: 'danger',
};

// Reach: chance a person actually reads the application (separate from fit).
export const REACH_LABEL = { high: 'Good chance to be seen', medium: 'Some chance to be seen', low: 'Crowded — low chance' };
export const REACH_SHORT = { high: 'Seen: high', medium: 'Seen: medium', low: 'Seen: low' };
export const REACH_TONE = { high: 'success', medium: 'info', low: 'danger' };
export const COMPANY_VERDICT_LABEL = { strong: 'Strong company to watch', good: 'Good company', caution: 'Caution', avoid: 'Avoid' };
export const COMPANY_VERDICT_TONE = { strong: 'success', good: 'info', caution: 'warning', avoid: 'danger' };
export const COMPETITION_LABEL = { low: 'Low competition', medium: 'Medium competition', high: 'High competition', very_high: 'Very high competition' };
export const EARLY_CAREER_LABEL = { yes: 'Hires 1–3 yr engineers', some: 'Sometimes hires 1–3 yr', rare: 'Rarely hires under 3 yrs', unknown: 'Early-career hiring unknown' };
export const CONSTRAINT_TONE = { pass: 'success', warn: 'warning', fail: 'danger', unknown: 'unknown' };
export const CONSTRAINT_LABEL = { pass: 'Pass', warn: 'Warning', fail: 'Fail', unknown: 'Unknown' };

export const DEFAULT_TRACKING = ['new', 'saved', 'preparing', 'applied', 'interviewing', 'offer', 'rejected', 'archived'];
export const TRACKING_LABEL = {
  new: 'New', saved: 'Saved', preparing: 'Preparing', applied: 'Applied', interviewing: 'Interviewing',
  offer: 'Offer', rejected: 'Rejected', archived: 'Archived',
};

export const WORK_MODES = ['remote', 'hybrid', 'onsite'];
export const WORK_MODE_LABEL = { remote: 'Remote', hybrid: 'Hybrid', onsite: 'On-site', unknown: 'Work mode unknown' };

export const SENIORITIES = ['intern', 'entry', 'junior', 'mid', 'senior', 'staff', 'principal', 'unknown'];
export const DOC_KIND_LABEL = { resume: 'Resume', cv: 'CV', cover_letter: 'Cover letter' };

export const YEARS_SOURCE_LABEL = {
  dates: 'computed from your experience dates', override: 'your override', stated: 'stated in your resume', unknown: 'unknown',
};

export function humanize(key) {
  if (key === null || key === undefined) return '';
  const s = String(key).replace(/[_-]+/g, ' ').trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

export function labelFor(list, key) {
  const hit = Array.isArray(list) ? list.find((x) => x && x.key === key) : null;
  return hit ? hit.label : humanize(key);
}

export function fmtNum(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: digits });
}

export function fmtCompact(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '0';
  const v = Number(n);
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(Math.round(v * 100) / 100);
}

export function fmtYears(y) {
  if (y === null || y === undefined || Number.isNaN(Number(y))) return 'unknown';
  const v = Math.round(Number(y) * 10) / 10;
  return `${v} ${v === 1 ? 'year' : 'years'}`;
}

export function fmtRange(min, max, unit = 'yrs') {
  const hasMin = min !== null && min !== undefined;
  const hasMax = max !== null && max !== undefined;
  if (hasMin && hasMax) return min === max ? `${min} ${unit}` : `${min}–${max} ${unit}`;
  if (hasMin) return `${min}+ ${unit}`;
  if (hasMax) return `up to ${max} ${unit}`;
  return 'not stated';
}

export function parseDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDate(iso) {
  const d = parseDate(iso);
  return d ? d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '—';
}

export function fmtDateTime(iso) {
  const d = parseDate(iso);
  return d ? d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
}

export function fmtTime(iso) {
  const d = parseDate(iso);
  return d ? d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
}

export function relTime(iso, now = Date.now()) {
  const d = parseDate(iso);
  if (!d) return '';
  const sec = Math.round((now - d.getTime()) / 1000);
  const abs = Math.abs(sec);
  const fut = sec < 0;
  let out;
  if (abs < 45) out = 'just now';
  else if (abs < 3600) out = `${Math.round(abs / 60)}m`;
  else if (abs < 86400) out = `${Math.round(abs / 3600)}h`;
  else if (abs < 86400 * 30) out = `${Math.round(abs / 86400)}d`;
  else if (abs < 86400 * 365) out = `${Math.round(abs / (86400 * 30))}mo`;
  else out = `${Math.round(abs / (86400 * 365))}y`;
  if (out === 'just now') return out;
  return fut ? `in ${out}` : `${out} ago`;
}

export function fmtDuration(startIso, endIso) {
  const a = parseDate(startIso);
  if (!a) return '';
  const b = parseDate(endIso) || new Date();
  const s = Math.max(0, Math.round((b - a) / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return m < 60 ? `${m}m ${s % 60}s` : `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function fmtMoney(n, currency) {
  if (n === null || n === undefined) return '';
  try {
    return new Intl.NumberFormat(undefined, {
      style: currency ? 'currency' : 'decimal', currency: currency || undefined, maximumFractionDigits: 0, notation: n >= 1e6 ? 'compact' : 'standard',
    }).format(n);
  } catch {
    return `${currency ? `${currency} ` : ''}${fmtNum(n)}`;
  }
}

export function fmtSalary(s) {
  if (!s) return '';
  if (s.min === null && s.max === null) return s.raw || '';
  const lo = s.min !== null && s.min !== undefined ? fmtMoney(s.min, s.currency) : '';
  const hi = s.max !== null && s.max !== undefined ? fmtMoney(s.max, s.currency) : '';
  const range = lo && hi ? `${lo} – ${hi}` : lo || hi;
  return s.period ? `${range} / ${s.period}` : range;
}

/** Only allow http(s)/mailto links from server data; everything else is dropped. */
export function safeUrl(u) {
  if (!u || typeof u !== 'string') return null;
  const t = u.trim();
  if (/^https?:\/\//i.test(t) || /^mailto:/i.test(t)) return t;
  return null;
}

export function hostOf(u) {
  try { return new URL(u).host.replace(/^www\./, ''); } catch { return ''; }
}

export function experienceText(exp) {
  if (!exp) return 'Experience: unknown';
  const req = fmtRange(exp.required_min, exp.required_max);
  const gap = exp.gap_years ? Math.round(exp.gap_years * 10) / 10 : 0;
  switch (exp.fit) {
    case 'within': return `Experience fits (${req})`;
    case 'under': return gap ? `Under by ${gap} yrs (${req})` : `Below range (${req})`;
    case 'over': return gap ? `Over by ${gap} yrs (${req})` : `Above range (${req})`;
    default: return 'Experience fit unknown';
  }
}

export const EXPERIENCE_TONE = { within: 'success', under: 'warning', over: 'info', unknown: 'unknown' };

export function scoreTone(score) {
  if (score === null || score === undefined) return 'unknown';
  if (score >= 80) return 'strong';
  if (score >= 65) return 'good';
  if (score >= 50) return 'stretch';
  if (score >= 30) return 'weak';
  return 'incompatible';
}

export function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)); }

export function plural(n, one, many = `${one}s`) { return `${n} ${n === 1 ? one : many}`; }
