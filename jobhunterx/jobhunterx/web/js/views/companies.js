// Companies: the researched watchlist for the candidate's cities. Each company's own job board is
// checked every few hours, so new roles are caught before the public-job-board crowd arrives.
import { html, useEffect, useState } from '../lib/preact.js';
import { useStore } from '../state/store.js';
import { loadWatchlist, checkWatchlistNow, navigate, setList } from '../actions.js';
import { Button, Badge, Skeleton, ErrorBox, EmptyState, PageHead, Tabs, Icon, Monogram, Notice } from '../components/ui.js';
import { CompanySection } from './jobdetail.js';
import { runProgress } from './discover.js';
import {
  COMPANY_VERDICT_LABEL, COMPANY_VERDICT_TONE, COMPETITION_LABEL, EARLY_CAREER_LABEL, relTime, humanize, plural,
} from '../lib/format.js';

const CATEGORY_LABEL = { ai_startup: 'AI startup', product: 'Product company', gcc: 'GCC (global tech centre)', ai_services_boutique: 'AI services (small)' };

function CompanyRow({ c, open, onToggle }) {
  const rv = c.reviews || {};
  return html`<article class=${`company-row card ${open ? 'is-open' : ''}`}>
    <button type="button" class="company-head" aria-expanded=${open ? 'true' : 'false'} onClick=${onToggle}>
      <${Monogram} name=${c.name} />
      <div class="grow">
        <div class="company-name">${c.name}<span class="muted small"> · ${(c.cities || []).join(', ')} · ${CATEGORY_LABEL[c.category] || humanize(c.category)}</span></div>
        <div class="muted small">${c.what_they_do}</div>
        <div class="row gap wrap" style=${{ marginTop: '6px' }}>
          <${Badge} tone=${COMPANY_VERDICT_TONE[c.verdict]}>${COMPANY_VERDICT_LABEL[c.verdict] || c.verdict}</${Badge}>
          ${c.competition ? html`<${Badge} tone=${c.competition === 'low' ? 'success' : c.competition === 'very_high' ? 'danger' : 'neutral'}>${COMPETITION_LABEL[c.competition]}</${Badge}>` : null}
          <${Badge} tone=${c.hires_early_career === 'yes' ? 'success' : c.hires_early_career === 'rare' ? 'warning' : 'neutral'}>${EARLY_CAREER_LABEL[c.hires_early_career] || 'Unknown'}</${Badge}>
          ${rv.ambitionbox ? html`<span class="fact">AmbitionBox ${rv.ambitionbox}</span>` : null}
          ${rv.glassdoor ? html`<span class="fact">Glassdoor ${rv.glassdoor}</span>` : null}
          ${c.red_flags && c.red_flags.length ? html`<span class="fact tone-text-warning">${plural(c.red_flags.length, 'red flag')}</span>` : null}
          ${c.board_supported ? html`<span class="fact tone-text-success" title="Its own job board is checked automatically">Auto-checked</span>`
            : html`<span class="fact" title="Its careers site can't be read automatically yet — open it yourself">Check manually</span>`}
        </div>
      </div>
      <${Icon} name=${open ? 'x' : 'next'} size=${16} />
    </button>
    ${open ? html`<div class="company-body"><${CompanySection} c=${c} /></div>` : null}
  </article>`;
}

/** Live view of a running watchlist check — every line and number comes from the server as it happens. */
function LiveCheck({ run, feed }) {
  const pct = runProgress(run);
  const p = run.progress;
  const cur = run.stages.find((st) => st.status === 'running');
  const c = run.counts || {};
  return html`<div class="card pad live-check" aria-live="polite">
    <div class="row gap wrap">
      <span class="live-dot"></span><strong>Checking your watchlist companies now</strong>
      <span class="muted small">${p && p.label ? p.label : cur ? cur.label : 'Starting…'}</span>
      <span class="grow"></span><span class="live-pct">${pct}%</span>
    </div>
    <div class="mc-bar is-active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${pct}><div class="mc-fill" style=${{ width: `${pct}%` }}></div></div>
    <div class="row gap wrap small muted">
      <span>${c.candidates || 0} openings found</span><span>·</span><span>${c.scored || 0} analysed</span><span>·</span>
      <span class="tone-text-success">${c.recommended || 0} fit you</span>
    </div>
    ${feed && feed.length ? html`<ul class="live-feed">${feed.slice().reverse().map((it) => html`<li key=${it.id} class=${`k-${it.kind}`}>${it.message}</li>`)}</ul>` : null}
  </div>`;
}

export function CompaniesView() {
  const w = useStore((s) => s.watch);
  const [filter, setFilter] = useState('all');
  const [openName, setOpenName] = useState(null);
  const [scope, setScope] = useState('mine');
  useEffect(() => { loadWatchlist(scope); }, [scope]);
  const d = w.data;
  const st = d && d.status;
  const last = st && st.last;
  const all = (d && d.companies) || [];
  const shown = all.filter((c) => filter === 'all' || c.verdict === filter || (filter === 'low' && c.competition === 'low')
    || (filter === 'early' && c.hires_early_career === 'yes'));
  const tabs = [
    { key: 'all', label: 'All', count: all.length },
    { key: 'strong', label: 'Strong', count: all.filter((c) => c.verdict === 'strong').length },
    { key: 'early', label: 'Hires 1–3 yrs', count: all.filter((c) => c.hires_early_career === 'yes').length },
    { key: 'low', label: 'Low competition', count: all.filter((c) => c.competition === 'low').length },
    { key: 'caution', label: 'Caution', count: all.filter((c) => c.verdict === 'caution').length },
  ];
  const checking = w.checking || (st && st.checking);
  const liveRun = w.run && ['queued', 'running'].includes(w.run.status) ? w.run : null;
  return html`<div class="view view-companies">
    <${PageHead} title=${html`Companies to <span class="serif">watch</span>`}
      sub="Researched companies in your cities. Their own job boards are checked every few hours, so you can apply in the first hours — not as applicant #1,500 on LinkedIn."
      actions=${html`<${Button} variant="primary" icon="refresh" busy=${checking} onClick=${checkWatchlistNow}>${checking ? 'Checking…' : 'Check for new roles now'}</${Button}>`} />
    <div class="card pad stack">
      <div class="row gap wrap">
        ${d && d.cities && d.cities.length ? html`<span>Your cities: <strong>${d.cities.join(', ')}</strong></span>` : null}
        ${st ? html`<span class="muted small">${st.enabled ? `Auto-check every ${st.interval_hours} h while the app is open` : 'Auto-check is off (Settings → Search tuning)'}</span>` : null}
        ${last && last.at ? html`<span class="muted small">Last check ${relTime(last.at)}${last.new_fits != null ? ` · ${last.new_fits} new fitting role(s)` : ''}</span>` : null}
        ${last && last.new_fits ? html`<${Button} size="sm" onClick=${() => { setList({ view: 'fresh' }); navigate('#/discover'); }}>See new roles</${Button}>` : null}
        <span class="grow"></span>
        <${Tabs} size="sm" label="Which companies" value=${scope} onChange=${setScope} tabs=${[{ key: 'mine', label: 'My cities' }, { key: 'all', label: 'All researched' }]} />
      </div>
      ${d && scope === 'mine' && !(d.cities || []).length ? html`<${Notice} tone="warning">None of your preferred locations are covered yet. Researched cities: ${(d.covered_cities || []).join(', ')}.
        Add one of them under Profile → preferences to use the watchlist.</${Notice}>` : null}
    </div>
    ${liveRun ? html`<${LiveCheck} run=${liveRun} feed=${w.feed} />` : null}
    <${Tabs} label="Filter companies" size="sm" value=${filter} onChange=${setFilter} tabs=${tabs} />
    <div class="company-list">
      ${w.status === 'error' ? html`<${ErrorBox} message=${w.error} onRetry=${() => loadWatchlist(scope)} />` : null}
      ${w.status === 'loading' && !d ? html`<${Skeleton} rows=${6} />` : null}
      ${d && !shown.length ? html`<${EmptyState} icon="info" title="No companies here">Try another filter${scope === 'mine' ? ' or "All researched"' : ''}.</${EmptyState}>` : null}
      ${shown.map((c) => html`<${CompanyRow} key=${c.name} c=${c} open=${openName === c.name} onToggle=${() => setOpenName(openName === c.name ? null : c.name)} />`)}
    </div>
  </div>`;
}
