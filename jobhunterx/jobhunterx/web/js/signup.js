// Sign-up page (prod mode, ALLOW_SIGNUP). Like the login page, nothing from an earlier visit is kept in the browser.
try { localStorage.clear(); } catch { /* storage unavailable */ }
try { sessionStorage.clear(); } catch { /* storage unavailable */ }
window.addEventListener('pageshow', (e) => { if (e.persisted) window.location.reload(); });

const form = document.getElementById('login-form');
const user = document.getElementById('username');
const pass = document.getElementById('password');
const pass2 = document.getElementById('password2');
const err = document.getElementById('login-error');
const btn = document.getElementById('login-btn');
const toggle = document.getElementById('pw-toggle');
const NAME_RE = /^[A-Za-z0-9_.@-]{3,40}$/;

toggle.addEventListener('click', () => {
  const show = pass.type === 'password';
  pass.type = show ? 'text' : 'password';
  pass2.type = pass.type;
  toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  err.textContent = '';
  const username = user.value.trim();
  if (!NAME_RE.test(username)) { err.textContent = 'Username: 3–40 letters, digits or _ . @ -'; user.focus(); return; }
  if (pass.value.length < 8) { err.textContent = 'Password: at least 8 characters.'; pass.focus(); return; }
  if (pass.value !== pass2.value) { err.textContent = 'The two passwords are not the same.'; pass2.focus(); return; }
  btn.disabled = true;
  btn.classList.add('is-busy');
  try {
    const res = await fetch('/api/auth/signup', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ username, password: pass.value }),
    });
    if (res.ok) {
      pass.value = ''; pass2.value = '';
      window.location.replace('/');          // signed in: the app asks for their AI keys first
      return;
    }
    let msg = 'Could not create the account. Please try again.';
    try { const data = await res.json(); msg = (data && data.error && data.error.message) || msg; } catch { /* not JSON */ }
    err.textContent = msg;
  } catch {
    err.textContent = 'Cannot reach the server. Check your connection and try again.';
  } finally {
    btn.disabled = false;
    btn.classList.remove('is-busy');
  }
});
