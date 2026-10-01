// App shell: navigation, theme, global overlays. Views read the store; actions mutate it.
import { html, render, useEffect } from './lib/preact.js';
import { useStore } from './state/store.js';
import { boot, navigate, setTheme } from './actions.js';
import { Icon, ConfirmDialog, Toasts } from './components/ui.js';
import { DiscoverView } from './views/discover.js';
import { JobDetailDrawer } from './views/jobdetail.js';
import { ProfileView } from './views/profile.js';
import { DocumentsView } from './views/documents.js';
import { TrackerView, BrowserView, InterventionsView, SettingsView } from './views/other.js';

const NAV = [
  { page: 'discover', label: 'Discover', icon: 'search' },
  { page: 'profile', label: 'Profile', icon: 'user' },
  { page: 'documents', label: 'Documents', icon: 'doc' },
  { page: 'tracker', label: 'Tracker', icon: 'board' },
  { page: 'browser', label: 'Browser agent', icon: 'globe' },
  { page: 'interventions', label: 'Interventions', icon: 'hand' },
  { page: 'settings', label: 'Settings', icon: 'gear' },
];
const VIEWS = {
  discover: DiscoverView, profile: ProfileView, documents: DocumentsView, tracker: TrackerView,
  browser: BrowserView, interventions: InterventionsView, settings: SettingsView,
};

function Shell() {
  const route = useStore((s) => s.route);
  const theme = useStore((s) => s.theme);
  const conn = useStore((s) => s.conn);
  const runActive = useStore((s) => !!(s.search.run && ['queued', 'running'].includes(s.search.run.status)));
  const ivCount = useStore((s) => s.interventions.items.length);
  const activity = useStore((s) => s.activity[0]);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  const View = VIEWS[route.page] || DiscoverView;
  return html`<div class="shell">
    <a class="skip-link" href="#main">Skip to content</a>
    <nav class="sidebar" aria-label="Main">
      <div class="brand"><img src="/assets/logo.svg" alt="" width="28" height="28" /><span>JobHunterX</span></div>
      <ul>${NAV.map((n) => html`<li key=${n.page}><a href=${`#/${n.page}`} class=${route.page === n.page ? 'active' : ''} aria-current=${route.page === n.page ? 'page' : undefined}>
        <${Icon} name=${n.icon} /><span>${n.label}</span>
        ${n.page === 'discover' && runActive ? html`<span class="pulse" aria-label="Search running"></span>` : null}
        ${n.page === 'interventions' && ivCount ? html`<span class="nav-count">${ivCount}</span>` : null}</a></li>`)}</ul>
      <div class="sidebar-foot">
        <span class=${`conn conn-${conn}`} title=${`Live updates: ${conn}`}>${conn === 'open' ? 'Live' : conn === 'reconnecting' ? 'Reconnecting…' : 'Offline'}</span>
        <button type="button" class="icon-btn" aria-label=${`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick=${() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
          <${Icon} name=${theme === 'dark' ? 'sun' : 'moon'} /></button>
      </div>
    </nav>
    <main id="main" class="main" tabindex="-1">
      <${View} />
      ${activity ? html`<div class="activity-line muted small" aria-live="polite">${activity.message}</div>` : null}
    </main>
    ${route.jobId && (route.page === 'discover' || route.page === 'tracker') ? html`<${JobDetailDrawer} key=${route.jobId} jobId=${route.jobId} onClose=${() => navigate(`#/${route.page}`)} />` : null}
    <${ConfirmDialog} /><${Toasts} />
  </div>`;
}

render(html`<${Shell} />`, document.getElementById('app'));
boot();
