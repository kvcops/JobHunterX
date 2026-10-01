import { html, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import {
  loadDetail, toggleSaved, setTracking, verifyJob, rescoreJob, generateDocument, autoApply, deleteJob, navigate,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Meter, Skeleton, ErrorBox, Drawer, Icon, Notice, Tabs,
} from '../components/ui.js';
import {
  VERDICT_LABEL, VALIDATION_LABEL, VALIDATION_TONE, CHECK_LABEL, CHECK_STATUS_LABEL, CHECK_STATUS_TONE,
  CONSTRAINT_TONE, CONSTRAINT_LABEL, TRACKING_LABEL, DEFAULT_TRACKING, WORK_MODE_LABEL, DOC_KIND_LABEL,
  fmtDate, relTime, fmtSalary, safeUrl, humanize, experienceText,
} from '../lib/format.js';
import { genKey } from '../state/domain.js';

function MatchTab({ job }) {
  const m = job.match;
  if (!m) return html`<${Notice}>This job has not been scored yet.</${Notice}>`;
  return html`<div class="stack">
    ${m.method === 'fallback' ? html`<${Notice} tone="warning">Partial analysis — the AI could not read this posting fully, so skill coverage and requirements may be incomplete.</${Notice}>` : null}
    <section>
      <h3 class="sec-title">Hard requirements</h3>
      <ul class="constraints">
        ${m.hard_constraints.map((c) => html`<li key=${c.key} class=${`constraint tone-${CONSTRAINT_TONE[c.status]}`}>
          <${Badge} tone=${CONSTRAINT_TONE[c.status]}>${CONSTRAINT_LABEL[c.status]}</${Badge}>
          <div><strong>${c.label}</strong>${!c.hard ? html` <span class="muted small">(advisory)</span>` : null}<div class="muted">${c.detail}</div></div>
        </li>`)}
      </ul>
    </section>
    <section>
      <h3 class="sec-title">How the score was built</h3>
      <div class="components">
        ${m.components.map((c) => html`<div class="component" key=${c.key}>
          <div class="component-head"><span>${c.label}</span><span class="muted small">weight ${Math.round(c.weight * 100)}% · ${Math.round(c.score * 100)}/100</span></div>
          <${Meter} value=${c.score} /><div class="muted small">${c.detail}</div></div>`)}
      </div>
      ${m.rejected_reasons.length ? html`<p class="muted small">Because a hard requirement failed, the score is capped no matter how many skills overlap.</p>` : null}
    </section>
    <div class="two-col">
      <section><h3 class="sec-title">Strengths</h3>
        ${m.strengths.length ? html`<ul class="bullets good">${m.strengths.map((x) => html`<li>${x}</li>`)}</ul>` : html`<p class="muted">None identified.</p>`}</section>
      <section><h3 class="sec-title">Gaps</h3>
        ${m.gaps.length ? html`<ul class="bullets bad">${m.gaps.map((x) => html`<li>${x}</li>`)}</ul>` : html`<p class="muted">No gaps found.</p>`}</section>
    </div>
    ${m.unknowns.length ? html`<section><h3 class="sec-title">Unknown — could not be verified</h3><ul class="bullets unk">${m.unknowns.map((x) => html`<li>${x}</li>`)}</ul></section>` : null}
    <section><h3 class="sec-title">Skills</h3>
      <div class="skill-cloud">
        ${m.matched_required.map((s) => html`<span class="chip chip-good" title="Required — you have it">${s}</span>`)}
        ${m.missing_required.map((s) => html`<span class="chip chip-bad" title="Required — not shown in your profile">${s}</span>`)}
        ${m.matched_preferred.map((s) => html`<span class="chip chip-good soft" title="Nice to have — you have it">${s}</span>`)}
        ${m.missing_preferred.map((s) => html`<span class="chip soft" title="Nice to have — not shown">${s}</span>`)}
      </div>
      <p class="muted small">Green: you have it. Red: required but not in your profile. Faded: nice-to-have.</p>
    </section>
  </div>`;
}

function VerifyTab({ job }) {
  const v = job.validation;
  return html`<div class="stack">
    <div class="row gap"><${Badge} tone=${VALIDATION_TONE[v.status]}>${VALIDATION_LABEL[v.status]}</${Badge}>
      <span class="muted small">confidence ${Math.round((v.confidence || 0) * 100)}% · checked ${v.checked_at ? relTime(v.checked_at) : 'never'}</span></div>
    ${v.notes && v.notes.length ? html`<ul class="bullets">${v.notes.map((n) => html`<li>${n}</li>`)}</ul>` : null}
    <table class="checks"><thead><tr><th>Check</th><th>Status</th><th>Value / evidence</th></tr></thead><tbody>
      ${Object.entries(v.checks || {}).map(([k, c]) => html`<tr key=${k}>
        <td>${CHECK_LABEL[k] || humanize(k)}</td>
        <td><${Badge} tone=${CHECK_STATUS_TONE[c.status]}>${CHECK_STATUS_LABEL[c.status]}</${Badge}></td>
        <td><div>${c.value || '—'}</div>${c.evidence ? html`<div class="muted small">${c.evidence}</div>` : null}</td></tr>`)}
    </tbody></table>
    <section><h3 class="sec-title">Sources</h3><ul class="sources">
      ${job.sources.map((s) => { const u = safeUrl(s.url); return html`<li>
        <${Badge} tone=${s.first_party ? 'success' : 'neutral'}>${s.first_party ? 'First-party' : humanize(s.kind)}</${Badge}>
        ${u ? html`<a href=${u} target="_blank" rel="noopener noreferrer">${s.name}</a>` : s.name}
        <span class="muted small">seen ${relTime(s.fetched_at)}</span></li>`; })}
    </ul></section>
  </div>`;
}

function RequirementsTab({ job }) {
  const r = job.requirements;
  const [full, setFull] = useState(false);
  return html`<div class="stack">
    <div class="facts-grid">
      <div><span class="muted small">Experience</span><div>${r.experience_min != null ? `${r.experience_min}${r.experience_max != null ? `–${r.experience_max}` : '+'} years` : 'Not stated'}</div>
        ${r.experience_evidence ? html`<div class="muted small">“${r.experience_evidence}”</div>` : null}</div>
      <div><span class="muted small">Education</span><div>${r.education_level === 'unknown' ? 'Not stated' : `${humanize(r.education_level)}${r.education_mandatory ? ' (required)' : ''}`}</div></div>
      <div><span class="muted small">Employment</span><div>${humanize(job.employment_type) || 'Not stated'}</div></div>
      <div><span class="muted small">Work mode</span><div>${WORK_MODE_LABEL[job.work_mode]}</div></div>
      <div><span class="muted small">Salary</span><div>${job.salary ? fmtSalary(job.salary) : 'Not stated'}</div></div>
      <div><span class="muted small">Notice period</span><div>${r.notice_period_max_days != null ? `≤ ${r.notice_period_max_days} days` : 'Not stated'}</div></div>
    </div>
    ${r.must_have_skills.length ? html`<section><h3 class="sec-title">Mandatory</h3><div class="chip-row">${r.must_have_skills.map((s) => html`<span class="chip">${s}</span>`)}</div></section>` : null}
    <section><h3 class="sec-title">Required skills</h3><div class="chip-row">${r.required_skills.length ? r.required_skills.map((s) => html`<span class="chip">${s}</span>`) : html`<span class="muted">None extracted</span>`}</div></section>
    ${r.preferred_skills.length ? html`<section><h3 class="sec-title">Nice to have</h3><div class="chip-row">${r.preferred_skills.map((s) => html`<span class="chip soft">${s}</span>`)}</div></section>` : null}
    ${r.responsibilities.length ? html`<section><h3 class="sec-title">What you would do</h3><ul class="bullets">${r.responsibilities.map((x) => html`<li>${x}</li>`)}</ul></section>` : null}
    <section><h3 class="sec-title">Full description</h3>
      <div class=${`jd-text ${full ? '' : 'clamped'}`}>${job.description || 'No description available.'}</div>
      ${job.description && job.description.length > 900 ? html`<button type="button" class="link-btn" onClick=${() => setFull(!full)}>${full ? 'Show less' : 'Show full description'}</button>` : null}
    </section>
  </div>`;
}

function DocActions({ job }) {
  const gen = useStore((s) => s.gen);
  const row = (kind) => {
    const g = gen[genKey(job.id, kind)];
    const docId = (g && g.documentId) || (job.documents && job.documents[kind]);
    const latest = (job.document_list || []).find((d) => d.id === docId);
    return html`<div class="doc-action" key=${kind}>
      <div><strong>${DOC_KIND_LABEL[kind]}</strong>
        <div class="muted small">${g && g.status === 'generating' ? 'Generating — this can take up to a minute…'
          : latest ? `Generated ${relTime(latest.created_at)}${latest.stale ? ' · profile changed since' : ''}${latest.warnings_count ? ` · ${latest.warnings_count} note(s)` : ''}` : 'Not generated yet'}</div>
        ${g && g.status === 'failed' ? html`<div class="error-text small" role="alert">${g.error}</div>` : null}
      </div>
      <div class="row gap">
        ${docId ? html`<${Button} size="sm" onClick=${() => navigate(`#/documents/${docId}`)}>Open</${Button}>` : null}
        <${Button} size="sm" variant=${docId ? 'secondary' : 'primary'} icon=${g && g.status === 'failed' ? 'refresh' : 'spark'}
          busy=${g && g.status === 'generating'} onClick=${() => generateDocument(job.id, kind)}>
          ${g && g.status === 'failed' ? 'Retry' : docId ? 'Regenerate' : 'Generate'}</${Button}>
      </div></div>`;
  };
  return html`<section class="card inset"><h3 class="sec-title">Application materials</h3>${row('resume')}${row('cover_letter')}</section>`;
}

export function JobDetailDrawer({ jobId, onClose }) {
  const entry = useStore((s) => s.details[jobId]);
  const tracking = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const pending = useStore((s) => s.pending);
  const [tab, setTab] = useState('match');
  const job = entry && entry.job;
  return html`<${Drawer} onClose=${onClose} label="Job details">
    <div class="drawer-head">
      <button type="button" class="icon-btn" aria-label="Close" onClick=${onClose}><${Icon} name="x" /></button>
      ${job ? html`<div class="row gap">
        <button type="button" class=${`icon-btn save-btn ${job.saved ? 'on' : ''}`} aria-pressed=${job.saved ? 'true' : 'false'}
          aria-label=${job.saved ? 'Unsave job' : 'Save job'} disabled=${!!pending.save[jobId]} onClick=${() => toggleSaved(jobId)}><${Icon} name="star" /></button>
        <button type="button" class="icon-btn" aria-label="Remove job" onClick=${() => deleteJob(jobId)}><${Icon} name="trash" /></button></div>` : null}
    </div>
    ${!entry || (entry.status === 'loading' && !job) ? html`<div class="drawer-body"><${Skeleton} lines=${6} /></div>` : null}
    ${entry && entry.status === 'error' && !job ? html`<div class="drawer-body"><${ErrorBox} message=${entry.error} onRetry=${() => loadDetail(jobId)} /></div>` : null}
    ${job ? html`<div class="drawer-body">
      <header class="detail-header">
        <${ScoreRing} score=${job.match ? job.match.score : null} verdict=${job.match && job.match.verdict} size=${68} />
        <div class="grow">
          <h2>${job.title}</h2>
          <div class="muted">${job.company} · ${job.location || 'Location not stated'}</div>
          <div class="row gap wrap">
            ${job.match ? html`<${Badge} tone=${job.match.verdict === 'incompatible' ? 'danger' : 'info'}>${VERDICT_LABEL[job.match.verdict]}</${Badge}>` : null}
            <${Badge} tone=${VALIDATION_TONE[job.validation.status]}>${VALIDATION_LABEL[job.validation.status]}</${Badge}>
            ${job.match && job.match.experience ? html`<span class="muted small">${experienceText(job.match.experience)}</span>` : null}
            ${job.posted_at ? html`<span class="muted small">Posted ${fmtDate(job.posted_at)}</span>` : null}
          </div>
          ${job.match ? html`<p class="detail-headline">${job.match.headline}</p>` : null}
        </div>
      </header>
      ${job.match_stale ? html`<${Notice} tone="warning">Your profile changed since this job was scored.
        <${Button} size="sm" busy=${!!pending.rescore[jobId]} onClick=${() => rescoreJob(jobId)}>Re-score now</${Button}></${Notice}>` : null}
      <div class="action-bar">
        ${safeUrl(job.apply_url) ? html`<a class="btn btn-primary" href=${safeUrl(job.apply_url)} target="_blank" rel="noopener noreferrer"><${Icon} name="external" size=${16} /><span>Open posting</span></a>` : null}
        <label class="inline-select"><span class="sr-only">Tracking status</span>
          <select class="input" value=${job.tracking_status} disabled=${!!pending.track[jobId]} onChange=${(e) => setTracking(jobId, e.currentTarget.value)}>
            ${tracking.map((t) => html`<option value=${t}>${TRACKING_LABEL[t] || humanize(t)}</option>`)}
          </select></label>
        <${Button} icon="refresh" busy=${!!pending.verify[jobId]} onClick=${() => verifyJob(jobId)}>Re-verify</${Button}>
        <${Button} busy=${!!pending.rescore[jobId]} onClick=${() => rescoreJob(jobId)}>Re-score</${Button}>
        <${Button} icon="globe" busy=${!!pending.apply[jobId]} onClick=${() => autoApply(jobId)}>Auto-apply</${Button}>
      </div>
      <${DocActions} job=${job} />
      <${Tabs} label="Job sections" value=${tab} onChange=${setTab}
        tabs=${[{ key: 'match', label: 'Why this score' }, { key: 'req', label: 'Requirements' }, { key: 'verify', label: 'Verification' }]} />
      <div role="tabpanel">
        ${tab === 'match' ? html`<${MatchTab} job=${job} />` : tab === 'req' ? html`<${RequirementsTab} job=${job} />` : html`<${VerifyTab} job=${job} />`}
      </div>
    </div>` : null}
  </${Drawer}>`;
}
