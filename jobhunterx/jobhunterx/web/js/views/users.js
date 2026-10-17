// Users (prod mode, admin only): create logins, reset a password, turn a login off, delete a user.
// Each user sees only their own profiles and brings their own AI keys; the admin never sees their data here —
// only which providers they added a key for.
import { html, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { loadUsers, createUser, resetUserPassword, setUserDisabled, deleteUser } from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, Icon, Field, PageHead, Notice } from '../components/ui.js';
import { relTime } from '../lib/format.js';

const USERNAME_RE = /^[A-Za-z0-9_.@-]{3,40}$/;

function NewUser() {
  const [name, setName] = useState('');
  const [pw, setPw] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const nameOk = USERNAME_RE.test(name.trim());
  const pwOk = pw.length >= 8;
  const submit = async (e) => {
    e.preventDefault();
    if (!nameOk || !pwOk || busy) return;
    setBusy(true);
    const ok = await createUser(name.trim(), pw);
    setBusy(false);
    if (ok) { setName(''); setPw(''); }
  };
  return html`<form class="set-section" onSubmit=${submit} autocomplete="off">
    <h2>Add a user</h2>
    <p class="muted small">Share the username and password with the person yourself. They can change the password after signing in.</p>
    <div class="form-grid">
      <${Field} label="Username" hint="3–40 letters, digits or _ . @ -">${(id) => html`<input id=${id} class="input" value=${name} autocomplete="off"
        spellcheck="false" maxlength="40" onInput=${(e) => setName(e.currentTarget.value)} />`}</${Field}>
      <${Field} label="Password" hint="At least 8 characters">${(id) => html`<div class="setup-input">
        <input id=${id} class="input" type=${show ? 'text' : 'password'} value=${pw} autocomplete="new-password" maxlength="200"
          onInput=${(e) => setPw(e.currentTarget.value)} />
        <button type="button" class="icon-btn" aria-label=${show ? 'Hide password' : 'Show password'} onClick=${() => setShow(!show)}><${Icon} name="eye" size=${15} /></button></div>`}</${Field}>
    </div>
    <div class="row gap"><${Button} type="submit" variant="primary" icon="plus" busy=${busy} disabled=${!nameOk || !pwOk}>Create user</${Button}></div>
  </form>`;
}

function UserRow({ u }) {
  const [resetting, setResetting] = useState(false);
  const [pw, setPw] = useState('');
  const [busy, setBusy] = useState(false);
  const saveReset = async () => {
    setBusy(true);
    const ok = await resetUserPassword(u, pw);
    setBusy(false);
    if (ok) { setResetting(false); setPw(''); }
  };
  return html`<div class=${`prov-card ${u.disabled ? 'off' : ''}`}>
    <div class="prov-head">
      <span class="avatar sm">${(u.username[0] || '?').toUpperCase()}</span>
      <div class="grow"><strong>${u.username}</strong>
        ${u.is_admin ? html` <${Badge} tone="info">Admin</${Badge}>` : null}
        ${u.signup ? html` <${Badge} tone="neutral" title="Made their own account; auto-apply needs their own Browser Use key">Signed up</${Badge}>` : null}
        ${u.disabled ? html` <${Badge} tone="danger">Can't sign in</${Badge}>` : u.signed_in ? html` <${Badge} tone="success">Signed in</${Badge}>` : null}
        <div class="muted small">${u.profiles} profile${u.profiles === 1 ? '' : 's'}
          · ${u.is_admin ? 'uses the server keys' : u.keys.length ? `own keys: ${u.keys.join(', ')}` : 'no AI key yet'}
          · ${u.last_login ? `last sign-in ${relTime(u.last_login)}` : 'never signed in'}</div></div>
      ${u.is_admin ? html`<span class="muted small">Set in .env</span>` : html`<div class="row gap wrap">
        <${Button} size="sm" icon="key" onClick=${() => setResetting(!resetting)}>New password</${Button}>
        <${Button} size="sm" onClick=${() => setUserDisabled(u, !u.disabled)}>${u.disabled ? 'Allow sign-in' : 'Block sign-in'}</${Button}>
        <${Button} size="sm" variant="danger" icon="trash" onClick=${() => deleteUser(u)}>Delete</${Button}></div>`}
    </div>
    ${resetting ? html`<div class="key-row editing">
      <input class="input" type="password" autocomplete="new-password" aria-label=${`New password for ${u.username}`} placeholder="New password (8+ characters)"
        value=${pw} onInput=${(e) => setPw(e.currentTarget.value)}
        onKeyDown=${(e) => { if (e.key === 'Enter' && pw.length >= 8) saveReset(); if (e.key === 'Escape') setResetting(false); }} />
      <${Button} size="sm" variant="primary" busy=${busy} disabled=${pw.length < 8} onClick=${saveReset}>Save</${Button}>
      <${Button} size="sm" onClick=${() => setResetting(false)}>Cancel</${Button}></div>` : null}
  </div>`;
}

export function UsersView() {
  const st = useStore((s) => s.users);
  const users = (st.data && st.data.users) || [];
  return html`<div class="view view-settings">
    <${PageHead} title="Users" sub="Who can sign in to this server. Each user sees only their own profiles and uses their own AI keys." />
    <section class="pane card"><div class="scroll pane-pad set-body">
      <${Notice} tone="info">Users bring their own AI keys (Google, NVIDIA, Groq, Mistral). The free shared models (Kilo, LLM7) are limited per server address, so only the admin uses them.</${Notice}>
      <${NewUser} />
      <section class="set-section"><div class="row space"><h2>All users</h2>
        <${Button} size="sm" icon="refresh" busy=${st.status === 'refreshing' || st.status === 'loading'} onClick=${loadUsers}>Refresh</${Button}></div>
        ${st.status === 'error' ? html`<${ErrorBox} message=${st.error} onRetry=${loadUsers} />` : null}
        ${!st.data && st.status !== 'error' ? html`<${Skeleton} rows=${3} />` : null}
        ${st.data && !users.length ? html`<${EmptyState} icon="user" title="No users yet">Add the first one above.</${EmptyState}>` : null}
        <div class="prov-list">${users.map((u) => html`<${UserRow} key=${u.id} u=${u} />`)}</div>
      </section>
    </div></section>
  </div>`;
}
