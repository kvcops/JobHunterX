// One-time setup: resume → review what was understood → preferences → first search.
// Shown only until the user finishes (or when no profile exists). The step survives reloads.
import { html, useState, useRef, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { uploadResume, saveProfile, setOnboardingStep, finishOnboarding } from '../actions.js';
import {
  Button, Icon, ChipsInput, Field, Notice, Meter, Seg, Skeleton, ScanDoc, RotatingText, Orb, CountUp, ErrorBox,
} from '../components/ui.js';
import { normalizeProfile, setIn, defaultSearchRequest } from '../state/domain.js';
import { WORK_MODES, WORK_MODE_LABEL, humanize } from '../lib/format.js';

const STEPS = [
  { key: 'upload', label: 'Your resume', hint: 'One PDF, read once' },
  { key: 'review', label: 'What we understood', hint: 'Check the essentials' },
  { key: 'prefs', label: 'What you want', hint: 'Places, modes, pay' },
  { key: 'launch', label: 'First search', hint: 'Find roles that fit' },
];
const COPY = {
  upload: [html`Let's get to <span class="serif">know</span> you`, 'Upload your resume once. JobHunterX reads it into a profile it uses for every search, score and document — and never invents anything.'],
  review: [html`Here's how we <span class="serif">see</span> you`, 'Experience is computed from your dates, and every skill is checked against what you actually wrote. Fix anything that looks off.'],
  prefs: [html`Where do you want to <span class="serif">go</span>?`, 'These preferences are hard rules: roles outside them are filtered out instead of being ranked high by keyword luck.'],
  launch: [html`You're all <span class="serif">set</span>`, 'Your first search reads each posting, checks it is real and open, and explains every score. Results stream in live.'],
};

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
    return html`<div class="ob-reading" aria-live="polite">
      <${ScanDoc} />
      <h3>Reading <span class="file-name">${up.fileName}</span></h3>
      <p class="muted"><${RotatingText} items=${['Extracting your roles, dates and achievements…', 'Reading skills from where you actually used them…',
        'Mapping your projects and education…', 'Working out which career tracks fit you…']} /></p>
      <p class="muted small">This usually takes under a minute.</p>
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

function ReviewStep({ draft, set }) {
  const env = useStore((s) => s.profile.envelope);
  const extraction = useStore((s) => s.profile.upload.extraction);
  const snap = env && env.snapshot;
  return html`<div class="stack">
    ${extraction && extraction.warnings && extraction.warnings.length ? html`<${Notice} tone="warning">${extraction.warnings.join(' ')}</${Notice}>` : null}
    ${snap ? html`<div class="ob-stats">
      <div class="ob-stat"><span class="n"><${CountUp} value=${snap.professional_years} /><small>yrs</small></span><span class="l">Experience</span></div>
      <div class="ob-stat"><span class="n">${humanize(snap.seniority)}</span><span class="l">Level</span></div>
      <div class="ob-stat"><span class="n"><${CountUp} value=${snap.skills.length} /></span><span class="l">Verified skills</span></div>
    </div>
    ${snap.role_families.length ? html`<div class="ob-tracks">${snap.role_families.slice(0, 3).map((f, i) => html`<div class="ob-track" style=${{ '--i': i }} title=${f.evidence}>
      <div class="row space"><span>${f.label}</span><span class="track-pct">${Math.round(f.closeness * 100)}%</span></div><${Meter} value=${f.closeness} tone="ink" /></div>`)}</div>` : null}
    <div class="chip-row ob-skills">${snap.skills.slice(0, 14).map((s, i) => html`<span class="chip chip-pop" style=${{ '--i': i }}>${s.name}</span>`)}</div>`
    : html`<${Skeleton} lines=${4} />`}
    <div class="form-grid tight">
      <${Field} label="Full name">${(id) => html`<input id=${id} class="input" value=${draft.name} onInput=${(e) => set(['name'], e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Email">${(id) => html`<input id=${id} class="input" type="email" value=${draft.email} onInput=${(e) => set(['email'], e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Roles you want" hint="Titles used first in every search." wide>
        <${ChipsInput} label="Target roles" value=${draft.preferences.target_roles} onChange=${(v) => set(['preferences', 'target_roles'], v)}
          placeholder=${(snap && snap.target_titles[0]) || 'e.g. AI Engineer'} /></${Field}>
    </div>
  </div>`;
}

function PrefsStep({ draft, set }) {
  const p = draft.preferences;
  return html`<div class="form-grid tight">
    <${Field} label="Cities you can work in" wide><${ChipsInput} label="Locations" value=${p.locations} onChange=${(v) => set(['preferences', 'locations'], v)} placeholder="Add a city and press Enter" /></${Field}>
    <div class="field field-wide"><span class="field-label">Work modes you accept</span>
      <${Seg} multi label="Work modes" options=${WORK_MODES.map((m) => [m, WORK_MODE_LABEL[m]])} value=${p.work_modes} onChange=${(v) => set(['preferences', 'work_modes'], v)} /></div>
    <div class="field field-wide toggles">
      <label class="switch"><input type="checkbox" checked=${p.willing_to_relocate} onChange=${(e) => set(['preferences', 'willing_to_relocate'], e.currentTarget.checked)} /><span class="switch-ui"></span> Willing to relocate within my country</label>
      <label class="switch"><input type="checkbox" checked=${p.open_to_international} onChange=${(e) => set(['preferences', 'open_to_international'], e.currentTarget.checked)} /><span class="switch-ui"></span> Open to roles abroad</label>
    </div>
    <${Field} label="Minimum annual salary" hint="Optional — leave empty if flexible.">${(id) => html`<input id=${id} class="input" type="number" min="0" value=${p.min_annual_salary ?? ''}
      onInput=${(e) => set(['preferences', 'min_annual_salary'], e.currentTarget.value === '' ? null : Number(e.currentTarget.value))} />`}</${Field}>
    <${Field} label="Currency">${(id) => html`<input id=${id} class="input" value=${p.salary_currency || ''} onInput=${(e) => set(['preferences', 'salary_currency'], e.currentTarget.value)} />`}</${Field}>
    <${Field} label="Career direction" hint="Where you want to grow — shapes which tracks are searched." wide>${(id) => html`<textarea id=${id} class="input" rows="2"
      value=${p.career_direction || ''} onInput=${(e) => set(['preferences', 'career_direction'], e.currentTarget.value)}></textarea>`}</${Field}>
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
      <div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="20" height="20" /></span>
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
          ${step === 'launch' ? html`<${LaunchStep} />` : null}
          ${saveError && (step === 'review' || step === 'prefs') ? html`<${ErrorBox} message=${saveError} />` : null}
        </div>
        ${step !== 'upload' ? html`<footer class="ob-foot">
          ${step === 'review' ? html`<${Button} icon="upload" onClick=${() => setOnboardingStep('upload')}>Use another file</${Button}>`
            : html`<${Button} icon="back" onClick=${() => setOnboardingStep(step === 'launch' ? 'prefs' : 'review')}>Back</${Button}>`}
          ${step === 'review' ? html`<${Button} variant="primary" busy=${saving} onClick=${() => saveThen('prefs')}>Looks right <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          ${step === 'prefs' ? html`<${Button} variant="primary" busy=${saving} onClick=${() => saveThen('launch')}>Continue <${Icon} name="arrow" size=${16} /></${Button}>` : null}
          ${step === 'launch' ? html`<div class="row gap">
            <${Button} onClick=${() => finishOnboarding()}>Explore first</${Button}>
            <${Button} variant="primary" size="lg" onClick=${() => finishOnboarding({ search: defaultSearchRequest(snap) })}>Find my roles <${Icon} name="arrow" size=${16} /></${Button}></div>` : null}
        </footer>` : null}
      </div>
    </section>
  </div>`;
}
