// App shell: lifecycle (boot → onboarding → app), navigation, theme, global overlays.
// Views read the store; actions mutate it.
import { html, render, useEffect, useLayoutEffect, useRef, useState } from './lib/preact.js';
import { useStore } from './state/store.js';
import { boot, navigate, setTheme, retryBoot } from './actions.js';
import { Icon, ConfirmDialog, Toasts, Button } from './components/ui.js';
import { DiscoverView } from './views/discover.js';
import { CompaniesView } from './views/companies.js';
import { ProfileView } from './views/profile.js';
import { DocumentsView } from './views/documents.js';
import { OnboardingView } from './views/onboarding.js';
import { SetupView } from './views/setup.js';
import { PeoplePicker, ProfileSwitcher } from './views/people.js';
import { TrackerView, BrowserView, InterventionsView, SettingsView } from './views/other.js';

// Ordered the way the work flows: who you are → what fits → what you send → where it stands.
const NAV_GROUPS = [
  { label: 'Workflow', items: [
    { page: 'profile', label: 'Profile', icon: 'user', step: 1 },
    { page: 'discover', label: 'Discover', icon: 'search', step: 2 },
    { page: 'companies', label: 'Companies', icon: 'layers' },
    { page: 'documents', label: 'Documents', icon: 'doc', step: 3 },
    { page: 'tracker', label: 'Tracker', icon: 'board', step: 4 },
  ] },
  { label: 'Automation', items: [
    { page: 'browser', label: 'Auto-apply', icon: 'globe' },
    { page: 'interventions', label: 'Interventions', icon: 'hand' },
  ] },
  { label: 'System', items: [{ page: 'settings', label: 'Settings', icon: 'gear' }] },
];
const VIEWS = {
  discover: DiscoverView, companies: CompaniesView, profile: ProfileView, documents: DocumentsView, tracker: TrackerView,
  browser: BrowserView, interventions: InterventionsView, settings: SettingsView,
};

function Ambient() {
  return html`<div class="ambient" aria-hidden="true"><i></i><i></i><i></i></div>`;
}

function Splash() {
  return html`<div class="splash" role="status" aria-live="polite">
    <div class="splash-mark" aria-hidden="true"><span class="orb-wave"></span><span class="orb-wave w2"></span><span class="orb-wave w3"></span>
      <img class="splash-logo" src="/assets/logo.svg" alt="" width="72" height="72" /></div>
    <div class="splash-name">JobHunter<span class="serif">X</span></div>
    <div class="splash-line"><span></span></div>
    <span class="sr-only">Loading</span>
  </div>`;
}

function BootError() {
  const err = useStore((s) => s.app.error);
  return html`<div class="splash">
    <div class="empty-icon"><span class="empty-halo"></span><${Icon} name="alert" size=${26} /></div>
    <h2>Can't reach JobHunterX</h2>
    <p class="muted" style=${{ maxWidth: '420px', textAlign: 'center' }}>${err || 'The local server did not respond.'} Make sure it is running, then try again.</p>
    <${Button} variant="primary" icon="refresh" onClick=${retryBoot}>Try again</${Button}>
  </div>`;
}

function Sidebar() {
  const route = useStore((s) => s.route);
  const theme = useStore((s) => s.theme);
  const runActive = useStore((s) => !!(s.search.run && ['queued', 'running'].includes(s.search.run.status)));
  const ivCount = useStore((s) => s.interventions.items.length);
  // One highlight that glides to the active item instead of jumping.
  const groupsRef = useRef();
  const [ind, setInd] = useState(null);
  const measure = () => {
    const el = groupsRef.current && groupsRef.current.querySelector('a.active');
    setInd(el ? { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight } : null);
  };
  useLayoutEffect(measure, [route.page]);
  useEffect(() => {
    if (!window.ResizeObserver || !groupsRef.current) return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(groupsRef.current);
    return () => ro.disconnect();
  }, []);
  return html`<aside class="sidebar">
    <nav class="sidebar-card" aria-label="Main">
      <a class="brand" href="#/discover" aria-label="JobHunterX home">
        <span class="brand-mark"><img src="/assets/logo.svg" alt="" width="34" height="34" /></span>
        <span class="brand-name">JobHunter<span class="serif">X</span></span>
      </a>
      <div class="nav-groups" ref=${groupsRef}>
        ${ind ? html`<span class="nav-ind" aria-hidden="true" style=${{ transform: `translate(${ind.x}px, ${ind.y}px)`, width: `${ind.w}px`, height: `${ind.h}px` }}></span>` : null}
        ${NAV_GROUPS.map((g) => html`<div class="nav-group" key=${g.label}>
        <div class="nav-label nav-group-label">${g.label}</div>
        <ul class="nav">${g.items.map((n) => html`<li key=${n.page}><a href=${`#/${n.page}`} class=${route.page === n.page ? 'active' : ''}
          aria-current=${route.page === n.page ? 'page' : undefined} title=${n.label}>
          <${Icon} name=${n.icon} size=${18} /><span class="lbl">${n.label}</span>
          ${n.step ? html`<span class="nav-step" aria-hidden="true">${n.step}</span>` : null}
          ${n.page === 'discover' && runActive ? html`<span class="dot" aria-label="Search running"></span>` : null}
          ${n.page === 'interventions' && ivCount ? html`<span class="nav-count">${ivCount}</span>` : null}</a></li>`)}</ul>
      </div>`)}</div>
      <div class="sidebar-foot">
        <${ProfileSwitcher} />
        <button type="button" class="icon-btn theme-btn" aria-label=${`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick=${() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
          <${Icon} name=${theme === 'dark' ? 'sun' : 'moon'} size=${17} /></button>
      </div>
    </nav>
  </aside>`;
}

function AppShell() {
  const route = useStore((s) => s.route);
  const activity = useStore((s) => s.activity[0]);
  const View = VIEWS[route.page] || DiscoverView;
  return html`<div class="shell">
    <a class="skip-link" href="#main">Skip to content</a>
    <${Sidebar} />
    <main id="main" class="main" tabindex="-1">
      <${View} key=${route.page} />
    </main>
    ${activity ? html`<div class="activity-line" aria-live="polite" key=${activity.id}>${activity.message}</div>` : null}
  </div>`;
}

function Root() {
  const phase = useStore((s) => s.app.phase);
  const theme = useStore((s) => s.theme);
  const motion = useStore((s) => s.motion);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  useEffect(() => { document.documentElement.dataset.motion = motion; }, [motion]);
  return html`<${Ambient} />
    ${phase === 'booting' ? html`<${Splash} />` : phase === 'error' ? html`<${BootError} />` : phase === 'setup' ? html`<${SetupView} />` : phase === 'pick' ? html`<${PeoplePicker} />` : phase === 'onboarding' ? html`<${OnboardingView} />` : html`<${AppShell} />`}
    <${ConfirmDialog} /><${Toasts} />`;
}

if (document.startViewTransition) document.documentElement.classList.add('vt');
render(html`<${Root} />`, document.getElementById('app'));
boot();
