// Login page (prod mode). Nothing from an earlier visit is kept: whatever the browser stored for the app
// (theme, picked profile, office memories…) is cleared as soon as this page opens.
try { localStorage.clear(); } catch { /* storage unavailable */ }
try { sessionStorage.clear(); } catch { /* storage unavailable */ }
// a copy of this page from the back/forward cache must not be reused
window.addEventListener('pageshow', (e) => { if (e.persisted) window.location.reload(); });

const form = document.getElementById('login-form');
const user = document.getElementById('username');
const pass = document.getElementById('password');
const err = document.getElementById('login-error');
const btn = document.getElementById('login-btn');
const toggle = document.getElementById('pw-toggle');

toggle.addEventListener('click', () => {
  const show = pass.type === 'password';
  pass.type = show ? 'text' : 'password';
  toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  err.textContent = '';
  const username = user.value.trim();
  if (!username || !pass.value) { err.textContent = 'Enter your username and password.'; return; }
  btn.disabled = true;
  btn.classList.add('is-busy');
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ username, password: pass.value }),
    });
    if (res.ok) {
      pass.value = '';
      window.location.replace('/');          // replace: Back never returns to the login form
      return;
    }
    let msg = 'Could not sign in. Please try again.';
    try { const data = await res.json(); msg = (data && data.error && data.error.message) || msg; } catch { /* not JSON */ }
    err.textContent = msg;
    pass.value = '';
    pass.focus();
  } catch {
    err.textContent = 'Cannot reach the server. Check your connection and try again.';
  } finally {
    btn.disabled = false;
    btn.classList.remove('is-busy');
  }
});
