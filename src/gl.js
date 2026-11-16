// The stage: ~2,000 job cards as one instanced mesh that re-forms itself for every chapter.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const LIME = '#C8FF3D', BONE = '#ECE8DF', INK = '#0B0B0B';
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const ss = (t) => t * t * (3 - 2 * t);
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const rr = (a, b) => a + rnd() * (b - a);

const TITLES = [['AI Engineer', 'Hyderabad · 0–2 yrs'], ['ML Engineer', 'Bengaluru · 1–3 yrs'], ['LLM Engineer', 'Remote India'], ['Frontend Engineer', 'React · TypeScript'],
  ['Senior AI Engineer', '6+ yrs'], ['Platform Engineer', 'Kubernetes'], ['Data Analyst', 'Immediate joiner'], ['Sales Executive', 'Field role'],
  ['Backend Engineer', 'Berlin · on-site'], ['Product Designer', 'Mumbai'], ['DevOps Engineer', 'Pune'], ['QA Engineer', 'Chennai'],
  ['Data Scientist', 'London'], ['Support Engineer', 'Night shift'], ['Marketing Lead', 'Delhi'], ['Android Developer', 'Kochi']];
const SW = ['#1F3D36', '#C2552D', '#3B3F8C', '#8A6D1F', '#5A2A4A', '#2E5E86', '#6B6B63', '#0B0B0B'];

function rrect(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }

function atlas() {
  const CW = 512, CH = 320, cv = document.createElement('canvas'); cv.width = CW * 4; cv.height = CH * 4; const c = cv.getContext('2d');
  TITLES.forEach(([t, s], i) => {
    const x = (i % 4) * CW, y = Math.floor(i / 4) * CH, dark = i % 7 === 5;
    c.save(); c.translate(x, y);
    c.fillStyle = dark ? '#1A1A18' : BONE; c.fillRect(0, 0, CW, CH);
    const g = c.createLinearGradient(0, 0, CW, CH); g.addColorStop(0, 'rgba(255,255,255,.10)'); g.addColorStop(1, 'rgba(0,0,0,.08)'); c.fillStyle = g; c.fillRect(0, 0, CW, CH);
    c.fillStyle = SW[i % SW.length]; rrect(c, 36, 36, 76, 76, 16); c.fill();
    c.fillStyle = '#fff'; c.font = '700 40px "Bricolage Grotesque", sans-serif'; c.textAlign = 'center'; c.fillText(t[0], 74, 89); c.textAlign = 'left';
    c.fillStyle = dark ? '#8d8d85' : '#77756d'; c.font = '500 19px "Geist Mono", monospace'; c.fillText('NO. ' + String(i * 37 + 104), 132, 62);
    c.fillStyle = dark ? '#55554f' : '#cfcbc0'; rrect(c, 132, 80, 150, 12, 6); c.fill();
    c.fillStyle = dark ? '#F3F0E8' : INK; c.font = '700 46px "Bricolage Grotesque", sans-serif'; c.fillText(t, 36, 178);
    c.fillStyle = dark ? '#a9a9a0' : '#55534c'; c.font = '500 22px "Geist Mono", monospace'; c.fillText(s, 36, 216);
    c.fillStyle = dark ? '#3a3a36' : '#d6d2c7'; rrect(c, 36, 250, 130, 34, 17); c.fill(); rrect(c, 178, 250, 96, 34, 17); c.fill(); rrect(c, CW - 120, 250, 84, 34, 17); c.fill();
    c.restore();
  });
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

function paper(kind) {
  const W = 768, H = 1056, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const c = cv.getContext('2d');
  c.fillStyle = '#F6F3EC'; c.fillRect(0, 0, W, H);
  const bar = (x, y, w, h = 12, col = '#D9D5CA') => { c.fillStyle = col; rrect(c, x, y, w, h, h / 2); c.fill(); };
  const hl = (x, y, w, h = 34) => { c.fillStyle = 'rgba(200,255,61,.75)'; c.fillRect(x, y, w, h); };
  c.fillStyle = INK;
  if (kind === 'cover') {
    c.font = '500 20px "Geist Mono", monospace'; c.fillStyle = '#8b887f'; c.fillText('COVER LETTER · UNDER 300 WORDS', 64, 90);
    c.fillStyle = INK; c.font = '700 54px "Bricolage Grotesque", sans-serif'; c.fillText('Dear team,', 64, 180);
    let y = 240; for (let i = 0; i < 16; i++) { if (i === 5 || i === 11) y += 26; if (i === 8) { bar(64, y, 520, 12, '#c9c5ba'); c.strokeStyle = '#E2472C'; c.lineWidth = 5; c.beginPath(); c.moveTo(56, y + 6); c.lineTo(596, y + 4); c.stroke(); c.fillStyle = '#E2472C'; c.font = '600 18px "Geist Mono", monospace'; c.fillText('NOT IN YOUR PROFILE', 64, y + 44); y += 70; continue; } bar(64, y, [600, 640, 560, 620, 380][i % 5]); y += 34; }
    c.fillStyle = INK; c.font = '400 44px "Instrument Serif", serif'; c.fillText('Asha Rao', 64, H - 110);
  } else {
    c.font = '700 64px "Bricolage Grotesque", sans-serif'; c.fillText('Asha Rao', 64, 124);
    c.font = '500 19px "Geist Mono", monospace'; c.fillStyle = '#8b887f'; c.fillText(kind === 'cv' ? 'CURRICULUM VITAE · WHOLE CAREER' : 'asha@example.com · Hyderabad', 64, 162);
    const sec = (y, t) => { c.fillStyle = '#8b887f'; c.font = '600 17px "Geist Mono", monospace'; c.fillText(t, 64, y); c.fillStyle = '#cfcbc0'; c.fillRect(64, y + 12, W - 128, 2); };
    sec(230, 'EXPERIENCE');
    if (kind === 'resume') hl(372, 258, 248);
    c.fillStyle = INK; c.font = '600 27px "Geist", sans-serif'; c.fillText('AI Engineer, Acme Labs', 64, 284); c.font = '500 21px "Geist Mono", monospace'; c.fillText('Jun 2024 – present', 380, 283);
    bar(64, 310, 610); bar(64, 340, 540);
    if (kind === 'resume') hl(64, 372, 420);
    c.fillStyle = INK; c.font = '500 23px "Geist", sans-serif'; c.fillText('Python · LangChain · FAISS · RAG', 70, 397); bar(64, 426, 580);
    c.font = '600 27px "Geist", sans-serif'; c.fillText('ML Intern, Nimbus', 64, 490); c.font = '500 21px "Geist Mono", monospace'; c.fillText('Jan – May 2024', 380, 489);
    bar(64, 516, 590); bar(64, 546, 420);
    sec(626, 'SKILLS'); bar(64, 662, 140, 30, '#E3DFD4'); bar(216, 662, 110, 30, '#E3DFD4'); bar(338, 662, 150, 30, '#E3DFD4'); bar(500, 662, 120, 30, '#E3DFD4');
    sec(752, kind === 'cv' ? 'PROJECTS' : 'EDUCATION'); bar(64, 790, 520); bar(64, 820, 600); if (kind === 'cv') { bar(64, 850, 480); bar(64, 880, 560); sec(940, 'CERTIFICATES'); bar(64, 976, 440); }
    else { sec(900, 'LOCATION'); hl(64, 926, 330); c.fillStyle = INK; c.font = '500 23px "Geist", sans-serif'; c.fillText('Hyderabad · not relocating', 70, 951); }
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// The agent's browser: a tiny looping film of a form being filled, drawn to a canvas every few frames.
function agentScreen() {
  const W = 1024, H = 680, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const F = [['Full name', 'Asha Rao', .8, 2.0], ['Email', 'asha@example.com', 2.5, 4.0], ['Phone', '+91   98765 43210', 4.5, 5.6], ['College', 'Example College of Engineering', 6.0, 7.4]];
  const pts = [[.0, 700, 560], [.8, 330, 190], [2.5, 330, 262], [4.5, 330, 334], [6.0, 330, 406], [7.8, 330, 478], [8.6, 190, 548], [9.4, 190, 610], [14, 700, 560]];
  const draw = (time) => {
    const t = time % 14.5;
    c.fillStyle = '#F4F1EA'; c.fillRect(0, 0, W, H);
    c.fillStyle = '#E2DED3'; c.fillRect(0, 0, W, 64); c.fillStyle = '#c4c0b4'; [28, 54, 80].forEach((x) => { c.beginPath(); c.arc(x, 32, 8, 0, 7); c.fill(); });
    c.fillStyle = '#F4F1EA'; rrect(c, 116, 14, 620, 36, 18); c.fill(); c.fillStyle = '#77756d'; c.font = '500 18px "Geist Mono", monospace'; c.fillText('careers.example.com/apply/ai-engineer', 136, 39);
    const you = t > 9.0 && t < 10.6, need = t > 8.6 && t <= 9.0;
    c.fillStyle = you ? '#1f7a5c' : '#b3541e'; c.beginPath(); c.arc(790, 32, 7, 0, 7); c.fill(); c.font = '600 17px "Geist Mono", monospace'; c.fillText(you ? 'YOU' : 'AGENT', 806, 38);
    c.fillStyle = INK; c.font = '700 34px "Bricolage Grotesque", sans-serif'; c.fillText('Apply · AI Engineer', 56, 124); c.fillStyle = '#77756d'; c.font = '500 18px "Geist", sans-serif'; c.fillText('Example Company · Hyderabad', 58, 152);
    F.forEach(([l, v, a, b], i) => {
      const y = 170 + i * 72, on = t >= a && t < b + .3;
      c.fillStyle = '#55534c'; c.font = '600 18px "Geist", sans-serif'; c.fillText(l, 56, y + 32);
      c.fillStyle = '#fff'; rrect(c, 190, y, 560, 48, 10); c.fill(); c.lineWidth = on ? 3 : 1.5; c.strokeStyle = on ? '#9BD41F' : '#d3cfc4'; c.stroke();
      const n = Math.floor(clamp((t - a) / (b - a), 0, 1) * v.length); c.fillStyle = INK; c.font = '500 20px "Geist", sans-serif'; c.fillText(v.slice(0, n) + (on && n < v.length ? '|' : ''), 206, y + 31);
    });
    c.fillStyle = '#55534c'; c.font = '600 18px "Geist", sans-serif'; c.fillText('Resume', 56, 490);
    c.fillStyle = '#fff'; rrect(c, 190, 458, 560, 48, 10); c.fill(); c.setLineDash(t > 8.2 ? [] : [6, 5]); c.strokeStyle = '#d3cfc4'; c.lineWidth = 1.5; c.stroke(); c.setLineDash([]);
    c.fillStyle = t > 8.2 ? INK : '#9a978d'; c.font = '500 18px "Geist Mono", monospace'; c.fillText(t > 8.2 ? 'Asha_Rao_Resume.pdf' : 'No file chosen', 206, 489);
    // "not a robot": the agent stops, a person ticks it, the agent carries on
    c.fillStyle = '#EDEAE1'; rrect(c, 56, 524, 430, 54, 10); c.fill(); c.strokeStyle = need || you ? '#E08A22' : '#d3cfc4'; c.lineWidth = need || you ? 3 : 1.5; c.stroke();
    c.fillStyle = '#fff'; rrect(c, 72, 538, 26, 26, 5); c.fill(); c.strokeStyle = '#9a978d'; c.lineWidth = 1.5; c.stroke();
    if (t > 9.8) { c.strokeStyle = '#1f7a5c'; c.lineWidth = 4; c.beginPath(); c.moveTo(77, 551); c.lineTo(84, 558); c.lineTo(94, 544); c.stroke(); }
    c.fillStyle = '#43413b'; c.font = '500 19px "Geist", sans-serif'; c.fillText('I’m not a robot', 112, 558);
    const msg = t < 8.6 ? null : t < 9.0 ? ['NEEDS YOU', '#E08A22'] : t < 10.6 ? ['YOU’RE IN CONTROL', '#1f7a5c'] : t < 12 ? ['GIVEN BACK · CARRIES ON', INK] : ['READY · YOU REVIEW FIRST', INK];
    if (msg) { c.font = '600 17px "Geist Mono", monospace'; const w = c.measureText(msg[0]).width + 40; c.fillStyle = msg[1]; rrect(c, 520, 532, w, 40, 20); c.fill(); c.fillStyle = '#fff'; c.fillText(msg[0], 540, 558); }
    // step log
    c.fillStyle = '#EAE6DC'; c.fillRect(780, 64, 244, H - 64); c.fillStyle = '#8b887f'; c.font = '600 14px "Geist Mono", monospace'; c.fillText('STEPS', 800, 100);
    [['Kit checked', .2], ['Type name', 2.0], ['Email, phone', 5.6], ['College ≠ university', 7.4], ['Upload resume', 8.2], ['Needs a person', 8.6], ['You took over', 9.0], ['Given back', 10.6], ['Ready to review', 12]].forEach(([s, at], i) => {
      if (t < at) return; const y = 118 + i * 56; c.fillStyle = '#F8F6F0'; rrect(c, 796, y, 212, 44, 8); c.fill(); c.fillStyle = (i === 5) ? '#b3541e' : (i === 6 || i === 7) ? '#1f7a5c' : '#2a2925'; c.font = '500 16px "Geist", sans-serif'; c.fillText(s, 810, y + 28);
    });
    // cursor
    let k = 0; while (k < pts.length - 2 && t > pts[k + 1][0]) k++;
    const a = pts[k], b = pts[k + 1], u = ss(clamp((t - a[0]) / Math.min(.7, b[0] - a[0]), 0, 1)), x = lerp(a[1], b[1], u), y = lerp(a[2], b[2], u);
    c.save(); c.translate(x, y); c.fillStyle = you ? '#1f7a5c' : LIME; c.strokeStyle = INK; c.lineWidth = 2.5; c.lineJoin = 'round'; c.beginPath(); c.moveTo(0, 0); c.lineTo(26, 20); c.lineTo(14, 22); c.lineTo(20, 36); c.lineTo(14, 39); c.lineTo(8, 25); c.lineTo(0, 33); c.closePath(); c.fill(); c.stroke(); c.restore();
    tex.needsUpdate = true;
  };
  return { tex, draw };
}

export function initGL(canvas, { reduce }) {
  const FAST = /[?&]fast/.test(location.search); // test mode: low-res, no bloom, instant morphs
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = .95;
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#060606'); scene.fog = new THREE.FogExp2('#060606', .03);
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = .5;
  const cam = new THREE.PerspectiveCamera(35, 1, .1, 120);
  const key = new THREE.DirectionalLight('#fff3e2', 2.4); key.position.set(-4, 6, 8); scene.add(key);
  const glowL = new THREE.PointLight(LIME, 0, 14, 1.6); scene.add(glowL);

  const small = Math.min(innerWidth, innerHeight) < 700;
  const N = small ? 800 : 1900, M = 8, T = 30; // M matches, T on the tracker board
  let W = 1, H = 1, portrait = false, L = { cx: 2.35, cy: 0, k: 1 };

  // --- instanced cards
  const sh = new THREE.Shape(), cw = 1, ch = .625, r = .05;
  sh.moveTo(-cw / 2 + r, -ch / 2); sh.lineTo(cw / 2 - r, -ch / 2); sh.quadraticCurveTo(cw / 2, -ch / 2, cw / 2, -ch / 2 + r); sh.lineTo(cw / 2, ch / 2 - r); sh.quadraticCurveTo(cw / 2, ch / 2, cw / 2 - r, ch / 2); sh.lineTo(-cw / 2 + r, ch / 2); sh.quadraticCurveTo(-cw / 2, ch / 2, -cw / 2, ch / 2 - r); sh.lineTo(-cw / 2, -ch / 2 + r); sh.quadraticCurveTo(-cw / 2, -ch / 2, -cw / 2 + r, -ch / 2);
  const geo = new THREE.ShapeGeometry(sh, 4); const uv = geo.attributes.uv, ps = geo.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, ps.getX(i) / cw + .5, ps.getY(i) / ch + .5);
  const aCell = new Float32Array(N * 2), aState = new Float32Array(N * 2);
  for (let i = 0; i < N; i++) { const c = i < M ? [0, 1, 2, 0, 1, 2, 0, 1][i] : Math.floor(rnd() * 16); aCell[i * 2] = c % 4; aCell[i * 2 + 1] = 3 - Math.floor(c / 4); }
  geo.setAttribute('aCell', new THREE.InstancedBufferAttribute(aCell, 2));
  const stAttr = new THREE.InstancedBufferAttribute(aState, 2); stAttr.setUsage(THREE.DynamicDrawUsage); geo.setAttribute('aState', stAttr);
  const mat = new THREE.MeshStandardMaterial({ map: atlas(), roughness: .5, metalness: 0, side: THREE.DoubleSide });
  mat.onBeforeCompile = (s) => {
    s.vertexShader = s.vertexShader.replace('#include <common>', '#include <common>\nattribute vec2 aCell; attribute vec2 aState; varying vec2 vState; varying vec2 vLoc;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvLoc = uv; vState = aState; vMapUv = (uv + aCell) * .25;');
    s.fragmentShader = s.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vState; varying vec2 vLoc;')
      .replace('#include <map_fragment>', '#include <map_fragment>\nif(!gl_FrontFacing) diffuseColor.rgb = vec3(.035);\ndiffuseColor.rgb *= mix(1., .16, vState.y);')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\nfloat ed = min(min(vLoc.x,1.-vLoc.x)*1.6, min(vLoc.y,1.-vLoc.y));\nfloat rim = 1.-smoothstep(.0,.07,ed);\ntotalEmissiveRadiance += vec3(.58,1.,.045) * vState.x * (rim*1.5 + .02) + diffuseColor.rgb * vState.x * .05;');
  };
  const cards = new THREE.InstancedMesh(geo, mat, N); cards.frustumCulled = false; cards.instanceMatrix.setUsage(THREE.DynamicDrawUsage); scene.add(cards);

  // --- formations
  const e = new THREE.Euler(), q = new THREE.Quaternion(), FN = 9;
  const mk = () => ({ p: new Float32Array(N * 3), q: new Float32Array(N * 4), s: new Float32Array(N), g: new Float32Array(N), d: new Float32Array(N), amp: .1 });
  let F = [];
  const set = (f, i, x, y, z, rx, ry, rz, s, g = 0, d = 0, ord = 'XYZ') => { f.p[i * 3] = x; f.p[i * 3 + 1] = y; f.p[i * 3 + 2] = z; q.setFromEuler(e.set(rx, ry, rz, ord)); q.toArray(f.q, i * 4); f.s[i] = s; f.g[i] = g; f.d[i] = d; };
  const bg = new Float32Array(N * 7), dl = new Float32Array(N), ph = new Float32Array(N), sw = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { bg.set([rr(-36, 36), rr(-18, 18), rr(-48, -16), rr(-.6, .6), rr(-.9, .9), rr(-.5, .5), rr(.9, 1.5)], i * 7); dl[i] = rnd(); ph[i] = rnd() * 6.28; sw.set([rr(-1, 1), rr(-1, 1), rr(-1, 1)], i * 3); }
  const toBg = (f, i, d = .55) => set(f, i, bg[i * 7], bg[i * 7 + 1], bg[i * 7 + 2], bg[i * 7 + 3], bg[i * 7 + 4], bg[i * 7 + 5], bg[i * 7 + 6], 0, d);
  function build() {
    seed = 97; const { cx, cy, k } = L; F = Array.from({ length: FN }, mk);
    // 0 · the storm
    F[0].amp = .5; for (let i = 0; i < N; i++) { const R = 7.5 + Math.pow(rnd(), .8) * 19, a = rnd() * 6.283; set(F[0], i, Math.cos(a) * R, rr(-10, 10), Math.sin(a) * R - 4, rr(-3, 3), rr(-3, 3), rr(-3, 3), rr(.8, 1.7), 0, rnd() < .5 ? .25 : 0); }
    // 1 · the wall (an endless feed, curved around you)
    { const R = 15, rows = Math.round(Math.sqrt(N / 3.4)), cols = Math.ceil(N / rows), da = 1.1 / R; F[1].amp = .03;
      for (let i = 0; i < N; i++) { const c = i % cols, r2 = Math.floor(i / cols), a = (c - (cols - 1) / 2) * da; set(F[1], i, Math.sin(a) * R, (r2 - (rows - 1) / 2) * .72, 7 - Math.cos(a) * R, 0, -a, 0, 1, 0, .42); } }
    // 2 · rings around the resume
    { F[2].amp = .12; const tilt = [[.5, .2], [-.35, -.5], [.15, .9]];
      for (let i = 0; i < N; i++) { const ring = i % 3, R = (3.1 + ring * 1.15 + rr(-.12, .12)) * k, a = (i / N) * 6.283 * (7 + ring * 2) + ring, [tx, tz] = tilt[ring];
        let x = Math.cos(a) * R, y = rr(-.12, .12), z = Math.sin(a) * R; const y1 = y * Math.cos(tx) - z * Math.sin(tx), z1 = y * Math.sin(tx) + z * Math.cos(tx); const x2 = x * Math.cos(tz) - y1 * Math.sin(tz), y2 = x * Math.sin(tz) + y1 * Math.cos(tz);
        set(F[2], i, cx + x2, cy + y2, z1 - .5, tx, -a + 1.57, tz, .3 * k, 0, .3); } }
    // 3 · the funnel: streams from many sources pulled to one point
    { F[3].amp = .05; for (let i = 0; i < N; i++) { const t = i / N, arm = i % 6, a = arm * 1.047 + t * 3.2 + rr(-.16, .16), R = 2.7 + t * 2.2 + rr(-.15, .15); set(F[3], i, Math.cos(a) * R, Math.sin(a) * R, 6 - t * 52, 0, -1.571 + .55, a, .95, 0, arm % 2 ? .5 : .12, 'ZYX'); } }
    // 4 · the cut: eight stay, lit; the rest fall away
    { for (let i = 0; i < N; i++) { if (i < M) { const c = i % 2, r2 = Math.floor(i / 2); set(F[4], i, cx + (c - .5) * 1.16 * k + (r2 % 2) * .08, cy + (1.5 - r2) * .76 * k, .6 - r2 * .1, 0, -.22, (c - .5) * .03, 1.02 * k, i === 0 ? 1 : .55, 0); } else toBg(F[4], i, .86); } }
    // 5 · documents: the best one above three papers
    { for (let i = 0; i < N; i++) { if (i === 0) set(F[5], i, cx - 1.75 * k, cy + 1.42 * k, 1.2, 0, .1, -.06, .78 * k, 1, 0); else toBg(F[5], i, .86); } }
    // 6 · the agent
    { for (let i = 0; i < N; i++) toBg(F[6], i, .84); }
    // 7 · the board
    { const cnt = [7, 6, 6, 4, 2, 5]; let n = 0; const col = [];
      cnt.forEach((c, ci) => { for (let j = 0; j < c; j++) col.push([ci, j]); });
      for (let i = 0; i < N; i++) { if (i < T) { const [ci, j] = col[i === 0 ? 13 : i <= 13 ? i - 1 : i]; set(F[7], i, (ci - 2.5) * 1.12 * k + (portrait ? 0 : 1.2), cy + 2.05 * k - j * .7 * k, -j * .22 + .2, -.3, portrait ? 0 : -.2, 0, .98 * k, i === 0 ? 1 : 0, ci === 5 ? .5 : 0); } else toBg(F[7], i, .86); n++; } }
    // 8 · the X
    { F[8].amp = .06; for (let i = 0; i < N; i++) { const t = rr(-1, 1), b = i % 2, s = 4.3 * k; set(F[8], i, t * s + rr(-.35, .35), (b ? -t : t) * s + rr(-.35, .35) + (portrait ? 1.2 : 0), rr(-1.4, 1.2) - 1, rr(-.5, .5), rr(-.5, .5), rr(-.6, .6), rr(.3, .55), b ? .5 : 0, b ? 0 : .5); } }
  }

  // --- hero props
  const bent = (w, h) => { const g = new THREE.PlaneGeometry(w, h, 14, 1), p = g.attributes.position; for (let i = 0; i < p.count; i++) { const x = p.getX(i) / w; p.setZ(i, -x * x * .22); } g.computeVertexNormals(); return g; };
  const sheet = (kind) => new THREE.Mesh(bent(1.56, 2.14), new THREE.MeshStandardMaterial({ map: paper(kind), roughness: .82, color: '#c9c7c2', side: THREE.DoubleSide }));
  const resume = sheet('resume'); scene.add(resume);
  const scan = new THREE.Mesh(new THREE.PlaneGeometry(1.7, .022), new THREE.MeshBasicMaterial({ color: new THREE.Color(LIME).multiplyScalar(2.2), toneMapped: false, transparent: true })); scene.add(scan);
  const docs = ['resume', 'cover', 'cv'].map((k2) => { const m = sheet(k2); scene.add(m); return m; });
  const ag = agentScreen();
  const brow = new THREE.Group(); scene.add(brow);
  const rsh = (w, h, r2) => { const s = new THREE.Shape(); s.moveTo(-w / 2 + r2, -h / 2); s.lineTo(w / 2 - r2, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r2); s.lineTo(w / 2, h / 2 - r2); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r2, h / 2); s.lineTo(-w / 2 + r2, h / 2); s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r2); s.lineTo(-w / 2, -h / 2 + r2); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r2, -h / 2); return s; };
  const frame = new THREE.Mesh(new THREE.ExtrudeGeometry(rsh(4.36, 2.94, .14), { depth: .08, bevelEnabled: true, bevelSize: .02, bevelThickness: .02, bevelSegments: 3 }), new THREE.MeshStandardMaterial({ color: '#141414', roughness: .32, metalness: .85 })); frame.position.z = -.11; brow.add(frame);
  const scrG = new THREE.ShapeGeometry(rsh(4.2, 2.79, .08), 6); { const u = scrG.attributes.uv, p = scrG.attributes.position; for (let i = 0; i < u.count; i++) u.setXY(i, p.getX(i) / 4.2 + .5, p.getY(i) / 2.79 + .5); }
  const scr = new THREE.Mesh(scrG, new THREE.MeshBasicMaterial({ map: ag.tex, color: '#b8b8b8' })); brow.add(scr);

  // --- post
  const rt = new THREE.WebGLRenderTarget(1, 1, { samples: small || FAST ? 0 : 4, type: THREE.HalfFloatType });
  const comp = new EffectComposer(renderer, rt); comp.addPass(new RenderPass(scene, cam));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .32, .6, 1.0); if (!FAST) comp.addPass(bloom);
  const fin = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uT: { value: 0 } }, vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
    fragmentShader: 'uniform sampler2D tDiffuse; uniform float uT; varying vec2 vUv; void main(){ vec2 c=vUv-.5; float d=dot(c,c); vec2 o=c*d*.006; vec3 col=vec3(texture2D(tDiffuse,vUv+o).r,texture2D(tDiffuse,vUv).g,texture2D(tDiffuse,vUv-o).b); col*=1.-d*1.15; float n=fract(sin(dot(vUv*vec2(1731.,977.)+fract(uT)*37.,vec2(12.9898,78.233)))*43758.5453); col+=(n-.5)*.03*(.4+col.g); gl_FragColor=vec4(col,1.); }' });
  comp.addPass(fin); comp.addPass(new OutputPass());

  function resize() {
    W = canvas.clientWidth || innerWidth; H = canvas.clientHeight || innerHeight; const pr = Math.min(devicePixelRatio || 1, small ? 1.5 : 1.6) * qual;
    renderer.setPixelRatio(pr); renderer.setSize(W, H, false); comp.setPixelRatio(pr); comp.setSize(W, H);
    cam.aspect = W / H; const p2 = W / H < .85; cam.fov = p2 ? 52 : 35; cam.updateProjectionMatrix();
    const nl = p2 ? { cx: 0, cy: 1.9, k: .8 } : { cx: W / H < 1.35 ? 1.7 : 2.35, cy: 0, k: W / H < 1.35 ? .82 : 1 };
    if (p2 !== portrait || nl.cx !== L.cx || !F.length) { portrait = p2; L = nl; build(); }
  }
  let qual = FAST ? .5 : 1; resize(); addEventListener('resize', resize);

  // --- loop
  const CAM = [[0, 0, 9, 0], [0, 0, 7, 0], [0, 0, 9, 0], [0, 0, 8, -20], [0, 0, 9, 0], [0, 0, 9, 0], [0, 0, 9, 0], [0, .2, 9.6, 0], [0, 0, 10.5, 0]];
  const m4 = new THREE.Matrix4(), v = new THREE.Vector3(), s3 = new THREE.Vector3(), qa = [0, 0, 0, 1];
  let pT = 0, pC = 0, mx = 0, my = 0, cxm = 0, cym = 0, spin = 0, spinV = 0, running = false, active = true, last = 0, time = 0, slow = 0, fr = 0, agT = 0;
  addEventListener('pointermove', (ev) => { const nx = ev.clientX / innerWidth * 2 - 1; spinV += (nx - mx) * .5; mx = nx; my = ev.clientY / innerHeight * 2 - 1; }, { passive: true });
  const wgt = (i) => clamp(1 - Math.abs(pC - i) * 1.5, 0, 1);

  function tick(now) {
    if (!active || document.hidden) { running = false; return; }
    requestAnimationFrame(tick);
    const dt = Math.min(.05, (now - last) / 1000 || .016); last = now; if (!reduce) time += dt;
    pC += (pT - pC) * (reduce || FAST || /[?&]snap/.test(location.search) ? 1 : Math.min(1, dt * 3.2)); if (Math.abs(pT - pC) < .0004) pC = pT;
    const i0 = clamp(Math.floor(pC), 0, FN - 2), f = clamp(pC - i0, 0, 1), A = F[i0], B = F[i0 + 1], arr = cards.instanceMatrix.array;
    const amp = lerp(A.amp, B.amp, f);
    for (let i = 0; i < N; i++) {
      const t = ss(clamp(f * 1.7 - dl[i] * .7, 0, 1)), i3 = i * 3, bow = Math.sin(Math.PI * t) * 1.6, w = time * .5 + ph[i];
      v.set(lerp(A.p[i3], B.p[i3], t) + sw[i3] * bow + Math.sin(w) * amp, lerp(A.p[i3 + 1], B.p[i3 + 1], t) + sw[i3 + 1] * bow + Math.cos(w * .8) * amp, lerp(A.p[i3 + 2], B.p[i3 + 2], t) + sw[i3 + 2] * bow);
      THREE.Quaternion.slerpFlat(qa, 0, A.q, i * 4, B.q, i * 4, t); q.fromArray(qa);
      const sc = lerp(A.s[i], B.s[i], t); s3.set(sc, sc, sc); m4.compose(v, q, s3).toArray(arr, i * 16);
      const g = lerp(A.g[i], B.g[i], t); aState[i * 2] = g * (.82 + .18 * Math.sin(time * 2 + ph[i])); aState[i * 2 + 1] = lerp(A.d[i], B.d[i], t);
    }
    cards.instanceMatrix.needsUpdate = true; stAttr.needsUpdate = true;
    // the storm turns slowly, and a little with your hand
    spinV *= .94; spin += spinV * dt * 2; spin *= .995; const w0 = clamp(1 - pC, 0, 1), w8 = clamp(pC - 7, 0, 1);
    cards.rotation.y = (Math.sin(time * .07) * .35 + time * .012 + spin) * w0 + Math.sin(time * .25) * .12 * w8;
    cards.rotation.x = my * .04 * w0;
    // camera
    const a = CAM[i0], b = CAM[i0 + 1], ft = ss(f), z = portrait ? 1.45 : 1;
    cxm += (mx * .55 - cxm) * Math.min(1, dt * 2.5); cym += (-my * .32 - cym) * Math.min(1, dt * 2.5);
    cam.position.set(lerp(a[0], b[0], ft) + cxm, lerp(a[1], b[1], ft) + cym + (portrait ? .4 : 0), lerp(a[2], b[2], ft) * z - (i0 === 3 ? f * 2.5 : 0) - (i0 === 2 ? f * 1 : 0));
    cam.lookAt(cxm * .2, (portrait ? .4 : 0) + cym * .2, lerp(a[3], b[3], ft));
    const { cx, cy, k } = L;
    // resume + scan line (chapter 2)
    const w2 = ss(wgt(2)); resume.visible = scan.visible = w2 > .002;
    if (resume.visible) { resume.position.set(cx, cy - (1 - w2) * 5 + Math.sin(time * .8) * .04, .2); resume.rotation.set(-.05 + (1 - w2) * 1.2, -.28 + Math.sin(time * .5) * .05, .04 - (1 - w2) * .6); resume.scale.setScalar(1.4 * k);
      const sy = Math.sin(time * 1.1) * .9; scan.position.set(cx - .02, cy + sy * k * 1.4, .55); scan.rotation.y = -.28; scan.scale.set(k * 1.4, 1, 1); scan.material.opacity = w2 * w2; }
    // three documents (chapter 5)
    const w5 = wgt(5); docs.forEach((d, i) => { const wi = ss(clamp(w5 * 1.5 - i * .2, 0, 1)); d.visible = wi > .002; if (!d.visible) return;
      d.position.set(cx - .25 * k + (i - 1) * 1.08 * k, cy - .25 * k - (1 - wi) * 5 + Math.sin(time * .7 + i) * .035, i === 1 ? .55 : .1); d.rotation.set(-.04 + (1 - wi) * .9, -.2 + (i - 1) * -.14, (1 - i) * .07 + (1 - wi) * (i - 1) * .5); d.scale.setScalar(.96 * k); });
    // the browser (chapter 6)
    const w6 = ss(wgt(6)); brow.visible = w6 > .002;
    if (brow.visible) { brow.position.set(portrait ? 0 : cx - .8, cy + (portrait ? .1 : 0) - (1 - w6) * 5.5 + Math.sin(time * .6) * .05, .4); brow.rotation.set(.03 + (1 - w6) * .5, (portrait ? 0 : -.36) + Math.sin(time * .4) * .03 + cxm * .08, (1 - w6) * -.2); brow.scale.setScalar((portrait ? .62 : .98) * (W / H < 1.35 && !portrait ? .8 : 1));
      agT += dt; if (agT > .07) { agT = 0; ag.draw(reduce ? 12.5 : time); } }
    glowL.position.set(cx, cy, 2.5); glowL.intensity = (wgt(4) + wgt(5) * .5 + w8 * .6) * 5;
    fin.uniforms.uT.value = time; comp.render();
    // adaptive quality: drop resolution if the machine struggles
    fr++; if (dt > .034) slow++; if (fr === 80) { if (slow > 44 && qual > .55) { qual -= .2; resize(); } fr = 0; slow = 0; }
  }
  const kick = () => { if (!running && active) { running = true; last = performance.now(); requestAnimationFrame(tick); } };
  document.addEventListener('visibilitychange', kick);
  return { setP(p) { pT = p; }, setActive(a) { active = a; if (a) kick(); }, refresh() { mat.map.dispose(); mat.map = atlas(); mat.needsUpdate = true; resume.material.map = paper('resume'); docs.forEach((d, i) => (d.material.map = paper(['resume', 'cover', 'cv'][i]))); } };
}
