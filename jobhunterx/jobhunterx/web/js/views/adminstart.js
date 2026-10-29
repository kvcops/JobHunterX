// Prod mode, admin only: the first screen after signing in — manage who can sign in, or open your own profile.
import { html } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { adminChoose, logout } from '../actions.js';
import { Button, Icon } from '../components/ui.js';
import { UsersView } from './users.js';

function Brand() {
  return html`<div class="brand"><span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
    <span class="brand-name">JobHunter<span class="serif">X</span></span></div>`;
}

export function AdminStart() {
  const user = useStore((s) => s.auth.user) || {};
  return html`<div class="admin-start">
    <div class="admin-start-head"><${Brand} />
      <${Button} size="sm" icon="logout" onClick=${logout}>Log out</${Button}></div>
    <h1>Welcome, <span class="serif">${user.username}</span></h1>
    <p class="muted">You are the admin. What would you like to do first?</p>
    <div class="admin-start-cards">
      <button type="button" class="card admin-card" onClick=${() => adminChoose('users')}>
        <span class="admin-card-icon"><${Icon} name="users" size=${26} /></span>
        <strong>Manage users</strong>
        <span class="muted small">Add people who can sign in, set a new password, block or delete a user.</span>
      </button>
      <button type="button" class="card admin-card" onClick=${() => adminChoose('profile')}>
        <span class="admin-card-icon"><${Icon} name="user" size=${26} /></span>
        <strong>Open my profile</strong>
        <span class="muted small">Go to your own job search — your profiles, jobs and documents.</span>
      </button>
    </div>
  </div>`;
}

/** The Users page on its own, before the admin has opened a profile. */
export function AdminUsers() {
  return html`<div class="admin-users">
    <div class="admin-start-head"><${Brand} />
      <div class="row gap"><${Button} variant="primary" icon="user" onClick=${() => adminChoose('profile')}>Open my profile</${Button}>
        <${Button} size="sm" icon="logout" onClick=${logout}>Log out</${Button}></div></div>
    <${UsersView} />
  </div>`;
}
