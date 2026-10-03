import { html, useState, useEffect } from '../lib/preact.js';
import { useStore, getState } from '../state/store.js';
import {
  loadDetail, toggleSaved, setTracking, verifyJob, rescoreJob, generateDocument, generateCv, loadDocuments, autoApply, deleteJob, navigate,
} from '../actions.js';
import {
  Button, Badge, ScoreRing, Meter, Skeleton, ErrorBox, Drawer, Icon, Notice, Tabs, Monogram, Select, VERDICT_TONE, Elapsed,
} from '../components/ui.js';
import {
  VERDICT_LABEL, VALIDATION_LABEL, VALIDATION_TONE, CHECK_LABEL, CHECK_STATUS_LABEL, CHECK_STATUS_TONE,
  CONSTRAINT_TONE, CONSTRAINT_LABEL, TRACKING_LABEL, DEFAULT_TRACKING, WORK_MODE_LABEL, DOC_KIND_LABEL,
  fmtDate, relTime, fmtSalary, safeUrl, humanize, experienceText, REACH_LABEL, REACH_TONE,
  COMPANY_VERDICT_LABEL, COMPANY_VERDICT_TONE, COMPETITION_LABEL, EARLY_CAREER_LABEL,
} from '../lib/format.js';
import { genKey } from '../state/domain.js';

function ReachSection({ reach }) {
  if (!reach) return null;
  return html`<section class="reach-box">
    <div class="row gap wrap"><h3 class="sec-title" style=${{ margin: 0 }}>Chance a person actually reads your application</h3>
      <${Badge} tone=${REACH_TONE[reach.level]}>${REACH_LABEL[reach.level]} · ${reach.score}/100</${Badge}></div>
    <p class="muted small">Separate from fit. Public LinkedIn / Naukri posts get hundreds to thousands of applicants —
      a fresh post on the company's own site, a smaller company or a direct email gives you a real chance.</p>
    <ul class="reach-signals">${reach.signals.map((s) => html`<li key=${s.key} class=${s.points > 0 ? 'up' : s.points < 0 ? 'down' : ''}>
      <span class="pts">${s.points > 0 ? `+${s.points}` : s.points}</span><span>${s.detail}</span></li>`)}</ul>
    ${reach.application_email ? html`<${Notice} tone="success">The posting asks for applications at <strong>${reach.application_email}</strong> (found in the job text).
      A short, specific email with your proof of work beats a portal application.</${Notice}>` : null}
  </section>`;
}

export function CompanySection({ c }) {
  if (!c) return null;
  const rv = c.reviews || {};
  const careers = safeUrl(c.careers_url);
  return html`<section class="company-box">
    <div class="row gap wrap"><h3 class="sec-title" style=${{ margin: 0 }}>About ${c.name}</h3>
      <${Badge} tone=${COMPANY_VERDICT_TONE[c.verdict]}>${COMPANY_VERDICT_LABEL[c.verdict] || c.verdict}</${Badge}>
      ${c.competition ? html`<${Badge} tone=${c.competition === 'low' ? 'success' : c.competition === 'very_high' ? 'danger' : 'neutral'}>${COMPETITION_LABEL[c.competition]}</${Badge}>` : null}
      <${Badge} tone=${c.hires_early_career === 'yes' ? 'success' : c.hires_early_career === 'rare' ? 'warning' : 'neutral'}>${EARLY_CAREER_LABEL[c.hires_early_career] || ''}</${Badge}></div>
    ${c.why ? html`<p>${c.why}</p>` : null}
    <div class="facts-grid">
      <div><span class="muted small">What they do</span><div>${c.what_they_do || '—'}</div></div>
      <div><span class="muted small">Real AI work</span><div>${c.ai_work || '—'}</div></div>
      <div><span class="muted small">Size · stage</span><div>${[c.size, humanize(c.stage)].filter((x) => x && x !== 'unknown' && x !== 'Unknown').join(' · ') || 'Unknown'}</div></div>
      <div><span class="muted small">Ratings</span><div>${rv.ambitionbox ? `AmbitionBox ${rv.ambitionbox}${rv.ambitionbox_reviews ? ` (${rv.ambitionbox_reviews} reviews)` : ''}` : ''}
        ${rv.glassdoor ? ` · Glassdoor ${rv.glassdoor}${rv.glassdoor_reviews ? ` (${rv.glassdoor_reviews})` : ''}` : ''}${!rv.ambitionbox && !rv.glassdoor ? 'Not found' : ''}</div></div>
      <div><span class="muted small">Heavy DSA interviews</span><div>${humanize(c.dsa_heavy_interviews) || 'Unknown'}</div></div>
      <div><span class="muted small">Pay signal</span><div>${c.pay_signal || 'Unknown'}</div></div>
    </div>
    ${rv.summary ? html`<div><span class="muted small">What employees say</span><p>${rv.summary}</p></div>` : null}
    ${c.red_flags && c.red_flags.length ? html`<div><span class="muted small">Red flags</span><ul class="bullets bad">${c.red_flags.map((x) => html`<li>${x}</li>`)}</ul></div>` : null}
    <div class="row gap wrap">
      ${careers ? html`<a class="btn btn-sm btn-secondary" href=${careers} target="_blank" rel="noopener noreferrer"><${Icon} name="external" size=${14} /><span>Careers page</span></a>` : null}
      ${(c.sources || []).slice(0, 4).map((u, i) => { const s = safeUrl(u); return s ? html`<a class="small" href=${s} target="_blank" rel="noopener noreferrer">source ${i + 1}</a>` : null; })}
      ${c.researched_on ? html`<span class="muted small">researched ${c.researched_on}</span>` : null}
    </div>
  </section>`;
}

function MatchTab({ job }) {
  const m = job.match;
  if (!m) return html`<${Notice}>This job has not been scored yet.</${Notice}>`;
  return html`<div class="stack">
    ${m.headline ? html`<p class="detail-headline">${m.headline}</p>` : null}
    <${ReachSection} reach=${m.reach} />
    <${CompanySection} c=${job.company_profile} />
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
          <${Meter} value=${c.score} /><div class="muted small" style=${{ marginTop: '6px' }}>${c.detail}</div></div>`)}
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
  const docs = useStore((s) => s.docs.items);
  useEffect(() => { if (getState().docs.status === 'idle') loadDocuments(); }, []);
  const row = (kind) => {
    const g = gen[genKey(job.id, kind)];
    const docId = (g && g.documentId) || (job.documents && job.documents[kind]);
    const latest = (job.document_list || []).find((d) => d.id === docId);
    const busy = g && g.status === 'generating';
    return html`<div class=${`kit-item ${busy ? 'is-busy' : ''}`} key=${kind}>
      <div class="kit-thumb" aria-hidden="true"><div class="sheet"><i></i><i></i><i></i><i></i><i></i></div>${busy ? html`<span class="scan-beam"></span>` : null}</div>
      <div class="grow"><strong>${DOC_KIND_LABEL[kind]}</strong>
        <div class="muted small">${busy ? html`Writing and fact-checking against your profile · <${Elapsed} since=${g.startedAt} />`
          : latest ? `Generated ${relTime(latest.created_at)}${latest.stale ? ' · profile changed since' : ''}${latest.warnings_count ? ` · ${latest.warnings_count} note(s)` : ''}` : 'Tailored to this job, using only facts from your profile.'}</div>
        ${g && g.status === 'failed' ? html`<div class="error-text small" role="alert">${g.error}</div>` : null}
      </div>
      <div class="row gap">
        ${docId ? html`<${Button} size="sm" onClick=${() => navigate(`#/documents/${docId}`)}>Open</${Button}>` : null}
        <${Button} size="sm" variant=${docId ? 'secondary' : 'primary'} icon=${g && g.status === 'failed' ? 'refresh' : 'spark'}
          busy=${busy} onClick=${() => generateDocument(job.id, kind)}>
          ${g && g.status === 'failed' ? 'Retry' : docId ? 'Regenerate' : 'Generate'}</${Button}>
      </div></div>`;
  };
  const cvGen = gen[genKey(null, 'cv')];
  const cvDoc = docs.find((d) => d.kind === 'cv');
  const cvBusy = cvGen && cvGen.status === 'generating';
  const cvId = (cvGen && cvGen.documentId) || (cvDoc && cvDoc.id);
  const cvRow = html`<div class=${`kit-item ${cvBusy ? 'is-busy' : ''}`} key="cv">
    <div class="kit-thumb" aria-hidden="true"><div class="sheet"><i></i><i></i><i></i><i></i><i></i></div>${cvBusy ? html`<span class="scan-beam"></span>` : null}</div>
    <div class="grow"><strong>CV</strong>
      <div class="muted small">${cvBusy ? html`Writing your CV · <${Elapsed} since=${cvGen.startedAt} />` : cvDoc ? `Made ${relTime(cvDoc.created_at)} · your full career story, shared by every application` : 'Your full career story (not job-specific). Some forms ask for it.'}</div>
      ${cvGen && cvGen.status === 'failed' ? html`<div class="error-text small" role="alert">${cvGen.error}</div>` : null}</div>
    <div class="row gap">
      ${cvId ? html`<${Button} size="sm" onClick=${() => navigate(`#/documents/${cvId}`)}>Open</${Button}>` : null}
      <${Button} size="sm" variant=${cvId ? 'secondary' : 'primary'} icon="spark" busy=${cvBusy} onClick=${() => generateCv('')}>${cvId ? 'Regenerate' : 'Generate'}</${Button}>
    </div></div>`;
  return html`<div class="stack"><p class="muted small"><strong>Resume</strong> = one page, tailored to this job. <strong>CV</strong> = your longer, general career story.
    Every AI edit is checked against your profile; anything it cannot back up is rejected. Auto-apply makes any missing ones for you.</p>
    ${row('resume')}${row('cover_letter')}${cvRow}</div>`;
}

const TABS = [
  { key: 'match', label: 'Why this score' }, { key: 'req', label: 'Requirements' },
  { key: 'verify', label: 'Verification' }, { key: 'kit', label: 'Application kit' },
];

/** The job workspace. Used inline (Discover) and inside a drawer (Tracker). */
export function JobDetail({ jobId, onClose }) {
  const entry = useStore((s) => s.details[jobId]);
  const tracking = useStore((s) => (s.meta.data && s.meta.data.tracking_statuses) || DEFAULT_TRACKING);
  const pending = useStore((s) => s.pending);
  const [tab, setTab] = useState('match');
  const job = entry && entry.job;
  if (!entry || (entry.status === 'loading' && !job)) {
    return html`<div class="detail"><div class="detail-top"><div class="row gap"><div class="sk-block sk-ring big"></div>
      <div class="grow"><div class="sk-block" style=${{ width: '30%' }}></div><div class="sk-block" style=${{ width: '60%', height: '22px', marginTop: '10px' }}></div></div></div></div>
      <div class="detail-body"><${Skeleton} lines=${6} /></div></div>`;
  }
  if (entry.status === 'error' && !job) return html`<div class="detail"><div class="detail-body"><${ErrorBox} message=${entry.error} onRetry=${() => loadDetail(jobId)} /></div></div>`;
  const apply = safeUrl(job.apply_url);
  return html`<div class="detail">
    <header class="detail-top">
      <div class="detail-tools">
        <button type="button" class="icon-btn" aria-label="Close" onClick=${onClose}><${Icon} name="x" /></button>
        <div class="row gap">
          <button type="button" class=${`icon-btn save-btn ${job.saved ? 'on' : ''}`} aria-pressed=${job.saved ? 'true' : 'false'}
            aria-label=${job.saved ? 'Unsave job' : 'Save job'} disabled=${!!pending.save[jobId]} onClick=${() => toggleSaved(jobId)}><${Icon} name="star" size=${16} /></button>
          <button type="button" class="icon-btn" aria-label="Remove job" onClick=${() => deleteJob(jobId)}><${Icon} name="trash" size=${16} /></button>
        </div>
      </div>
      <div class="detail-header">
        <${ScoreRing} score=${job.match ? job.match.score : null} verdict=${job.match && job.match.verdict} size=${78} />
        <div class="grow">
          <div class="detail-company"><${Monogram} name=${job.company} size=${22} /> ${job.company} · ${job.location || 'Location not stated'}</div>
          <h2>${job.title}</h2>
          <div class="row gap wrap">
            ${job.match ? html`<${Badge} tone=${VERDICT_TONE[job.match.verdict]}>${VERDICT_LABEL[job.match.verdict]}</${Badge}>` : null}
            <${Badge} tone=${VALIDATION_TONE[job.validation.status]}>${VALIDATION_LABEL[job.validation.status]}</${Badge}>
            ${job.match && job.match.experience ? html`<span class="muted small">${experienceText(job.match.experience)}</span>` : null}
            ${job.posted_at ? html`<span class="muted small">Posted ${fmtDate(job.posted_at)}</span>` : null}
          </div>
        </div>
      </div>
      <div class="action-bar">
        ${apply ? html`<a class="btn btn-primary btn-sm" href=${apply} target="_blank" rel="noopener noreferrer"><${Icon} name="external" size=${15} /><span>Open posting</span></a>` : null}
        <${Select} size="sm" label="Tracking status" tone=${`s-${job.tracking_status}`} value=${job.tracking_status} disabled=${!!pending.track[jobId]}
          onChange=${(v) => setTracking(jobId, v)} options=${tracking.map((t) => [t, TRACKING_LABEL[t] || humanize(t)])} />
        <${Button} size="sm" icon="refresh" busy=${!!pending.verify[jobId]} onClick=${() => verifyJob(jobId)}>Re-verify</${Button}>
        <${Button} size="sm" icon="bolt" busy=${!!pending.rescore[jobId]} onClick=${() => rescoreJob(jobId)}>Re-score</${Button}>
        <${Button} size="sm" icon="globe" busy=${!!pending.apply[jobId]} onClick=${() => autoApply(jobId)}>Auto-apply</${Button}>
      </div>
      ${job.match_stale ? html`<${Notice} tone="warning">Your profile changed since this job was scored.
        <${Button} size="sm" busy=${!!pending.rescore[jobId]} onClick=${() => rescoreJob(jobId)}>Re-score now</${Button}></${Notice}>` : null}
      <${Tabs} label="Job sections" value=${tab} onChange=${setTab} tabs=${TABS} size="sm" />
    </header>
    <div class="detail-body scroll" role="tabpanel" key=${tab}>
      ${tab === 'match' ? html`<${MatchTab} job=${job} />` : tab === 'req' ? html`<${RequirementsTab} job=${job} />`
        : tab === 'verify' ? html`<${VerifyTab} job=${job} />` : html`<${DocActions} job=${job} />`}
    </div>
  </div>`;
}

export function JobDetailDrawer({ jobId, onClose }) {
  return html`<${Drawer} onClose=${onClose} label="Job details"><${JobDetail} jobId=${jobId} onClose=${onClose} /></${Drawer}>`;
}
