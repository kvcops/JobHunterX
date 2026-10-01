import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { uploadResume, saveProfile, loadProfile } from '../actions.js';
import {
  Button, Badge, Skeleton, ErrorBox, ChipsInput, Field, Icon, Notice, Meter, Tabs,
} from '../components/ui.js';
import { normalizeProfile, setIn, getIn } from '../state/domain.js';
import { WORK_MODES, WORK_MODE_LABEL, SENIORITIES, YEARS_SOURCE_LABEL, humanize } from '../lib/format.js';

function Upload() {
  const up = useStore((s) => s.profile.upload);
  const [drag, setDrag] = useState(false);
  const input = useRef();
  const pick = (files) => files && files[0] && uploadResume(files[0]);
  return html`<section class=${`card upload ${drag ? 'drag' : ''}`}
      onDragOver=${(e) => { e.preventDefault(); setDrag(true); }} onDragLeave=${() => setDrag(false)}
      onDrop=${(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files); }}>
    <div class="upload-icon"><${Icon} name="doc" size=${26} /></div>
    <div class="grow">
      <h2>Your resume</h2>
      <p class="muted">Upload a PDF. JobHunterX reads it into an editable profile — nothing is invented; check and correct it below.</p>
      ${up.status === 'uploading' ? html`<p class="small" aria-live="polite"><span class="spinner"></span> Reading ${up.fileName}… this can take up to a minute.</p>` : null}
      ${up.status === 'error' ? html`<div class="error-text small" role="alert">${up.error}</div>` : null}
      ${up.extraction && up.extraction.warnings.length ? html`<${Notice} tone="warning">${up.extraction.warnings.join(' ')}</${Notice}>` : null}
    </div>
    <input ref=${input} type="file" accept="application/pdf,.pdf" class="sr-only" onChange=${(e) => { pick(e.currentTarget.files); e.currentTarget.value = ''; }} />
    <${Button} variant="primary" icon="doc" busy=${up.status === 'uploading'} onClick=${() => input.current.click()}>Upload PDF</${Button}>
  </section>`;
}

function Understanding({ snap }) {
  if (!snap) return html`<section class="card"><h2>How JobHunterX understands you</h2><${Skeleton} lines=${4} /></section>`;
  return html`<section class="card understanding" aria-label="How JobHunterX understands you">
    <div class="row space"><h2>How JobHunterX understands you</h2>
      <${Badge} tone=${snap.method === 'llm' ? 'success' : 'warning'}>${snap.method === 'llm' ? 'AI analysis' : 'Basic (AI unavailable)'}</${Badge}></div>
    <div class="facts-grid">
      <div><span class="muted small">Experience</span><div class="big">${snap.professional_years} yrs</div><div class="muted small">${YEARS_SOURCE_LABEL[snap.years_source]}</div></div>
      <div><span class="muted small">Level</span><div class="big">${humanize(snap.seniority)}</div></div>
      <div><span class="muted small">Education</span><div class="big">${humanize(snap.education_level)}</div></div>
      <div><span class="muted small">Locations</span><div>${snap.locations.map((p) => p.city || p.country).join(', ') || 'Not set'}</div>
        <div class="muted small">${snap.work_modes.map((m) => WORK_MODE_LABEL[m]).join(' · ')}${snap.willing_to_relocate ? ' · open to relocation' : ''}</div></div>
    </div>
    <h3 class="sec-title">Career tracks</h3>
    <div class="tracks">${snap.role_families.map((f) => html`<div class="track" title=${f.evidence}>
      <span>${f.label}</span><${Meter} value=${f.closeness} tone="info" /></div>`)}</div>
    <h3 class="sec-title">Titles we search for</h3>
    <div class="chip-row">${[...snap.target_titles, ...snap.adjacent_titles].map((t, i) => html`<span class=${`chip ${i >= snap.target_titles.length ? 'soft' : ''}`}>${t}</span>`)}</div>
    <h3 class="sec-title">Skills with evidence</h3>
    <div class="skill-evidence">${snap.skills.slice(0, 40).map((s) => html`<span class=${`chip ${s.strength >= 0.95 ? 'chip-good' : s.strength >= 0.8 ? '' : 'soft'}`}
      title=${s.sources.join('\n')}>${s.name}</span>`)}</div>
    <p class="muted small">Solid: used at work · Normal: used in projects · Faded: listed only. Hover a skill to see where it was found.</p>
    ${snap.notes.length ? html`<ul class="bullets muted small">${snap.notes.map((n) => html`<li>${n}</li>`)}</ul>` : null}
  </section>`;
}

function TextField({ draft, path, label, set, type = 'text', hint, textarea, wide }) {
  const v = getIn(draft, path);
  return html`<${Field} label=${label} hint=${hint} wide=${wide}>${(id) => textarea
    ? html`<textarea id=${id} class="input" rows="4" value=${v || ''} onInput=${(e) => set(path, e.currentTarget.value)}></textarea>`
    : html`<input id=${id} class="input" type=${type} value=${v === null || v === undefined ? '' : v}
        onInput=${(e) => set(path, type === 'number' ? (e.currentTarget.value === '' ? null : Number(e.currentTarget.value)) : e.currentTarget.value)} />`}</${Field}>`;
}

function ListEditor({ draft, set, path, fields, empty, title }) {
  const items = getIn(draft, path) || [];
  return html`<div class="stack">
    ${items.map((it, i) => html`<div class="list-item card inset" key=${i}>
      <div class="row space"><strong>${it[fields[0].key] || `${title} ${i + 1}`}</strong>
        <button type="button" class="icon-btn" aria-label=${`Remove ${title.toLowerCase()} ${i + 1}`} onClick=${() => set(path, items.filter((_, j) => j !== i))}><${Icon} name="trash" size=${16} /></button></div>
      <div class="form-grid">
        ${fields.map((f) => f.kind === 'lines'
          ? html`<${Field} label=${f.label} hint="One per line" wide>${(id) => html`<textarea id=${id} class="input" rows="5" value=${(it[f.key] || []).join('\n')}
              onInput=${(e) => set([...path, i, f.key], e.currentTarget.value.split('\n'))}
              onBlur=${(e) => set([...path, i, f.key], e.currentTarget.value.split('\n').map((x) => x.trim()).filter(Boolean))}></textarea>`}</${Field}>`
          : f.kind === 'chips'
            ? html`<${Field} label=${f.label} wide><${ChipsInput} label=${f.label} value=${it[f.key] || []} onChange=${(v) => set([...path, i, f.key], v)} /></${Field}>`
            : html`<${TextField} draft=${draft} path=${[...path, i, f.key]} label=${f.label} set=${set} textarea=${f.kind === 'text'} wide=${f.kind === 'text'} />`)}
      </div></div>`)}
    <${Button} size="sm" icon="plus" onClick=${() => set(path, [...items, { ...empty }])}>Add ${title.toLowerCase()}</${Button}>
  </div>`;
}

function Editor({ profile }) {
  const saving = useStore((s) => s.profile.saving);
  const saveError = useStore((s) => s.profile.saveError);
  const saveDetails = useStore((s) => s.profile.saveDetails);
  const [draft, setDraft] = useState(() => normalizeProfile(profile));
  const [base, setBase] = useState(() => JSON.stringify(normalizeProfile(profile)));
  const [tab, setTab] = useState('about');
  const serverJson = JSON.stringify(normalizeProfile(profile));
  const dirty = JSON.stringify(draft) !== base;
  useEffect(() => { if (!dirty) { setDraft(normalizeProfile(profile)); setBase(serverJson); } }, [serverJson]);
  const set = (path, value) => setDraft((d) => setIn(d, path, value));
  const p = draft.preferences;
  const save = async () => {
    const clean = setIn(draft, ['experience'], draft.experience.map((e) => ({ ...e, bullets: e.bullets.map((b) => b.trim()).filter(Boolean) })));
    if (await saveProfile(clean)) setBase(JSON.stringify(normalizeProfile(clean)));
  };
  const tabs = [
    { key: 'about', label: 'About' }, { key: 'prefs', label: 'Preferences' }, { key: 'exp', label: 'Experience' },
    { key: 'proj', label: 'Projects' }, { key: 'edu', label: 'Education' }, { key: 'more', label: 'More' }, { key: 'qa', label: 'Application answers' },
  ];
  return html`<section class="card editor" aria-label="Edit profile">
    <div class="row space sticky-head"><h2>Your profile</h2>
      <div class="row gap">${dirty ? html`<span class="muted small">Unsaved changes</span>` : null}
        <${Button} disabled=${!dirty || saving} onClick=${() => setDraft(JSON.parse(base))}>Discard</${Button}>
        <${Button} variant="primary" busy=${saving} disabled=${!dirty} onClick=${save}>Save profile</${Button}></div></div>
    ${saveError ? html`<${ErrorBox} message=${[saveError, ...saveDetails].join(' · ')} onRetry=${save} />` : null}
    <${Tabs} label="Profile sections" tabs=${tabs} value=${tab} onChange=${setTab} />
    ${tab === 'about' ? html`<div class="form-grid">
      ${[['name', 'Full name'], ['email', 'Email', 'email'], ['phone', 'Phone'], ['location', 'Current location'], ['suggested_role', 'Current / target title'],
        ['linkedin', 'LinkedIn URL', 'url'], ['github', 'GitHub URL', 'url'], ['portfolio', 'Portfolio URL', 'url']].map(([k, l, t]) => html`<${TextField} draft=${draft} path=${[k]} label=${l} set=${set} type=${t || 'text'} />`)}
      <${TextField} draft=${draft} path=${['summary']} label="Summary" set=${set} textarea wide />
      <${Field} label="Skills" wide><${ChipsInput} label="Skills" value=${draft.skills} onChange=${(v) => set(['skills'], v)} placeholder="Add a skill…" /></${Field}>
    </div>` : null}
    ${tab === 'prefs' ? html`<div class="form-grid">
      <${Field} label="Target roles" hint="Titles you want. Used first in every search." wide><${ChipsInput} label="Target roles" value=${p.target_roles} onChange=${(v) => set(['preferences', 'target_roles'], v)} /></${Field}>
      <${Field} label="Acceptable locations" hint="Cities you can work in." wide><${ChipsInput} label="Locations" value=${p.locations} onChange=${(v) => set(['preferences', 'locations'], v)} /></${Field}>
      <div class="field field-wide"><span class="field-label">Work modes you accept</span><div class="seg" role="group" aria-label="Work modes">
        ${WORK_MODES.map((m) => html`<button type="button" class=${`seg-btn ${p.work_modes.includes(m) ? 'on' : ''}`} aria-pressed=${p.work_modes.includes(m) ? 'true' : 'false'}
          onClick=${() => set(['preferences', 'work_modes'], p.work_modes.includes(m) ? p.work_modes.filter((x) => x !== m) : [...p.work_modes, m])}>${WORK_MODE_LABEL[m]}</button>`)}</div></div>
      <${TextField} draft=${draft} path=${['preferences', 'home_country']} label="Home country" set=${set} />
      <div class="field"><span class="field-label">Flexibility</span>
        <label class="check"><input type="checkbox" checked=${p.willing_to_relocate} onChange=${(e) => set(['preferences', 'willing_to_relocate'], e.currentTarget.checked)} /> Willing to relocate within my country</label>
        <label class="check"><input type="checkbox" checked=${p.open_to_international} onChange=${(e) => set(['preferences', 'open_to_international'], e.currentTarget.checked)} /> Open to roles abroad</label></div>
      <${TextField} draft=${draft} path=${['preferences', 'min_annual_salary']} label="Minimum annual salary" type="number" set=${set} hint="Leave empty if flexible." />
      <${TextField} draft=${draft} path=${['preferences', 'salary_currency']} label="Salary currency" set=${set} />
      <${TextField} draft=${draft} path=${['preferences', 'notice_period_days']} label="Notice period (days)" type="number" set=${set} />
      <${Field} label="Employment types" hint="e.g. full_time, contract, internship"><${ChipsInput} label="Employment types" value=${p.employment_types} onChange=${(v) => set(['preferences', 'employment_types'], v)} /></${Field}>
      <${Field} label="Companies to exclude" wide><${ChipsInput} label="Excluded companies" value=${p.excluded_companies} onChange=${(v) => set(['preferences', 'excluded_companies'], v)} /></${Field}>
      <${TextField} draft=${draft} path=${['preferences', 'career_direction']} label="Career direction" set=${set} textarea wide hint="Where you want to grow — this shapes which tracks are searched." />
      <${TextField} draft=${draft} path=${['preferences', 'years_experience_override']} label="Years of experience (override)" type="number" set=${set} hint="Only if the computed value is wrong." />
      <${Field} label="Seniority (override)">${(id) => html`<select id=${id} class="input" value=${p.seniority_override || ''} onChange=${(e) => set(['preferences', 'seniority_override'], e.currentTarget.value || null)}>
        <option value="">Automatic</option>${SENIORITIES.filter((x) => x !== 'unknown').map((x) => html`<option value=${x}>${humanize(x)}</option>`)}</select>`}</${Field}>
    </div>` : null}
    ${tab === 'exp' ? html`<${ListEditor} draft=${draft} set=${set} path=${['experience']} title="Experience"
      empty=${{ role: '', company: '', location: '', start: '', end: '', employment_type: '', bullets: [] }}
      fields=${[{ key: 'role', label: 'Role' }, { key: 'company', label: 'Company' }, { key: 'location', label: 'Location' }, { key: 'employment_type', label: 'Type (full_time, internship…)' },
        { key: 'start', label: 'Start (e.g. Jan 2024)' }, { key: 'end', label: 'End (empty = present)' }, { key: 'bullets', label: 'What you did', kind: 'lines' }]} />` : null}
    ${tab === 'proj' ? html`<${ListEditor} draft=${draft} set=${set} path=${['projects']} title="Project"
      empty=${{ title: '', description: '', url: '', technologies: [] }}
      fields=${[{ key: 'title', label: 'Title' }, { key: 'url', label: 'Link' }, { key: 'description', label: 'Description', kind: 'text' }, { key: 'technologies', label: 'Technologies', kind: 'chips' }]} />` : null}
    ${tab === 'edu' ? html`<${ListEditor} draft=${draft} set=${set} path=${['education']} title="Education"
      empty=${{ degree: '', institution: '', start: '', end: '', grade: '', details: '' }}
      fields=${[{ key: 'degree', label: 'Degree' }, { key: 'institution', label: 'Institution' }, { key: 'start', label: 'Start' }, { key: 'end', label: 'End' }, { key: 'grade', label: 'Grade' }, { key: 'details', label: 'Details', kind: 'text' }]} />` : null}
    ${tab === 'more' ? html`<div class="form-grid">
      ${[['certifications', 'Certifications'], ['achievements', 'Achievements'], ['competitions', 'Competitions & hackathons'], ['languages', 'Spoken languages']].map(([k, l]) =>
        html`<${Field} label=${l} wide><${ChipsInput} label=${l} value=${draft[k]} onChange=${(v) => set([k], v)} /></${Field}>`)}
    </div>` : null}
    ${tab === 'qa' ? html`<div class="form-grid">
      <p class="muted small field-wide">Used only by the browser agent to answer application-form questions.</p>
      ${['current_ctc', 'expected_ctc', 'expected_salary', 'notice_period', 'work_authorization', 'requires_sponsorship', 'preferred_work_mode', 'willing_to_relocate', 'years_of_experience'].map((k) =>
        html`<${TextField} draft=${draft} path=${['qa_memory', k]} label=${humanize(k)} set=${set} />`)}
    </div>` : null}
  </section>`;
}

export function ProfileView() {
  const pr = useStore((s) => s.profile);
  const env = pr.envelope;
  return html`<div class="page">
    <${Upload} />
    ${pr.status === 'loading' && !env ? html`<section class="card"><${Skeleton} lines=${6} /></section>` : null}
    ${pr.status === 'error' && !env ? html`<${ErrorBox} message=${pr.error} onRetry=${loadProfile} />` : null}
    ${env && env.profile ? html`<${Understanding} snap=${env.snapshot} /><${Editor} profile=${env.profile} />` : null}
    ${env && !env.profile ? html`<${Editor} profile=${null} />` : null}
  </div>`;
}
