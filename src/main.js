import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import Lenis from 'lenis';
import { initGL } from './gl.js';

gsap.registerPlugin(ScrollTrigger, SplitText);
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, fine = matchMedia('(hover:hover) and (pointer:fine)').matches;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v)), sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const say = (() => { const n = document.createElement('div'); n.setAttribute('aria-live', 'polite'); n.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)'; document.body.appendChild(n); return (t) => { n.textContent = ''; setTimeout(() => (n.textContent = t), 60); }; })();

/* ---------- smooth scroll ---------- */
let lenis = null;
if (!reduce) { lenis = new Lenis({ lerp: .1, wheelMultiplier: 1 }); lenis.on('scroll', ScrollTrigger.update); gsap.ticker.add((t) => lenis.raf(t * 1000)); gsap.ticker.lagSmoothing(0); }
const go = (el) => { if (lenis) lenis.scrollTo(el, { offset: 0, duration: 1.4 }); else el.scrollIntoView(); };
document.addEventListener('click', (e) => { const a = e.target.closest('a[href^="#"]'); if (!a) return; const t = document.getElementById(a.getAttribute('href').slice(1)); if (!t) return; e.preventDefault(); closeMenu(); go(t); t.setAttribute('tabindex', '-1'); t.focus({ preventScroll: true }); });

/* ---------- OS guess (never auto-downloads) ---------- */
const OS = (() => { const p = ((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || '') + ' ' + navigator.userAgent; if (/android|iphone|ipad|ipod/i.test(p)) return 'mobile'; if (/win/i.test(p)) return 'win'; if (/mac/i.test(p)) return 'mac'; if (/linux|x11|cros/i.test(p)) return 'lin'; return null; })();
const OSN = { win: 'Windows', mac: 'macOS', lin: 'Linux' };
if (OSN[OS]) { $('#heroDlT').textContent = 'Download for ' + OSN[OS]; $$('.os em').forEach((e) => e.classList.toggle('on', e.dataset.r === OS)); }

/* ---------- menu ---------- */
const menu = $('#menu'), burger = $('#burger');
function closeMenu() { if (menu.hidden) return; menu.hidden = true; burger.setAttribute('aria-expanded', 'false'); burger.setAttribute('aria-label', 'Open menu'); lenis && lenis.start(); }
burger.addEventListener('click', () => { if (!menu.hidden) return closeMenu(); menu.hidden = false; burger.setAttribute('aria-expanded', 'true'); burger.setAttribute('aria-label', 'Close menu'); lenis && lenis.stop(); gsap.from(menu.children, { yPercent: 60, opacity: 0, duration: .8, ease: 'expo.out', stagger: .05 }); $('a', menu).focus(); });
addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeMenu(); burger.focus(); } });

/* ---------- the stage ---------- */
let gl = null;
try { gl = initGL($('#gl'), { reduce }); } catch (err) { console.warn('WebGL unavailable', err); document.documentElement.classList.add('nogl'); }
const chaps = $$('.chap'), story = $('#story'), fin = $('#fin'), nav = $('#nav');
let tops = [], hs = [], lastY = 0;
const measure = () => { tops = chaps.map((c) => c.offsetTop + story.offsetTop); hs = chaps.map((c) => c.offsetHeight); };
function onScroll() {
  const y = scrollY, vh = innerHeight;
  let k = 0; for (let i = 0; i < chaps.length; i++) if (y >= tops[i]) k = i;
  const t = clamp((y - tops[k]) / Math.max(1, hs[k] - vh), 0, 1), e = clamp((t - .5) / .5, 0, 1);
  let p = k + (k < chaps.length - 1 ? e * e * (3 - 2 * e) : 0);
  if (fin.getBoundingClientRect().top < vh * .75) p = 8;
  gl && gl.setP(p);
  chaps.forEach((c, i) => c.classList.toggle('on', y > tops[i] - vh * .45 && y < tops[i] + hs[i] - vh * .55));
  nav.classList.toggle('hide', y > vh && y > lastY + 3 && menu.hidden); if (y < lastY - 3) nav.classList.remove('hide'); lastY = y;
}
measure(); addEventListener('resize', () => { measure(); onScroll(); }); addEventListener('scroll', onScroll, { passive: true }); onScroll();
if (gl) { const vis = new Set(); const io = new IntersectionObserver((es) => { es.forEach((e) => (e.isIntersecting ? vis.add(e.target) : vis.delete(e.target))); gl.setActive(vis.size > 0); }); io.observe(story); io.observe(fin); }
const navA = $$('.nav ul a');
['story', 'try', 'inside', 'screens', 'source', 'faq'].forEach((id) => new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) navA.forEach((a) => (a.getAttribute('href') === '#' + id ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current'))); }), { rootMargin: '-45% 0px -50% 0px' }).observe(document.getElementById(id)));

/* ---------- preloader → reveal ---------- */
const lns = $$('.hero .ln').map((l) => { const s = document.createElement('span'); s.style.display = 'block'; while (l.firstChild) s.appendChild(l.firstChild); l.appendChild(s); return s; });
(async () => {
  const pre = $('#pre'), n = $('#preN'), bar = $('#preB'), o = { v: 0 };
  const fonts = document.fonts ? Promise.all(['700 40px "Bricolage Grotesque"', '500 20px "Geist"', '500 20px "Geist Mono"', 'italic 40px "Instrument Serif"'].map((f) => document.fonts.load(f))).catch(() => {}) : Promise.resolve();
  if (reduce) { await fonts; gl && gl.refresh(); pre.remove(); splits(); return; }
  gsap.set(lns, { yPercent: 115 }); gsap.set('.hero-b > *, .hero-meta, .scroll-cue', { opacity: 0, y: 24 });
  const count = gsap.to(o, { v: 100, duration: 1.5, ease: 'power2.inOut', onUpdate() { n.textContent = String(Math.round(o.v)).padStart(2, '0'); bar.style.transform = `scaleX(${o.v / 100})`; } });
  await Promise.all([fonts, count]); gl && gl.refresh();
  const tl = gsap.timeline();
  tl.to('.pre-in > *', { yPercent: -120, duration: .7, ease: 'expo.in', stagger: .05 })
    .to(pre, { yPercent: -100, duration: 1, ease: 'expo.inOut', onComplete: () => pre.remove() }, '-=.25')
    .to(lns, { yPercent: 0, duration: 1.4, ease: 'expo.out', stagger: .12 }, '-=.45')
    .to('.hero-b > *, .hero-meta, .scroll-cue', { opacity: 1, y: 0, duration: 1, ease: 'expo.out', stagger: .08 }, '-=.9');
  splits();
})();
function splits() {
  measure(); ScrollTrigger.refresh();
  if (reduce) return;
  $$('[data-split]').forEach((el) => SplitText.create(el, { type: 'lines', mask: 'lines', linesClass: 'sl', autoSplit: true, onSplit: (s) => gsap.from(s.lines, { yPercent: 115, duration: 1.2, ease: 'expo.out', stagger: .1, scrollTrigger: { trigger: el, start: 'top 88%', once: true } }) }));
  gsap.utils.toArray('.head .lede, .panel, .feat li, .case, .truth div, .qa details, .steps > li, .osp, .os button, .stack .lv, .ag-grid div').forEach((el) => gsap.from(el, { y: 50, opacity: 0, duration: 1.1, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 92%', once: true } }));
}

/* ---------- magnetic buttons, tilt cards ---------- */
if (fine && !reduce) {
  $$('.mag').forEach((b) => { const x = gsap.quickTo(b, 'x', { duration: .6, ease: 'expo.out' }), y = gsap.quickTo(b, 'y', { duration: .6, ease: 'expo.out' });
    b.addEventListener('pointermove', (e) => { const r = b.getBoundingClientRect(); x((e.clientX - r.left - r.width / 2) * .3); y((e.clientY - r.top - r.height / 2) * .4); });
    b.addEventListener('pointerleave', () => { x(0); y(0); }); });
  $$('.tilt').forEach((c) => { const rx = gsap.quickTo(c, 'rotationX', { duration: .8, ease: 'expo.out' }), ry = gsap.quickTo(c, 'rotationY', { duration: .8, ease: 'expo.out' });
    c.addEventListener('pointermove', (e) => { const r = c.getBoundingClientRect(), px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height; ry((px - .5) * 9); rx((.5 - py) * 7); c.style.setProperty('--mx', px * 100 + '%'); c.style.setProperty('--my', py * 100 + '%'); });
    c.addEventListener('pointerleave', () => { rx(0); ry(0); }); });
}

/* ---------- A · match explorer ---------- */
const ROLES = [
  { n: 'AI Engineer', s: '0–2 yrs · Hyderabad', fit: 93, v: 'Strong match', seen: 75, sv: 'Good chance — 4 days old, on the company’s own board', c: [['Career track', 'ok', 'Same track: GenAI / LLM engineering'], ['Experience', 'ok', '0–2 years asked; you have ~1.6'], ['Location', 'ok', 'Hyderabad — where you live'], ['Must-haves', 'ok', 'Python, LLMs, RAG — all shown at work'], ['Notice', 'unk', 'Not stated — kept as unknown']] },
  { n: 'Senior AI Engineer', s: '6+ yrs · same skills', fit: 22, v: 'Incompatible', seen: 30, sv: 'Low chance — public listing, three weeks old', cap: 'A failed hard check caps the score. Identical skills don’t lift it.', c: [['Career track', 'ok', 'Same track'], ['Experience', 'fail', 'Requires 6+ years; you have ~1.6'], ['Location', 'ok', 'Hyderabad'], ['Must-haves', 'ok', 'All shown at work'], ['Notice', 'unk', 'Not stated']] },
  { n: 'Frontend Engineer', s: 'React · TypeScript', fit: 12, v: 'Incompatible', seen: 60, sv: 'Fair chance — fresh, but a crowded public board', cap: 'Different career track. Keyword overlap can’t make it a fit.', c: [['Career track', 'fail', 'Frontend, not AI/ML engineering'], ['Experience', 'ok', 'Years fit'], ['Location', 'ok', 'Remote allowed'], ['Must-haves', 'fail', 'React, TypeScript — not in your profile'], ['Notice', 'ok', '30 days accepted']] },
  { n: 'AI Engineer', s: 'Kubernetes mandatory', fit: 31, v: 'Incompatible', seen: 70, sv: 'Good chance — company board, this week', cap: 'A short, explicit must-have still rules a job out.', c: [['Career track', 'ok', 'Same track'], ['Experience', 'ok', '1–3 years asked'], ['Location', 'ok', 'Hyderabad, hybrid'], ['Must-haves', 'fail', 'Mandatory: Kubernetes — not in your profile'], ['Notice', 'ok', '30 days accepted']] },
  { n: 'AI Engineer', s: 'Berlin · on-site', drop: 1, c: [['Country', 'fail', 'Outside India — dropped before scoring. It never takes a result slot and costs no AI call.']] }
];
(() => {
  const box = $('#roles'); box.innerHTML = ROLES.map((r, i) => `<button type="button" role="radio" aria-checked="${!i}" tabindex="${i ? -1 : 0}">${r.n}<small>${r.s}</small></button>`).join('');
  const bs = $$('button', box), o = { f: 0, s: 0 };
  const show = (i) => { const r = ROLES[i]; bs.forEach((b, k) => { b.setAttribute('aria-checked', k === i); b.tabIndex = k === i ? 0 : -1; });
    const f = r.drop ? 0 : r.fit, s = r.drop ? 0 : r.seen;
    gsap.to(o, { f, s, duration: reduce ? 0 : 1.1, ease: 'expo.out', onUpdate() { $('#fitN').textContent = r.drop ? '—' : Math.round(o.f); $('#seenN').textContent = r.drop ? '—' : Math.round(o.s); } });
    $('#fitB').style.transform = `scaleX(${f / 100})`; $('#seenB').style.transform = `scaleX(${s / 100})`;
    $('#fitV').textContent = r.drop ? 'Dropped — not scored' : r.v; $('#seenV').textContent = r.drop ? 'Not measured' : r.sv;
    $('#fitN').parentElement.dataset.t = f < 60 ? 'bad' : 'ok'; $('#seenN').parentElement.dataset.t = r.drop ? 'bad' : 'ok';
    $('#checks').innerHTML = r.c.map(([a, st, w]) => `<li data-s="${st}"><b>${a}</b><span>${w}</span></li>`).join('');
    if (!reduce) gsap.from('#checks li', { opacity: 0, x: -14, duration: .6, ease: 'expo.out', stagger: .05 });
    const cap = $('#capN'); cap.hidden = !r.cap; cap.textContent = r.cap || ''; };
  bs.forEach((b, i) => { b.addEventListener('click', () => show(i)); b.addEventListener('keydown', (e) => { const m = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]; if (m) { e.preventDefault(); const n = (i + m + ROLES.length) % ROLES.length; show(n); bs[n].focus(); } }); });
  ScrollTrigger.create({ trigger: '#mx', start: 'top 80%', once: true, onEnter: () => show(0) });
})();

/* ---------- B · agent simulation ---------- */
(() => {
  const B = $('#brw'), pg = $('#pg'), cur = $('#cur'), log = $('#log'), st = $('#agS'), banner = $('#banner');
  const b = { go: $('#aGo'), stop: $('#aStop'), take: $('#aTake'), give: $('#aGive') }, inp = { name: $('#fN'), email: $('#fE'), phone: $('#fP') }, cap = $('#cap'), capB = $('#capB'), file = $('#fF');
  let state = 'idle', token = 0, resumeAs = 'running';
  const set = (s, label) => { state = s; st.textContent = label || { idle: 'Ready', running: 'Agent working', stopped: 'Stopped · saved', you: 'You’re in control', needs: 'Needs you', done: 'Done · nothing sent' }[s]; st.dataset.s = s;
    B.dataset.mode = s === 'you' ? 'you' : 'agent'; $('#who').textContent = s === 'you' ? 'YOU' : 'AGENT';
    b.stop.disabled = !(s === 'running' || s === 'needs'); b.take.disabled = !(s === 'running' || s === 'needs' || s === 'stopped'); b.give.disabled = s !== 'you'; b.go.disabled = !(s === 'idle' || s === 'stopped' || s === 'done');
    b.go.textContent = s === 'stopped' ? 'Continue' : s === 'done' ? 'Run again' : 'Start'; b.take.classList.toggle('hot', s === 'needs'); b.give.classList.toggle('hot', s === 'you'); b.go.classList.toggle('hot', !b.go.disabled);
    const you = s === 'you'; Object.values(inp).forEach((i) => (i.readOnly = !you)); capB.disabled = !you; banner.classList.toggle('show', you); };
  const add = (t, note = '', cls = '') => { const li = document.createElement('li'); li.className = cls; li.innerHTML = t + (note ? `<small>${note}</small>` : ''); log.appendChild(li); log.scrollTop = log.scrollHeight; };
  const gate = async (ms) => { const t = token; await sleep(reduce ? Math.min(ms, 30) : ms); while (state !== 'running') { if (t !== token) throw 0; await sleep(120); } if (t !== token) throw 0; };
  const to = async (el) => { const a = pg.getBoundingClientRect(), r = el.getBoundingClientRect(); cur.style.transform = `translate(${r.left - a.left + Math.min(46, r.width / 2)}px,${r.top - a.top + r.height / 2}px)`; await gate(750); };
  const foc = (f) => $$('.fl', pg).forEach((x) => x.classList.toggle('f', x.dataset.f === f));
  const type = async (i, t) => { i.value = ''; for (const ch of t) { i.value += ch; await gate(36); } };
  async function run() { const t = ++token;
    try { log.innerHTML = ''; Object.values(inp).forEach((i) => (i.value = '')); capB.checked = false; file.textContent = 'No file chosen'; file.classList.remove('done'); cap.classList.remove('show', 'need'); cur.style.transform = 'translate(24px,24px)'; set('running');
      add('Kit checked', 'resume · cover letter · CV'); await gate(500);
      foc('name'); await to(inp.name); await type(inp.name, 'Asha Rao'); add('Fill in name');
      foc('email'); await to(inp.email); await type(inp.email, 'asha@example.com');
      foc('phone'); await to(inp.phone); await type(inp.phone, '98765 43210'); add('Email and phone', '+91 in its own picker');
      foc('file'); await to(file); file.textContent = 'Asha_Rao_Resume.pdf'; file.classList.add('done'); add('Attach the resume'); await gate(300);
      foc(''); cap.classList.add('show'); await to(cap); cap.classList.add('need'); set('needs'); add('A “not a robot” check needs a person', 'press Take over', 'need'); say('The agent needs you. Take over to complete the check.');
      while (!(capB.checked && state === 'running')) { if (t !== token) throw 0; if (state === 'running' && !capB.checked) { set('needs'); add('Still waiting for the check', '', 'need'); } await sleep(150); }
      cap.classList.remove('need'); await gate(300); add('Carried on from where you left it', 'progress kept'); await gate(500);
      set('done'); add('Ready to submit. In the app the agent submits, or you press “I submitted it”.', 'demo ends here'); say('Demo finished. Nothing was sent.'); } catch (e) { /* reset */ } }
  b.go.addEventListener('click', () => { if (state === 'stopped') { set(resumeAs); add('Continue', 'from the last page'); } else run(); });
  b.stop.addEventListener('click', () => { resumeAs = state; set('stopped'); add('Stopped at once', 'steps saved'); });
  b.take.addEventListener('click', () => { if (state !== 'stopped') resumeAs = state; set('you'); add('You took over', 'your clicks go to the page', 'you'); (cap.classList.contains('show') ? capB : inp.name).focus({ preventScroll: true }); });
  b.give.addEventListener('click', () => { set('running'); add('Given back to the agent', '', 'you'); });
  set('idle');
})();

/* ---------- pipeline: sideways on scroll ---------- */
if (!reduce && innerWidth > 760) {
  const tr = $('#pipeT'), dist = () => tr.scrollWidth - innerWidth;
  gsap.to(tr, { x: () => -dist(), ease: 'none', scrollTrigger: { trigger: '#pipe', pin: true, scrub: .8, end: () => '+=' + dist(), invalidateOnRefresh: true } });
}

/* ---------- features: a screenshot follows the pointer ---------- */
if (fine) {
  const peek = $('#peek'), img = $('#peekI'), x = gsap.quickTo(peek, 'x', { duration: .7, ease: 'expo.out' }), y = gsap.quickTo(peek, 'y', { duration: .7, ease: 'expo.out' });
  const hide = () => gsap.to(peek, { opacity: 0, scale: .6, duration: .3, ease: 'power3.in', overwrite: true });
  $('#feat').addEventListener('pointerleave', hide);
  addEventListener('scroll', () => { const h = document.elementFromPoint(lastPX, lastPY); if (!h || !h.closest('#feat li')) hide(); }, { passive: true });
  let lastPX = 0, lastPY = 0; addEventListener('pointermove', (e) => { lastPX = e.clientX; lastPY = e.clientY; }, { passive: true });
  $$('#feat li').forEach((li) => { new Image().src = `assets/shots/${li.dataset.img}.webp`;
    li.addEventListener('pointerenter', () => { img.src = `assets/shots/${li.dataset.img}.webp`; gsap.to(peek, { opacity: 1, scale: 1, duration: .6, ease: 'expo.out', overwrite: true }); });
    li.addEventListener('pointerleave', hide);
    li.addEventListener('pointermove', (e) => { const w = peek.offsetWidth; x(clamp(e.clientX + 30, 10, innerWidth - w - 10)); y(clamp(e.clientY - peek.offsetHeight * .55, 10, innerHeight - peek.offsetHeight - 10)); }); });
}

/* ---------- architecture ---------- */
(() => {
  const M = { web: ['web/', 'Preact + htm', 'The app you see', 'The interface in your browser or desktop window: Preact with htm and bundled fonts, no build step. Light and dark themes, keyboard friendly, live progress.'],
    api: ['api/', 'FastAPI · WebSockets', 'The front desk', 'FastAPI routes and two WebSockets: one streams live search events, the other streams the Auto-apply browser into the app. Rate limits on every AI endpoint.'],
    services: ['services/', 'orchestration', 'The foreman', 'Runs searches, the watchlist watcher, documents, profiles and the Auto-apply kit. One search at a time; every event carries its run id.'],
    intelligence: ['intelligence/', 'understand · judge', 'Understanding & judgement', 'Reads the candidate and each job, matches with hard checks first, scores reach, finds people to contact, and learns skill links. Weights live in one tunable policy file.'],
    discovery: ['discovery/', 'find · verify', 'Finding real jobs', 'Search, adapters for Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable, Workday, Oracle and Keka, page parsing, dedupe, validation, and SSRF-safe fetching.'],
    generation: ['generation/', 'write · fact-check', 'Honest documents', 'Resume, CV and cover letter; fact-checking every AI line against your profile; five styles; a chat editor whose edits are whitelisted and checked; PDF rendering.'],
    agents: ['agents/', 'browser', 'The browser agent', 'Runs an Auto-apply session (stop, take over, continue, close) on one thread that owns the browser, and streams Chrome’s screencast into the app.'],
    config: ['config/', 'LLM router', 'The model router', 'Every AI call goes through a task chain: the first usable model answers, the next takes over if one is busy, rate-limited or rejected. Works with Google AI Studio, NVIDIA NIM, Groq, Mistral and Kilo.'],
    tools: ['tools/', 'search · zero-spend', 'Search tools', 'Deep Search, search providers and their router, a usage ledger, and a guard that blocks any search call that could cost money.'],
    watchlist: ['watchlist/', 'companies.json', 'The researched watchlist', 'About 130 companies in Hyderabad, Bengaluru and remote India, each with real AI work, early-career hiring, ratings and red flags.'],
    storage: ['storage.py', 'SQLite', 'Memory', 'A local SQLite database for jobs, documents, people, search runs and apply sessions — checked, repaired and backed up on every start.'] };
  const rows = [['web'], ['api'], ['services'], ['intelligence', 'discovery', 'generation', 'agents'], ['config', 'tools', 'watchlist', 'storage']], st = $('#stack');
  st.innerHTML = rows.map((r, i) => (i ? '<div class="join"></div>' : '') + `<div class="lv" style="--n:${r.length}">${r.map((k) => `<button type="button" data-k="${k}" aria-pressed="false"><b>${M[k][0]}</b><span>${M[k][1]}</span></button>`).join('')}</div>`).join('');
  const pick = (k) => { $$('button', st).forEach((b) => b.setAttribute('aria-pressed', b.dataset.k === k)); $('#aiT').textContent = M[k][0]; $('#aiH').textContent = M[k][2]; $('#aiP').textContent = M[k][3]; if (!reduce) gsap.from('#aiH, #aiP', { opacity: 0, y: 12, duration: .5, ease: 'expo.out', stagger: .05 }); };
  st.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) pick(b.dataset.k); }); pick('web');
})();

/* ---------- screenshots ---------- */
(() => {
  const S = [['match', 'Why this score', 'Click a job and it opens beside the list.', 'Job list with an AI Engineer role scored 93 and its explanation'], ['live_progress', 'Search, live', 'Real counts the server reports.', 'Search in progress with real counts'], ['companies', 'Companies to watch', 'Verdicts, ratings and red flags.', 'Researched company watchlist'], ['documents', 'Honest documents', 'Fact-checked, always one page.', 'Document editor with a one-page resume'], ['browser', 'Auto-apply, live', 'The browser streams into the app.', 'Auto-apply with a live browser and step log'], ['apply_help', 'When it needs you', 'Take over, then Continue.', 'Auto-apply waiting for the user'], ['tracker', 'Track everything', 'One stage bar, one click onward.', 'Application tracker'], ['dark', 'Dark mode', 'One click.', 'The app in dark mode']];
  const reel = $('#reel'); reel.innerHTML = S.map(([k, t, d, a], i) => `<figure><button type="button" data-i="${i}" aria-label="Open full size: ${t}"><img src="assets/shots/${k}.webp" alt="${a}" loading="lazy" width="1440" height="900" draggable="false"></button><figcaption><b>${t}</b><span>${d}</span></figcaption></figure>`).join('');
  const z = $('#zoom'); let moved = 0;
  reel.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b || moved > 6) return; const [k, t, d, a] = S[+b.dataset.i]; $('#zoomI').src = `assets/shots/${k}.webp`; $('#zoomI').alt = a; $('#zoomP').textContent = `${t} — ${d}`; z.showModal && z.showModal(); });
  $('#zoomX').addEventListener('click', () => z.close()); z.addEventListener('click', (e) => { if (e.target === z) z.close(); });
  let down = null; reel.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') return; down = { x: e.clientX, s: reel.scrollLeft }; moved = 0; });
  addEventListener('pointermove', (e) => { if (!down) return; moved = Math.abs(e.clientX - down.x); if (moved > 6) reel.classList.add('drag'); reel.scrollLeft = down.s - (e.clientX - down.x); });
  addEventListener('pointerup', () => { down = null; reel.classList.remove('drag'); });
})();

/* ---------- downloads ---------- */
const osB = $$('#osT button'), osP = osB.map((b) => document.getElementById(b.getAttribute('aria-controls'))), K = ['win', 'mac', 'lin'];
function selOS(k, f) { const i = Math.max(0, K.indexOf(k)); osB.forEach((b, j) => { b.setAttribute('aria-selected', j === i); b.tabIndex = j === i ? 0 : -1; osP[j].hidden = j !== i; }); if (!reduce) gsap.fromTo(osP[i], { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: .7, ease: 'expo.out', overwrite: true }); if (f) osB[i].focus(); }
osB.forEach((b, i) => { b.addEventListener('click', () => selOS(K[i])); b.addEventListener('keydown', (e) => { const m = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key]; if (m) { e.preventDefault(); selOS(K[(i + m + 3) % 3], true); } }); });
if (OSN[OS] && OS !== 'win') selOS(OS);
(async () => { try { const c = new AbortController(); setTimeout(() => c.abort(), 6000); const r = await fetch('https://api.github.com/repos/kvcops/JobHunterX/releases/latest', { signal: c.signal }); if (!r.ok) return; const j = await r.json();
  (j.assets || []).forEach((a) => $$(`[data-sz="${CSS.escape(a.name)}"]`).forEach((el) => (el.textContent = Math.round(a.size / 1048576) + ' MB')));
  if (j.name) $('#relLive').innerHTML = `Current: <a href="${j.html_url}">${j.name.replace(/^JobHunterX\s*/i, 'v')}</a>.`; } catch (e) { /* offline: static text stays */ } })();

/* ---------- source: OS switch + copy ---------- */
const sB = $$('#seg button'), sK = $('#seg i');
function setO(k, f) { const i = Math.max(0, K.indexOf(k)); sB.forEach((b, j) => { b.setAttribute('aria-selected', j === i); b.tabIndex = j === i ? 0 : -1; }); sK.style.width = sB[i].offsetWidth + 'px'; sK.style.transform = `translateX(${sB[i].offsetLeft}px)`;
  $$('#source [data-os]').forEach((el) => (el.hidden = !el.dataset.os.split(' ').includes(k))); $$('#source [data-pr]').forEach((p) => (p.textContent = k === 'win' ? 'PS> ' : '$ ')); if (f) sB[i].focus(); }
const curO = () => (sB.find((b) => b.getAttribute('aria-selected') === 'true') || sB[0]).dataset.o;
sB.forEach((b, i) => { b.addEventListener('click', () => { setO(b.dataset.o); ScrollTrigger.refresh(); }); b.addEventListener('keydown', (e) => { const m = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (m) { e.preventDefault(); setO(sB[(i + m + 3) % 3].dataset.o, true); } }); });
setO(OSN[OS] ? OS : 'win'); addEventListener('resize', () => setO(curO())); document.fonts && document.fonts.ready.then(() => setO(curO()));
const copy = async (t) => { try { await navigator.clipboard.writeText(t); return true; } catch (e) { const a = document.createElement('textarea'); a.value = t; a.style.cssText = 'position:fixed;opacity:0'; document.body.appendChild(a); a.select(); let ok = false; try { ok = document.execCommand('copy'); } catch (er) { /* */ } a.remove(); return ok; } };
document.addEventListener('click', async (e) => { const b = e.target.closest('.cp'); if (!b) return; const ok = await copy(b.dataset.c); b.textContent = ok ? 'Copied' : 'Ctrl+C'; b.classList.add('done'); say(ok ? 'Copied' : 'Copy failed — select and copy'); clearTimeout(b._t); b._t = setTimeout(() => { b.classList.remove('done'); b.textContent = 'Copy'; }, 1600); });
$$('.more details').forEach((d) => d.addEventListener('toggle', () => ScrollTrigger.refresh()));
$$('.qa details').forEach((d) => d.addEventListener('toggle', () => ScrollTrigger.refresh()));
