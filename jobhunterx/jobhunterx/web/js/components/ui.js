// Shared presentational components. No data fetching here.
import { html, useState, useEffect, useRef, useId } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { closeConfirm, dismissToast } from '../actions.js';
import { scoreTone, VERDICT_LABEL } from '../lib/format.js';

const ICONS = {
  search: 'M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm10 17-5.2-5.2',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0',
  doc: 'M7 3h7l5 5v13H7zM14 3v5h5M9.5 13h7M9.5 17h7',
  board: 'M4 5h16v14H4zM9 5v14M15 5v14',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm-9 9h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z',
  hand: 'M8 13V5.5a1.5 1.5 0 0 1 3 0V12m0-6.5v-1a1.5 1.5 0 0 1 3 0V12m0-5.5a1.5 1.5 0 0 1 3 0V14a6 6 0 0 1-6 6h-1a6 6 0 0 1-5.2-3L3.5 13a1.5 1.5 0 0 1 2.6-1.5L8 14',
  gear: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm8.5 3a8.5 8.5 0 0 0-.1-1.3l2-1.6-2-3.4-2.4 1a8 8 0 0 0-2.2-1.3L15.5 2h-4l-.4 2.6a8 8 0 0 0-2.2 1.3l-2.4-1-2 3.4 2 1.6a8.5 8.5 0 0 0 0 2.6l-2 1.6 2 3.4 2.4-1a8 8 0 0 0 2.2 1.3l.4 2.6h4l.4-2.6a8 8 0 0 0 2.2-1.3l2.4 1 2-3.4-2-1.6c.1-.4.1-.9.1-1.3z',
  star: 'M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z',
  x: 'M6 6l12 12M18 6 6 18',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  alert: 'M12 4 2.5 20h19zM12 10v4.5M12 17.5v.5',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 8v6m0-9.5v.5',
  external: 'M14 4h6v6M20 4l-9 9M18 14v6H4V6h6',
  refresh: 'M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7',
  download: 'M12 4v11m-5-5 5 5 5-5M5 20h14',
  trash: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  moon: 'M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z',
  spark: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
  back: 'M15 5l-7 7 7 7',
  stop: 'M6 6h12v12H6z',
  plus: 'M12 5v14M5 12h14',
};

export function Icon({ name, size = 18, label }) {
  return html`<svg class="icon" width=${size} height=${size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden=${label ? undefined : 'true'}
    role=${label ? 'img' : undefined} aria-label=${label}><path d=${ICONS[name] || ''} /></svg>`;
}

export function Button({ variant = 'secondary', size, icon, busy, disabled, children, class: cls = '', ...rest }) {
  return html`<button type="button" class=${`btn btn-${variant} ${size ? `btn-${size}` : ''} ${cls}`}
    disabled=${disabled || busy} aria-busy=${busy ? 'true' : undefined} ...${rest}>
    ${busy ? html`<span class="spinner" aria-hidden="true"></span>` : icon ? html`<${Icon} name=${icon} size=${16} />` : null}
    ${children ? html`<span>${children}</span>` : null}
  </button>`;
}

export function Badge({ tone = 'neutral', children, title }) {
  return html`<span class=${`badge tone-${tone}`} title=${title}>${children}</span>`;
}

export function ScoreRing({ score, verdict, size = 52 }) {
  const has = typeof score === 'number';
  const tone = verdict === 'incompatible' ? 'danger' : has ? scoreTone(score) : 'unknown';
  const r = 20;
  const c = 2 * Math.PI * r;
  const pct = has ? Math.max(0, Math.min(100, score)) : 0;
  return html`<div class=${`score-ring tone-${tone}`} style=${{ width: `${size}px`, height: `${size}px` }}
      role="img" aria-label=${has ? `Match score ${score} of 100, ${VERDICT_LABEL[verdict] || ''}` : 'Not scored yet'}>
    <svg viewBox="0 0 48 48" width=${size} height=${size} aria-hidden="true">
      <circle cx="24" cy="24" r=${r} class="ring-bg" />
      <circle cx="24" cy="24" r=${r} class="ring-fg" stroke-dasharray=${`${(pct / 100) * c} ${c}`} transform="rotate(-90 24 24)" />
    </svg>
    <span class="score-num">${has ? score : '–'}</span>
  </div>`;
}

export function Meter({ value, tone }) {
  const pct = Math.round(Math.max(0, Math.min(1, value || 0)) * 100);
  return html`<div class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${pct}>
    <div class=${`meter-fill tone-${tone || (pct >= 70 ? 'success' : pct >= 45 ? 'warning' : 'danger')}`} style=${{ width: `${pct}%` }}></div>
  </div>`;
}

export function Skeleton({ lines = 3, card }) {
  return html`<div class=${card ? 'skeleton-card' : 'skeleton'} aria-hidden="true">
    ${Array.from({ length: lines }, (_, i) => html`<div class="sk-line" style=${{ width: `${90 - i * 17}%` }}></div>`)}
  </div>`;
}

export function EmptyState({ icon = 'info', title, children, action }) {
  return html`<div class="empty"><div class="empty-icon"><${Icon} name=${icon} size=${28} /></div>
    <h3>${title}</h3>${children ? html`<p>${children}</p>` : null}${action || null}</div>`;
}

export function ErrorBox({ message, onRetry }) {
  return html`<div class="error-box" role="alert"><${Icon} name="alert" />
    <div class="grow">${message}</div>
    ${onRetry ? html`<${Button} size="sm" icon="refresh" onClick=${onRetry}>Retry</${Button}>` : null}</div>`;
}

export function Notice({ tone = 'info', children }) {
  return html`<div class=${`notice tone-${tone}`}><${Icon} name=${tone === 'warning' ? 'alert' : 'info'} size=${16} /><div>${children}</div></div>`;
}

export function Field({ label, hint, children, wide }) {
  const id = useId();
  return html`<label class=${`field ${wide ? 'field-wide' : ''}`} for=${id}>
    <span class="field-label">${label}</span>
    ${typeof children === 'function' ? children(id) : children}
    ${hint ? html`<span class="field-hint">${hint}</span>` : null}
  </label>`;
}

/** Free-text chips (no fixed vocabulary): Enter/comma adds, Backspace removes last. */
export function ChipsInput({ value = [], onChange, placeholder, label }) {
  const [draft, setDraft] = useState('');
  const add = (raw) => {
    const parts = raw.split(',').map((x) => x.trim()).filter(Boolean);
    const next = [...value];
    parts.forEach((p) => { if (!next.some((v) => v.toLowerCase() === p.toLowerCase())) next.push(p); });
    if (next.length !== value.length) onChange(next);
    setDraft('');
  };
  return html`<div class="chips-input">
    ${value.map((v, i) => html`<span class="chip" key=${v}>${v}
      <button type="button" class="chip-x" aria-label=${`Remove ${v}`} onClick=${() => onChange(value.filter((_, j) => j !== i))}><${Icon} name="x" size=${12} /></button></span>`)}
    <input aria-label=${label || placeholder} value=${draft} placeholder=${value.length ? '' : placeholder}
      onInput=${(e) => setDraft(e.currentTarget.value)}
      onKeyDown=${(e) => {
        if ((e.key === 'Enter' || e.key === ',') && draft.trim()) { e.preventDefault(); add(draft); }
        else if (e.key === 'Backspace' && !draft && value.length) onChange(value.slice(0, -1));
      }}
      onBlur=${() => draft.trim() && add(draft)} />
  </div>`;
}

function useFocusTrap(ref, onClose) {
  useEffect(() => {
    const prev = document.activeElement;
    const el = ref.current;
    const first = el && el.querySelector('input, button, select, textarea, [tabindex]');
    first && first.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose(); }
      if (e.key === 'Tab' && el) {
        const items = [...el.querySelectorAll('a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])')];
        if (!items.length) return;
        const a = items[0];
        const b = items[items.length - 1];
        if (e.shiftKey && document.activeElement === a) { e.preventDefault(); b.focus(); }
        else if (!e.shiftKey && document.activeElement === b) { e.preventDefault(); a.focus(); }
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => { document.removeEventListener('keydown', onKey, true); prev && prev.focus && prev.focus(); };
  }, []);
}

export function ConfirmDialog() {
  const c = useStore((s) => s.confirm);
  if (!c) return null;
  return html`<${ConfirmInner} c=${c} />`;
}
function ConfirmInner({ c }) {
  const ref = useRef();
  const [typed, setTyped] = useState('');
  useFocusTrap(ref, () => closeConfirm(false));
  const blocked = c.typeToConfirm && typed !== c.typeToConfirm;
  return html`<div class="overlay" onClick=${(e) => e.target === e.currentTarget && closeConfirm(false)}>
    <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="dlg-title" ref=${ref}>
      <h2 id="dlg-title">${c.title}</h2>
      <p>${c.body}</p>
      ${c.typeToConfirm ? html`<${Field} label=${`Type ${c.typeToConfirm} to confirm`}>${(id) => html`<input id=${id} value=${typed} onInput=${(e) => setTyped(e.currentTarget.value)} />`}</${Field}>` : null}
      <div class="dialog-actions">
        <${Button} onClick=${() => closeConfirm(false)}>Cancel</${Button}>
        <${Button} variant=${c.tone === 'danger' ? 'danger' : 'primary'} disabled=${blocked} onClick=${() => closeConfirm(true)}>${c.confirm || 'Confirm'}</${Button}>
      </div>
    </div></div>`;
}

export function Toasts() {
  const toasts = useStore((s) => s.toasts);
  return html`<div class="toasts" role="status" aria-live="polite">
    ${toasts.map((t) => html`<div key=${t.id} class=${`toast tone-${t.tone}`}>
      <span class="grow">${t.message}</span>
      <button type="button" class="icon-btn" aria-label="Dismiss" onClick=${() => dismissToast(t.id)}><${Icon} name="x" size=${14} /></button>
    </div>`)}</div>`;
}

export function Drawer({ onClose, children, label }) {
  const ref = useRef();
  useFocusTrap(ref, onClose);
  return html`<div class="drawer-overlay" onClick=${(e) => e.target === e.currentTarget && onClose()}>
    <aside class="drawer" role="dialog" aria-modal="true" aria-label=${label} ref=${ref} tabindex="-1">${children}</aside></div>`;
}

export function Tabs({ tabs, value, onChange, label }) {
  return html`<div class="tabs" role="tablist" aria-label=${label}>
    ${tabs.map((t) => html`<button type="button" role="tab" key=${t.key} aria-selected=${value === t.key ? 'true' : 'false'}
      class=${`tab ${value === t.key ? 'active' : ''}`} onClick=${() => onChange(t.key)}>
      ${t.label}${typeof t.count === 'number' ? html`<span class="tab-count">${t.count}</span>` : null}</button>`)}</div>`;
}
