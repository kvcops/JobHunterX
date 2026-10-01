// Experience breakdown: total (with internships) vs professional vs internships, plus every role.
import { html } from '../lib/preact.js';
import { CountUp, Badge } from './ui.js';

export function fmtMonths(m) {
  if (m == null) return 'dates unclear';
  const y = Math.floor(m / 12);
  const r = m % 12;
  return [y ? `${y} yr${y > 1 ? 's' : ''}` : '', r ? `${r} mo` : ''].filter(Boolean).join(' ') || '< 1 mo';
}

const KIND = {
  professional: ['Professional', 'success'], internship: ['Internship', 'info'],
  excluded: ['Not counted', 'neutral'], undated: ['No dates', 'warning'],
};

export function ExperienceSummary({ snap, compact }) {
  if (!snap) return null;
  const rows = snap.experience_breakdown || [];
  const override = snap.years_source === 'override';
  return html`<div class=${`xp ${compact ? 'compact' : ''}`}>
    <div class="xp-tiles">
      <div class="xp-tile"><span class="n"><${CountUp} value=${snap.total_years || snap.professional_years} /><small>yrs</small></span>
        <span class="l">Total</span><span class="h">incl. internships</span></div>
      <div class="xp-tile hl"><span class="n"><${CountUp} value=${snap.professional_years} /><small>yrs</small></span>
        <span class="l">Professional</span><span class="h">${override ? 'set by you' : 'used for matching'}</span></div>
      <div class="xp-tile"><span class="n"><${CountUp} value=${snap.internship_years || 0} /><small>yrs</small></span>
        <span class="l">Internships</span><span class="h">counted separately</span></div>
    </div>
    ${!compact && rows.length ? html`<ul class="xp-rows">${rows.map((r, i) => html`<li key=${i} style=${{ '--i': i }}>
      <span class=${`xp-dot k-${r.kind}`}></span>
      <div class="grow"><strong>${r.role || 'Role'}</strong><span class="muted small">${r.company || ''}${r.company ? ' · ' : ''}${r.start || '?'} – ${r.end || 'Present'}</span></div>
      <span class="xp-len">${fmtMonths(r.months)}</span>
      <${Badge} tone=${(KIND[r.kind] || KIND.professional)[1]}>${(KIND[r.kind] || KIND.professional)[0]}</${Badge}>
    </li>`)}</ul>` : null}
    ${!compact ? html`<p class="muted small xp-note">Overlapping jobs are counted once. Matching uses professional years; internships still count as evidence for skills.
      Wrong? Set an override in Profile → Preferences.</p>` : null}
  </div>`;
}
