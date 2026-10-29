import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { generateCv, loadDocuments, loadDocument, updateDocument, deleteDocument, saveDocumentStyle } from '../actions.js';
import { StylePicker, ChatDock, SnapFilter, useStyles } from './docchat.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Notice, PageHead, Popover, Tabs, ComboInput } from '../components/ui.js';
import { DOC_KIND_LABEL, relTime, safeUrl } from '../lib/format.js';
import { api } from '../lib/api.js';
import { genKey } from '../state/domain.js';

const ext = (l) => { const u = safeUrl(l.url); return u ? html`<a href=${u} target="_blank" rel="noopener noreferrer">${l.text || l.label}</a>` : null; };
const linkRow = (links) => (links && links.length ? html`<span class="paper-links">${links.map((l, i) => html`${i ? ' · ' : ''}${ext(l)}`)}</span>` : null);

function ResumePreview({ c, style = 'classic' }) {
  const il = c.item_links || {};
  return html`<article class="paper" data-style=${style}>
    <header class="paper-head"><h2 data-p="header.name">${c.header.name}</h2>${c.headline ? html`<div class="paper-sub" data-p="headline">${c.headline}</div>` : null}
      <div class="paper-contact">${[c.header.email, c.header.phone, c.header.location].filter(Boolean).join(' · ')}
        ${c.header.links.length ? html`<br />${linkRow(c.header.links)}` : null}</div></header>
    ${c.summary ? html`<section><h3>Summary</h3><p data-p="summary">${c.summary}</p></section>` : null}
    ${c.skills.length ? html`<section><h3>Skills</h3>${c.skills.map((g, i) => html`<p data-p=${`skills.${i}`}><strong>${g.category}:</strong> ${g.items.join(', ')}</p>`)}</section>` : null}
    ${c.experience.length ? html`<section><h3>Experience</h3>${c.experience.map((e, i) => html`<div class="paper-item">
      <div class="row space"><strong>${e.role}${e.company ? ` — ${e.company}` : ''}</strong><span class="muted small">${[e.start, e.end].filter(Boolean).join(' – ')}</span></div>
      <ul>${e.bullets.map((b, j) => html`<li data-p=${`experience.${i}.bullets.${j}`}>${b}</li>`)}</ul></div>`)}</section>` : null}
    ${c.projects.length ? html`<section><h3>Projects</h3>${c.projects.map((p, i) => html`<div class="paper-item">
      <div class="row space"><span><strong>${p.title}</strong>${p.technologies.length ? html` <span class="muted small">· ${p.technologies.join(', ')}</span>` : null}</span>
        ${linkRow(p.links && p.links.length ? p.links : p.url ? [{ url: p.url, label: 'Link' }] : [])}</div><p data-p=${`projects.${i}.description`}>${p.description}</p></div>`)}</section>` : null}
    ${c.education.length ? html`<section><h3>Education</h3>${c.education.map((e) => html`<p><strong>${e.degree}</strong>${e.institution ? ` — ${e.institution}` : ''} <span class="muted small">${[e.start, e.end].filter(Boolean).join(' – ')}${e.grade ? ` · ${e.grade}` : ''}</span></p>`)}</section>` : null}
    ${['certifications', 'achievements', 'competitions', 'languages'].map((k) => c[k] && c[k].length ? html`<section><h3>${k[0].toUpperCase() + k.slice(1)}</h3><ul>${c[k].map((x, i) => html`<li data-p=${`${k}.${i}`}>${x}${il[x] ? html` · ${linkRow(il[x])}` : null}</li>`)}</ul></section>` : null)}
  </article>`;
}

function LetterPreview({ c, style = 'classic' }) {
  return html`<article class="paper" data-style=${style}><p data-p="greeting">${c.greeting}</p>${c.paragraphs.map((p, i) => html`<p data-p=${`paragraphs.${i}`}>${p}</p>`)}<p data-p="closing">${c.closing}</p><p>${c.signature}</p></article>`;
}

const clone = (value) => JSON.parse(JSON.stringify(value));
const lines = (value) => (value || []).join('\n');
const fromLines = (value) => value.split('\n').map((x) => x.trim()).filter(Boolean);

function JsonField({ label, value, onChange }) {
  const [text, setText] = useState(() => JSON.stringify(value || [], null, 2));
  const [error, setError] = useState('');
  return html`<label class="field"><span class="field-label">${label}</span>
    <textarea class="input" rows="7" value=${text} onInput=${(e) => {
      setText(e.currentTarget.value);
      try { onChange(JSON.parse(e.currentTarget.value)); setError(''); } catch { setError('Use valid JSON for this section.'); }
    }}></textarea>
    ${error ? html`<span class="error-text small">${error}</span>` : null}</label>`;
}

function LinkEditor({ links = [], onChange }) {
  const update = (index, key, next) => {
    const nextLinks = links.map((link, i) => {
      if (i !== index) return link;
      return key === 'url' ? { ...link, url: next } : { ...link, label: next, text: next };
    });
    onChange(nextLinks);
  };
  const remove = (index) => onChange(links.filter((_, i) => i !== index));
  return html`<div class="field">
    <span class="field-label">Links</span>
    <div class="stack">
      ${links.map((link, i) => html`<div class="link-row" key=${i}>
        <input class="input link-label" aria-label=${`Link ${i + 1} label`} placeholder="Label" value=${link.label || ''}
          onInput=${(e) => update(i, 'label', e.currentTarget.value)} />
        <input class="input" aria-label=${`Link ${i + 1} URL`} placeholder="https://…" value=${link.url || ''}
          onInput=${(e) => update(i, 'url', e.currentTarget.value)} />
        <button type="button" class="icon-btn" aria-label=${`Remove link ${i + 1}`} onClick=${() => remove(i)}>
          <${Icon} name="trash" size=${15} />
        </button>
      </div>`)}
      <button type="button" class="btn btn-secondary btn-sm" onClick=${() => onChange([...links, { label: '', url: '', text: '' }])}>
        Add link
      </button>
    </div>
    <span class="muted small">Edit the label and destination shown in the resume.</span>
  </div>`;
}

function LinkedItemsEditor({ label, items = [], itemLinks = {}, onChange }) {
  const updateItem = (index, nextText) => {
    const previous = items[index] || '';
    const nextItems = items.map((item, i) => i === index ? nextText : item);
    const nextLinks = { ...itemLinks };
    if (previous !== nextText && Object.prototype.hasOwnProperty.call(nextLinks, previous)) {
      nextLinks[nextText] = nextLinks[previous];
      delete nextLinks[previous];
    }
    onChange(nextItems, nextLinks);
  };
  const updateLinks = (item, links) => onChange(items, { ...itemLinks, [item]: links });
  const removeItem = (index) => {
    const item = items[index];
    const nextLinks = { ...itemLinks };
    delete nextLinks[item];
    onChange(items.filter((_, i) => i !== index), nextLinks);
  };
  return html`<div class="field">
    <span class="field-label">${label}</span>
    <div class="stack">
      ${items.map((item, i) => html`<div class="linked-item" key=${`${item}-${i}`}>
        <div class="row gap">
          <input class="input" value=${item} aria-label=${`${label} ${i + 1}`}
            onInput=${(e) => updateItem(i, e.currentTarget.value)} />
          <button type="button" class="icon-btn" aria-label=${`Remove ${label.toLowerCase()} ${i + 1}`} onClick=${() => removeItem(i)}>
            <${Icon} name="trash" size=${15} />
          </button>
        </div>
        <${LinkEditor} links=${itemLinks[item] || []} onChange=${(links) => updateLinks(item, links)} />
      </div>`)}
      <button type="button" class="btn btn-secondary btn-sm" onClick=${() => onChange([...items, ''], itemLinks)}>
        Add ${label.toLowerCase().replace(/s$/, '')}
      </button>
    </div>
    <span class="muted small">Attach credential or evidence links to each item.</span>
  </div>`;
}

function DocumentEditor({ doc, value, onChange }) {
  const set = (key, next) => onChange({ ...value, [key]: next });
  const setHeader = (key, next) => set('header', { ...value.header, [key]: next });
  if (doc.kind === 'cover_letter') return html`<div class="editor-form">
    ${[['greeting', 'Greeting'], ['closing', 'Closing'], ['signature', 'Signature']].map(([k, label]) => html`
      <label class="field"><span class="field-label">${label}</span><input class="input" value=${value[k] || ''} onInput=${(e) => set(k, e.currentTarget.value)} /></label>`)}
    <label class="field"><span class="field-label">Paragraphs</span><textarea class="input" rows="12" value=${lines(value.paragraphs)} onInput=${(e) => set('paragraphs', fromLines(e.currentTarget.value))}></textarea><span class="muted small">One paragraph per line.</span></label>
  </div>`;
  return html`<div class="editor-form">
    <div class="editor-grid">${[['name', 'Name'], ['email', 'Email'], ['phone', 'Phone'], ['location', 'Location']].map(([k, label]) => html`
      <label class="field"><span class="field-label">${label}</span><input class="input" value=${value.header?.[k] || ''} onInput=${(e) => setHeader(k, e.currentTarget.value)} /></label>`)}</div>
    <label class="field"><span class="field-label">Headline</span><input class="input" value=${value.headline || ''} onInput=${(e) => set('headline', e.currentTarget.value)} /></label>
    <${LinkEditor} links=${value.header?.links || []} onChange=${(next) => setHeader('links', next)} />

    <label class="field"><span class="field-label">Summary</span><textarea class="input" rows="6" value=${value.summary || ''} onInput=${(e) => set('summary', e.currentTarget.value)}></textarea></label>
    <${LinkedItemsEditor} label="Certifications" items=${value.certifications} itemLinks=${value.item_links || {}}
      onChange=${(items, itemLinks) => onChange({ ...value, certifications: items, item_links: itemLinks })} />
    <${LinkedItemsEditor} label="Achievements" items=${value.achievements} itemLinks=${value.item_links || {}}
      onChange=${(items, itemLinks) => onChange({ ...value, achievements: items, item_links: itemLinks })} />
    <${LinkedItemsEditor} label="Competitions" items=${value.competitions} itemLinks=${value.item_links || {}}
      onChange=${(items, itemLinks) => onChange({ ...value, competitions: items, item_links: itemLinks })} />
    <${LinkedItemsEditor} label="Languages" items=${value.languages} itemLinks=${value.item_links || {}}
      onChange=${(items, itemLinks) => onChange({ ...value, languages: items, item_links: itemLinks })} />
    <${JsonField} label="Skills (JSON)" value=${value.skills} onChange=${(v) => set('skills', v)} />
    <${JsonField} label="Experience (JSON)" value=${value.experience} onChange=${(v) => set('experience', v)} />
    <${JsonField} label="Projects (JSON)" value=${value.projects} onChange=${(v) => set('projects', v)} />
    <${JsonField} label="Education (JSON)" value=${value.education} onChange=${(v) => set('education', v)} />
  </div>`;
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
  const styles = useStyles();
  const [tab, setTab] = useState('preview');
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [style, setStyle] = useState(null);            // the style being looked at (instant); the saved one follows in the background
  const [styleBusy, setStyleBusy] = useState(false);
  const [undo, setUndo] = useState([]);                // earlier drafts, for "Undo last"
  const dirtyRef = useRef(false);
  const paperRef = useRef(null);
  const styleTimer = useRef(0);
  useEffect(() => { loadDocument(docId); }, [docId]);
  useEffect(() => { if (entry?.doc && !dirtyRef.current) setDraft(clone(entry.doc.content)); }, [entry?.doc]);
  useEffect(() => { if (entry?.doc && style === null) setStyle(entry.doc.style || 'classic'); }, [entry?.doc]);
  useEffect(() => () => clearTimeout(styleTimer.current), []);
  if (!entry || entry.status === 'loading') return html`<div class="pane-pad"><${Skeleton} lines=${10} /></div>`;
  if (entry.status === 'error') return html`<div class="pane-pad"><${ErrorBox} message=${entry.error} onRetry=${() => loadDocument(docId)} /></div>`;
  const d = entry.doc;
  const editing = tab === 'edit';
  const dirty = !!draft && JSON.stringify(draft) !== JSON.stringify(d.content);
  dirtyRef.current = dirty;
  const shown = style || d.style || 'classic';
  const save = async () => {
    setSaving(true);
    const updated = await updateDocument(docId, draft);
    setSaving(false);
    if (updated) { dirtyRef.current = false; setDraft(clone(updated.content)); setUndo([]); setTab('preview'); }
  };
  const pickStyle = (id) => {
    setStyle(id);                                     // the preview changes right now: it is only CSS
    clearTimeout(styleTimer.current);
    styleTimer.current = setTimeout(async () => {     // the stored PDF follows once the user stops clicking
      setStyleBusy(true);
      await saveDocumentStyle(docId, id);
      setStyleBusy(false);
    }, 500);
  };
  const propose = (content) => { setUndo((u) => [...u.slice(-9), draft]); setDraft(content); };
  const undoLast = () => { setUndo((u) => { if (!u.length) return u; setDraft(u[u.length - 1]); return u.slice(0, -1); }); };
  const body = draft || d.content;
  return html`<div class="detail">
    <header class="detail-top doc-top">
      <div class="row space wrap">
        <div class="grow"><span class="doc-kind">${DOC_KIND_LABEL[d.kind]}</span><h2>${d.title}</h2>
          <div class="muted small">${relTime(d.created_at)} · ${d.page_count} page(s)
            ${d.job ? html` · for <a href=${`#/discover/job/${d.job_id}`}>${d.job.title} @ ${d.job.company}</a>` : ''}</div></div>
        <div class="row gap">${d.has_pdf ? html`<a class="btn btn-primary btn-sm" href=${api.documentPdfUrl(d.id, shown === (d.style || 'classic') ? '' : shown)} download title="Downloads the PDF in the selected style"><${Icon} name="download" size=${15} /><span>Download PDF</span></a>` : null}
          <button type="button" class="btn btn-secondary btn-sm" onClick=${() => { setDraft(clone(d.content)); dirtyRef.current = false; setUndo([]); setTab(editing ? 'preview' : 'edit'); }}>${editing ? 'Cancel' : 'Edit'}</button>
          ${editing || dirty ? html`<button type="button" class="btn btn-primary btn-sm" disabled=${!dirty || saving} onClick=${save}>${saving ? 'Saving…' : 'Save changes'}</button>` : null}
          <button type="button" class="icon-btn" aria-label="Delete document" onClick=${() => deleteDocument(d.id)}><${Icon} name="trash" size=${16} /></button></div>
      </div>
      <${StylePicker} styles=${styles} value=${shown} onChange=${pickStyle} busy=${styleBusy} />
      ${d.manually_edited ? html`<${Notice} tone="info">Manually edited · saved ${relTime(d.updated_at)}</${Notice}>` : null}
      ${dirty && !editing ? html`<${Notice} tone="warning">You have unsaved changes. “Save changes” keeps them and updates the PDF; “Edit” → “Cancel” discards them.</${Notice}>` : null}
      ${d.stale ? html`<${Notice} tone="warning">Your profile changed after this was generated. Regenerate it to include the latest information.</${Notice}>` : null}
      <${Tabs} size="sm" label="Document sections" value=${tab} onChange=${setTab}
        tabs=${[{ key: 'preview', label: 'Preview' }, { key: 'edit', label: 'Edit' }, { key: 'prov', label: 'What changed', count: d.provenance.rewrites.length }]} />
    </header>
    <div class="detail-main">
    <div class="detail-body scroll paper-stage" key=${tab} ref=${paperRef}>
      <${SnapFilter} />
      ${tab === 'preview' ? (d.kind === 'cover_letter' ? html`<${LetterPreview} c=${body} style=${shown} />` : html`<${ResumePreview} c=${body} style=${shown} />`) : tab === 'edit' ? html`<${DocumentEditor} key=${`${d.id}:${d.updated_at}`} doc=${d} value=${draft || d.content} onChange=${setDraft} />` : html`<${Provenance} doc=${d} />`}
    </div>
    ${tab === 'preview' ? html`<${ChatDock} doc=${d} draft=${body} onProposal=${propose} onUndo=${undoLast} canUndo=${undo.length > 0}
      getPaper=${() => paperRef.current && paperRef.current.querySelector('.paper')} />` : null}
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
          <${ComboInput} label="Optional focus" value=${focus} placeholder="Whole career" options=${tracks} onChange=${setFocus} /></label>
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
