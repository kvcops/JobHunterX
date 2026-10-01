import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { generateCv, loadDocuments, loadDocument, deleteDocument } from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Notice, PageHead, Popover, Tabs } from '../components/ui.js';
import { DOC_KIND_LABEL, relTime, safeUrl } from '../lib/format.js';
import { api } from '../lib/api.js';
import { genKey } from '../state/domain.js';

function ResumePreview({ c }) {
  return html`<article class="paper">
    <header class="paper-head"><h2>${c.header.name}</h2>${c.headline ? html`<div class="paper-sub">${c.headline}</div>` : null}
      <div class="paper-contact">${[c.header.email, c.header.phone, c.header.location].filter(Boolean).join(' · ')}
        ${c.header.links.map((l) => { const u = safeUrl(l.url); return u ? html` · <a href=${u} target="_blank" rel="noopener noreferrer">${l.label}</a>` : null; })}</div></header>
    ${c.summary ? html`<section><h3>Summary</h3><p>${c.summary}</p></section>` : null}
    ${c.skills.length ? html`<section><h3>Skills</h3>${c.skills.map((g) => html`<p><strong>${g.category}:</strong> ${g.items.join(', ')}</p>`)}</section>` : null}
    ${c.experience.length ? html`<section><h3>Experience</h3>${c.experience.map((e) => html`<div class="paper-item">
      <div class="row space"><strong>${e.role}${e.company ? ` — ${e.company}` : ''}</strong><span class="muted small">${[e.start, e.end].filter(Boolean).join(' – ')}</span></div>
      <ul>${e.bullets.map((b) => html`<li>${b}</li>`)}</ul></div>`)}</section>` : null}
    ${c.projects.length ? html`<section><h3>Projects</h3>${c.projects.map((p) => html`<div class="paper-item"><strong>${p.title}</strong>
      ${p.technologies.length ? html` <span class="muted small">· ${p.technologies.join(', ')}</span>` : null}<p>${p.description}</p></div>`)}</section>` : null}
    ${c.education.length ? html`<section><h3>Education</h3>${c.education.map((e) => html`<p><strong>${e.degree}</strong>${e.institution ? ` — ${e.institution}` : ''} <span class="muted small">${[e.start, e.end].filter(Boolean).join(' – ')}${e.grade ? ` · ${e.grade}` : ''}</span></p>`)}</section>` : null}
    ${['certifications', 'achievements', 'competitions', 'languages'].map((k) => c[k] && c[k].length ? html`<section><h3>${k[0].toUpperCase() + k.slice(1)}</h3><ul>${c[k].map((x) => html`<li>${x}</li>`)}</ul></section>` : null)}
  </article>`;
}

function LetterPreview({ c }) {
  return html`<article class="paper"><p>${c.greeting}</p>${c.paragraphs.map((p) => html`<p>${p}</p>`)}<p>${c.closing}<br />${c.signature}</p></article>`;
}

function Provenance({ doc }) {
  const p = doc.provenance;
  const [all, setAll] = useState(false);
  const rewrites = all ? p.rewrites : p.rewrites.slice(0, 6);
  return html`<section class="provenance">
    <p class="muted small">Every AI edit is fact-checked against your profile. Edits that add numbers, tools or claims you never wrote are rejected and your original text is kept.</p>
    ${p.warnings.map((w) => html`<${Notice} tone="warning">${w}</${Notice}>`)}
    ${doc.kind === 'resume' && (p.omitted_projects.length || p.omitted_experience.length) ? html`<p class="muted small">Left out to stay on one page (less relevant to this job): ${p.omitted_projects.length} project(s).</p>` : null}
    ${rewrites.length ? html`<ul class="rewrites">${rewrites.map((r) => html`<li class=${r.accepted ? 'ok' : 'rejected'}>
      <${Badge} tone=${r.accepted ? 'success' : 'danger'}>${r.accepted ? 'Accepted' : 'Rejected'}</${Badge}> <span class="muted small">${r.section}</span>
      ${r.original ? html`<div class="diff-old">${r.original}</div>` : null}<div class="diff-new">${r.rewritten}</div>
      ${r.reason ? html`<div class="muted small">${r.reason}</div>` : null}</li>`)}</ul>` : html`<p class="muted">No AI rewrites — your original text was used.</p>`}
    ${p.rewrites.length > 6 ? html`<button type="button" class="link-btn" onClick=${() => setAll(!all)}>${all ? 'Show fewer' : `Show all ${p.rewrites.length}`}</button>` : null}
    <p class="muted small">${p.llm_model ? `Written with ${p.llm_model} · ${p.llm_calls} AI call(s)` : 'No AI used'}</p>
  </section>`;
}

function DocumentDetail({ docId }) {
  const entry = useStore((s) => s.docDetails[docId]);
  const [tab, setTab] = useState('preview');
  useEffect(() => { loadDocument(docId); }, [docId]);
  if (!entry || entry.status === 'loading') return html`<div class="pane-pad"><${Skeleton} lines=${10} /></div>`;
  if (entry.status === 'error') return html`<div class="pane-pad"><${ErrorBox} message=${entry.error} onRetry=${() => loadDocument(docId)} /></div>`;
  const d = entry.doc;
  return html`<div class="detail">
    <header class="detail-top doc-top">
      <div class="row space wrap">
        <div class="grow"><span class="doc-kind">${DOC_KIND_LABEL[d.kind]}</span><h2>${d.title}</h2>
          <div class="muted small">${relTime(d.created_at)} · ${d.page_count} page(s)
            ${d.job ? html` · for <a href=${`#/discover/job/${d.job_id}`}>${d.job.title} @ ${d.job.company}</a>` : ''}</div></div>
        <div class="row gap">${d.has_pdf ? html`<a class="btn btn-primary btn-sm" href=${api.documentPdfUrl(d.id)} download><${Icon} name="download" size=${15} /><span>Download PDF</span></a>` : null}
          <button type="button" class="icon-btn" aria-label="Delete document" onClick=${() => deleteDocument(d.id)}><${Icon} name="trash" size=${16} /></button></div>
      </div>
      ${d.stale ? html`<${Notice} tone="warning">Your profile changed after this was generated. Regenerate it to include the latest information.</${Notice}>` : null}
      <${Tabs} size="sm" label="Document sections" value=${tab} onChange=${setTab}
        tabs=${[{ key: 'preview', label: 'Preview' }, { key: 'prov', label: 'What changed', count: d.provenance.rewrites.length }]} />
    </header>
    <div class="detail-body scroll paper-stage" key=${tab}>
      ${tab === 'preview' ? (d.kind === 'cover_letter' ? html`<${LetterPreview} c=${d.content} />` : html`<${ResumePreview} c=${d.content} />`) : html`<${Provenance} doc=${d} />`}
    </div>
  </div>`;
}

function CvGenerator() {
  const g = useStore((s) => s.gen[genKey(null, 'cv')]);
  const tracks = useStore((s) => (s.profile.envelope && s.profile.envelope.snapshot ? s.profile.envelope.snapshot.role_families.map((f) => f.label) : []));
  const [focus, setFocus] = useState('');
  const [open, setOpen] = useState(false);
  const busy = g && g.status === 'generating';
  return html`<div class="pop-anchor">
    <${Button} variant="primary" icon="spark" busy=${busy} data-popover-anchor onClick=${() => setOpen(!open)}>${busy ? 'Writing CV…' : 'Generate CV'}</${Button}>
    <${Popover} open=${open} onClose=${() => setOpen(false)} label="Generate CV" align="right">
      <div class="stack" style=${{ gap: '12px', width: '300px' }}>
        <div><strong>Comprehensive CV</strong><p class="muted small">Your full career on multiple pages — every role, project and achievement. Not tailored to one job.</p></div>
        <label class="field"><span class="field-label">Optional focus</span>
          <input class="input" list="cv-tracks" value=${focus} placeholder="Whole career" onInput=${(e) => setFocus(e.currentTarget.value)} />
          <datalist id="cv-tracks">${tracks.map((t) => html`<option value=${t} />`)}</datalist></label>
        ${g && g.status === 'failed' ? html`<div class="error-text small" role="alert">${g.error}</div>` : null}
        <${Button} variant="primary" icon=${g && g.status === 'failed' ? 'refresh' : 'spark'} busy=${busy} onClick=${() => { setOpen(false); generateCv(focus.trim()); }}>
          ${g && g.status === 'failed' ? 'Retry' : 'Generate CV'}</${Button}>
      </div>
    </${Popover}>
  </div>`;
}

export function DocumentsView() {
  const docs = useStore((s) => s.docs);
  const route = useStore((s) => s.route);
  const selected = route.docId || (docs.items[0] && docs.items[0].id);
  const groups = ['resume', 'cv', 'cover_letter'].map((k) => [k, docs.items.filter((d) => d.kind === k)]);
  return html`<div class="view view-documents">
    <${PageHead} title=${html`Documents, <span class="serif">fact-checked</span>`}
      sub="Tailored resumes and cover letters per job, plus a full CV — nothing invented." actions=${html`<${CvGenerator} />`} />
    <div class="split split-docs">
      <section class="pane card" aria-label="Document library">
        <div class="scroll pane-pad doc-library">
          ${docs.status === 'error' ? html`<${ErrorBox} message=${docs.error} onRetry=${loadDocuments} />` : null}
          ${docs.status === 'loading' ? html`<${Skeleton} rows=${4} />` : null}
          ${docs.status !== 'loading' && !docs.items.length ? html`<${EmptyState} icon="doc" title="No documents yet">
            Open a job and use its Application kit, or generate your CV.</${EmptyState}>` : null}
          ${groups.map(([kind, items]) => items.length ? html`<div key=${kind} class="doc-group"><div class="sec-title">${DOC_KIND_LABEL[kind]}s · ${items.length}</div>
            ${items.map((d, i) => html`<a class=${`doc-row ${selected === d.id ? 'is-selected' : ''}`} style=${{ '--i': i }} href=${`#/documents/${d.id}`} key=${d.id}
                aria-current=${selected === d.id ? 'true' : undefined}>
              <div class="doc-mini" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
              <div class="grow"><strong>${d.job ? d.job.title : d.title}</strong>
                <span class="muted small">${d.job ? d.job.company : d.focus || 'Whole career'} · ${relTime(d.created_at)}</span></div>
              ${d.stale ? html`<${Badge} tone="warning">Stale</${Badge}>` : null}
            </a>`)}</div>` : null)}
        </div>
      </section>
      <section class="pane card" aria-label="Document preview">
        ${selected ? html`<${DocumentDetail} key=${selected} docId=${selected} />`
          : html`<div class="pane-center"><${EmptyState} icon="spark" title="Your documents appear here">Each one shows the final text and every AI edit the fact-checker accepted or rejected.</${EmptyState}></div>`}
      </section>
    </div>
  </div>`;
}
