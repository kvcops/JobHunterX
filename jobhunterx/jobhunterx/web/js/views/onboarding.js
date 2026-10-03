// One-time setup: resume → about you → goals → pay & availability → first search.
// Shown only until the user finishes (or when a profile has no data yet). The step survives reloads.
import { html, useState, useRef, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { uploadResume, saveProfile, setOnboardingStep, finishOnboarding } from '../actions.js';
import {
  Button, Icon, ChipsInput, Field, Notice, Meter, Seg, Skeleton, ScanDoc, Orb, ErrorBox, AutoTextarea, Spinner, Elapsed, UPLOAD_STAGES,
} from '../components/ui.js';
import { ExperienceSummary } from '../components/experience.js';
import { normalizeProfile, setIn, defaultSearchRequest } from '../state/domain.js';
import { WORK_MODES, WORK_MODE_LABEL, humanize, safeUrl } from '../lib/format.js';

const STEPS = [
  { key: 'upload', label: 'Your resume', hint: 'One PDF, read once' },
  { key: 'review', label: 'About you', hint: 'Experience, contact, location' },
  { key: 'prefs', label: 'Your goals', hint: 'Titles, places, remote' },
  { key: 'pay', label: 'Pay & availability', hint: 'CTC, notice period' },
  { key: 'launch', label: 'First search', hint: 'Find roles that fit' },
];
const COPY = {
  upload: [html`Let's get to <span class="serif">know</span> you`, 'Upload your resume once. JobHunterX reads it into a profile it uses for every search, score and document — and never invents anything.'],
  review: [html`Here's how we <span class="serif">see</span> you`, 'Experience is computed from your dates — internships are counted separately — and every skill is checked against what you actually wrote.'],
  prefs: [html`Where do you want to <span class="serif">go</span>?`, 'Add every title and city you would consider. These are hard rules: roles outside them are filtered out, not ranked high by keyword luck.'],
  pay: [html`Pay & <span class="serif">availability</span>`, 'Used to filter roles below your minimum and to fill application forms. Stays on your machine.'],
  launch: [html`You're all <span class="serif">set</span>`, 'Your first search reads each posting, checks it is real and open, and explains every score. Results stream in live.'],
};
const uniq = (xs) => [...new Map(xs.filter(Boolean).map((x) => [String(x).trim().toLowerCase(), String(x).trim()])).values()].filter(Boolean);
const city = (loc) => (loc || '').split(',')[0].trim();

function Stepper({ step }) {
  const idx = STEPS.findIndex((s) => s.key === step);
  return html`<ol class="stepper" aria-label="Setup progress">
    ${STEPS.map((s, i) => html`<li key=${s.key} class=${i < idx ? 'done' : i === idx ? 'current' : ''} aria-current=${i === idx ? 'step' : undefined}>
      <span class="stepper-dot">${i < idx ? html`<${Icon} name="check" size=${13} />` : i + 1}</span>
      <span class="stepper-text"><strong>${s.label}</strong><span>${s.hint}</span></span></li>`)}
    <span class="stepper-fill" style=${{ '--k': idx / (STEPS.length - 1) }} aria-hidden="true"></span>
  </ol>`;
}


function UploadStep() {
  const up = useStore((s) => s.profile.upload);
  const [drag, setDrag] = useState(false);
  const input = useRef();
  const pick = (files) => files && files[0] && uploadResume(files[0]);
  if (up.status === 'uploading') {
    const at = Math.max(0, UPLOAD_STAGES.findIndex(([k]) => k === (up.stage === 'received' ? 'extracting' : up.stage)));
    return html`<div class="ob-reading" aria-live="polite">
      <${ScanDoc} />
      <h3>Reading <span class="file-name">${up.fileName}</span></h3>
      <ol class="up-stages">${UPLOAD_STAGES.map(([k, label], i) => html`<li key=${k} class=${i < at ? 'done' : i === at ? 'now' : ''}>
        <span class="up-dot">${i < at ? html`<${Icon} name="check" size=${11} />` : i === at ? html`<${Spinner} size=${12} />` : null}</span>${label}</li>`)}</ol>
      <p class="muted small">Elapsed <${Elapsed} since=${up.startedAt || Date.now()} /> · free AI tiers can take 1–3 minutes. You can keep this tab open; it continues in the background.</p>
    </div>`;
  }
  return html`<div class="stack">
    <button type="button" class=${`dropzone ${drag ? 'drag' : ''}`} onClick=${() => input.current.click()}
      onDragOver=${(e) => { e.preventDefault(); setDrag(true); }} onDragLeave=${() => setDrag(false)}
      onDrop=${(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files); }}>
      <svg class="dz-border" aria-hidden="true"><rect x="1" y="1" rx="22" ry="22" /></svg>
      <span class="dz-icon"><${Icon} name="upload" size=${26} /></span>
      <strong>${drag ? 'Drop it here' : 'Drop your resume PDF here'}</strong>
      <span class="muted small">or click to browse · PDF only</span>
    </button>
    <input ref=${input} type="file" accept="application/pdf,.pdf" class="sr-only" aria-label="Resume PDF"
      onChange=${(e) => { pick(e.currentTarget.files); e.currentTarget.value = ''; }} />
    ${up.status === 'error' ? html`<${ErrorBox} message=${up.error} onRetry=${() => input.current.click()} />` : null}
    <ul class="ob-promises">
      <li><${Icon} name="shield" size=${16} /> Stays on your machine</li>
      <li><${Icon} name="check" size=${16} /> Nothing invented</li>
      <li><${Icon} name="refresh" size=${16} /> Editable any time</li>
    </ul>
    <button type="button" class="link-btn ob-skip" onClick=${() => finishOnboarding({ to: '#/profile' })}>No resume handy? Fill in your profile manually</button>
  </div>`;
}

function foundLinks(d) {
  const out = [];
  [['LinkedIn', d.linkedin], ['GitHub', d.github], ['Portfolio', d.portfolio]].forEach(([l, u]) => u && out.push({ where: '', label: l, url: u }));
  (d.links || []).forEach((l) => l.url && out.push({ where: '', label: l.label || 'Link', url: l.url }));
  (d.projects || []).forEach((pr) => (pr.links || []).forEach((l) => l.url && out.push({ where: pr.title, label: l.label || 'Link', url: l.url })));
  (d.item_links || []).forEach((l) => l.url && out.push({ where: l.item, label: l.label || 'Link', url: l.url }));
  return out;
}

function ReviewStep({ draft, set }) {
  const env = useStore((s) => s.profile.envelope);
  const extraction = useStore((s) => s.profile.upload.extraction);
  const snap = env && env.snapshot;
  const locSugg = uniq([draft.location, ...draft.experience.map((e) => e.location)]);
  return html`<div class="stack">
    ${extraction && extraction.warnings && extraction.warnings.length ? html`<${Notice} tone="warning">${extraction.warnings.join(' ')}</${Notice}>` : null}
    ${snap ? html`<div class="ob-level"><span class="chip">${humanize(snap.seniority)} level</span>
        <span class="chip">${snap.skills.length} verified skills</span>${snap.role_families.slice(0, 2).map((f) => html`<span class="chip soft">${f.label}</span>`)}</div>
      <${ExperienceSummary} snap=${snap} />` : html`<${Skeleton} lines=${4} />`}
    <div class="form-grid tight">
      <${Field} label="Full name">${(id) => html`<input id=${id} class="input" autocomplete="name" value=${draft.name} onInput=${(e) => set(['name'], e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Email">${(id) => html`<input id=${id} class="input" type="email" autocomplete="email" value=${draft.email} onInput=${(e) => set(['email'], e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Phone">${(id) => html`<input id=${id} class="input" type="tel" autocomplete="tel" value=${draft.phone} onInput=${(e) => set(['phone'], e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Current location" hint="City, state, country">${(id) => html`<input id=${id} class="input" list="ob-loc" autocomplete="address-level2" value=${draft.location}
        placeholder="e.g. Hyderabad, Telangana, India" onInput=${(e) => set(['location'], e.currentTarget.value)} />
        <datalist id="ob-loc">${locSugg.map((l) => html`<option value=${l} />`)}</datalist>`}</${Field}>
    </div>
    ${(() => {
      const links = foundLinks(draft);
      return links.length ? html`<div class="ob-links"><span class="field-label"><${Icon} name="external" size=${13} /> Links we found · ${links.length}</span>
        <div class="chip-row">${links.map((l, i) => { const u = safeUrl(l.url); return u ? html`<a key=${i} class="chip link-chip" href=${u} target="_blank" rel="noopener noreferrer" title=${l.url}>
          ${l.where ? html`<span class="muted">${l.where.length > 26 ? `${l.where.slice(0, 25)}…` : l.where} ·</span>` : null}${l.label}</a>` : null; })}</div>
        <span class="field-hint">They go into your resume and CV next to the project or entry they belong to. Edit them any time in Profile.</span></div>` : null;
    })()}
  </div>`;
}

function PrefsStep({ draft, set }) {
  const env = useStore((s) => s.profile.envelope);
  const snap = env && env.snapshot;
  const p = draft.preferences;
  const remote = p.work_modes.includes('remote');
  const titleSugg = uniq([...(snap ? [...snap.target_titles, ...snap.adjacent_titles, ...snap.role_families.map((f) => f.label)] : []), draft.suggested_role,
    ...draft.experience.map((e) => e.role)]);
  const locSugg = uniq([city(draft.location), ...draft.experience.map((e) => city(e.location)), ...(snap ? snap.locations.map((l) => l.city) : [])]);
  const country = p.home_country || (snap && snap.home_country) || '';
  return html`<div class="form-grid tight">
    <${Field} label="Job titles you want" hint="Add as many as you like — each one is searched." wide>
      <${ChipsInput} label="Target roles" value=${p.target_roles} onChange=${(v) => set(['preferences', 'target_roles'], v)}
        placeholder="Type a title and press Enter" suggestions=${titleSugg} /></${Field}>
    <${Field} label="Cities you can work in" hint="Add every city you'd move to or commute to." wide>
      <${ChipsInput} label="Locations" value=${p.locations} onChange=${(v) => set(['preferences', 'locations'], v)}
        placeholder="Type a city and press Enter" suggestions=${locSugg} /></${Field}>
    <div class="field field-wide"><span class="field-label">Work modes you accept</span>
      <${Seg} multi label="Work modes" options=${WORK_MODES.map((m) => [m, WORK_MODE_LABEL[m]])} value=${p.work_modes} onChange=${(v) => set(['preferences', 'work_modes'], v)} /></div>
    <div class="field field-wide toggles option-cards">
      <label class=${`opt-card ${remote ? 'on' : ''}`}><input type="checkbox" checked=${remote}
          onChange=${(e) => set(['preferences', 'work_modes'], e.currentTarget.checked ? uniq([...p.work_modes, 'remote']) : p.work_modes.filter((m) => m !== 'remote'))} />
        <span class="switch-ui"></span><span><strong>Remote roles${country ? ` anywhere in ${country}` : ''}</strong><small>Not tied to the cities above</small></span></label>
      <label class=${`opt-card ${p.willing_to_relocate ? 'on' : ''}`}><input type="checkbox" checked=${p.willing_to_relocate} onChange=${(e) => set(['preferences', 'willing_to_relocate'], e.currentTarget.checked)} />
        <span class="switch-ui"></span><span><strong>Willing to relocate</strong><small>Other cities in ${country || 'my country'}</small></span></label>
      <label class=${`opt-card ${p.open_to_international ? 'on' : ''}`}><input type="checkbox" checked=${p.open_to_international} onChange=${(e) => set(['preferences', 'open_to_international'], e.currentTarget.checked)} />
        <span class="switch-ui"></span><span><strong>Roles abroad</strong><small>Remote for foreign companies or relocation</small></span></label>
    </div>
    <${Field} label="Home country">${(id) => html`<input id=${id} class="input" autocomplete="country-name" value=${p.home_country || ''} placeholder=${(snap && snap.home_country) || 'e.g. India'}
      onInput=${(e) => set(['preferences', 'home_country'], e.currentTarget.value)} />`}</${Field}>
    <${Field} label="Employment types" hint="e.g. full_time, contract, internship">
      <${ChipsInput} label="Employment types" value=${p.employment_types} onChange=${(v) => set(['preferences', 'employment_types'], v)} placeholder="full_time"
        suggestions=${['full_time', 'contract', 'internship', 'part_time']} /></${Field}>
    <${Field} label="Career direction" hint="Where you want to grow — shapes which tracks are searched." wide>${(id) => html`<${AutoTextarea} id=${id}
      value=${p.career_direction || ''} placeholder="e.g. Move from data science into applied LLM engineering" onInput=${(e) => set(['preferences', 'career_direction'], e.currentTarget.value)} />`}</${Field}>
  </div>`;
}

function PayStep({ draft, set }) {
  const p = draft.preferences;
  const q = draft.qa_memory;
  return html`<div class="form-grid tight">
    <${Field} label="Current CTC" hint="Annual, as you'd write it on a form (e.g. 6 LPA).">${(id) => html`<input id=${id} class="input" value=${q.current_ctc || ''}
      onInput=${(e) => set(['qa_memory', 'current_ctc'], e.currentTarget.value)} placeholder="e.g. 6 LPA" />`}</${Field}>
    <${Field} label="Expected CTC">${(id) => html`<input id=${id} class="input" value=${q.expected_ctc || ''}
      onInput=${(e) => set(['qa_memory', 'expected_ctc'], e.currentTarget.value)} placeholder="e.g. 10 LPA" />`}</${Field}>
    <${Field} label="Minimum annual salary (filter)" hint="Roles that clearly pay less are ruled out. Leave empty if flexible.">${(id) => html`<input id=${id} class="input" type="number" min="0" step="1000"
      value=${p.min_annual_salary ?? ''} onInput=${(e) => set(['preferences', 'min_annual_salary'], e.currentTarget.value === '' ? null : Number(e.currentTarget.value))} placeholder="e.g. 800000" />`}</${Field}>
    <${Field} label="Currency">${(id) => html`<input id=${id} class="input" value=${p.salary_currency || ''} maxlength="6" placeholder="INR"
      onInput=${(e) => set(['preferences', 'salary_currency'], e.currentTarget.value.toUpperCase())} />`}</${Field}>
    <${Field} label="Notice period (days)" hint="0 if you can join immediately.">${(id) => html`<input id=${id} class="input" type="number" min="0" max="365"
      value=${p.notice_period_days ?? ''} onInput=${(e) => { const v = e.currentTarget.value === '' ? null : Number(e.currentTarget.value);
        set(['preferences', 'notice_period_days'], v); set(['qa_memory', 'notice_period'], v == null ? '' : `${v} days`); }} />`}</${Field}>
    <${Field} label="Work authorization">${(id) => html`<input id=${id} class="input" value=${q.work_authorization || ''}
      onInput=${(e) => set(['qa_memory', 'work_authorization'], e.currentTarget.value)} placeholder="e.g. Indian citizen" />`}</${Field}>
    <${Field} label="Need visa sponsorship?">${(id) => html`<${Seg} label="Sponsorship" options=${[['No', 'No'], ['Yes', 'Yes']]}
      value=${q.requires_sponsorship || 'No'} onChange=${(v) => set(['qa_memory', 'requires_sponsorship'], v)} />`}</${Field}>
  </div>`;
}

function LaunchStep() {
  const env = useStore((s) => s.profile.envelope);
  const snap = env && env.snapshot;
  const req = defaultSearchRequest(snap);
  return html`<div class="ob-launch">
    <${Orb} size=${150} />
    <div class="ob-plan">
      <div><span class="sec-title">Titles</span><div class="chip-row">${(snap ? [...snap.target_titles, ...snap.adjacent_titles].slice(0, 6) : []).map((t, i) => html`<span class="chip chip-pop" style=${{ '--i': i }}>${t}</span>`)}</div></div>
      <div><span class="sec-title">Where</span><div class="chip-row">${req.locations.length ? req.locations.map((t) => html`<span class="chip"><${Icon} name="pin" size=${12} /> ${t}</span>`) : html`<span class="muted small">Your profile location</span>`}
        ${req.work_modes.map((m) => html`<span class="chip soft">${WORK_MODE_LABEL[m]}</span>`)}</div></div>
    </div>
  </div>`;
}

export function OnboardingView() {
  const { step, dir } = useStore((s) => s.onboarding);
  const env = useStore((s) => s.profile.envelope);
  const saving = useStore((s) => s.profile.saving);
  const saveError = useStore((s) => s.profile.saveError);
  const profile = env && env.profile;
  const [draft, setDraft] = useState(() => normalizeProfile(profile));
  const [base, setBase] = useState(() => JSON.stringify(normalizeProfile(profile)));
  const serverJson = JSON.stringify(normalizeProfile(profile));
  // A fresh upload replaces the draft (unless the user already started editing it).
  useEffect(() => { if (JSON.stringify(draft) === base) { setDraft(normalizeProfile(profile)); setBase(serverJson); } }, [serverJson]);
  const set = (path, value) => setDraft((d) => setIn(d, path, value));
  const dirty = JSON.stringify(draft) !== base;

  const saveThen = async (next) => {
    if (dirty) {
      if (!(await saveProfile(draft, { quiet: true }))) return;
      setBase(JSON.stringify(draft));
    }
    setOnboardingStep(next);
  };
  const snap = env && env.snapshot;
  const [title, lead] = COPY[step];
  return html`<div class="onboarding">
    <aside class="ob-side">
      <div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
        <span class="brand-name">JobHunter<span class="serif">X</span></span></div>
      <div class="ob-copy" key=${step}><h1>${title}</h1><p class="lead">${lead}</p></div>
      <${Stepper} step=${step} />
    </aside>
    <section class="ob-main">
      <div class=${`ob-card card step-anim ${dir < 0 ? 'from-left' : 'from-right'}`} key=${step}>
        <div class="ob-body">
          ${step === 'upload' ? html`<${UploadStep} />` : null}
          ${step === 'review' ? html`<${ReviewStep} draft=${draft} set=${set} />` : null}
          ${step === 'prefs' ? html`<${PrefsStep} draft=${draft} set=${set} />` : null}
          ${step === 'pay' ? html`<${PayStep} draft=${draft} set=${set} />` : null}
          ${step === 'launch' ? html`<${LaunchStep} />` : null}
          ${saveError && ['review', 'prefs', 'pay'].includes(step) ? html`<${ErrorBox} message=${saveError} />` : null}
        </div>
        ${step !== 'upload' ? html`<footer class="ob-foot">
          ${step === 'review' ? html`<${Button} icon="upload" onClick=${() => setOnboardingStep('upload')}>Use another file</${Button}>`
            : html`<${Button} icon="back" onClick=${() => setOnboardingStep({ prefs: 'review', pay: 'prefs', launch: 'pay' }[step])}>Back</${Button}>`}
          ${step === 'review' ? html`<${Button} variant="primary" busy=${saving} onClick=${() => saveThen('prefs')}>Looks right <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          ${step === 'prefs' ? html`<${Button} variant="primary" busy=${saving} onClick=${() => saveThen('pay')}>Continue <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          ${step === 'pay' ? html`<${Button} variant="primary" busy=${saving} onClick=${() => saveThen('launch')}>Continue <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          ${step === 'launch' ? html`<div class="row gap">
            <${Button} onClick=${() => finishOnboarding()}>Explore first</${Button}>
            <${Button} variant="primary" size="lg" onClick=${() => finishOnboarding({ search: defaultSearchRequest(snap) })}>Find my roles <${Icon} name="arrow" size=${16} /></${Button}></div>` : null}
        </footer>` : null}
      </div>
    </section>
  </div>`;
}
