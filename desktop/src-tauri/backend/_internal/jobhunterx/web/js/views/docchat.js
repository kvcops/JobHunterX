// Style picker + AI chat editor for resumes, CVs and cover letters.
//
// Style: the preview switches instantly in the browser (CSS only, same content); the server re-renders the PDF in the
// background and a download can name any style.
// Chat: the AI proposes small, fact-checked edits (nothing is saved by it). Accepted edits "snap" in: the old text
// disintegrates and the new text assembles. The user keeps the result (normal save) or undoes it.
import { html, useState, useEffect, useRef } from '../lib/preact.js';
import { api } from '../lib/api.js';
import { Button, Icon } from '../components/ui.js';
import { errorText, toast } from '../actions.js';

// ---------------------------------------------------------------------------------------------- styles
export const FALLBACK_STYLES = [
  { id: 'classic', label: 'Classic', accent: '#111827', align: 'left', font: 'Helvetica' },
  { id: 'professional', label: 'Professional', accent: '#1e3a5f', align: 'center', font: 'Helvetica' },
  { id: 'harvard', label: 'Harvard', accent: '#000000', align: 'center', font: 'Times-Roman' },
  { id: 'modern', label: 'Modern', accent: '#0369a1', align: 'left', font: 'Helvetica' },
  { id: 'slate', label: 'Slate', accent: '#475569', align: 'left', font: 'Helvetica' },
];
let stylesPromise = null;
export function useStyles() {
  const [list, setList] = useState(FALLBACK_STYLES);
  useEffect(() => {
    stylesPromise = stylesPromise || api.documentStyles().then((r) => r.styles).catch(() => null);
    stylesPromise.then((s) => { if (s && s.length) setList(s); else stylesPromise = null; });
  }, []);
  return list;
}

export function StylePicker({ styles, value, onChange, busy }) {
  return html`<div class="style-picker" role="radiogroup" aria-label="Document style">
    ${styles.map((s) => html`<button type="button" role="radio" aria-checked=${value === s.id} key=${s.id}
        class=${`style-chip ${value === s.id ? 'is-on' : ''}`} title=${s.description || s.label} onClick=${() => onChange(s.id)}>
      <span class=${`style-swatch ${s.align === 'center' ? 'is-center' : ''} ${s.font === 'Times-Roman' ? 'is-serif' : ''}`} style=${{ '--sw': s.accent }} aria-hidden="true"><i></i><i></i><i></i></span>
      <span>${s.label}</span></button>`)}
    ${busy ? html`<span class="muted small style-busy" aria-live="polite">Updating PDF…</span>` : null}
  </div>`;
}

// ---------------------------------------------------------------------------------------------- snap effect
const reduced = () => {
  const m = document.documentElement.dataset.motion;
  if (m === 'reduced') return true;
  if (m === 'full') return false;
  return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
};

/** One shared SVG turbulence filter; its displacement grows while an element dissolves. */
export function SnapFilter() {
  return html`<svg class="snap-defs" width="0" height="0" aria-hidden="true" focusable="false">
    <filter id="jhx-snap" x="-20%" y="-40%" width="140%" height="180%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.035 0.09" numOctaves="2" seed="7" result="noise" />
      <feDisplacementMap id="jhx-snap-map" in="SourceGraphic" in2="noise" scale="0" xChannelSelector="R" yChannelSelector="G" />
    </filter></svg>`;
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2);

/** Animate elements from whole to dust (dir = 1) or from dust to whole (dir = -1). Resolves when finished. */
function dust(els, dir, ms) {
  return new Promise((resolve) => {
    if (!els.length || reduced()) { resolve(); return; }
    const map = document.getElementById('jhx-snap-map');
    const t0 = performance.now();
    els.forEach((el, i) => { el.style.willChange = 'filter, transform, opacity'; el.dataset.snapI = String(i % 5); });
    const step = (now) => {
      const raw = Math.min(1, (now - t0) / ms);
      const t = ease(dir === 1 ? raw : 1 - raw);
      if (map) map.setAttribute('scale', String(Math.round(t * 110)));
      els.forEach((el) => {
        const k = 1 + Number(el.dataset.snapI) * 0.12;                // elements drift at slightly different speeds
        el.style.filter = t > 0.002 ? 'url(#jhx-snap)' : '';
        el.style.opacity = String(Math.max(0, 1 - t ** 1.6));
        el.style.transform = `translate(${(t * 34 * k).toFixed(1)}px, ${(-t * 16 * k).toFixed(1)}px) rotate(${(t * 1.6).toFixed(2)}deg)`;
      });
      if (raw < 1) requestAnimationFrame(step);
      else {
        if (dir === -1) els.forEach((el) => { el.style.filter = ''; el.style.opacity = ''; el.style.transform = ''; });
        els.forEach((el) => { el.style.willChange = ''; });
        if (map) map.setAttribute('scale', '0');
        resolve();
      }
    };
    requestAnimationFrame(step);
  });
}

const SAFE_PATH = /^[a-z_]+(\.\d+)?(\.[a-z_]+(\.\d+)?)*$/i;      // paths come from the server; only plain ones reach a selector
const pick = (root, paths) => (root ? paths.filter((p) => SAFE_PATH.test(p)).flatMap((p) => Array.from(root.querySelectorAll(`[data-p="${p}"]`))) : []);

/** Show an accepted proposal: the old text snaps away, `commit()` swaps in the new content, the new text assembles. */
export async function playSnap(root, changes, commit) {
  const touched = changes.filter((c) => c.accepted);
  if (!root || !touched.length || reduced()) { commit(); return; }
  root.classList.add('whoosh');
  await dust(pick(root, touched.map((c) => c.path)), 1, 650);
  commit();
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));      // let the new text render
  const fresh = pick(root, touched.filter((c) => c.after).map((c) => c.path));
  fresh.forEach((el) => { el.style.opacity = '0'; });
  await dust(fresh, -1, 750);
  root.classList.remove('whoosh');
}

// ---------------------------------------------------------------------------------------------- chat dock
const SUGGESTIONS = {
  resume: ['Make my summary shorter', 'Tighten the first experience’s bullets', 'Put my strongest skills first', 'Remove the weakest project'],
  cv: ['Make my summary shorter', 'Tighten the bullets', 'Put my strongest skills first', 'Remove the oldest achievement'],
  cover_letter: ['Make it shorter', 'Make the opening stronger', 'Make the tone warmer', 'Remove the last paragraph'],
};

export function ChatDock({ doc, draft, onProposal, onUndo, canUndo, getPaper }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState([]);
  const endRef = useRef(null);
  useEffect(() => { if (endRef.current) endRef.current.scrollIntoView({ block: 'end' }); }, [log, open, busy]);

  const send = async (instruction) => {
    const q = (instruction || text).trim();
    if (q.length < 3 || busy) return;
    setText('');
    setBusy(true);
    const history = log.filter((m) => m.role).slice(-6).map((m) => ({ role: m.role, text: m.text.slice(0, 600) }));
    setLog((l) => [...l, { role: 'user', text: q }]);
    try {
      const out = await api.chatDocument(doc.id, { instruction: q, content: draft, history });
      const applied = out.changes.filter((c) => c.accepted);
      setLog((l) => [...l, { role: 'assistant', text: out.reply, changes: out.changes }]);
      if (applied.length) await playSnap(getPaper(), out.changes, () => onProposal(out.content, out.changes));
    } catch (err) {
      setLog((l) => [...l, { role: 'assistant', text: errorText(err), error: true }]);
    } finally {
      setBusy(false);
    }
  };

  if (!open) return html`<button type="button" class="chat-fab" onClick=${() => setOpen(true)} aria-label="Edit this document with AI">
    <${Icon} name="spark" size=${18} /><span>Edit with AI</span></button>`;
  return html`<aside class="chat-dock" aria-label="AI editor">
    <header class="chat-head"><strong><${Icon} name="spark" size=${15} /> Edit with AI</strong>
      <div class="row gap">${canUndo ? html`<button type="button" class="link-btn small" onClick=${onUndo}>Undo last</button>` : null}
        <button type="button" class="icon-btn" aria-label="Close" onClick=${() => setOpen(false)}><${Icon} name="back" size=${15} /></button></div></header>
    <div class="chat-log scroll" role="log" aria-live="polite">
      ${!log.length ? html`<p class="muted small">Ask for a change in your own words. I only reword and reorder what is already true — nothing is invented, links and dates are never touched, and nothing is saved until you keep it.</p>
        <div class="chat-sugs">${(SUGGESTIONS[doc.kind] || SUGGESTIONS.resume).map((s) => html`<button type="button" class="chip" key=${s} onClick=${() => send(s)}>${s}</button>`)}</div>` : null}
      ${log.map((m, i) => html`<div class=${`chat-msg ${m.role} ${m.error ? 'err' : ''}`} key=${i}>
        <p>${m.text}</p>
        ${m.changes && m.changes.length ? html`<ul class="chat-changes">${m.changes.map((c) => html`<li key=${c.id} class=${c.accepted ? 'ok' : 'no'}>
          <span class="chat-chg-label">${c.accepted ? '✓' : '✕'} ${c.label}</span>
          ${c.before ? html`<span class="diff-old">${c.before}</span>` : null}
          ${c.after ? html`<span class="diff-new">${c.after}</span>` : null}
          ${!c.accepted && c.reason ? html`<span class="muted small">${c.reason}</span>` : null}</li>`)}</ul>` : null}</div>`)}
      ${busy ? html`<div class="chat-msg assistant"><span class="chat-typing" aria-label="Thinking"><i></i><i></i><i></i></span></div>` : null}
      <div ref=${endRef}></div>
    </div>
    <form class="chat-form" onSubmit=${(e) => { e.preventDefault(); send(); }}>
      <input class="input" value=${text} maxlength="600" placeholder="e.g. make the summary two lines" aria-label="What should change?"
        onInput=${(e) => setText(e.currentTarget.value)} disabled=${busy} />
      <${Button} variant="primary" size="sm" type="submit" disabled=${busy || text.trim().length < 3}>Send</${Button}>
    </form>
  </aside>`;
}
