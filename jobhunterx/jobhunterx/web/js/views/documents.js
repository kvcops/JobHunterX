import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { generateCv, generateCustomResume, loadDocuments, loadDocument, updateDocument, deleteDocument, saveDocumentStyle } from '../actions.js';
import { StylePicker, ChatDock, SnapFilter, useStyles } from './docchat.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Notice, PageHead, Popover, Portal, Tabs, ComboInput, useFocusTrap } from '../components/ui.js';
import { DOC_KIND_LABEL, relTime, safeUrl } from '../lib/format.js';
import { ResumePaper, LetterPaper, EditToolbar, clone, commitValue, commitActive, insertAt, removeAt, setPath, focusLater, fitSummary } from './doceditor.js';
import { api } from '../lib/api.js';
import { genKey } from '../state/domain.js';

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

function TargetPanel({ t }) {
  const kw = t.keywords || [];
  const hit = new Set(t.matched || []);
  const missing = kw.filter((k) => !hit.has(k));
  return html`<div class="target-panel">
    <div class="row space wrap"><span><span class="muted small">Tailored to</span> <strong>${t.title}</strong>${t.company ? html` <span class="muted">@ ${t.company}</span>` : null}
      ${safeUrl(t.url) ? html` · <a href=${safeUrl(t.url)} target="_blank" rel="noopener noreferrer" class="small">posting</a>` : null}</span>
      ${kw.length ? html`<${Badge} tone=${hit.size / kw.length >= 0.7 ? 'success' : hit.size / kw.length >= 0.4 ? 'warning' : 'danger'}>${hit.size}/${kw.length} job keywords</${Badge}>` : null}</div>
    ${missing.length ? html`<p class="muted small">Not on the page yet: ${missing.map((k, i) => html`${i ? ', ' : ''}<span class="kw-miss">${k}</span>`)}. Add one only where you really used it.</p>` : null}
  </div>`;
}

function DocumentDetail({ docId }) {
  const entry = useStore((s) => s.docDetails[docId]);
  const styles = useStyles();
  const [tab, setTab] = useState('page');
  const [draft, setDraft] = useState(null);
  const [clean, setClean] = useState(false);           // "clean view": the page without editing affordances
  const [style, setStyle] = useState(null);            // the style being looked at (instant); the saved one follows in the background
  const [styleBusy, setStyleBusy] = useState(false);
  const [undo, setUndo] = useState([]);                // earlier drafts, for "Undo"
  const [save, setSave] = useState({ state: 'idle' }); // idle | pending | saving | saved | failed
  const draftRef = useRef(null);
  const seq = useRef(0);                               // bumps on every local change: a slow save never overwrites newer typing
  const unsaved = useRef(false);                       // a change the server hasn't stored yet (Download waits for it)
  const timer = useRef(0);
  const paperRef = useRef(null);
  const styleTimer = useRef(0);
  useEffect(() => { loadDocument(docId); }, [docId]);
  useEffect(() => { if (entry?.doc && draftRef.current === null) { draftRef.current = clone(entry.doc.content); setDraft(draftRef.current); } }, [entry?.doc]);
  useEffect(() => { if (entry?.doc && style === null) setStyle(entry.doc.style || 'classic'); }, [entry?.doc]);
  useEffect(() => () => { clearTimeout(styleTimer.current); clearTimeout(timer.current); }, []);
  if (!entry || entry.status === 'loading') return html`<div class="pane-pad"><${Skeleton} lines=${10} /></div>`;
  if (entry.status === 'error') return html`<div class="pane-pad"><${ErrorBox} message=${entry.error} onRetry=${() => loadDocument(docId)} /></div>`;
  const d = entry.doc;
  const shown = style || d.style || 'classic';   // d.style is already normalised by the server
  const body = draft || d.content;

  const flush = async () => {
    clearTimeout(timer.current);
    const mine = seq.current;
    setSave({ state: 'saving' });
    const updated = await updateDocument(docId, draftRef.current, { quiet: true });
    if (!updated) { setSave({ state: 'failed' }); return false; }
    if (mine === seq.current) { unsaved.current = false; draftRef.current = clone(updated.content); setDraft(draftRef.current); setSave({ state: 'saved' }); }
    return true;
  };
  const change = (next, { now = false } = {}) => {
    setUndo((u) => [...u.slice(-29), draftRef.current]);
    draftRef.current = next;
    seq.current += 1;
    unsaved.current = true;
    setDraft(next);
    setSave({ state: 'pending' });
    clearTimeout(timer.current);
    if (now) return flush();
    timer.current = setTimeout(flush, 1200);
    return null;
  };
  const ed = {
    value: body,
    editing: !clean && tab === 'page',
    commit: (path, v) => change(commitValue(draftRef.current, path, v)),
    insert: (listPath, index, value, focusPath) => { focusLater(focusPath || `${listPath}.${index}`); change(insertAt(draftRef.current, listPath, index, value)); },
    remove: (listPath, index, focusPath) => { if (focusPath) focusLater(focusPath); change(removeAt(draftRef.current, listPath, index)); },
    undo: () => {
      if (!undo.length) return;
      const prev = undo[undo.length - 1];
      setUndo((u) => u.slice(0, -1));
      draftRef.current = prev;
      seq.current += 1;
      unsaved.current = true;
      setDraft(prev);
      setSave({ state: 'pending' });
      clearTimeout(timer.current);
      timer.current = setTimeout(flush, 300);
    },
    canUndo: undo.length > 0,
    askLink: () => {},
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
  // AI edits (chat) are saved at once, so the stored PDF (and Download) matches what the page shows.
  const propose = (content) => change(content, { now: true });
  const hidden = d.kind === 'resume' ? fitSummary(body, d.fit) : '';
  const status = { pending: 'Unsaved…', saving: 'Saving and updating the PDF…', failed: 'Not saved — check your connection',
    saved: `Saved · ${d.page_count} page${d.page_count === 1 ? '' : 's'}`, idle: d.manually_edited ? `Edited ${relTime(d.updated_at)}` : 'Click any text to edit it' }[save.state];
  const isLetter = d.kind === 'cover_letter';
  return html`<div class="detail">
    <header class="detail-top doc-top">
      <div class="row space wrap">
        <div class="grow"><span class="doc-kind">${DOC_KIND_LABEL[d.kind]}</span><h2>${d.title}</h2>
          <div class="muted small">${relTime(d.created_at)} · ${d.page_count} page(s)
            ${d.job && d.job_id ? html` · for <a href=${`#/discover/job/${d.job_id}`}>${d.job.title} @ ${d.job.company}</a>` : ''}</div></div>
        <div class="row gap">
          <button type="button" class=${`btn btn-secondary btn-sm ${clean ? 'is-on' : ''}`} aria-pressed=${clean} title="See the page without editing marks"
            onClick=${() => setClean(!clean)}><${Icon} name="eye" size=${15} /><span>${clean ? 'Edit on page' : 'Clean view'}</span></button>
          ${d.has_pdf ? html`<a class=${`btn btn-primary btn-sm ${save.state === 'saving' || save.state === 'pending' ? 'is-busy' : ''}`}
            href=${api.documentPdfUrl(d.id, shown === (d.style || 'classic') ? '' : shown)} download
            onClick=${async (e) => { commitActive(); if (unsaved.current) { e.preventDefault(); if (await flush()) window.location.href = api.documentPdfUrl(d.id, shown === (d.style || 'classic') ? '' : shown); } }}
            title="Downloads the PDF in the selected style"><${Icon} name="download" size=${15} /><span>Download PDF</span></a>` : null}
          <button type="button" class="icon-btn" aria-label="Delete document" onClick=${() => deleteDocument(d.id)}><${Icon} name="trash" size=${16} /></button></div>
      </div>
      <${StylePicker} styles=${styles} value=${shown} onChange=${pickStyle} busy=${styleBusy} />
      ${d.target ? html`<${TargetPanel} t=${d.target} />` : null}
      ${d.stale ? html`<${Notice} tone="warning">Your profile changed after this was generated. Regenerate it to include the latest information.</${Notice}>` : null}
      <${Tabs} size="sm" label="Document sections" value=${tab} onChange=${setTab}
        tabs=${[{ key: 'page', label: 'Page' }, { key: 'prov', label: 'What changed', count: d.provenance.rewrites.length }]} />
    </header>
    <div class="detail-main">
    <div class="detail-body scroll paper-stage" key=${tab} ref=${paperRef}>
      <${SnapFilter} />
      ${tab === 'page' ? html`
        ${ed.editing ? html`<${EditToolbar} ed=${ed} layout=${body.layout} canLayout=${!isLetter} status=${status}
          onLayout=${(v) => { if (v !== body.layout) change(setPath(draftRef.current, 'layout', v), { now: true }); }} />` : null}
        ${hidden ? html`<div class="fit-note" role="status"><${Icon} name="info" size=${14} /> To stay on one page the PDF leaves out ${hidden} (faded below). Shorten a line or remove something to bring them back.</div>` : null}
        ${isLetter ? html`<${LetterPaper} ed=${ed} style=${shown} />` : html`<${ResumePaper} ed=${ed} style=${shown} fit=${d.fit} kind=${d.kind} />`}`
        : html`<${Provenance} doc=${d} />`}
    </div>
    ${tab === 'page' ? html`<${ChatDock} doc=${d} draft=${body} onProposal=${propose} onUndo=${ed.undo} canUndo=${undo.length > 0}
      getPaper=${() => paperRef.current && paperRef.current.querySelector('.paper')} />` : null}
    </div>
  </div>`;
}

const LAYOUT_OPTIONS = [{ id: 'single', label: 'One column' }, { id: 'two_column', label: 'Two columns' }];

/** "Resume for a job": paste a job description or a link, get a one-page resume written for it. */
function CustomResume() {
  const g = useStore((s) => s.gen[genKey(null, 'custom')]);
  const [open, setOpen] = useState(false);
  const busy = g && g.status === 'generating';
  return html`<${Button} variant="primary" icon="spark" busy=${busy} onClick=${() => setOpen(true)}>${busy ? 'Tailoring…' : 'Resume for a job'}</${Button}>
    ${open ? html`<${Portal}><${CustomResumeDialog} g=${g} busy=${busy} onClose=${() => setOpen(false)} /></${Portal}>` : null}`;
}

function CustomResumeDialog({ g, busy, onClose }) {
  const styles = useStyles();
  const ref = useRef();
  const [f, setF] = useState({ url: '', jd_text: '', title: '', company: '', layout: 'single', style: 'classic' });
  useFocusTrap(ref, () => { if (!busy) onClose(); });
  const set = (k) => (e) => setF({ ...f, [k]: e.currentTarget.value });
  const ready = f.jd_text.trim().length >= 80 || /^https?:\/\/\S+\.\S+/.test(f.url.trim());
  const go = async (e) => {
    e.preventDefault();
    if (!ready || busy) return;
    const doc = await generateCustomResume({ ...f, url: f.url.trim(), jd_text: f.jd_text.trim() });
    if (doc) onClose();
  };
  return html`<div class="overlay" onClick=${(e) => e.target === e.currentTarget && !busy && onClose()}>
    <form class="dialog custom-resume" role="dialog" aria-modal="true" aria-label="Resume for a job" ref=${ref} onSubmit=${go}>
      <div class="row space"><h2 class="dlg-h">A one-page resume for any job</h2>
        <button type="button" class="icon-btn" aria-label="Close" disabled=${busy} onClick=${onClose}><${Icon} name="x" size=${16} /></button></div>
      <p class="muted small">Paste the job description or a link to the posting. Your resume is rewritten for it from your profile — every line fact-checked, nothing invented.</p>
      <label class="field"><span class="field-label">Link to the job</span>
        <input class="input" type="url" inputmode="url" placeholder="https://company.com/careers/role" value=${f.url} onInput=${set('url')} /></label>
      <label class="field"><span class="field-label">…or paste the job description</span>
        <textarea class="input" rows="7" placeholder="Paste the full description: responsibilities, requirements, skills…" value=${f.jd_text} onInput=${set('jd_text')}></textarea>
        <span class="muted small">${f.jd_text.trim() ? `${f.jd_text.trim().length} characters` : 'LinkedIn links can’t be read — paste their text instead.'}</span></label>
      <div class="editor-grid">
        <label class="field"><span class="field-label">Job title <span class="muted">(optional)</span></span><input class="input" value=${f.title} onInput=${set('title')} /></label>
        <label class="field"><span class="field-label">Company <span class="muted">(optional)</span></span><input class="input" value=${f.company} onInput=${set('company')} /></label>
      </div>
      <div class="field"><span class="field-label">Layout</span>
        <div class="ed-seg" role="radiogroup" aria-label="Layout">${LAYOUT_OPTIONS.map((o) => html`<button type="button" role="radio" aria-checked=${f.layout === o.id}
          class=${f.layout === o.id ? 'is-on' : ''} onClick=${() => setF({ ...f, layout: o.id })}>${o.label}</button>`)}</div></div>
      <div class="field"><span class="field-label">Style</span><${StylePicker} styles=${styles} value=${f.style} onChange=${(id) => setF({ ...f, style: id })} /></div>
      ${g && g.status === 'failed' ? html`<div class="error-text small" role="alert">${g.error}</div>` : null}
      <div class="dialog-actions">
        ${busy ? html`<span class="muted small grow">Reading the job and tailoring — usually 20-60 seconds.</span>` : null}
        <${Button} type="button" disabled=${busy} onClick=${onClose}>Cancel</${Button}>
        <${Button} variant="primary" icon="spark" type="submit" busy=${busy} disabled=${!ready}>${busy ? 'Tailoring…' : 'Create resume'}</${Button}>
      </div>
    </form>
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
      sub="Tailored resumes and cover letters per job, plus a full CV — nothing invented. Click any text on the page to edit it." actions=${html`<${CustomResume} /><${CvGenerator} />`} />
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
              <div class="grow"><strong>${d.job ? d.job.title : d.target ? d.target.title : d.title}</strong>
                <span class="muted small">${d.job ? d.job.company : d.target ? (d.target.company || 'Your job description') : d.focus || 'Whole career'} · ${relTime(d.created_at)}</span></div>
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
