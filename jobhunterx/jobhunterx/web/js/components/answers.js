// Pay and application-form answers, shared by onboarding and the profile page.
// Pay is always entered the same way — lakhs per year (LPA) — with the full rupee amount shown under the field,
// so nobody has to guess between "8", "8 LPA", "8 lakhs" and "800000". Fixed + variable = current CTC.
import { html, useEffect, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { Field, Seg } from './ui.js';
import { WorkAuthInput } from './places.js';
import { WORK_MODES, WORK_MODE_LABEL } from '../lib/format.js';

/** 8.5 -> "₹8,50,000" (Indian digit grouping). */
export function inr(lpa) {
  if (lpa == null || lpa === '' || Number.isNaN(Number(lpa))) return '';
  return `₹${Math.round(Number(lpa) * 100000).toLocaleString('en-IN')}`;
}

const num = (v) => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const round2 = (n) => Math.round(n * 100) / 100;

/**
 * An amount per year in lakhs, from however it is typed: "7.5" / "7.5 LPA" / "7.5L" -> 7.5, "50k" / "50,000" -> 0.5,
 * "2 lakh" -> 2, "1.2 Cr" -> 120, "40k per month" -> 4.8. A bare small number is lakhs; a large one is rupees.
 * Same rules as parse_lpa on the server.
 */
export function parseLpa(text) {
  const t = String(text ?? '').toLowerCase().replace(/,/g, '').trim();
  const m = t.match(/\d+(?:\.\d+)?|\.\d+/);
  if (!m) return null;
  let n = Number(m[0]);
  const rest = t.slice(m.index + m[0].length);
  if (/^\s*(cr|crore)/.test(rest)) n *= 100;
  else if (/^\s*(lpa|lakh|lac|l\b)/.test(rest)) { /* already lakhs */ }
  else if (/^\s*(k|thousand)\b/.test(rest)) n = (n * 1000) / 100000;
  else if (n >= 1000) n /= 100000;
  if (/(per month|\/\s*month|monthly|\bpm\b|p\.m\.)/.test(t)) n *= 12;
  return Number.isFinite(n) ? round2(n) : null;
}

/** Pay field: type it any common way (7.5, 7.5 LPA, 50k, 2L, 8,00,000); it is kept as lakhs per year. */
function LpaInput({ id, value, onChange, placeholder }) {
  const v = num(value);
  const [text, setText] = useState(v == null ? '' : String(v));
  // the saved value changed from outside (a reload, Discard): show it
  useEffect(() => { if (parseLpa(text) !== v) setText(v == null ? '' : String(v)); }, [v]);
  return html`<div class="unit-input">
    <input id=${id} class="input" type="text" inputmode="decimal" autocomplete="off" value=${text} placeholder=${placeholder}
      onInput=${(e) => { const t = e.currentTarget.value; setText(t); onChange(t.trim() ? parseLpa(t) : null); }}
      onBlur=${() => { const n = parseLpa(text); setText(n == null ? '' : String(n)); }} />
    <span class="unit" aria-hidden="true">LPA</span>
  </div>`;
}

const perYear = (lpa, empty) => (num(lpa) != null ? `= ${inr(lpa)} per year (${num(lpa)} LPA) · about ${inr(num(lpa) / 12)} a month` : empty);

/** Current fixed + variable pay, the total they make, expected CTC, the lowest pay to search for, notice period. */
export function PayFields({ draft, set }) {
  const q = draft.qa_memory;
  const p = draft.preferences;
  const fixed = num(q.current_fixed_lpa);
  const variable = num(q.current_variable_lpa);
  const total = fixed == null && variable == null ? null : round2((fixed || 0) + (variable || 0));
  const minLpa = p.min_annual_salary == null ? null : round2(p.min_annual_salary / 100000);
  return html`<div class="form-grid tight pay-grid">
    <p class="muted small field-wide pay-note">Pay is <strong>per year</strong>. Type it the way you say it — <code>7.5</code> or <code>7.5 LPA</code>,
      <code>50k</code>, <code>2L</code>, <code>8,00,000</code> — the exact amount it was read as shows under the field. Leave a field empty if it does not apply (e.g. a fresher has no current pay).</p>
    <${Field} label="Current fixed pay" hint=${perYear(fixed, 'Base salary in a year, before bonus')}>${(id) => html`<${LpaInput} id=${id}
      value=${fixed} placeholder="e.g. 7.5" onChange=${(v) => set(['qa_memory', 'current_fixed_lpa'], v)} />`}</${Field}>
    <${Field} label="Current variable pay" hint=${perYear(variable, 'Bonus / incentives in a year. 0 if none')}>${(id) => html`<${LpaInput} id=${id}
      value=${variable} placeholder="e.g. 50k or 1.5" onChange=${(v) => set(['qa_memory', 'current_variable_lpa'], v)} />`}</${Field}>
    <div class="field field-wide"><span class="field-label">Current CTC (fixed + variable)</span>
      <div class="pay-total">${total == null ? html`<span class="muted">Fill in the fields above</span>`
        : html`<strong>${total} LPA</strong><span class="muted">${inr(total)} per year</span>`}</div></div>
    <${Field} label="Expected CTC" hint=${perYear(q.expected_ctc_lpa, 'Total yearly pay you ask for')}>${(id) => html`<${LpaInput} id=${id}
      value=${q.expected_ctc_lpa} placeholder="e.g. 12.5" onChange=${(v) => set(['qa_memory', 'expected_ctc_lpa'], v)} />`}</${Field}>
    <${Field} label="Lowest pay to search for" hint=${minLpa != null ? `Roles that clearly pay under ${inr(minLpa)} a year are left out` : 'Optional. Leave empty if flexible'}>${(id) => html`<${LpaInput} id=${id}
      value=${minLpa} placeholder="e.g. 8" onChange=${(v) => { set(['preferences', 'min_annual_salary'], v == null ? null : Math.round(v * 100000)); set(['preferences', 'salary_currency'], 'INR'); }} />`}</${Field}>
    <${Field} label="Notice period" hint="Days. 0 if you can join right away.">${(id) => html`<div class="unit-input">
      <input id=${id} class="input" type="number" inputmode="numeric" min="0" max="365" step="1" value=${p.notice_period_days ?? ''} placeholder="e.g. 30"
        onInput=${(e) => { const v = num(e.currentTarget.value);
          set(['preferences', 'notice_period_days'], v); set(['qa_memory', 'notice_period'], v == null ? '' : v === 0 ? 'Immediate joiner' : `${v} days`); }} />
      <span class="unit" aria-hidden="true">days</span></div>`}</${Field}>
  </div>`;
}

const ANY = 'Any';
/** Work authorization, sponsorship, work mode, relocation and years — prefilled from the rest of the profile. */
export function AnswerFields({ draft, set }) {
  const snap = useStore((s) => s.profile.envelope && s.profile.envelope.snapshot);
  const q = draft.qa_memory;
  const p = draft.preferences;
  const country = p.home_country || 'India';
  const modeOpts = [...WORK_MODES.map((m) => [WORK_MODE_LABEL[m], WORK_MODE_LABEL[m]]), [ANY, 'Any']];
  const modeNow = q.preferred_work_mode || (p.work_modes.length === 1 ? WORK_MODE_LABEL[p.work_modes[0]] : p.work_modes.length ? ANY : '');
  const relocate = q.willing_to_relocate || (p.willing_to_relocate ? 'Yes' : 'No');
  const sponsorship = q.requires_sponsorship || (/^(citizen|permanent resident) of/i.test(q.work_authorization || '') ? 'No' : '');
  const years = q.years_of_experience !== '' && q.years_of_experience != null ? q.years_of_experience
    : snap ? String(Math.round(snap.professional_years * 10) / 10) : '';
  return html`<div class="form-grid tight">
    <${Field} label="Work authorization" hint="Pick from the list or type your own.">${(id) => html`<${WorkAuthInput} id=${id} value=${q.work_authorization}
      country=${country} onChange=${(v) => set(['qa_memory', 'work_authorization'], v)} />`}</${Field}>
    <div class="field"><span class="field-label">Need visa sponsorship?</span>
      <${Seg} label="Sponsorship" options=${[['No', 'No'], ['Yes', 'Yes']]} value=${sponsorship} onChange=${(v) => set(['qa_memory', 'requires_sponsorship'], v)} /></div>
    <div class="field"><span class="field-label">Preferred work mode</span>
      <${Seg} label="Preferred work mode" options=${modeOpts} value=${modeNow} onChange=${(v) => set(['qa_memory', 'preferred_work_mode'], v)} /></div>
    <div class="field"><span class="field-label">Willing to relocate?</span>
      <${Seg} label="Willing to relocate" options=${[['Yes', 'Yes'], ['No', 'No']]} value=${relocate}
        onChange=${(v) => { set(['qa_memory', 'willing_to_relocate'], v); set(['preferences', 'willing_to_relocate'], v === 'Yes'); }} /></div>
    <${Field} label="Years of experience" hint=${snap ? `Worked out from your resume: ${Math.round(snap.professional_years * 10) / 10} (internships not counted). Change it if needed.` : 'Full-time years, internships not counted.'}>${(id) => html`<div class="unit-input">
      <input id=${id} class="input" type="number" inputmode="decimal" min="0" max="50" step="any" value=${years} placeholder="e.g. 2"
        onInput=${(e) => set(['qa_memory', 'years_of_experience'], e.currentTarget.value)} />
      <span class="unit" aria-hidden="true">years</span></div>`}</${Field}>
  </div>`;
}
