// Edit a resume / CV / cover letter right on the page it is shown on.
//
// Every piece of text on the paper is its own contenteditable field bound to a path in the document content
// ("experience.0.bullets.2"). Typing never re-renders the field (the caret stays put); leaving it, or pressing Enter,
// commits the text — with **bold**, *italic* and [links](https://…) kept as plain markers (lib/richtext.js) that the
// PDF draws the same way. Enter in a bullet starts the next one; Backspace in an empty one removes it. The toolbar
// formats the selection, edits links, adds/removes list items and switches the page layout.
import { html, useState, useEffect, useLayoutEffect, useRef } from '../lib/preact.js';
import { Icon } from '../components/ui.js';
import { toHtml, fromElement, safeLink } from '../lib/richtext.js';

// ---------------------------------------------------------------------------------------------- paths
export const clone = (value) => JSON.parse(JSON.stringify(value));
const keyOf = (k) => (/^\d+$/.test(k) ? Number(k) : k);

export function getPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? o : o[keyOf(k)]), obj);
}

export function setPath(obj, path, value) {
  const keys = path.split('.').map(keyOf);
  const root = Array.isArray(obj) ? [...obj] : { ...obj };
  let cur = root;
  keys.forEach((k, i) => {
    if (i === keys.length - 1) { cur[k] = value; return; }
    const next = cur[k];
    cur[k] = Array.isArray(next) ? [...next] : { ...(next || {}) };
    cur = cur[k];
  });
  return root;
}

export function insertAt(obj, listPath, index, value) {
  const list = [...(getPath(obj, listPath) || [])];
  list.splice(index, 0, value);
  return setPath(obj, listPath, list);
}

export function removeAt(obj, listPath, index) {
  const list = [...(getPath(obj, listPath) || [])];
  list.splice(index, 1);
  return setPath(obj, listPath, list);
}

// Credential links are stored per item text (item_links): renaming the item must carry its links along.
const LINKED = /^(certifications|achievements|competitions|languages)\.(\d+)$/;
export function commitValue(content, path, next) {
  const m = path.match(LINKED);
  if (m) {
    const prev = getPath(content, path);
    const links = content.item_links || {};
    if (prev && prev !== next && Object.prototype.hasOwnProperty.call(links, prev)) {
      const moved = { ...links, [next]: links[prev] };
      delete moved[prev];
      return { ...setPath(content, path, next), item_links: moved };
    }
  }
  return setPath(content, path, next);
}

// ---------------------------------------------------------------------------------------------- focus bookkeeping
// The field the caret is in (for the toolbar) and the field to focus after a structural change (a new bullet).
const focusState = { field: null, pending: null, listeners: new Set() };
const announce = () => focusState.listeners.forEach((fn) => fn(focusState.field));
export function useActiveField() {
  const [f, setF] = useState(focusState.field);
  useEffect(() => { focusState.listeners.add(setF); return () => focusState.listeners.delete(setF); }, []);
  return f;
}
export function focusLater(path) { focusState.pending = path; }
/** Commit the field being typed in (toolbar actions keep the caret there, so it hasn't blurred). */
export function commitActive() { if (focusState.field) focusState.field.commit(); }

function caretToEnd(el) {
  const r = document.createRange();
  r.selectNodeContents(el);
  r.collapse(false);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(r);
}

/**
 * One editable piece of text. `list` = { path, index, make } when it is a member of a list (bullets, items): Enter adds
 * the next member, Backspace in an empty one removes it. `format`/`parse` map a non-string value (skills list) to text.
 */
export function Editable({ ed, path, tag = 'span', cls = '', ph = '', list = null, linkPath = '', format, parse, block = false }) {
  const ref = useRef(null);
  const raw = getPath(ed.value, path);
  const text = format ? format(raw) : (raw ?? '');
  // Layout effects: they run right after the render, before the next key press — a fast typist's next letters land
  // in the new bullet, not the one they just left.
  useLayoutEffect(() => {
    const el = ref.current;
    if (el && document.activeElement !== el) el.innerHTML = toHtml(text);
  }, [text]);
  useLayoutEffect(() => {
    if (focusState.pending === path && ref.current) {
      focusState.pending = null;
      ref.current.focus();
      caretToEnd(ref.current);
    }
  });
  if (!ed.editing) {
    const Tag = tag;
    return html`<${Tag} class=${cls} data-p=${path} dangerouslySetInnerHTML=${{ __html: toHtml(text) }} />`;
  }
  const commit = () => {
    const el = ref.current;
    if (!el) return;
    const next = fromElement(el);
    if (next !== text) ed.commit(path, parse ? parse(next) : next);
  };
  const field = { path, list, linkPath, commit, el: () => ref.current };
  const onKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
      if (list) ed.insert(list.path, list.index + 1, list.make ? list.make() : '');
      else ref.current.blur();
    } else if (e.key === 'Backspace' && list && !ref.current.textContent.trim()) {
      e.preventDefault();
      ed.remove(list.path, list.index, list.index > 0 ? `${list.path}.${list.index - 1}` : '');
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      ed.askLink();
    }
  };
  const onPaste = (e) => {          // paste words, not someone else's fonts and colours
    e.preventDefault();
    const t = (e.clipboardData || window.clipboardData).getData('text/plain').replace(/\s+/g, ' ');
    document.execCommand('insertText', false, t);
  };
  const Tag = tag;
  return html`<${Tag} ref=${ref} class=${`ed ${block ? 'ed-block' : ''} ${cls}`} data-p=${path} data-ph=${ph}
    contenteditable="true" spellcheck="true" role="textbox" aria-label=${ph || path}
    onFocus=${() => { focusState.field = field; announce(); }}
    onBlur=${() => { commit(); setTimeout(() => { if (focusState.field === field && document.activeElement !== ref.current) { focusState.field = null; announce(); } }, 150); }}
    onKeyDown=${onKeyDown} onPaste=${onPaste}
    onClick=${(e) => { const a = e.target.closest && e.target.closest('a'); if (a) e.preventDefault(); }} />`;
}

// ---------------------------------------------------------------------------------------------- toolbar
function useSavedRange() {
  const range = useRef(null);
  return {
    save() { const s = window.getSelection(); range.current = s && s.rangeCount ? s.getRangeAt(0).cloneRange() : null; },
    restore() { if (!range.current) return; const s = window.getSelection(); s.removeAllRanges(); s.addRange(range.current); },
  };
}

const tb = (e) => e.preventDefault();      // toolbar buttons must not steal the caret from the text

export function EditToolbar({ ed, layout, onLayout, canLayout, status }) {
  const field = useActiveField();
  const [link, setLink] = useState(null);   // { url } while the link box is open
  const saved = useSavedRange();
  ed.askLink = () => openLink();
  const exec = (cmd) => { if (!field) return; document.execCommand(cmd); };
  function currentAnchor() {
    const s = window.getSelection();
    const n = s && s.anchorNode;
    const el = n && (n.nodeType === 1 ? n : n.parentElement);
    return el && el.closest ? el.closest('a') : null;
  }
  function openLink() {
    if (!field) return;
    saved.save();
    const a = currentAnchor();
    const existing = field.linkPath ? getPath(ed.value, `${field.linkPath}.url`) : a ? a.getAttribute('href') : '';
    setLink({ url: existing || 'https://' });
  }
  function applyLink(e) {
    e.preventDefault();
    const url = safeLink(link.url);
    setLink(null);
    if (!field) return;
    if (field.linkPath) { if (url) ed.commit(`${field.linkPath}.url`, url); return; }
    const el = field.el();
    if (!el || !url) return;
    el.focus();
    saved.restore();
    const s = window.getSelection();
    if (s.isCollapsed) {
      const a = currentAnchor();
      if (a) a.setAttribute('href', url);
      else document.execCommand('insertHTML', false, `<a href="${url.replace(/"/g, '%22')}">${url.replace(/^https?:\/\/(www\.)?/, '').replace(/</g, '&lt;')}</a>`);
    } else {
      document.execCommand('createLink', false, url);
    }
    field.commit();
  }
  function unlink() {
    if (!field) return;
    if (field.linkPath && field.list) { ed.remove(field.list.path, field.list.index); return; }
    const a = currentAnchor();
    if (a) {
      const r = document.createRange();
      r.selectNodeContents(a);
      const s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    }
    document.execCommand('unlink');
    field.commit();
  }
  const inList = !!(field && field.list);
  return html`<div class="ed-toolbar" role="toolbar" aria-label="Formatting">
    <div class="ed-tools">
      <button type="button" class="ed-btn" title="Bold (Ctrl+B)" aria-label="Bold" disabled=${!field} onMouseDown=${tb} onClick=${() => exec('bold')}><b>B</b></button>
      <button type="button" class="ed-btn" title="Italic (Ctrl+I)" aria-label="Italic" disabled=${!field} onMouseDown=${tb} onClick=${() => exec('italic')}><i>I</i></button>
      <button type="button" class="ed-btn" title="Insert or edit link (Ctrl+K)" aria-label="Link" disabled=${!field} onMouseDown=${tb} onClick=${openLink}><${Icon} name="link" size=${15} /></button>
      <button type="button" class="ed-btn" title=${field && field.linkPath ? 'Remove this link' : 'Remove link'} aria-label="Remove link" disabled=${!field} onMouseDown=${tb} onClick=${unlink}><${Icon} name="unlink" size=${15} /></button>
      <span class="ed-sep" aria-hidden="true"></span>
      <button type="button" class="ed-btn ed-wide" title="Add a line after this one (Enter)" disabled=${!inList} onMouseDown=${tb}
        onClick=${() => { field.commit(); ed.insert(field.list.path, field.list.index + 1, field.list.make ? field.list.make() : ''); }}><${Icon} name="plus" size=${14} /><span>Line</span></button>
      <button type="button" class="ed-btn ed-wide" title="Remove this line" disabled=${!inList} onMouseDown=${tb}
        onClick=${() => ed.remove(field.list.path, field.list.index)}><${Icon} name="minus" size=${14} /><span>Line</span></button>
      <span class="ed-sep" aria-hidden="true"></span>
      <button type="button" class="ed-btn ed-wide" title="Undo the last change" disabled=${!ed.canUndo} onMouseDown=${tb} onClick=${() => { commitActive(); ed.undo(); }}><${Icon} name="undo" size=${14} /><span>Undo</span></button>
      ${canLayout ? html`<span class="ed-sep" aria-hidden="true"></span>
        <div class="ed-seg" role="radiogroup" aria-label="Page layout">
          <button type="button" role="radio" aria-checked=${layout !== 'two_column'} class=${layout !== 'two_column' ? 'is-on' : ''} onMouseDown=${tb} onClick=${() => { commitActive(); onLayout('single'); }}>One column</button>
          <button type="button" role="radio" aria-checked=${layout === 'two_column'} class=${layout === 'two_column' ? 'is-on' : ''} onMouseDown=${tb} onClick=${() => { commitActive(); onLayout('two_column'); }}><${Icon} name="columns" size=${13} /> Two columns</button>
        </div>` : null}
    </div>
    <span class="ed-status muted small" aria-live="polite">${status}</span>
    ${link ? html`<form class="ed-linkbox" onSubmit=${applyLink}>
      <input class="input" type="url" value=${link.url} aria-label="Link address" autofocus
        onInput=${(e) => setLink({ url: e.currentTarget.value })} onKeyDown=${(e) => { if (e.key === 'Escape') setLink(null); }} />
      <button type="submit" class="btn btn-primary btn-sm">Apply</button>
      <button type="button" class="btn btn-secondary btn-sm" onClick=${() => setLink(null)}>Cancel</button>
    </form>` : null}
  </div>`;
}

// ---------------------------------------------------------------------------------------------- previews
const LIMIT = (fit, key) => (fit && typeof fit[key] === 'number' ? fit[key] : Infinity);
const cut = (i, max) => (i >= max ? 'fit-cut' : '');

function Links({ ed, base, links }) {
  return html`${(links || []).map((l, i) => html`${i ? html`<span class="sep"> · </span>` : null}${ed.editing
    ? html`<${Editable} ed=${ed} path=${`${base}.${i}.text`} cls="ed-link" ph="link text" linkPath=${`${base}.${i}`}
        list=${{ path: base, index: i, make: () => ({ label: '', url: 'https://', text: '' }) }} />`
    : safeLink(l.url) ? html`<a href=${safeLink(l.url)} target="_blank" rel="noopener noreferrer">${l.text || l.label}</a>` : html`<span>${l.text || l.label}</span>`}`)}
    ${ed.editing ? html`<button type="button" class="ed-add-inline" title="Add a link" onClick=${() => ed.insert(base, (links || []).length, { label: '', url: 'https://', text: '' })}>+ link</button>` : null}`;
}

function AddRow({ ed, label, onAdd }) {
  return ed.editing ? html`<button type="button" class="ed-add" onClick=${onAdd}><${Icon} name="plus" size=${12} /> ${label}</button>` : null;
}

function RemoveBtn({ ed, listPath, index, what }) {
  return ed.editing ? html`<button type="button" class="ed-x" title=${`Remove this ${what}`} aria-label=${`Remove this ${what}`}
    onClick=${() => ed.remove(listPath, index)}><${Icon} name="x" size=${12} /></button>` : null;
}

const joinList = (v) => (v || []).join(', ');
const splitList = (s) => s.split(/\s*,\s*/).map((x) => x.trim()).filter(Boolean);

/** The resume / CV page. `fit` (from the server) marks what the one-page PDF leaves out. */
export function ResumePaper({ ed, style = 'classic', fit = {}, kind = 'resume' }) {
  const c = ed.value;
  const two = c.layout === 'two_column';
  const il = c.item_links || {};
  const f = kind === 'resume' ? fit : {};
  const E = (p, o = {}) => html`<${Editable} ed=${ed} path=${p} ...${o} />`;
  const contact = ['email', 'phone', 'location'].filter((k) => ed.editing || c.header[k]);

  const head = html`<header class="paper-head">
    ${E('header.name', { tag: 'h2', ph: 'Your name' })}
    ${ed.editing || c.headline ? E('headline', { tag: 'div', cls: 'paper-sub', ph: 'Headline (your title)' }) : null}
    <div class="paper-contact">${contact.map((k, i) => html`${i ? html`<span class="sep"> · </span>` : null}${E(`header.${k}`, { ph: k })}`)}
      ${(c.header.links || []).length || ed.editing ? html`<br /><span class="paper-links"><${Links} ed=${ed} base="header.links" links=${c.header.links} /></span>` : null}</div>
  </header>`;

  const summary = (ed.editing || c.summary) ? html`<section class=${f.hide_summary ? 'fit-cut' : ''}><h3>Summary</h3>${E('summary', { tag: 'p', ph: 'A 2-3 sentence summary for this job', block: true })}</section>` : null;

  const skills = (c.skills.length || ed.editing) ? html`<section><h3>Skills</h3>
    ${c.skills.map((g, i) => html`<p class=${`paper-skill ed-row ${cut(i, LIMIT(f, 'max_skill_groups'))}`} key=${i}>
      ${!ed.editing && c.skills.length === 1 && /^(skills|other)$/i.test(g.category) ? null : html`<strong>${E(`skills.${i}.category`, { ph: 'Category' })}:</strong> `}${E(`skills.${i}.items`, { ph: 'skill, skill, skill', format: joinList, parse: splitList })}
      <${RemoveBtn} ed=${ed} listPath="skills" index=${i} what="skill group" /></p>`)}
    <${AddRow} ed=${ed} label="Skill group" onAdd=${() => ed.insert('skills', c.skills.length, { category: '', items: [] }, `skills.${c.skills.length}.category`)} />
  </section>` : null;

  const bullets = (base, list, max) => html`<ul>${(list || []).map((b, j) => html`<li class=${cut(j, max)} key=${j}>${E(`${base}.${j}`, {
    ph: 'What you did and what came of it', block: true, list: { path: base, index: j } })}</li>`)}</ul>`;

  const experience = (c.experience.length || ed.editing) ? html`<section><h3>Experience</h3>
    ${c.experience.map((e, i) => html`<div class=${`paper-item ed-row ${cut(i, LIMIT(f, 'max_experience'))}`} key=${i}>
      <div class="row space"><strong>${E(`experience.${i}.role`, { ph: 'Role' })}${ed.editing || e.company ? html` — ${E(`experience.${i}.company`, { ph: 'Company' })}` : ''}</strong>
        <span class="muted small">${E(`experience.${i}.start`, { ph: 'Start' })}${ed.editing || e.start || e.end ? ' – ' : ''}${E(`experience.${i}.end`, { ph: 'End' })}</span></div>
      ${bullets(`experience.${i}.bullets`, e.bullets, LIMIT(f, 'max_bullets_per_exp'))}
      ${ed.editing && !e.bullets.length ? html`<${AddRow} ed=${ed} label="Bullet" onAdd=${() => ed.insert(`experience.${i}.bullets`, 0, '')} />` : null}
      <${RemoveBtn} ed=${ed} listPath="experience" index=${i} what="role" /></div>`)}
    <${AddRow} ed=${ed} label="Role" onAdd=${() => ed.insert('experience', c.experience.length, { role: '', company: '', location: '', start: '', end: '', bullets: [''] }, `experience.${c.experience.length}.role`)} />
  </section>` : null;

  const projects = (c.projects.length || ed.editing) ? html`<section class=${LIMIT(f, 'max_projects') === 0 ? 'fit-cut' : ''}><h3>Projects</h3>
    ${c.projects.map((p, i) => html`<div class=${`paper-item ed-row ${cut(i, LIMIT(f, 'max_projects'))}`} key=${i}>
      <div class="row space"><span><strong>${E(`projects.${i}.title`, { ph: 'Project name' })}</strong>
        ${ed.editing || p.technologies.length ? html` <span class="muted small">· ${E(`projects.${i}.technologies`, { ph: 'tech, tech', format: joinList, parse: splitList })}</span>` : null}</span>
        <span class="paper-links"><${Links} ed=${ed} base=${`projects.${i}.links`} links=${p.links && p.links.length ? p.links : (p.url && !ed.editing ? [{ url: p.url, label: 'Link' }] : [])} /></span></div>
      ${E(`projects.${i}.description`, { tag: 'p', ph: 'What it does, how you built it, the result', block: true })}
      <${RemoveBtn} ed=${ed} listPath="projects" index=${i} what="project" /></div>`)}
    <${AddRow} ed=${ed} label="Project" onAdd=${() => ed.insert('projects', c.projects.length, { title: '', description: '', technologies: [], url: '', links: [] }, `projects.${c.projects.length}.title`)} />
  </section>` : null;

  const education = (c.education.length || ed.editing) ? html`<section><h3>Education</h3>
    ${c.education.map((e, i) => html`<div class=${`paper-edu paper-item ed-row ${cut(i, LIMIT(f, 'max_education'))}`} key=${i}>
      <div class="row space"><span><strong>${E(`education.${i}.degree`, { ph: 'Degree' })}</strong>${ed.editing || e.institution ? html` — ${E(`education.${i}.institution`, { ph: 'Institution' })}` : ''}
        ${ed.editing || e.grade ? html`<span class="muted small"> · ${E(`education.${i}.grade`, { ph: 'Grade' })}</span>` : ''}</span>
        ${ed.editing || e.start || e.end ? html`<span class="muted small nowrap">${E(`education.${i}.start`, { ph: 'Start year' })}${e.start && e.end || ed.editing ? ' – ' : ''}${E(`education.${i}.end`, { ph: 'End year' })}</span>` : null}</div>
      <${RemoveBtn} ed=${ed} listPath="education" index=${i} what="education entry" /></div>`)}
    <${AddRow} ed=${ed} label="Education" onAdd=${() => ed.insert('education', c.education.length, { degree: '', institution: '', university: '', start: '', end: '', grade: '', details: '' }, `education.${c.education.length}.degree`)} />
  </section>` : null;

  const listSection = (k, title, maxKey) => (c[k] && c[k].length) || (ed.editing && k !== 'competitions')
    ? html`<section class=${LIMIT(f, maxKey) === 0 ? 'fit-cut' : ''}><h3>${title}</h3><ul>${(c[k] || []).map((x, i) => html`<li class=${cut(i, LIMIT(f, maxKey))} key=${i}>
        ${E(`${k}.${i}`, { ph: title.replace(/s$/, ''), block: true, list: { path: k, index: i } })}
        ${il[x] && !ed.editing ? html` · <span class="paper-links">${il[x].map((l) => (safeLink(l.url) ? html`<a href=${safeLink(l.url)} target="_blank" rel="noopener noreferrer">${l.text || l.label}</a>` : null))}</span>` : null}</li>`)}</ul>
      ${ed.editing && !(c[k] || []).length ? html`<${AddRow} ed=${ed} label=${title.replace(/s$/, '')} onAdd=${() => ed.insert(k, 0, '')} />` : null}</section>`
    : null;

  const certs = listSection('certifications', 'Certifications', 'max_certs');
  const achievements = listSection('achievements', 'Achievements', 'max_achievements');
  const languages = listSection('languages', 'Languages', 'max_extras');
  const competitions = listSection('competitions', 'Competitions', 'max_extras');

  return html`<article class=${`paper ${ed.editing ? 'is-editing' : ''}`} data-style=${style} data-layout=${two ? 'two_column' : 'single'}>
    ${head}
    ${two ? html`<div class="paper-cols"><div class="paper-side">${skills}${education}${certs}${languages}${competitions}</div>
        <div class="paper-main">${summary}${experience}${projects}${achievements}</div></div>`
      : html`${summary}${skills}${experience}${projects}${education}${certs}${achievements}${competitions}${languages}`}
  </article>`;
}

export function LetterPaper({ ed, style = 'classic' }) {
  const c = ed.value;
  const E = (p, o = {}) => html`<${Editable} ed=${ed} path=${p} ...${o} />`;
  return html`<article class=${`paper ${ed.editing ? 'is-editing' : ''}`} data-style=${style}>
    ${E('greeting', { tag: 'p', ph: 'Dear Hiring Manager,', block: true })}
    ${(c.paragraphs || []).map((_, i) => E(`paragraphs.${i}`, { tag: 'p', ph: 'Paragraph', block: true, list: { path: 'paragraphs', index: i } }))}
    ${E('closing', { tag: 'p', ph: 'Sincerely,', block: true })}${E('signature', { tag: 'p', ph: 'Your name', block: true })}
  </article>`;
}

/** What the one-page PDF leaves out, in words ("2 bullets, 1 project"), counted against the current text. */
export function fitSummary(c, fit) {
  if (!fit || !Object.keys(fit).length || !c) return '';
  const parts = [];
  const n = (count, one, many) => (count > 0 ? parts.push(`${count} ${count === 1 ? one : many}`) : null);
  const lim = (k) => LIMIT(fit, k);
  const exp = c.experience || [];
  n(Math.max(0, exp.length - lim('max_experience')), 'role', 'roles');
  n(exp.slice(0, lim('max_experience')).reduce((a, e) => a + Math.max(0, (e.bullets || []).length - lim('max_bullets_per_exp')), 0), 'bullet', 'bullets');
  n(Math.max(0, (c.projects || []).length - lim('max_projects')), 'project', 'projects');
  n(Math.max(0, (c.achievements || []).length - lim('max_achievements')), 'achievement', 'achievements');
  n(Math.max(0, (c.certifications || []).length - lim('max_certs')), 'certification', 'certifications');
  n(Math.max(0, (c.education || []).length - lim('max_education')), 'education entry', 'education entries');
  n(Math.max(0, (c.skills || []).length - lim('max_skill_groups')), 'skill group', 'skill groups');
  if (fit.hide_summary && c.summary) parts.push('the summary');
  return parts.join(', ');
}
