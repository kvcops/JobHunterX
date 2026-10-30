// Desktop app (JobHunterX installed with its own window): links that would open a new browser tab — job postings,
// company sites, "Draft email" — open in the computer's default browser / mail app instead. The window itself can't
// show other sites, so the local server opens them. Does nothing in a normal browser.
let desktop = false;

export function isDesktop() { return desktop; }

async function openOutside(href) {
  try {
    const r = await fetch('/api/desktop/open', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: href }), credentials: 'same-origin',
    });
    return r.ok;
  } catch {
    return false;
  }
}

function outsideTarget(a) {
  if (!a || !a.getAttribute('href') || a.hasAttribute('download')) return null;   // downloads are saved by the window
  let url;
  try { url = new URL(a.href, window.location.href); } catch { return null; }
  if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) return null;
  const sameApp = url.origin === window.location.origin;
  if (sameApp && a.target !== '_blank') return null;                              // in-app navigation stays in the app
  return url.href;
}

export async function initDesktopLinks() {
  try {
    const r = await fetch('/api/setup', { credentials: 'same-origin' });
    desktop = !!(r.ok && (await r.json()).desktop);
  } catch {
    desktop = false;
  }
  if (!desktop) return;
  // capture phase: runs before the browser follows the link; the app's own click handlers still run
  document.addEventListener('click', (e) => {
    if (e.defaultPrevented || e.button > 1) return;
    const a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    const href = outsideTarget(a);
    if (!href) return;
    e.preventDefault();
    openOutside(href);
  }, true);
  document.addEventListener('auxclick', (e) => {                                   // middle-click
    const href = outsideTarget(e.target && e.target.closest ? e.target.closest('a[href]') : null);
    if (href) { e.preventDefault(); openOutside(href); }
  }, true);
  const nativeOpen = window.open.bind(window);
  window.open = (u, target, features) => {
    try {
      const url = new URL(String(u || ''), window.location.href);
      if (['http:', 'https:', 'mailto:'].includes(url.protocol) && (url.origin !== window.location.origin || target === '_blank')) {
        openOutside(url.href);
        return null;
      }
    } catch { /* not a URL: let the browser decide */ }
    return nativeOpen(u, target, features);
  };
}
