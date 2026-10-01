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

const NAV_GROUPS = [
  { label: 'General', items: [
    { page: 'discover', label: 'Discover', icon: 'search' },
    { page: 'profile', label: 'Profile', icon: 'user' },
    { page: 'documents', label: 'Documents', icon: 'doc' },
    { page: 'tracker', label: 'Tracker', icon: 'board' },
  ] },
  { label: 'Automation', items: [
    { page: 'browser', label: 'Browser agent', icon: 'globe' },
    { page: 'interventions', label: 'Interventions', icon: 'hand' },
  ] },
  { label: 'Others', items: [{ page: 'settings', label: 'Settings', icon: 'gear' }] },
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
  const name = useStore((s) => (s.profile.envelope && s.profile.envelope.profile ? s.profile.envelope.profile.name : ''));
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  const View = VIEWS[route.page] || DiscoverView;
  const initials = (name || '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '—';
  return html`<div class="shell">
    <div class="ambient" aria-hidden="true"><i></i><i></i><i></i></div>
    <a class="skip-link" href="#main">Skip to content</a>
    <aside class="sidebar">
      <nav class="sidebar-card" aria-label="Main">
        <a class="brand" href="#/discover" aria-label="JobHunterX home">
          <span class="brand-mark"><img src="/assets/logo.svg" alt="" width="20" height="20" /></span>
          <span class="brand-name">JobHunterX</span>
        </a>
        <div class="nav-groups">${NAV_GROUPS.map((g) => html`<div class="nav-group" key=${g.label}>
          <div class="nav-label nav-group-label">${g.label}</div>
          <ul class="nav">${g.items.map((n) => html`<li key=${n.page}><a href=${`#/${n.page}`} class=${route.page === n.page ? 'active' : ''}
            aria-current=${route.page === n.page ? 'page' : undefined} title=${n.label}>
            <${Icon} name=${n.icon} size=${18} /><span class="lbl">${n.label}</span>
            ${n.page === 'discover' && runActive ? html`<span class="dot" aria-label="Search running"></span>` : null}
            ${n.page === 'interventions' && ivCount ? html`<span class="nav-count">${ivCount}</span>` : null}</a></li>`)}</ul>
        </div>`)}</div>
        <div class="sidebar-foot">
          <span class=${`conn conn-${conn}`} title=${`Live updates: ${conn}`}>${conn === 'open' ? 'Live updates' : conn === 'reconnecting' ? 'Reconnecting…' : 'Offline'}</span>
        </div>
      </nav>
    </aside>
    <main id="main" class="main" tabindex="-1">
      <div class="utility">
        <button type="button" class="circle-btn" aria-label=${`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick=${() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
          <${Icon} name=${theme === 'dark' ? 'sun' : 'moon'} size=${17} /></button>
        <a class="circle-btn avatar" href="#/profile" aria-label="Your profile" title=${name || 'Your profile'}>${initials}</a>
      </div>
      <${View} />
    </main>
    ${activity ? html`<div class="activity-line" aria-live="polite">${activity.message}</div>` : null}
    ${route.jobId && (route.page === 'discover' || route.page === 'tracker') ? html`<${JobDetailDrawer} key=${route.jobId} jobId=${route.jobId} onClose=${() => navigate(`#/${route.page}`)} />` : null}
    <${ConfirmDialog} /><${Toasts} />
  </div>`;
}

render(html`<${Shell} />`, document.getElementById('app'));
boot();
