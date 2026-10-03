// Switchable profiles ("people"): the start-up picker, the sidebar switcher and the manager in Settings.
import { html, useState, useEffect } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { choosePerson, createPerson, renamePerson, deletePerson } from '../actions.js';
import { Icon, Button, Spinner, Popover, Monogram } from '../components/ui.js';
import { relTime, plural } from '../lib/format.js';

function initials(name) {
  return (name || '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';
}

function PersonCard({ p, active, busy, onPick, index }) {
  // the delete button sits beside the card button (a button cannot hold another button)
  return html`<div class="person-slot">
    <button type="button" class=${`person-card ${active ? 'is-last' : ''} ${busy ? 'is-busy' : ''}`} style=${{ '--i': index }}
      onClick=${() => onPick(p.id)} disabled=${busy} aria-label=${`Open ${p.name}`}>
    <span class="person-ava" style=${{ '--h': (p.name.length * 47) % 360 }}>${busy ? html`<${Spinner} size=${22} />` : initials(p.name)}</span>
    <strong class="person-name">${p.name}</strong>
    <span class="person-sub">${p.headline || (p.has_profile ? 'Profile ready' : 'Setup not finished')}${p.location ? ` · ${p.location}` : ''}</span>
    <span class="person-meta">${plural(p.jobs || 0, 'job')} · ${p.saved || 0} saved · ${relTime(p.last_used_at || p.created_at)}</span>
    ${active ? html`<span class="person-flag">Last used</span>` : null}
  </button>
    <button type="button" class="person-del" aria-label=${`Delete ${p.name}`} title="Delete this profile" disabled=${busy}
      onClick=${() => deletePerson(p.id)}><${Icon} name="trash" size=${15} /></button>
  </div>`;
}

/** Full-screen "Who's searching?" shown once per browser session to returning users. */
export function PeoplePicker() {
  const people = useStore((s) => s.people);
  const pick = (id) => choosePerson(id);
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Enter' && e.target === document.body && people.active) pick(people.active); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [people.active]);
  return html`<div class="picker">
    <div class="picker-inner">
      <div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
        <span class="brand-name">JobHunter<span class="serif">X</span></span></div>
      <h1>Welcome back. <span class="serif">Who's</span> searching?</h1>
      <p class="lead">Each profile keeps its own resume, matches, tracker and documents.</p>
      <div class="person-grid">
        ${people.items.map((p, i) => html`<${PersonCard} key=${p.id} p=${p} index=${i} active=${p.id === people.active} busy=${people.switching === p.id} onPick=${pick} />`)}
        <button type="button" class="person-card add" style=${{ '--i': people.items.length }} onClick=${() => createPerson()} disabled=${!!people.switching}>
          <span class="person-ava add"><${Icon} name="plus" size=${24} /></span>
          <strong class="person-name">New profile</strong>
          <span class="person-sub">Start fresh with another resume</span>
        </button>
      </div>
      <p class="muted small picker-hint">Tip: press <kbd>Enter</kbd> to open the last used profile. Hover a profile to delete it.</p>
    </div>
  </div>`;
}

/** Sidebar footer: the current person, with a popover to switch or add. */
export function ProfileSwitcher() {
  const people = useStore((s) => s.people);
  const conn = useStore((s) => s.conn);
  const [open, setOpen] = useState(false);
  const me = people.items.find((p) => p.id === people.active);
  const name = (me && me.name) || 'Your profile';
  return html`<div class="pop-anchor switcher">
    <button type="button" class="me" data-popover-anchor aria-expanded=${open ? 'true' : 'false'} aria-label="Switch profile" onClick=${() => setOpen(!open)}>
      <span class="avatar">${initials(name)}</span>
      <span class="me-text"><strong>${name}</strong>
        <span class=${`conn conn-${conn}`}>${conn === 'open' ? 'Live' : conn === 'reconnecting' ? 'Reconnecting…' : 'Offline'}</span></span>
      <svg class="me-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M7 15l5-5 5 5" /></svg>
    </button>
    <${Popover} open=${open} onClose=${() => setOpen(false)} label="Profiles">
      <div class="switch-list">
        <div class="sec-title">Profiles</div>
        ${people.items.map((p) => html`<button type="button" key=${p.id} class=${`switch-item ${p.id === people.active ? 'on' : ''}`}
            onClick=${() => { setOpen(false); if (p.id !== people.active) choosePerson(p.id); }}>
          <span class="avatar sm">${initials(p.name)}</span>
          <span class="grow"><strong>${p.name}</strong><span class="muted small">${p.headline || 'No resume yet'}</span></span>
          ${p.id === people.active ? html`<${Icon} name="check" size=${15} />` : people.switching === p.id ? html`<${Spinner} size=${14} />` : null}
        </button>`)}
        <button type="button" class="switch-item add" onClick=${() => { setOpen(false); createPerson(); }}>
          <span class="avatar sm add"><${Icon} name="plus" size=${14} /></span><span class="grow"><strong>Add a profile</strong></span></button>
        <a class="switch-manage" href="#/settings" onClick=${() => setOpen(false)}>Manage profiles</a>
      </div>
    </${Popover}>
  </div>`;
}

/** Settings → Profiles: rename and delete. */
export function PeopleManager() {
  const people = useStore((s) => s.people);
  const [edit, setEdit] = useState(null);
  const [name, setName] = useState('');
  return html`<section class="set-section"><div class="row space"><h2>Profiles</h2>
      <${Button} size="sm" icon="plus" onClick=${() => createPerson()}>New profile</${Button}></div>
    <p class="muted small">Each profile has its own resume, preferences, matches, tracker and documents. Switch from the sidebar.</p>
    <div class="stack" style=${{ gap: '8px', marginTop: '12px' }}>
      ${people.items.map((p) => html`<div class="person-row" key=${p.id}>
        <${Monogram} name=${p.name} size=${36} />
        <div class="grow">${edit === p.id
          ? html`<input class="input" value=${name} aria-label="Profile name" onInput=${(e) => setName(e.currentTarget.value)}
              onKeyDown=${(e) => { if (e.key === 'Enter' && name.trim()) { renamePerson(p.id, name.trim()); setEdit(null); } if (e.key === 'Escape') setEdit(null); }} />`
          : html`<strong>${p.name}</strong>${p.id === people.active ? html` <span class="badge tone-success">Active</span>` : null}
            <div class="muted small">${p.headline || 'No resume yet'} · ${plural(p.jobs || 0, 'job')} · created ${relTime(p.created_at)}</div>`}</div>
        ${edit === p.id
          ? html`<${Button} size="sm" variant="primary" disabled=${!name.trim()} onClick=${() => { renamePerson(p.id, name.trim()); setEdit(null); }}>Save</${Button}>`
          : html`<${Button} size="sm" onClick=${() => { setEdit(p.id); setName(p.name); }}>Rename</${Button}>`}
        <button type="button" class="icon-btn" aria-label=${`Delete ${p.name}`} onClick=${() => deletePerson(p.id)}><${Icon} name="trash" size=${16} /></button>
      </div>`)}
    </div></section>`;
}
