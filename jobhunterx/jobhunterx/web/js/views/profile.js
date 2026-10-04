import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { uploadResume, saveProfile, loadProfile } from '../actions.js';
import {
  Button, Badge, Skeleton, ErrorBox, ChipsInput, Field, Icon, Notice, Meter, Tabs, PageHead, Stat, Seg, Select, AutoTextarea, ScanDoc, EmptyState, Elapsed, uploadStageLabel,
} from '../components/ui.js';
import { normalizeProfile, setIn, getIn } from '../state/domain.js';
import { ExperienceSummary } from '../components/experience.js';
import { WORK_MODES, WORK_MODE_LABEL, SENIORITIES, YEARS_SOURCE_LABEL, humanize } from '../lib/format.js';

function UploadButton() {
  const up = useStore((s) => s.profile.upload);
  const has = useStore((s) => !!(s.profile.envelope && s.profile.envelope.profile));
  const input = useRef();
  return html`<${Button} variant=${has ? 'secondary' : 'primary'} icon="upload" busy=${up.status === 'uploading'} onClick=${() => input.current.click()}>
      ${up.status === 'uploading' ? 'Reading…' : has ? 'Replace resume' : 'Upload resume'}</${Button}>
    <input ref=${input} type="file" accept="application/pdf,.pdf" class="sr-only" aria-label="Resume PDF"
      onChange=${(e) => { const f = e.currentTarget.files && e.currentTarget.files[0]; if (f) uploadResume(f); e.currentTarget.value = ''; }} />`;
}

function Reading() {
  const up = useStore((s) => s.profile.upload);
  if (up.status !== 'uploading') return null;
  return html`<div class="reading-overlay" aria-live="polite"><${ScanDoc} />
    <strong>Reading ${up.fileName}</strong>
    <p class="muted small">${uploadStageLabel(up.stage)}… · <${Elapsed} since=${up.startedAt} /></p></div>`;
}

function Understanding({ snap }) {
  if (!snap) return html`<div class="understanding"><h2>How JobHunterX understands you</h2><${Skeleton} lines=${6} /></div>`;
  return html`<div class="understanding" aria-label="How JobHunterX understands you">
    <div class="dna-head"><div><h2>How JobHunterX understands you</h2><p class="muted small">Derived from your profile. Every skill is checked against what you actually wrote.</p></div>
      <${Badge} tone=${snap.method === 'llm' ? 'success' : 'warning'}>${snap.method === 'llm' ? 'AI analysis' : 'Basic (AI unavailable)'}</${Badge}></div>
    <div class="stats">
      <${Stat} label="Level" value=${humanize(snap.seniority)} />
      <${Stat} label="Education" value=${humanize(snap.education_level)} />
      <${Stat} label="Locations" value=${snap.locations.map((p) => p.city || p.country).join(', ') || 'Not set'}
        hint=${`${snap.work_modes.map((m) => WORK_MODE_LABEL[m]).join(' · ')}${snap.willing_to_relocate ? ' · open to relocation' : ''}`} />
    </div>
    <h3 class="sec-title" style=${{ marginTop: '20px' }}>Experience · ${YEARS_SOURCE_LABEL[snap.years_source] || ''}</h3>
    <${ExperienceSummary} snap=${snap} />
    <h3 class="sec-title" style=${{ marginTop: '20px' }}>Career tracks</h3>
    <div class="tracks">${snap.role_families.map((f) => html`<div class="track" title=${f.evidence}>
      <div class="row space"><span>${f.label}</span><span class="track-pct">${Math.round(f.closeness * 100)}%</span></div><${Meter} value=${f.closeness} tone="ink" /></div>`)}</div>
    <h3 class="sec-title">Titles we search for</h3>
    <div class="chip-row">${[...snap.target_titles, ...snap.adjacent_titles].map((t, i) => html`<span class=${`chip ${i >= snap.target_titles.length ? 'soft' : ''}`}>${t}</span>`)}</div>
    <h3 class="sec-title">Skills with evidence</h3>
    <div class="skill-evidence">${snap.skills.slice(0, 40).map((s) => html`<span class=${`chip ${s.strength >= 0.95 ? 'chip-good' : s.strength >= 0.8 ? '' : 'soft'}`}
      title=${s.sources.join('\n')}>${s.name}</span>`)}</div>
    <p class="muted small">Solid: used at work · Normal: used in projects · Faded: listed only. Hover a skill to see where it was found.</p>
    ${snap.notes.length ? html`<ul class="bullets muted small">${snap.notes.map((n) => html`<li>${n}</li>`)}</ul>` : null}
  </div>`;
}

function TextField({ draft, path, label, set, type = 'text', hint, textarea, wide }) {
  const v = getIn(draft, path);
  return html`<${Field} label=${label} hint=${hint} wide=${wide}>${(id) => textarea
    ? html`<${AutoTextarea} id=${id} rows=${3} value=${v || ''} onInput=${(e) => set(path, e.currentTarget.value)} />`
    : html`<input id=${id} class="input" type=${type} value=${v === null || v === undefined ? '' : v}
        onInput=${(e) => set(path, type === 'number' ? (e.currentTarget.value === '' ? null : Number(e.currentTarget.value)) : e.currentTarget.value)} />`}</${Field}>`;
}

/** Label + address pairs ("Code" → github.com/…). Empty rows are dropped when saving. */
function LinksEditor({ value, onChange, labelHint = 'Code, Live demo…' }) {
  const rows = value || [];
  const put = (i, k, v) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return html`<div class="links-editor">
    ${rows.map((r, i) => html`<div class="link-row" key=${i}>
      <input class="input link-label" value=${r.label} placeholder=${labelHint} aria-label=${`Link ${i + 1} text`} onInput=${(e) => put(i, 'label', e.currentTarget.value)} />
      <input class="input" type="url" value=${r.url} placeholder="https://…" aria-label=${`Link ${i + 1} address`} onInput=${(e) => put(i, 'url', e.currentTarget.value)} />
      <button type="button" class="icon-btn" aria-label=${`Remove link ${i + 1}`} onClick=${() => onChange(rows.filter((_, j) => j !== i))}><${Icon} name="trash" size=${15} /></button>
    </div>`)}
    <button type="button" class="link-btn add-link" onClick=${() => onChange([...rows, { label: '', url: '' }])}><${Icon} name="plus" size=${14} /> Add link</button>
  </div>`;
}

const cleanLinks = (rows) => (rows || []).map((l) => ({ ...l, label: (l.label || '').trim(), url: (l.url || '').trim() })).filter((l) => l.url);

function ItemLinksEditor({ draft, set }) {
  const entries = [['certification', 'certifications'], ['achievement', 'achievements'], ['competition', 'competitions']]
    .flatMap(([sec, key]) => draft[key].map((x) => [`${sec}::${x}`, x, humanize(sec)]));
  const rows = draft.item_links;
  const put = (i, patch) => set(['item_links'], rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  if (!entries.length) return html`<p class="muted small">Add a certification or achievement above to give it a link (for example a credential page).</p>`;
  return html`<div class="links-editor">
    ${rows.map((r, i) => html`<div class="link-row three" key=${i}>
      <${Select} label=${`Entry for link ${i + 1}`} block value=${`${r.section}::${r.item}`} options=${entries}
        onChange=${(v) => { const [section, ...rest] = v.split('::'); put(i, { section, item: rest.join('::') }); }} />
      <input class="input link-label" value=${r.label} placeholder="Verify, Certificate…" aria-label=${`Link ${i + 1} text`} onInput=${(e) => put(i, { label: e.currentTarget.value })} />
      <input class="input" type="url" value=${r.url} placeholder="https://…" aria-label=${`Link ${i + 1} address`} onInput=${(e) => put(i, { url: e.currentTarget.value })} />
      <button type="button" class="icon-btn" aria-label=${`Remove link ${i + 1}`} onClick=${() => set(['item_links'], rows.filter((_, j) => j !== i))}><${Icon} name="trash" size=${15} /></button>
    </div>`)}
    <button type="button" class="link-btn add-link" onClick=${() => { const [section, ...rest] = entries[0][0].split('::'); set(['item_links'], [...rows, { section, item: rest.join('::'), label: '', url: '' }]); }}>
      <${Icon} name="plus" size=${14} /> Add link to an entry</button>
  </div>`;
}

function ListEditor({ draft, set, path, fields, empty, title }) {
  const items = getIn(draft, path) || [];
  return html`<div class="stack">
    ${items.map((it, i) => html`<div class="list-item card inset" key=${i}>
      <div class="row space"><strong>${it[fields[0].key] || `${title} ${i + 1}`}</strong>
        <button type="button" class="icon-btn" aria-label=${`Remove ${title.toLowerCase()} ${i + 1}`} onClick=${() => set(path, items.filter((_, j) => j !== i))}><${Icon} name="trash" size=${16} /></button></div>
      <div class="form-grid">
        ${fields.map((f) => f.kind === 'lines'
          ? html`<${Field} label=${f.label} hint="One per line" wide>${(id) => html`<${AutoTextarea} id=${id} rows=${3} value=${(it[f.key] || []).join('\n')}
              onInput=${(e) => set([...path, i, f.key], e.currentTarget.value.split('\n'))}
              onBlur=${(e) => set([...path, i, f.key], e.currentTarget.value.split('\n').map((x) => x.trim()).filter(Boolean))} />`}</${Field}>`
          : f.kind === 'chips'
            ? html`<${Field} label=${f.label} wide><${ChipsInput} label=${f.label} value=${it[f.key] || []} onChange=${(v) => set([...path, i, f.key], v)} /></${Field}>`
          : f.kind === 'links'
            ? html`<${Field} label=${f.label} hint=${f.hint} wide><${LinksEditor} value=${it[f.key] || []} onChange=${(v) => set([...path, i, f.key], v)} /></${Field}>`
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
    let clean = setIn(draft, ['experience'], draft.experience.map((e) => ({ ...e, bullets: e.bullets.map((b) => b.trim()).filter(Boolean) })));
    clean = setIn(clean, ['projects'], clean.projects.map((pr) => { const links = cleanLinks(pr.links); return { ...pr, links, url: links.length ? links[0].url : '' }; }));
    clean = setIn(clean, ['links'], cleanLinks(clean.links));
    clean = setIn(clean, ['item_links'], cleanLinks(clean.item_links).filter((l) => l.item));
    if (await saveProfile(clean)) setBase(JSON.stringify(normalizeProfile(clean)));
  };
  const tabs = [
    { key: 'about', label: 'About' }, { key: 'prefs', label: 'Preferences' }, { key: 'exp', label: 'Experience' },
    { key: 'proj', label: 'Projects' }, { key: 'edu', label: 'Education' }, { key: 'more', label: 'More' }, { key: 'qa', label: 'Application answers' },
  ];
  return html`<div class="editor" aria-label="Edit profile">
    <div class="editor-head">
      <div class="row space"><h2>Your profile</h2>
        <div class="row gap">${dirty ? html`<span class="dirty-pill">Unsaved</span>` : null}
          <${Button} size="sm" disabled=${!dirty || saving} onClick=${() => setDraft(JSON.parse(base))}>Discard</${Button}>
          <${Button} size="sm" variant="primary" busy=${saving} disabled=${!dirty} onClick=${save}>Save profile</${Button}></div></div>
      ${saveError ? html`<${ErrorBox} message=${[saveError, ...saveDetails].join(' · ')} onRetry=${save} />` : null}
      <${Tabs} label="Profile sections" tabs=${tabs} value=${tab} onChange=${setTab} size="sm" />
    </div>
    <div class="scroll editor-body" key=${tab}>
    ${tab === 'about' ? html`<div class="form-grid">
      ${[['name', 'Full name'], ['email', 'Email', 'email'], ['phone', 'Phone'], ['location', 'Current location'], ['suggested_role', 'Current / target title'],
        ['linkedin', 'LinkedIn URL', 'url'], ['github', 'GitHub URL', 'url'], ['portfolio', 'Portfolio URL', 'url']].map(([k, l, t]) => html`<${TextField} draft=${draft} path=${[k]} label=${l} set=${set} type=${t || 'text'} />`)}
      <${Field} label="Other links" hint="Blog, Kaggle, Scholar, personal site… shown in your resume header." wide><${LinksEditor} value=${draft.links} labelHint="Blog, Kaggle…" onChange=${(v) => set(['links'], v)} /></${Field}>
      <${TextField} draft=${draft} path=${['summary']} label="Summary" set=${set} textarea wide />
      <${Field} label="Skills" wide><${ChipsInput} label="Skills" value=${draft.skills} onChange=${(v) => set(['skills'], v)} placeholder="Add a skill…" /></${Field}>
    </div>` : null}
    ${tab === 'prefs' ? html`<div class="form-grid">
      <${Field} label="Target roles" hint="Titles you want. Used first in every search." wide><${ChipsInput} label="Target roles" value=${p.target_roles} onChange=${(v) => set(['preferences', 'target_roles'], v)} /></${Field}>
      <${Field} label="Acceptable locations" hint="Cities you can work in." wide><${ChipsInput} label="Locations" value=${p.locations} onChange=${(v) => set(['preferences', 'locations'], v)} /></${Field}>
      <div class="field field-wide"><span class="field-label">Work modes you accept</span>
        <${Seg} multi label="Work modes" options=${WORK_MODES.map((m) => [m, WORK_MODE_LABEL[m]])} value=${p.work_modes} onChange=${(v) => set(['preferences', 'work_modes'], v)} /></div>
      <${TextField} draft=${draft} path=${['preferences', 'home_country']} label="Home country" set=${set} />
      <div class="field"><span class="field-label">Flexibility</span>
        <label class="switch"><input type="checkbox" checked=${p.willing_to_relocate} onChange=${(e) => set(['preferences', 'willing_to_relocate'], e.currentTarget.checked)} /><span class="switch-ui"></span> Willing to relocate within my country</label>
        <label class="switch"><input type="checkbox" checked=${p.open_to_international} onChange=${(e) => set(['preferences', 'open_to_international'], e.currentTarget.checked)} /><span class="switch-ui"></span> Open to roles abroad</label></div>
      <${TextField} draft=${draft} path=${['preferences', 'min_annual_salary']} label="Minimum annual salary" type="number" set=${set} hint="Leave empty if flexible." />
      <${TextField} draft=${draft} path=${['preferences', 'salary_currency']} label="Salary currency" set=${set} />
      <${TextField} draft=${draft} path=${['preferences', 'notice_period_days']} label="Notice period (days)" type="number" set=${set} />
      <${Field} label="Employment types" hint="e.g. full_time, contract, internship"><${ChipsInput} label="Employment types" value=${p.employment_types} onChange=${(v) => set(['preferences', 'employment_types'], v)} /></${Field}>
      <${Field} label="Companies to exclude" wide><${ChipsInput} label="Excluded companies" value=${p.excluded_companies} onChange=${(v) => set(['preferences', 'excluded_companies'], v)} /></${Field}>
      <${TextField} draft=${draft} path=${['preferences', 'career_direction']} label="Career direction" set=${set} textarea wide hint="Where you want to grow — this shapes which tracks are searched." />
      <${TextField} draft=${draft} path=${['preferences', 'years_experience_override']} label="Years of experience (override)" type="number" set=${set} hint="Only if the computed value is wrong." />
      <${Field} label="Seniority (override)">${(id) => html`<${Select} id=${id} block label="Seniority override" value=${p.seniority_override || ''}
        onChange=${(v) => set(['preferences', 'seniority_override'], v || null)}
        options=${[['', 'Automatic', 'Computed from your experience'], ...SENIORITIES.filter((x) => x !== 'unknown').map((x) => [x, humanize(x)])]} />`}</${Field}>
    </div>` : null}
    ${tab === 'exp' ? html`<${ListEditor} draft=${draft} set=${set} path=${['experience']} title="Experience"
      empty=${{ role: '', company: '', location: '', start: '', end: '', employment_type: '', bullets: [] }}
      fields=${[{ key: 'role', label: 'Role' }, { key: 'company', label: 'Company' }, { key: 'location', label: 'Location' }, { key: 'employment_type', label: 'Type (full_time, internship…)' },
        { key: 'start', label: 'Start (e.g. Jan 2024)' }, { key: 'end', label: 'End (empty = present)' }, { key: 'bullets', label: 'What you did', kind: 'lines' }]} />` : null}
    ${tab === 'proj' ? html`<${ListEditor} draft=${draft} set=${set} path=${['projects']} title="Project"
      empty=${{ title: '', description: '', url: '', links: [], technologies: [] }}
      fields=${[{ key: 'title', label: 'Title' }, { key: 'description', label: 'Description', kind: 'text' }, { key: 'technologies', label: 'Technologies', kind: 'chips' },
        { key: 'links', label: 'Links', kind: 'links', hint: 'Code, live demo, paper, video… The first one is the main link.' }]} />` : null}
    ${tab === 'edu' ? html`<${ListEditor} draft=${draft} set=${set} path=${['education']} title="Education"
      empty=${{ degree: '', institution: '', university: '', start: '', end: '', grade: '', details: '' }}
      fields=${[{ key: 'degree', label: 'Degree' }, { key: 'institution', label: 'College / school' }, { key: 'university', label: 'Affiliated university' }, { key: 'start', label: 'Start' }, { key: 'end', label: 'End' }, { key: 'grade', label: 'Grade' }, { key: 'details', label: 'Details', kind: 'text' }]} />` : null}
    ${tab === 'more' ? html`<div class="form-grid">
      ${[['certifications', 'Certifications'], ['achievements', 'Achievements'], ['competitions', 'Competitions & hackathons'], ['languages', 'Spoken languages']].map(([k, l]) =>
        html`<${Field} label=${l} wide><${ChipsInput} label=${l} value=${draft[k]} onChange=${(v) => set([k], v)} /></${Field}>`)}
      <${Field} label="Links for certificates & achievements" hint="e.g. a credential page next to the certification." wide><${ItemLinksEditor} draft=${draft} set=${set} /></${Field}>
    </div>` : null}
    ${tab === 'qa' ? html`<div class="form-grid">
      <p class="muted small field-wide">Used only by the browser agent to answer application-form questions.</p>
      ${['current_ctc', 'expected_ctc', 'expected_salary', 'notice_period', 'work_authorization', 'requires_sponsorship', 'preferred_work_mode', 'willing_to_relocate', 'years_of_experience'].map((k) =>
        html`<${TextField} draft=${draft} path=${['qa_memory', k]} label=${humanize(k)} set=${set} />`)}
    </div>` : null}
    </div>
  </div>`;
}

export function ProfileView() {
  const pr = useStore((s) => s.profile);
  const env = pr.envelope;
  const up = pr.upload;
  return html`<div class="view view-profile">
    <${PageHead} title=${html`Your career, <span class="serif">understood</span>`}
      sub="Everything downstream — search, scoring, documents — uses only this profile." actions=${html`<${UploadButton} />`} />
    ${up.status === 'error' ? html`<${ErrorBox} message=${up.error} />` : null}
    ${up.extraction && up.extraction.warnings.length ? html`<${Notice} tone="warning">${up.extraction.warnings.join(' ')}</${Notice}>` : null}
    <div class="split split-profile">
      <section class="pane card">
        <${Reading} />
        <div class="scroll pane-pad">
          ${pr.status === 'loading' && !env ? html`<${Skeleton} lines=${8} />` : null}
          ${pr.status === 'error' && !env ? html`<${ErrorBox} message=${pr.error} onRetry=${loadProfile} />` : null}
          ${env && env.profile ? html`<${Understanding} snap=${env.snapshot} />` : null}
          ${env && !env.profile ? html`<${EmptyState} icon="upload" title="No resume yet">Upload a PDF, or fill in the profile on the right by hand.</${EmptyState}>` : null}
        </div>
      </section>
      <section class="pane card">
        ${env ? html`<${Editor} profile=${env.profile} />` : html`<div class="pane-pad"><${Skeleton} lines=${8} /></div>`}
      </section>
    </div>
  </div>`;
}
