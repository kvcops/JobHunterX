// "Agents at work" — a small 3D office where the eight pipeline agents (animated robots) work, take breaks and talk.
//
// WORK — every work scene is triggered by a real event of the running search:
//   profile understood  → Profile analyst walks over and hands the profile to the Planner
//   searches planned    → Planner hands the plan to the Scout
//   searching / boards  → Scout runs out through the web portal (web search) or to the server room (company boards)
//   page read           → Reader reads that posting
//   dedupe              → Reader brings the stack to the Curator, who merges duplicates
//   validate good / bad → Verifier stamps it, or shakes its head and bins it
//   verdicts            → Analyst gives a thumbs-up (and a surprised face) and passes fits to the Ranker, or bins the rest
//   search complete     → the Ranker dances, everyone cheers, then a results review in the meeting room (real numbers)
//
// LIFE — when an agent has no work it lives in the office: chai in the pantry, chats at the water cooler, a sit on
// the sofa, a stand-up in the meeting room, a look at the server racks. That is clearly break time: it never shows or
// claims search progress, and any chat that mentions numbers uses the run's real counts. Work always comes first —
// an agent on a break walks straight back to its desk the moment its part of a real search starts.
//
// ROOMS — work floor (8 stations) · pantry · server room · meeting room, joined by doorways; agents walk a small
// route network so they go through doors, not walls.
import * as THREE from '../../vendor/three.module.min.js';
import { GLTFLoader } from '../../vendor/three-addons/GLTFLoader.js';
import * as SkeletonUtils from '../../vendor/three-addons/SkeletonUtils.js';

const ROBOT_URL = '/assets/models/robot.glb';
const ROBOT_HEIGHT = 2.35;

// Work floor x ∈ [-15, 15], z ∈ [-11, 11]. West wing (x < -15): server room (north) · hall · pantry (south).
// East wing (x > 15): meeting room with a lounge corner.
export const STATIONS = [
  { key: 'understand', name: 'Profile analyst', home: [-12, 4.5], face: [1, 0], hue: 18, prop: 'desk',
    intro: 'Hi! I read your resume and work out who we are searching for.' },
  { key: 'plan', name: 'Planner', home: [-12, -2.5], face: [1, 0], hue: 265, prop: 'board',
    intro: 'Hello! I plan which titles, places and company boards to search.' },
  { key: 'discover', name: 'Scout', home: [-8.5, -7.6], face: [0, 1], hue: 205, prop: 'portal',
    intro: 'Hey! I run out to the web and to company job boards to find openings.' },
  { key: 'normalize', name: 'Reader', home: [-3, -7.6], face: [0, 1], hue: 160, prop: 'shelf',
    intro: 'Hi! I open every job page and read the full description.' },
  { key: 'dedupe', name: 'Curator', home: [3, -7.6], face: [0, 1], hue: 40, prop: 'sorter',
    intro: 'Hello! I spot the same job posted on many sites and keep one.' },
  { key: 'validate', name: 'Verifier', home: [8.5, -7.6], face: [0, 1], hue: 140, prop: 'stamp',
    intro: 'Hi! I check every job is real and still open before you see it.' },
  { key: 'match', name: 'Analyst', home: [11.6, -2.8], face: [-1, 0], hue: 330, prop: 'chart',
    intro: 'Hey! I read what each job asks for and score how well you fit.' },
  { key: 'rank', name: 'Ranker', home: [11.6, 3.4], face: [-1, 0], hue: 28, prop: 'podium',
    intro: 'Hello! I rank the jobs that fit and explain why.' },
];
const hsl = (h, s, l) => new THREE.Color().setHSL((((h % 360) + 360) % 360) / 360, s, l);
const V = (x, z, y = 0) => new THREE.Vector3(x, y, z);
const short = (t, n = 46) => (t && t.length > n ? `${t.slice(0, n - 1)}…` : t || '');
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const rand = (a, b) => a + Math.random() * (b - a);
const titleOf = (msg) => {
  const q = /[“"]([^”"]+)[”"]/.exec(msg || '');
  if (q) return q[1];
  const f = /(?:requirements for|Read|·)\s+(.+?)\s+at\s+/.exec(msg || '');
  return f ? f[1].trim() : '';
};

// ---------------------------------------------------------------------------------------------- conversations
// [speaker (0 = the one who starts, 1 = the other), line, gesture?, face?]. {name} values come from the real run.
const BANTER = [
  [[0, 'Chai or coffee?'], [1, 'Irani chai. Obviously.', 'Yes'], [0, 'Osmania biscuits on the side?', null, 'Surprised'], [1, 'Now we are talking!', 'ThumbsUp']],
  [[0, 'Saw a posting asking 5 years in a 2-year-old framework', null, 'Angry'], [1, 'Classic. Straight to the bin.', 'No'], [0, 'At least we tell people why', 'Yes']],
  [[0, 'Traffic on the ORR again today?'], [1, 'I live inside a laptop. Zero traffic.', 'Wave'], [0, 'Lucky you', null, 'Sad']],
  [[0, 'Biryani for lunch?', 'Wave'], [1, 'Paradise or Bawarchi?'], [0, "Let's not start that debate again", 'No']],
  [[0, 'Why do we read company boards directly?'], [1, 'Fewer applicants there — a real person reads them', 'Yes'], [0, 'Better than being one of a thousand', 'ThumbsUp']],
  [[0, 'Does applying early really matter?'], [1, 'Yes — recruiters read the first batch first', 'Yes'], [0, 'So freshness goes up the ranking', 'ThumbsUp']],
  [[0, 'What makes a good match, really?'], [1, 'Real skills, right level, right city', 'Yes'], [0, 'Not just matching keywords', 'ThumbsUp']],
  [[0, 'Learned a new skill name today', null, 'Surprised'], [1, 'Which one?'], [0, 'Agentic AI — close to LLM and RAG work', 'Yes'], [1, 'Nice, that counts as related now', 'ThumbsUp']],
  [[0, 'Stand-up in five?'], [1, 'Only if there are samosas', 'Yes'], [0, 'Deal', 'ThumbsUp']],
  [[0, 'Mass-hiring companies again?', null, 'Angry'], [1, 'Filtered out. Good companies only.', 'No'], [0, 'That is the way', 'ThumbsUp']],
  [[0, 'Weekend plans?'], [1, 'Recharging my battery'], [0, 'Literally?', null, 'Surprised'], [1, 'Literally.', 'Yes']],
  [[0, 'The Scout never walks, have you noticed?'], [1, 'Always running through that portal', 'Wave'], [0, 'Speed matters in hiring', 'Yes']],
  [[0, 'Old postings — do we still show them?'], [1, 'Shown, but marked as possibly filled', 'Yes'], [0, 'Honest. I like it.', 'ThumbsUp']],
  [[0, 'Hyderabad or Bengaluru?'], [1, 'Wherever the good roles are', 'Wave'], [0, 'Diplomatic answer', null, 'Surprised']],
  [[0, 'Do we ever invent anything on a resume?', null, 'Surprised'], [1, 'Never. Only what is really there.', 'No'], [0, 'Good. Trust matters.', 'Yes']],
];
// break chat while a search is running (the speaker's own part is done)
const BREAK_TALK = [
  [[0, 'My part is done — chai break', 'Wave'], [1, 'Same. Now we wait for the others', 'Yes']],
  [[0, 'Quick break before the results'], [1, 'The Analyst is doing the hard part now', 'Yes']],
  [[0, 'How is the search going?'], [1, 'Moving along — everyone is busy', 'ThumbsUp']],
];
// lines that use real numbers from the current or last run (only offered when those numbers exist)
const DATA_TALK = [
  { needs: ['results'], lines: [[0, 'How many search results so far?'], [1, '{results}, and the Reader is opening them', 'Yes']] },
  { needs: ['fits', 'top'], lines: [[0, 'Any good ones yet?', null, 'Surprised'], [1, '{fits} fit so far. Best: {top}', 'ThumbsUp']] },
  { needs: ['fits'], lines: [[0, 'How did the last search go?'], [1, '{fits} roles fit out of {scored} analysed', 'ThumbsUp'], [0, 'Quality over quantity', 'Yes']] },
  { needs: ['rejected'], lines: [[0, 'So many were not a fit?'], [1, '{rejected} — wrong level, field or city', 'No'], [0, 'Better than wasting an application', 'Yes']] },
];

export async function createWorld(container, { dark = false, reducedMotion = false, onSay = () => {}, onSelect = () => {} } = {}) {
  // ------------------------------------------------------------------ renderer / scene
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.domElement.className = 'aw3d-gl';
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.5, 260);

  const owned = new Set();
  const M = (color, extra = {}) => { const m = new THREE.MeshStandardMaterial({ color, roughness: 0.75, metalness: 0.03, ...extra }); owned.add(m); return m; };
  const shade = (o) => { o.traverse((c) => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } }); return o; };
  const box = (w, h, d, m) => shade(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m));
  const cyl = (rt, rb, h, m, seg = 24, open = false) => shade(new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg, 1, open), m));
  const sphere = (r, m, seg = 20) => shade(new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.7)), m));
  const put = (o, x, y, z, ry = 0) => { o.position.set(x, y, z); o.rotation.y = ry; scene.add(o); return o; };

  // ------------------------------------------------------------------ light
  const hemi = new THREE.HemisphereLight(0xfff6ec, 0xc9b8a6, 1.0);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff0dc, 2.0);
  sun.position.set(10, 30, 18);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 16, bottom: -16, near: 1, far: 80 });
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.02;
  scene.add(sun);
  const fill = new THREE.PointLight(0xffd9b0, 18, 30, 1.6); fill.position.set(-6, 7, 2); scene.add(fill);
  const pantryLamp = new THREE.PointLight(0xffc98a, 14, 16, 1.6); pantryLamp.position.set(-20, 5, 6.5); scene.add(pantryLamp);
  const serverGlow = new THREE.PointLight(0x5aa8ff, 10, 14, 1.6); serverGlow.position.set(-20, 4, -6.5); scene.add(serverGlow);
  const meetLamp = new THREE.PointLight(0xfff1dd, 12, 20, 1.6); meetLamp.position.set(21, 6, -1); scene.add(meetLamp);

  // ------------------------------------------------------------------ textures
  function canvasTex(w, h, draw, repeat) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); }
    return t;
  }
  function plankTexture(isDark) {
    return canvasTex(512, 512, (g) => {
      const base = isDark ? [58, 48, 42] : [212, 182, 146];
      for (let row = 0; row < 16; row++) {
        let x = -((row * 97) % 180);
        while (x < 512) {
          const w = 150 + ((row * 31 + Math.abs(x)) % 90);
          const v = ((row * 13 + Math.abs(x) * 7) % 21) - 10;
          g.fillStyle = `rgb(${base[0] + v},${base[1] + v},${base[2] + v * 0.8})`; g.fillRect(x, row * 32, w, 32);
          g.fillStyle = `rgba(0,0,0,${isDark ? 0.35 : 0.14})`; g.fillRect(x, row * 32, 2, 32);
          x += w;
        }
        g.fillStyle = `rgba(0,0,0,${isDark ? 0.4 : 0.16})`; g.fillRect(0, row * 32 + 31, 512, 1.5);
      }
    }, [8.5, 4]);
  }
  function tileTexture(a, b, n = 8) {
    return canvasTex(256, 256, (g, w) => {
      const s = w / n;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { g.fillStyle = (i + j) % 2 ? a : b; g.fillRect(i * s, j * s, s, s); }
      g.strokeStyle = 'rgba(0,0,0,.12)'; g.lineWidth = 2;
      for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * s, 0); g.lineTo(i * s, w); g.stroke(); g.beginPath(); g.moveTo(0, i * s); g.lineTo(w, i * s); g.stroke(); }
    }, [3, 3]);
  }

  // ------------------------------------------------------------------ building
  const floorMat = M(0xffffff);
  put(box(52, 0.6, 23, floorMat), 1, -0.3, 0);
  const pantryFloor = M(0xffffff, { roughness: 0.6 }), serverFloor = M(0xffffff, { roughness: 0.5, metalness: 0.15 }), carpet = M(0x6d7fa3, { roughness: 0.98 });
  const zone = (x0, x1, z0, z1, m) => { const p = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0), m); p.rotation.x = -Math.PI / 2; p.position.set((x0 + x1) / 2, 0.008, (z0 + z1) / 2); p.receiveShadow = true; scene.add(p); return p; };
  zone(-25, -15, 1.5, 11.5, pantryFloor); zone(-25, -15, -11, -1, serverFloor); zone(15, 27, -11, 11.5, carpet);

  const wallMat = M(0xf4ede4), trimMat = M(0xd8cabb), partMat = M(0xe9e0d4);
  const glass = M(0xbfe0ff, { emissive: 0x9fd0ff, emissiveIntensity: 0.55, roughness: 0.15 });
  const glassPane = new THREE.MeshPhysicalMaterial({ color: 0xcfe6ff, roughness: 0.08, transmission: 0.0, transparent: true, opacity: 0.22, depthWrite: false });
  owned.add(glassPane);
  put(box(52.5, 4.6, 0.5, wallMat), 1, 2.3, -11.25);                               // north
  put(box(0.5, 4.6, 23, wallMat), -25.25, 2.3, 0);                                 // west
  put(box(0.5, 4.6, 23, wallMat), 27.25, 2.3, 0);                                  // east
  put(box(52.5, 0.28, 0.12, trimMat), 1, 0.14, -10.95);
  for (const x of [5.6, 12]) { put(box(3.4, 2.1, 0.08, glass), x, 2.6, -10.98); put(box(3.6, 0.12, 0.2, trimMat), x, 1.5, -10.95); }
  put(box(0.08, 2.1, 3.4, glass), -24.98, 2.6, 6.8);                              // pantry window
  // interior walls are low (2.4) so the camera sees into every room
  const part = (x, z, w, d) => put(box(w, 2.4, d, partMat), x, 1.2, z);
  part(-15, -5.85, 0.3, 10.3); part(-15, 6.7, 0.3, 9.6);                           // west partition, door at z ≈ 0.6
  part(-23.05, -1, 3.9, 0.3); part(-16.95, -1, 3.9, 0.3);                          // server room wall, door at x ≈ -20
  part(-23.05, 1.5, 3.9, 0.3); part(-16.95, 1.5, 3.9, 0.3);                        // pantry wall, door at x ≈ -20
  for (const [z, d] of [[-2.35, 17.3], [10.2, 2.6]]) {                             // meeting room glass, door at z ≈ 7.6
    const g = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.6, d), glassPane); g.position.set(15, 1.3, z); scene.add(g);
    put(box(0.16, 0.12, d, trimMat), 15, 2.6, z); put(box(0.16, 0.12, d, trimMat), 15, 0.06, z);
  }
  // room name plates
  function plate(text, x, z, ry = 0) {
    const t = canvasTex(512, 128, (g, w, h) => { g.fillStyle = '#1f2026'; g.fillRect(0, 0, w, h); g.fillStyle = '#fff'; g.font = '600 58px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, w / 2, h / 2 + 2); });
    const m = new THREE.MeshBasicMaterial({ map: t }); owned.add(m);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.48), m); p.position.set(x, 2.15, z); p.rotation.y = ry; scene.add(p);
  }
  plate('Pantry', -18.2, 1.68); plate('Server room', -18.2, -0.83); plate('Meeting room', 15.08, 4.6, Math.PI / 2);

  const rug = new THREE.Mesh(new THREE.PlaneGeometry(13, 7.5), M(0xc96f4a, { roughness: 0.95 }));
  rug.rotation.x = -Math.PI / 2; rug.position.set(0, 0.012, 0.6); rug.receiveShadow = true; scene.add(rug);
  const rugIn = new THREE.Mesh(new THREE.PlaneGeometry(11.6, 6.1), M(0xe6c4a0, { roughness: 0.95 }));
  rugIn.rotation.x = -Math.PI / 2; rugIn.position.set(0, 0.016, 0.6); rugIn.receiveShadow = true; scene.add(rugIn);
  const leaf = M(0x4f8f5a), pot = M(0xb5684a);
  const plants = [];
  function plant(x, z, s) {
    const g = new THREE.Group(); g.position.set(x, 0, z); scene.add(g);
    const p = cyl(0.5 * s, 0.38 * s, 0.75 * s, pot); p.position.y = 0.38 * s; g.add(p);
    for (let i = 0; i < 4; i++) { const b = sphere(0.55 * s, leaf, 12); b.position.set(Math.cos(i * 1.7) * 0.25 * s, (1.1 + i * 0.32) * s, Math.sin(i * 1.7) * 0.25 * s); b.scale.set(1, 1.25, 1); g.add(b); }
    plants.push(g);
  }
  for (const [x, z, s] of [[-14, -10, 1.2], [14, -10, 1.0], [-14, 10.4, 1.1], [7.5, 10, 0.9], [-7.5, 10, 0.9], [26.2, 10.6, 1.1], [-15.9, -1.9, 0.8]]) plant(x, z, s);

  // ------------------------------------------------------------------ station furniture (work floor)
  const wood = M(0xb88a62), darkWood = M(0x7d5a3f), metal = M(0x4b4f58), paperM = M(0xffffff, { roughness: 0.9 });
  const chairM = M(0x3b3f4a);
  function deskAt(group, w = 2.6, d = 1.1) {
    const top = box(w, 0.12, d, wood); top.position.y = 1.0; group.add(top);
    for (const [x, z] of [[-w / 2 + 0.1, -d / 2 + 0.1], [w / 2 - 0.1, -d / 2 + 0.1], [-w / 2 + 0.1, d / 2 - 0.1], [w / 2 - 0.1, d / 2 - 0.1]]) {
      const l = box(0.08, 0.98, 0.08, metal); l.position.set(x, 0.49, z); group.add(l);
    }
  }
  function monitorAt(group, hue, x = 0, z = -0.2) {
    const mon = box(1.05, 0.66, 0.06, metal); mon.position.set(x, 1.55, z); group.add(mon);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.56), M(hsl(hue, 0.55, 0.6), { emissive: hsl(hue, 0.7, 0.45), emissiveIntensity: 0.6 }));
    scr.position.set(x, 1.55, z - 0.035); scr.rotation.y = Math.PI; group.add(scr);
    const st = box(0.1, 0.36, 0.1, metal); st.position.set(x, 1.2, z); group.add(st);
    return scr;
  }
  function chairAt(group, x, z, ry = 0) {
    const c = new THREE.Group(); c.position.set(x, 0, z); c.rotation.y = ry;
    const seat = box(0.8, 0.1, 0.8, chairM); seat.position.y = 0.62; c.add(seat);
    const back = box(0.8, 0.8, 0.1, chairM); back.position.set(0, 1.05, -0.36); c.add(back);
    const leg = cyl(0.05, 0.05, 0.6, metal, 8); leg.position.y = 0.31; c.add(leg);
    const base = cyl(0.36, 0.36, 0.05, metal, 16); base.position.y = 0.03; c.add(base);
    group.add(c);
    return c;
  }
  const stations = {};
  for (const s of STATIONS) {
    const g = new THREE.Group();
    g.position.set(s.home[0], 0, s.home[1]);
    g.rotation.y = Math.atan2(s.face[0], s.face[1]);
    scene.add(g);
    const parts = { g };
    const pad = new THREE.Mesh(new THREE.CircleGeometry(2.6, 48), new THREE.MeshBasicMaterial({ color: hsl(s.hue, 0.7, 0.6), transparent: true, opacity: 0.12, depthWrite: false }));
    owned.add(pad.material);
    pad.rotation.x = -Math.PI / 2; pad.position.y = 0.02; g.add(pad); parts.pad = pad;
    const deskG = new THREE.Group(); deskG.position.z = 1.35; g.add(deskG); parts.desk = deskG;
    chairAt(g, 0, -0.25);
    if (s.prop === 'desk') { deskAt(deskG); parts.screen = monitorAt(deskG, s.hue); }
    if (s.prop === 'board') {
      deskAt(deskG, 2.2, 0.9);
      const bd = box(3.2, 2.0, 0.08, M(0xfcfcfa)); bd.position.set(0, 2.3, -1.9); g.add(bd);
      const fr = box(3.4, 0.12, 0.25, trimMat); fr.position.set(0, 1.26, -1.86); g.add(fr);
      parts.lines = [];
      for (let i = 0; i < 5; i++) {
        const w = 0.6 + ((i * 7) % 5) * 0.32;
        const l = box(w, 0.08, 0.02, M(hsl(s.hue + i * 35, 0.6, 0.5))); l.position.set(-1.0 + w / 2, 2.95 - i * 0.3, -1.85); g.add(l); parts.lines.push(l);
      }
    }
    if (s.prop === 'portal') {
      deskAt(deskG, 2.0, 0.9);
      const globe = sphere(0.36, M(hsl(s.hue, 0.6, 0.6), { emissive: hsl(s.hue, 0.7, 0.35), emissiveIntensity: 0.4 }), 20); globe.position.set(0.5, 1.45, 1.35); g.add(globe); parts.globe = globe;
      const arch = new THREE.Group(); arch.position.set(0, 0, -3.15); g.add(arch);
      const ringM = M(hsl(s.hue, 0.8, 0.55), { emissive: hsl(s.hue, 0.9, 0.5), emissiveIntensity: 1.1 });
      const ring = shade(new THREE.Mesh(new THREE.TorusGeometry(1.3, 0.14, 14, 48, Math.PI), ringM)); ring.position.y = 1.9; arch.add(ring);
      for (const x of [-1.3, 1.3]) { const p = cyl(0.14, 0.14, 1.9, ringM, 12); p.position.set(x, 0.95, 0); arch.add(p); }
      const veil = new THREE.Mesh(new THREE.PlaneGeometry(2.45, 3.1), new THREE.MeshBasicMaterial({ color: hsl(s.hue, 0.95, 0.75), transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
      owned.add(veil.material); veil.position.set(0, 1.55, 0.02); arch.add(veil);
      parts.portal = { arch, veil, ringM };
    }
    if (s.prop === 'shelf') {
      deskAt(deskG, 2.2, 0.9);
      const sh = box(3.0, 3.2, 0.7, darkWood); sh.position.set(0, 1.6, -2.4); g.add(sh);
      for (let r = 0; r < 4; r++) for (let i = 0; i < 8; i++) {
        const bk = box(0.26, 0.5 + ((i * 7 + r) % 3) * 0.1, 0.5, M(hsl(s.hue + i * 41 + r * 70, 0.45, 0.55)));
        bk.position.set(-1.15 + i * 0.33, 0.45 + r * 0.76, -2.05); g.add(bk);
      }
    }
    if (s.prop === 'sorter') {
      deskAt(deskG, 3.0, 1.2);
      for (let i = 0; i < 3; i++) { const t = box(0.75, 0.08, 0.9, M(hsl(s.hue + i * 25, 0.5, 0.6))); t.position.set(0.3 + i * 0.85 - 0.85, 1.1, 0); deskG.add(t); }
    }
    if (s.prop === 'stamp') {
      deskAt(deskG, 2.4, 1.0);
      const stamp = new THREE.Group(); stamp.position.set(0.55, 1.06, 0.0); deskG.add(stamp);
      const sb = cyl(0.22, 0.26, 0.14, M(hsl(s.hue, 0.6, 0.42))); sb.position.y = 0.07; stamp.add(sb);
      const sh = cyl(0.07, 0.09, 0.42, wood, 10); sh.position.y = 0.35; stamp.add(sh);
      const kn = sphere(0.13, wood, 12); kn.position.y = 0.6; stamp.add(kn);
      parts.stamp = stamp;
    }
    if (s.prop === 'chart') {
      deskAt(deskG); parts.screen = monitorAt(deskG, s.hue, -0.4);
      parts.bars = [];
      for (let i = 0; i < 4; i++) {
        const b = box(0.2, 1, 0.2, M(hsl(s.hue + i * 15, 0.65, 0.55), { emissive: hsl(s.hue, 0.6, 0.3), emissiveIntensity: 0.25 }));
        b.position.set(0.55 + (i % 2) * 0.28, 1.2, -0.15 + Math.floor(i / 2) * 0.28); b.scale.y = 0.15; deskG.add(b); parts.bars.push(b);
      }
    }
    if (s.prop === 'podium') {
      for (const [x, h, c] of [[0, 1.0, 0.82], [-0.95, 0.68, 0.72], [0.95, 0.45, 0.66]]) { const st = box(0.92, h, 0.92, M(hsl(s.hue, 0.4, c))); st.position.set(x, h / 2, 1.5); g.add(st); }
      const gold = M(0xe7b54a, { metalness: 0.6, roughness: 0.28, emissive: 0x6b4a10, emissiveIntensity: 0.25 });
      const trophy = new THREE.Group(); trophy.position.set(0, 1.0, 1.5); g.add(trophy);
      const tb = cyl(0.22, 0.28, 0.14, gold); tb.position.y = 0.07; trophy.add(tb);
      const stem = cyl(0.06, 0.08, 0.35, gold, 10); stem.position.y = 0.3; trophy.add(stem);
      const cup = cyl(0.34, 0.14, 0.5, gold); cup.position.y = 0.72; trophy.add(cup);
      parts.trophy = trophy;
      parts.board = new THREE.Group(); parts.board.position.set(-2.2, 0, 0.4); parts.board.rotation.y = 0.55; g.add(parts.board);
      const bb2 = box(1.6, 2.2, 0.08, M(0x2f3440)); bb2.position.y = 2.0; parts.board.add(bb2);
      const bl = box(0.1, 1.0, 0.1, metal); bl.position.y = 0.5; parts.board.add(bl);
      parts.cards = new THREE.Group(); parts.board.add(parts.cards);
    }
    const pile = new THREE.Group(); pile.position.set(-0.75, 1.07, 0.1); deskG.add(pile); parts.pile = pile; parts.count = 0;
    if (s.key === 'validate' || s.key === 'match') {
      const bin = cyl(0.42, 0.34, 0.8, M(0x6b717c), 20, true); bin.position.set(1.9, 0.4, 1.1); g.add(bin);
      parts.bin = new THREE.Group(); parts.bin.position.set(1.9, 0, 1.1); g.add(parts.bin); parts.binCount = 0;
    }
    stations[s.key] = parts;
  }

  // ------------------------------------------------------------------ pantry
  const white = M(0xf7f5f0), red = M(0xd2483d, { emissive: 0x7a1a12, emissiveIntensity: 0.4 }), teal = M(0x3c8f8a);
  put(box(1.0, 1.0, 6.4, darkWood), -24.25, 0.5, 6.4);
  put(box(1.1, 0.08, 6.5, M(0xe8e2d8, { roughness: 0.4 })), -24.25, 1.04, 6.4);
  const coffee = new THREE.Group(); put(coffee, -24.3, 1.08, 4.4);
  { const b = box(0.6, 0.8, 0.55, M(0x2a2c31, { metalness: 0.4, roughness: 0.35 })); b.position.y = 0.4; coffee.add(b);
    const l = box(0.08, 0.08, 0.02, red); l.position.set(0.31, 0.62, 0); l.rotation.y = Math.PI / 2; coffee.add(l);
    const cup = cyl(0.09, 0.07, 0.14, white, 12); cup.position.set(0.18, 0.08, 0); coffee.add(cup); }
  const kettle = cyl(0.22, 0.26, 0.4, M(0xc0c4cc, { metalness: 0.7, roughness: 0.25 })); put(kettle, -24.3, 1.28, 5.5);
  put(box(1.0, 2.3, 1.0, white), -24.2, 1.15, 2.4);                                  // fridge
  put(box(0.03, 0.9, 0.06, metal), -23.68, 1.5, 2.15);
  const cooler = new THREE.Group(); put(cooler, -15.8, 0, 10.6);
  { const b = box(0.6, 1.1, 0.6, white); b.position.y = 0.55; cooler.add(b);
    const bottle = cyl(0.25, 0.25, 0.7, M(0x8fc8ff, { transparent: true, opacity: 0.7, roughness: 0.1 }), 16); bottle.position.y = 1.45; cooler.add(bottle); }
  const tableTop = cyl(0.95, 0.95, 0.08, wood, 32); put(tableTop, -20, 1.0, 7.2);
  put(cyl(0.08, 0.1, 1.0, metal, 10), -20, 0.5, 7.2);
  for (const x of [-21.25, -18.75]) { put(cyl(0.32, 0.32, 0.08, teal, 16), x, 0.72, 7.2); put(cyl(0.05, 0.05, 0.7, metal, 8), x, 0.36, 7.2); }
  const sofa = new THREE.Group(); put(sofa, -21, 0, 10.8, Math.PI);
  { const sm = M(0x9a5d7a, { roughness: 0.95 });
    const seat = box(3.0, 0.5, 1.0, sm); seat.position.y = 0.45; sofa.add(seat);
    const back = box(3.0, 0.9, 0.3, sm); back.position.set(0, 0.95, -0.42); sofa.add(back);
    for (const x of [-1.6, 1.6]) { const a = box(0.3, 0.7, 1.0, sm); a.position.set(x, 0.6, 0); sofa.add(a); } }
  // wall clock (real time) on the pantry wall
  const clockTex = canvasTex(256, 256, () => {});
  const clockMat = new THREE.MeshBasicMaterial({ map: clockTex, transparent: true }); owned.add(clockMat);
  const clockFace = new THREE.Mesh(new THREE.CircleGeometry(0.5, 40), clockMat); clockFace.position.set(-22.6, 1.85, 1.67); scene.add(clockFace);
  let clockMinute = -1;
  function drawClock() {
    const d = new Date(); const m = d.getHours() * 60 + d.getMinutes();
    if (m === clockMinute) return; clockMinute = m;
    const c = clockTex.image, g = c.getContext('2d'), r = 120;
    g.clearRect(0, 0, 256, 256);
    g.fillStyle = '#fbfaf7'; g.beginPath(); g.arc(128, 128, r, 0, Math.PI * 2); g.fill();
    g.lineWidth = 10; g.strokeStyle = '#2b2d33'; g.stroke();
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; g.lineWidth = i % 3 ? 3 : 7; g.beginPath(); g.moveTo(128 + Math.sin(a) * 96, 128 - Math.cos(a) * 96); g.lineTo(128 + Math.sin(a) * 108, 128 - Math.cos(a) * 108); g.stroke(); }
    const hand = (a, len, w, col) => { g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.beginPath(); g.moveTo(128, 128); g.lineTo(128 + Math.sin(a) * len, 128 - Math.cos(a) * len); g.stroke(); };
    hand(((d.getHours() % 12) + d.getMinutes() / 60) / 12 * Math.PI * 2, 58, 9, '#2b2d33');
    hand(d.getMinutes() / 60 * Math.PI * 2, 86, 6, '#2b2d33');
    g.fillStyle = '#d2483d'; g.beginPath(); g.arc(128, 128, 8, 0, Math.PI * 2); g.fill();
    clockTex.needsUpdate = true;
  }
  // steam from the coffee machine while someone makes chai
  const steamM = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.0, depthWrite: false }); owned.add(steamM);
  const steam = []; for (let i = 0; i < 6; i++) { const p = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), steamM.clone()); owned.add(p.material); p.visible = false; scene.add(p); steam.push({ p, t: i / 6 }); }
  let brewing = 0;

  // ------------------------------------------------------------------ server room
  const rackM = M(0x23262d, { metalness: 0.3, roughness: 0.5 });
  const ledMats = [0x44e08a, 0x5aa8ff, 0xffb547].map((c) => M(c, { emissive: c, emissiveIntensity: 1.2 }));
  const leds = [];
  function rack(x, z, ry) {
    const g = new THREE.Group(); put(g, x, 0, z, ry);
    const b = box(1.2, 2.8, 0.9, rackM); b.position.y = 1.4; g.add(b);
    for (let i = 0; i < 9; i++) {
      const u = box(1.0, 0.04, 0.02, M(0x3a3e47)); u.position.set(0, 0.4 + i * 0.27, 0.46); g.add(u);
      for (let j = 0; j < 3; j++) { const l = new THREE.Mesh(new THREE.PlaneGeometry(0.07, 0.05), ledMats[(i + j) % 3]); l.position.set(-0.38 + j * 0.12, 0.5 + i * 0.27, 0.461); g.add(l); leds.push(l); }
    }
  }
  for (let i = 0; i < 5; i++) rack(-23.6 + i * 1.6, -10.35, 0);
  for (let i = 0; i < 3; i++) rack(-24.45, -7.6 + i * 1.6, Math.PI / 2);
  { const g = new THREE.Group(); put(g, -16.9, 0, -5.2, -Math.PI / 2); deskAt(g, 1.8, 0.8); monitorAt(g, 205, 0, -0.1); }

  // ------------------------------------------------------------------ meeting room
  put(box(1.7, 0.12, 9.2, wood), 21, 1.0, -2.6);
  for (const z of [-6.6, 1.4]) put(box(0.3, 0.98, 0.3, metal), 21, 0.49, z);
  const meetChairs = [];
  for (const z of [-6, -4, -2, 0]) for (const [x, ry] of [[19.55, Math.PI / 2], [22.45, -Math.PI / 2]]) {
    const g = new THREE.Group(); scene.add(g);
    chairAt(g, x, z, ry);
    meetChairs.push({ pos: V(x, z), face: ry, busy: false });
  }
  // the live board: real numbers from the run, on the meeting-room wall and over the work floor
  const boardTex = canvasTex(1024, 512, () => {});
  const tickerTex = canvasTex(1024, 320, () => {});
  for (const [tex, w, h, x, y, z] of [[boardTex, 5.4, 2.7, 21, 2.6, -10.94], [tickerTex, 3.4, 1.06, 0.2, 3.72, -10.96]]) {
    const m = new THREE.MeshBasicMaterial({ map: tex }); owned.add(m);
    const s = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m); s.position.set(x, y, z); scene.add(s);
    put(box(w + 0.2, h + 0.2, 0.06, M(0x1b1c21)), x, y, z - 0.04);
  }
  for (const [x, z, c] of [[24.4, 8.2, 0xe2a04a], [25.6, 9.6, 0x4a90c2], [23.4, 9.9, 0x8bbf6a]]) { const b = sphere(0.65, M(c, { roughness: 0.95 }), 18); b.scale.set(1, 0.6, 1); put(b, x, 0.4, z); }
  put(box(0.06, 1.6, 2.8, M(0xfcfcfa)), 27.0, 2.0, 3.2);                            // whiteboard

  // ------------------------------------------------------------------ papers & cards
  const paperGeo = new THREE.BoxGeometry(0.5, 0.025, 0.66);
  const tweens = [];
  const flying = [];
  function setPile(key, n) {
    const st = stations[key]; st.count = Math.max(0, n);
    const want = Math.min(10, st.count);
    while (st.pile.children.length < want) {
      const p = new THREE.Mesh(paperGeo, paperM); p.castShadow = true;
      p.position.y = st.pile.children.length * 0.03; p.rotation.y = (Math.random() - 0.5) * 0.3; st.pile.add(p);
    }
    while (st.pile.children.length > want) st.pile.remove(st.pile.children[st.pile.children.length - 1]);
  }
  function addToBin(key) {
    const st = stations[key]; if (!st.bin) return;
    st.binCount++;
    if (st.bin.children.length < 6) {
      const p = new THREE.Mesh(paperGeo, paperM); p.scale.setScalar(0.7);
      p.position.set((Math.random() - 0.5) * 0.3, 0.15 + st.bin.children.length * 0.08, (Math.random() - 0.5) * 0.3);
      p.rotation.set(Math.random(), Math.random() * 3, Math.random()); st.bin.add(p);
    }
  }
  const cardM = M(0x67c08a, { emissive: 0x2f8a55, emissiveIntensity: 0.35 });
  function addResultCard() {
    const cards = stations.rank.cards; const i = cards.children.length; if (i >= 8) return;
    const c = box(0.62, 0.36, 0.03, cardM);
    c.position.set(-0.36 + (i % 2) * 0.72, 2.85 - Math.floor(i / 2) * 0.48, 0.07); c.scale.set(0.01, 0.01, 1); cards.add(c);
    tweens.push({ t: 0, d: 0.5, fn: (k) => c.scale.set(k, k, 1) });
  }

  // ------------------------------------------------------------------ routes (doors, not walls)
  const NODES = {
    C: [0, 0.6, 'work'], WR: [-8, 0.6, 'work'], ER: [8, 0.6, 'work'], NR: [0, -3.5, 'work'], SE: [8, 7.6, 'work'], NG: [5.9, -4.2, 'work'],
    DWi: [-13.2, 0.6, 'work'], DW: [-15, 0.6, 'hall'], WH: [-17.5, 0.25, 'hall'], WM: [-20, 0.25, 'hall'],
    SRd: [-20, -1, 'server'], SRi: [-20, -3.5, 'server'], PTd: [-20, 1.5, 'pantry'], PTi: [-20, 4, 'pantry'], PTe: [-17.3, 8.6, 'pantry'],
    DEi: [13.4, 7.6, 'work'], DE: [15, 7.6, 'meet'], MRi: [17.5, 7.6, 'meet'], MRs: [21, 4.5, 'meet'], MRw: [18.3, -2, 'meet'],
    MRe: [23.7, -2, 'meet'], MRnw: [18.3, -8.8, 'meet'], MRn: [21, -9.1, 'meet'],
  };
  const EDGES = [['C', 'WR'], ['C', 'ER'], ['C', 'NR'], ['NR', 'NG'], ['ER', 'NG'], ['WR', 'DWi'], ['DWi', 'DW'], ['DW', 'WH'], ['WH', 'WM'], ['WM', 'SRd'], ['SRd', 'SRi'],
    ['WM', 'PTd'], ['PTd', 'PTi'], ['PTi', 'PTe'], ['ER', 'SE'], ['SE', 'DEi'], ['DEi', 'DE'], ['DE', 'MRi'], ['MRi', 'MRs'], ['MRs', 'MRw'],
    ['MRs', 'MRe'], ['MRw', 'MRnw'], ['MRnw', 'MRn']];
  const adj = {};
  for (const [a, b] of EDGES) { (adj[a] = adj[a] || []).push(b); (adj[b] = adj[b] || []).push(a); }
  const nodeP = (id) => V(NODES[id][0], NODES[id][1]);
  const roomOf = (p) => (p.x < -15 ? (p.z < -1 ? 'server' : p.z > 1.5 ? 'pantry' : 'hall') : p.x > 15 ? 'meet' : 'work');
  const nearestNode = (p, room) => {
    let best = null, bd = Infinity;
    for (const [id, [x, z, r]] of Object.entries(NODES)) { if (r !== room) continue; const d = Math.hypot(p.x - x, p.z - z); if (d < bd) { bd = d; best = id; } }
    return best || 'C';
  };
  function path(a, b) {
    const dist = { [a]: 0 }, prev = {}, todo = new Set(Object.keys(NODES));
    while (todo.size) {
      let u = null; for (const n of todo) if (dist[n] !== undefined && (u === null || dist[n] < dist[u])) u = n;
      if (u === null || u === b) break;
      todo.delete(u);
      for (const v of adj[u] || []) { const d = dist[u] + nodeP(u).distanceTo(nodeP(v)); if (dist[v] === undefined || d < dist[v]) { dist[v] = d; prev[v] = u; } }
    }
    const out = []; for (let n = b; n; n = prev[n]) { out.unshift(n); if (n === a) break; }
    return out[0] === a ? out : [a, b];
  }
  let agents = {};
  const stationAt = (p) => Object.values(agents).find((x) => Math.hypot(x.home.x - p.x, x.home.z - p.z) < 0.9);
  /** Walking points from `from` to `to`: out round its own desk, along the route network, round the target desk. */
  function route(from, to) {
    const pre = [], post = [];
    let a0 = from, b0 = to;
    const sf = stationAt(from); if (sf) { pre.push(sf.sideOut, sf.sideFront); a0 = sf.sideFront; }
    const st = stationAt(to); if (st) { post.push(st.sideFront, st.sideOut); b0 = st.sideFront; }
    const ra = roomOf(a0), rb = roomOf(b0);
    const mid = ra === rb && ra !== 'work' ? [] : path(nearestNode(a0, ra), nearestNode(b0, rb)).map(nodeP);
    return [...pre, ...mid, ...post, to.clone()];
  }

  // ------------------------------------------------------------------ robots
  const gltf = await new GLTFLoader().loadAsync(ROBOT_URL);
  const src = gltf.scene;
  const bbox = new THREE.Box3().setFromObject(src);
  const robotScale = ROBOT_HEIGHT / (bbox.max.y - bbox.min.y);
  const clips = Object.fromEntries(gltf.animations.map((a) => [a.name, a]));
  const ONCE = new Set(['Wave', 'Yes', 'No', 'ThumbsUp', 'Punch', 'Jump', 'Standing', 'Sitting', 'Death', 'WalkJump']);
  let speed = 1;
  let runActive = false;
  const pickables = [];

  class Agent {
    constructor(s) {
      this.s = s; this.key = s.key;
      this.holder = new THREE.Group();
      const model = SkeletonUtils.clone(src);
      model.scale.setScalar(robotScale);
      model.traverse((o) => {
        if (!o.isMesh) return;
        o.castShadow = true; o.receiveShadow = true;
        o.userData.agentKey = s.key; pickables.push(o);
        if (o.material && o.material.name === 'Main') {
          o.material = o.material.clone(); o.material.color = hsl(s.hue, 0.62, 0.55); owned.add(o.material); this.mainMat = o.material;
        }
        if (o.morphTargetDictionary && o.morphTargetDictionary.Surprised !== undefined) this.head = o;
      });
      this.holder.add(model);
      scene.add(this.holder);
      this.mixer = new THREE.AnimationMixer(model);
      this.actions = {};
      for (const [n, c] of Object.entries(clips)) {
        const a = this.mixer.clipAction(c);
        if (ONCE.has(n)) { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }
        this.actions[n] = a;
      }
      this.cur = null;
      this.home = V(s.home[0], s.home[1]);
      this.faceAngle = Math.atan2(s.face[0], s.face[1]);
      this.holder.position.copy(this.home);
      this.holder.rotation.y = this.faceAngle;
      this.front = this.home.clone().add(V(s.face[0] * 3.1, s.face[1] * 3.1));
      const side = V(s.face[1], -s.face[0]);
      this.sideOut = this.home.clone().add(side.clone().multiplyScalar(1.9));
      this.sideFront = this.front.clone().add(side.clone().multiplyScalar(1.9));
      this.queue = [];
      this.task = null;
      this.carry = new THREE.Group(); this.carry.position.set(0, 1.25, 0.62); this.carry.visible = false; this.holder.add(this.carry);
      this.carried = 0;
      this.seated = null;               // null | 'desk' | 'chair' | 'sofa'
      this.state = 'pending';
      this.nextIdle = rand(1, 6);
      this.convo = null;
      this.spot = null;
      this.expr = { name: null, until: 0 };
      this.glow = 0;
      this.play('Idle');
    }
    play(name, fade = 0.25) {
      const next = this.actions[name]; if (!next) return 0;
      if (this.cur === next && !ONCE.has(name)) return next.getClip().duration;
      next.reset(); next.enabled = true; next.setEffectiveTimeScale(speed); next.setEffectiveWeight(1);
      if (this.cur) next.crossFadeFrom(this.cur, fade, false);
      next.play();
      this.cur = next;
      return next.getClip().duration / speed;
    }
    face(name, secs = 2.5) { this.expr = { name, until: clock + secs }; }
    setCarry(n) {
      this.carried = Math.max(0, n);
      const want = Math.min(6, this.carried);
      while (this.carry.children.length < want) { const p = new THREE.Mesh(paperGeo, paperM); p.castShadow = true; p.position.y = this.carry.children.length * 0.035; p.rotation.y = (Math.random() - 0.5) * 0.25; this.carry.add(p); }
      while (this.carry.children.length > want) this.carry.remove(this.carry.children[this.carry.children.length - 1]);
      this.carry.visible = this.carried > 0;
    }
    atHome() { return Math.hypot(this.holder.position.x - this.home.x, this.holder.position.z - this.home.z) < 0.6; }
    get hasWork() { return (this.task && !this.task.idle) || this.queue.some((t) => !t.idle); }
    get busy() { return !!this.task || this.queue.length > 0; }
    push(...tasks) { this.queue.push(...tasks); }
    pushIdle(...tasks) { for (const t of tasks) t.idle = true; this.queue.push(...tasks); }
    /** Work has arrived: drop any break plans and walk back to the desk first. */
    prepWork() {
      const wasWorking = this.hasWork;
      const hadIdle = this.queue.some((t) => t.idle) || (this.task && this.task.idle);
      this.queue = this.queue.filter((t) => !t.idle);
      if (this.task && this.task.idle) { this.task = null; this.play('Idle', 0.2); }
      if (this.convo) { this.convo.cancelled = true; this.convo = null; }
      if (this.meeting) { this.meeting.cancelled = true; this.meeting = null; }
      if (this.spot) { this.spot.busy = false; this.spot = null; }
      // an agent already busy with a work scene finishes it (scenes end at the desk); one on a break walks back first
      if (!wasWorking && (hadIdle || !this.atHome() || (this.seated && this.seated !== 'desk'))) {
        const back = [];
        if (this.seated && this.seated !== 'desk') back.push(T.stand());
        if (!this.atHome()) back.push(T.go(() => this.home), T.faceHome());
        this.queue.unshift(...back);
      }
    }
    update(dt) {
      if (!this.task && this.queue.length) { this.task = this.queue.shift(); if (this.task.start) this.task.start(this); }
      if (this.task && this.task.update(this, dt)) this.task = null;
      if (!this.task && !this.queue.length) this.rest();
      // face: ease the morph target towards the current expression
      if (this.head) {
        const inf = this.head.morphTargetInfluences, dict = this.head.morphTargetDictionary;
        const want = clock < this.expr.until ? this.expr.name : null;
        for (const [n, i] of Object.entries(dict)) inf[i] += ((n === want ? 0.85 : 0) - inf[i]) * Math.min(1, dt * 6);
      }
      if (this.mainMat) {
        const g = selected === this.key ? 0.32 : hovered === this.key ? 0.2 : 0;
        this.glow += (g - this.glow) * Math.min(1, dt * 8);
        this.mainMat.emissive = this.mainMat.emissive || new THREE.Color();
        this.mainMat.emissive.copy(hsl(this.s.hue, 0.7, 0.5)).multiplyScalar(this.glow);
      }
      this.mixer.update(dt);
    }
    // nothing queued: during a search, agents whose part has not started wait at their desk
    rest() {
      const wantDesk = runActive && this.state === 'pending';
      if (wantDesk) {
        if (!this.atHome()) { this.prepWork(); return; }
        if (this.seated !== 'desk') {
          this.seated = 'desk'; this.holder.position.copy(this.home).add(V(-this.s.face[0] * 0.25, -this.s.face[1] * 0.25));
          this.holder.rotation.y = this.faceAngle; this.play('Sitting', 0.4);
        }
        return;
      }
      if (this.seated === 'desk' && runActive) { this.push(T.stand()); return; }
      if (!this.seated && (!this.cur || (this.cur !== this.actions.Idle && !this.cur.isRunning()))) this.play('Idle');
    }
  }

  // ------------------------------------------------------------------ tasks: small steps of a scene
  let focus = null, focusUntil = 0, clock = 0;
  let hovered = null, selected = null;
  const T = {
    /** walk through `points` (array, or a function returning a destination that is routed when the walk starts) */
    walkTo(points, run = false) {
      let pts = Array.isArray(points) ? points.map((p) => p.clone()) : null;
      return {
        start(a) {
          if (!pts) pts = route(a.holder.position, points());
          a.seated = null; a.play(run ? 'Running' : 'Walking', 0.2);
        },
        update(a, dt) {
          const target = pts[0];
          if (!target) { a.play('Idle', 0.25); return true; }
          const pos = a.holder.position;
          let dx = target.x - pos.x, dz = target.z - pos.z;
          const dist = Math.hypot(dx, dz);
          const step = (run ? 5.8 : 3.0) * speed * dt;
          if (dist <= Math.max(step, 0.05)) { pos.set(target.x, 0, target.z); pts.shift(); return false; }
          // step aside from anyone standing right in the way
          let sx = 0, sz = 0;
          for (const o of Object.values(agents)) {
            if (o === a || !o.holder.visible) continue;
            const ox = pos.x - o.holder.position.x, oz = pos.z - o.holder.position.z, d = Math.hypot(ox, oz);
            if (d > 0.01 && d < 1.0) { sx += (ox / d) * (1.0 - d); sz += (oz / d) * (1.0 - d); }
          }
          dx = dx / dist + sx * 0.8; dz = dz / dist + sz * 0.8;
          const n = Math.hypot(dx, dz) || 1;
          pos.x += (dx / n) * step; pos.z += (dz / n) * step; pos.y = 0;
          turnTo(a, Math.atan2(dx, dz), dt * 10);
          return false;
        },
      };
    },
    go(dest, run = false) { return T.walkTo(dest, run); },
    faceAgent(other) { return { update(a, dt) { const p = other.holder.position; return turnTo(a, Math.atan2(p.x - a.holder.position.x, p.z - a.holder.position.z), dt * 8); } }; },
    faceAngle(ang) { return { update(a, dt) { return turnTo(a, ang, dt * 8); } }; },
    faceHome() { return { update(a, dt) { return turnTo(a, a.faceAngle, dt * 8); } }; },
    anim(name) { let left = 0; return { start(a) { left = a.play(name, 0.2) * 0.95; }, update(a, dt) { left -= dt; if (left <= 0) { if (!a.seated) a.play('Idle', 0.3); return true; } return false; } }; },
    loop(name, secs) { let left = secs; return { start(a) { a.play(name, 0.3); }, update(a, dt) { left -= dt * speed; if (left <= 0) { a.play('Idle', 0.3); return true; } return false; } }; },
    wait(secs) { let left = secs; return { update(a, dt) { left -= dt * speed; return left <= 0; } }; },
    say(text, secs = 3.6, kind = 'work') { return { start(a) { onSay(a.key, text, secs / speed, kind); }, update() { return true; } }; },
    call(fn) { return { start(a) { fn(a); }, update() { return true; } }; },
    until(cond, timeout = 10) { let t = 0; return { update(a, dt) { t += dt; return cond() || t > timeout; } }; },
    focus(fn) { return { start(a) { focus = fn(a); focusUntil = clock + 6; }, update() { return true; } }; },
    sit(kind, pos, ang) {
      return {
        start(a) { a.holder.position.set(pos.x, 0, pos.z); a.holder.rotation.y = ang; a.seated = kind; a.play('Sitting', 0.35); },
        update() { return true; },
      };
    },
    stand() { let left = 0; return { start(a) { left = a.seated ? a.play('Standing', 0.25) * 0.9 : 0; a.seated = null; }, update(a, dt) { left -= dt; return left <= 0; } }; },
  };
  function turnTo(a, ang, k) {
    let d = ang - a.holder.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    if (Math.abs(d) < 0.03) { a.holder.rotation.y = ang; return true; }
    a.holder.rotation.y += d * Math.min(1, k);
    return false;
  }
  function throwPaper(from, to, onLand) {
    const p = new THREE.Mesh(paperGeo, paperM); p.castShadow = true; scene.add(p);
    flying.push({ p, from: from.clone(), to: to.clone(), t: 0, d: 0.7, onLand });
  }
  const worldPos = (obj) => obj.getWorldPosition(new THREE.Vector3());

  agents = Object.fromEntries(STATIONS.map((s) => [s.key, new Agent(s)]));
  const list = Object.values(agents);

  // ------------------------------------------------------------------ work scenes (real events only)
  function handoff(fromKey, toKey, n, lineA, lineB) {
    const A = agents[fromKey], B = agents[toKey];
    A.prepWork(); B.prepWork();
    const meet = B.front.clone();
    const dir = A.front.clone().sub(meet); dir.y = 0; if (dir.lengthSq() < 0.01) dir.set(1, 0, 0); dir.normalize();
    const spotA = meet.clone().add(dir.clone().multiplyScalar(0.8));
    const spotB = meet.clone().sub(dir.clone().multiplyScalar(0.8));
    const sync = { aReady: false, bReady: false, done: false };
    A.push(
      T.call((a) => { a.setCarry(n); setPile(fromKey, stations[fromKey].count - n); }),
      T.focus(() => meet),
      T.say(lineA),
      T.walkTo([A.sideOut, A.sideFront, spotA]),
      T.call(() => { sync.aReady = true; }),
      T.until(() => sync.bReady),
      T.faceAgent(B),
      T.anim('Yes'),
      T.call((a) => { const from = worldPos(a.carry); const to = worldPos(B.holder).setY(1.3); a.setCarry(0); throwPaper(from, to, () => { B.setCarry(n); }); }),
      T.wait(0.6),
      T.call(() => { sync.done = true; }),
      T.walkTo([A.sideFront, A.sideOut, A.home]),
      T.faceHome(),
    );
    B.push(
      T.walkTo([B.sideOut, B.sideFront, spotB]),
      T.call(() => { sync.bReady = true; }),
      T.until(() => sync.aReady),
      T.faceAgent(A),
      T.anim('Wave'),
      T.until(() => sync.done, 6),
      T.say(lineB),
      T.anim('ThumbsUp'),
      T.walkTo([B.sideFront, B.sideOut, B.home]),
      T.faceHome(),
      T.call((b) => { const got = b.carried; b.setCarry(0); setPile(toKey, stations[toKey].count + got); }),
    );
  }
  let portalFlash = 0, stampHit = 0, serverBusy = 0;
  /** web search: through the portal. Company boards: a run to the server room racks. */
  function scoutTrip(line, found, toServers) {
    const S = agents.discover; S.prepWork();
    if (toServers) {
      const rackSpot = V(-20.2 + rand(-1.6, 1.6), -8.4);
      S.push(T.focus(() => rackSpot), T.say(short(line, 60)), T.go(() => rackSpot, true), T.faceAngle(Math.PI),
        T.call(() => { serverBusy = 2.2; }), T.anim('Yes'), T.call((a) => a.setCarry(Math.max(1, found))),
        T.go(() => S.home, true), T.faceHome(), T.call((a) => { const n = a.carried; a.setCarry(0); setPile('discover', stations.discover.count + n); }));
      return;
    }
    const portal = stations.discover.portal;
    const gate = worldPos(portal.arch).setY(0).add(V(0, 0.9));
    const inside = gate.clone().add(V(0, -1.6));
    S.push(
      T.focus(() => gate),
      T.say(short(line, 60)),
      T.walkTo([S.sideOut, gate], true),
      T.walkTo([inside], true),
      T.call((a) => { a.holder.visible = false; portalFlash = 1; }),
      T.wait(1.1),
      T.call((a) => { a.holder.visible = true; portalFlash = 1; a.setCarry(Math.max(1, found)); }),
      T.walkTo([gate, S.sideOut, S.home], true),
      T.faceHome(),
      T.call((a) => { const n = a.carried; a.setCarry(0); setPile('discover', stations.discover.count + n); }),
    );
  }

  let lastId = null, celebrated = false, runId;
  let stateMap = {};
  const world = { scoredRatio: 0, counts: {}, status: '', total: 0, top: '' };
  function queueLoad() { return list.reduce((n, a) => n + a.queue.filter((t) => !t.idle).length, 0); }
  function passToNext(fromKey, toKey, toBin) {
    const st = stations[fromKey];
    setPile(fromKey, st.count - 1);
    if (toBin) throwPaper(worldPos(st.pile), worldPos(st.bin).setY(0.7), () => addToBin(fromKey));
    else throwPaper(worldPos(st.pile), worldPos(stations[toKey].pile), () => setPile(toKey, stations[toKey].count + 1));
  }
  const work = (key, ...tasks) => { const a = agents[key]; a.prepWork(); a.push(...tasks); };

  function onEvent(it) {
    const msg = it.message || '';
    const k = it.kind;
    switch (it.stage) {
      case 'understand':
        if (k === 'work') work('understand', T.say(short(msg, 64)), T.anim('Yes'));
        else if (k === 'good') { setPile('understand', 1); handoff('understand', 'plan', 1, 'Here is who we are searching for', 'Thanks — planning the searches now'); }
        break;
      case 'plan':
        if (k === 'work') work('plan', T.say(short(msg, 64)), T.anim('Wave'));
        else if (k === 'info' && /planned/.test(msg)) {
          const n = (/(\d+) searches planned/.exec(msg) || [])[1];
          setPile('plan', 1); handoff('plan', 'discover', 1, `Here is the plan${n ? `: ${n} searches` : ''}`, 'On it — heading out to look!');
        }
        break;
      case 'discover': {
        const S = agents.discover;
        if (k === 'work' && S.queue.length < 12) {
          const board = /Opening (.+?)'s careers board/.exec(msg);
          const boards = /job boards/.test(msg);
          scoutTrip(board ? `Checking ${board[1]}'s own job board` : msg, board ? 2 : 3, !!(board || boards));
        } else if (k === 'good' || k === 'info') work('discover', T.say(short(msg, 70)));
        break;
      }
      case 'normalize': {
        const R = agents.normalize;
        if (k === 'work') handoff('discover', 'normalize', Math.max(2, stations.discover.count), `Here are the ${stations.discover.count || ''} job posts I found`.replace('  ', ' '), 'Great — I will open every page');
        else if (/^Read /.test(msg) && R.queue.length < 10) work('normalize', T.say(`Reading “${short(titleOf(msg), 34)}”`), T.anim('Yes'));
        else if (k === 'info' && R.queue.length < 10) work('normalize', T.say(short(msg, 70)));
        break;
      }
      case 'dedupe':
        if (k === 'work') handoff('normalize', 'dedupe', Math.max(2, stations.normalize.count), 'All the postings, read and ready', 'Let me merge the duplicates');
        else work('dedupe', T.say(short(msg, 70)), T.anim('ThumbsUp'));
        break;
      case 'validate': {
        const Vf = agents.validate;
        if (k === 'work') {
          if (!Vf.handed) { Vf.handed = true; handoff('dedupe', 'validate', Math.max(2, stations.dedupe.count), 'Unique jobs — please check they are real', 'Checking each one is live'); }
          work('validate', T.say(short(msg, 64)));
        } else if (Vf.queue.length < 16) {
          const t = short(titleOf(msg) || msg.replace(/ (is live|has closed|looks old).*$/, ''), 34);
          if (k === 'good') work('validate', T.anim('Punch'), T.call(() => { stampHit = 1; passToNext('validate', 'match'); }), T.say(`✓ ${t} is live`, 2.6));
          else if (k === 'reject') work('validate', T.call((a) => a.face('Sad', 2)), T.anim('No'), T.call(() => passToNext('validate', 'match', true)), T.say(`✗ ${short(msg, 46)}`, 2.6));
          else work('validate', T.say(short(msg, 56), 2.6), T.call(() => passToNext('validate', 'match')));
        }
        break;
      }
      case 'extract':
        gateAnalyst();
        if (k === 'work' && agents.match.queue.length < 12) work('match', T.say(`Reading what “${short(titleOf(msg) || 'this job', 28)}” asks for`), T.anim('Yes'));
        break;
      case 'match': {
        gateAnalyst();
        const A = agents.match;
        if (A.queue.length > 16) break;
        const fit = /^(Strong match|Good match|Stretch)/.test(msg);
        const bad = /^Not a fit/.test(msg) || k === 'reject';
        if (fit) {
          const title = titleOf(msg) || (msg.split('·')[1] || '').trim();
          if (/^(Strong|Good)/.test(msg) && title) world.top = short(title, 40);
          work('match', T.call((a) => a.face('Surprised', 2.2)), T.anim('ThumbsUp'), T.say(short(msg, 70), 3));
          handoff('match', 'rank', 1, `“${short(title || 'This one', 30)}” fits you!`, 'Adding it to your results');
          agents.rank.push(T.call(() => addResultCard()));
        } else if (bad) {
          work('match', T.call((a) => a.face('Sad', 2)), T.anim('No'), T.say(short(msg, 70), 3), T.call(() => passToNext('match', null, true)));
        } else work('match', T.say(short(msg, 70), 3));
        break;
      }
      case 'rank':
        if (k === 'done') celebrate(msg);
        break;
      default:
    }
  }
  function gateAnalyst() {
    const A = agents.match;
    if (A.gated) return;
    A.gated = true;
    A.prepWork();
    A.push(T.until(() => !agents.validate.hasWork, 45));
  }
  let reviewAt = 0;
  function celebrate(msg) {
    if (celebrated) return; celebrated = true;
    const R = agents.rank;
    let cheered = false;
    R.prepWork();
    R.push(T.until(() => !agents.match.hasWork && !agents.validate.hasWork && !agents.dedupe.hasWork, 90),
      T.focus(() => R.front.clone()), T.call((a) => { cheered = true; a.face('Surprised', 3); }), T.say(short(msg, 80), 6), T.loop('Dance', 5));
    let i = 0;
    for (const a of list) {
      if (a === R) continue;
      a.prepWork();
      a.push(T.until(() => cheered, 120), T.wait(0.4 + (i++) * 0.25), T.anim(i % 2 ? 'Wave' : 'ThumbsUp'));
    }
    reviewAt = clock + 22;                     // then everyone meets to look at the results together
  }
  function reset(newRun) {
    runId = newRun; celebrated = false; lastId = null; world.top = ''; reviewAt = 0;
    for (const a of list) {
      a.queue.length = 0; a.task = null; a.setCarry(0); a.handed = false; a.gated = false; a.holder.visible = true;
      if (a.convo) a.convo.cancelled = true; a.convo = null;
      if (a.meeting) a.meeting.cancelled = true; a.meeting = null;
      if (a.spot) a.spot.busy = false; a.spot = null;
      a.seated = null; a.play('Idle', 0.1);
      if (!a.atHome()) a.push(T.go(() => a.home), T.faceHome());
    }
    for (const k of Object.keys(stations)) { setPile(k, 0); if (stations[k].bin) { stations[k].bin.clear(); stations[k].binCount = 0; } }
    stations.rank.cards.clear();
  }

  // ------------------------------------------------------------------ office life (breaks, chats, meetings)
  const SPOTS = {
    pantryTable: [{ pos: V(-21.25, 7.2), seat: true, face: Math.PI / 2 }, { pos: V(-18.75, 7.2), seat: true, face: -Math.PI / 2 }],
    cooler: [{ pos: V(-16.6, 9.3) }, { pos: V(-17.9, 10.2) }],
    sofa: [{ pos: V(-21.7, 10.75), seat: true, face: Math.PI }, { pos: V(-20.3, 10.75), seat: true, face: Math.PI }],
    lounge: [{ pos: V(23.2, 7.4) }, { pos: V(24.6, 7.0) }],
    floorA: [{ pos: V(-2.4, 3.4) }, { pos: V(-1.0, 3.4) }],
    floorB: [{ pos: V(2.6, 5.4) }, { pos: V(4.0, 5.4) }],
    window: [{ pos: V(5.3, -9.5) }, { pos: V(6.5, -9.3) }],
  };
  const COFFEE = { pos: V(-23.45, 4.4), face: -Math.PI / 2 };
  const RACKS = { pos: V(-19.6, -8.4), face: Math.PI };
  const PRESENTER = { pos: V(21, -8.9), face: 0 };
  let lastMeeting = -200;

  const facts = () => {
    const c = world.counts || {};
    return { results: c.search_results || 0, fits: c.recommended || 0, scored: c.scored || 0, rejected: c.rejected || 0, top: world.top || '' };
  };
  const fill_ = (text, f) => text.replace(/\{(\w+)\}/g, (_, k) => String(f[k] ?? ''));
  function pickTalk() {
    const f = facts();
    const data = DATA_TALK.filter((d) => d.needs.every((n) => f[n]));
    if (runActive) return Math.random() < 0.5 && data.length ? pick(data).lines : pick(BREAK_TALK);
    return data.length && Math.random() < 0.35 ? pick(data).lines : pick(BANTER);
  }
  const free = (a) => !a.hasWork && !a.convo && !a.meeting && (!runActive || ['done', 'skipped'].includes(a.state));
  function takeSpotPair(names) {
    for (const n of names.sort(() => Math.random() - 0.5)) { const pr = SPOTS[n]; if (pr.every((s) => !s.busy)) return pr; }
    return null;
  }
  function claim(a, spot) { if (a.spot) a.spot.busy = false; a.spot = spot; if (spot) spot.busy = true; }
  function leaveSeat(a) { return a.seated ? [T.stand()] : []; }

  /** Two agents meet at a spot and talk, taking turns, looking at each other. */
  function converse(A, B, lines, pair) {
    const c = { turn: -1, ready: 0, cancelled: false };
    A.convo = c; B.convo = c;
    const f = facts();
    [A, B].forEach((X, idx) => {
      const other = idx ? A : B, spot = pair[idx];
      claim(X, spot);
      X.pushIdle(...leaveSeat(X), T.go(() => spot.pos), T.faceAgent(other),
        ...(spot.seat ? [T.sit('chair', spot.pos, Math.atan2(pair[1 - idx].pos.x - spot.pos.x, pair[1 - idx].pos.z - spot.pos.z))] : []),
        T.call(() => { c.ready++; }), T.until(() => c.ready >= 2 || c.cancelled, 30),
        T.call(() => { if (c.turn < 0) c.turn = 0; }));
      lines.forEach(([who, text, gesture, expr], i) => {
        if (who !== idx) return;
        const secs = 2.2 + text.length / 22;
        X.pushIdle(T.until(() => c.turn === i || c.cancelled, 40),
          T.call((a) => { if (c.cancelled) return; onSay(a.key, fill_(text, f), secs, 'chat'); if (expr) a.face(expr, secs); }),
          ...(gesture && !spot.seat ? [T.anim(gesture)] : []),
          T.wait(gesture && !spot.seat ? Math.max(0.6, secs - 1.6) : secs),
          T.call(() => { if (c.turn === i) c.turn = i + 1; }));
      });
      X.pushIdle(T.until(() => c.turn >= lines.length || c.cancelled, 60), T.wait(rand(1, 4)), T.call((a) => { a.convo = null; }));
    });
  }
  function coffeeBreak(A) {
    if (COFFEE.busy) { wander(A); return; }           // one at the machine at a time
    claim(A, COFFEE);
    A.pushIdle(...leaveSeat(A), T.go(() => COFFEE.pos), T.faceAngle(COFFEE.face),
      T.call(() => { brewing = 4; }), T.say(pick(['Chai time', 'One cutting chai, please', 'Filter coffee today', 'Refuelling…']), 2.6, 'chat'),
      T.wait(3.2), T.anim('Yes'));
    const seat = pick([...SPOTS.pantryTable, ...SPOTS.sofa].filter((s) => !s.busy));
    if (seat) { claim(A, seat); A.pushIdle(T.go(() => seat.pos), T.sit(seat === SPOTS.sofa[0] || seat === SPOTS.sofa[1] ? 'sofa' : 'chair', seat.pos, seat.face)); }
  }
  function wander(A) {
    const choice = pick(['window', 'desk', 'racks', 'lounge']);
    claim(A, null);
    if (choice === 'desk') { A.pushIdle(...leaveSeat(A), T.go(() => A.home), T.faceHome(), T.sit('desk', A.home.clone().add(V(-A.s.face[0] * 0.25, -A.s.face[1] * 0.25)), A.faceAngle)); return; }
    if (choice === 'racks') { A.pushIdle(...leaveSeat(A), T.go(() => RACKS.pos), T.faceAngle(RACKS.face), T.call(() => { serverBusy = 1.2; }), T.anim('Yes')); return; }
    const spot = pick(SPOTS[choice === 'window' ? 'window' : 'lounge'].filter((s) => !s.busy));
    if (!spot) return;
    claim(A, spot);
    A.pushIdle(...leaveSeat(A), T.go(() => spot.pos), T.faceAngle(choice === 'window' ? Math.PI : rand(-1, 1)), T.wait(rand(2, 5)));
  }
  /** Everyone free meets in the meeting room. A results review uses the run's real numbers. */
  function meeting(people, review) {
    lastMeeting = clock;
    const f = facts();
    const host = review ? agents.rank : people.find((p) => p.key === 'plan') || people[0];
    const seats = meetChairs.filter((s) => !s.busy);
    const attendees = people.filter((p) => p !== host).slice(0, seats.length);
    const m = { arrived: 0, n: attendees.length + 1, done: false, cancelled: false };
    const lines = review
      ? [`Results review — ${f.fits} roles fit you`, f.scored ? `We analysed ${f.scored} jobs, ${f.rejected} were not a fit` : 'Every job was checked against your profile',
        f.top ? `Best match so far: ${f.top}` : 'Each score comes with the reasons', 'Great work, team. Ready for the next search.']
      : [pick(['Quick sync, team', 'Stand-up time', 'Two-minute huddle']), 'Reminder: company boards first — fewer applicants there',
        'Fresh postings first; old ones get a warning', 'And never invent anything on a resume. Thanks!'];
    for (const p of [host, ...attendees]) { p.meeting = m; if (p.convo) { p.convo.cancelled = true; p.convo = null; } p.queue = p.queue.filter((t) => !t.idle); if (p.task && p.task.idle) p.task = null; }
    host.pushIdle(...leaveSeat(host), T.go(() => PRESENTER.pos), T.faceAngle(PRESENTER.face), T.call(() => { m.arrived++; }),
      T.until(() => m.arrived >= m.n || m.cancelled, 40), T.focus(() => V(21, -3)));
    lines.forEach((text, i) => host.pushIdle(T.call((a) => { if (!m.cancelled) onSay(a.key, text, 3.4, 'chat'); }), T.anim(i === 0 ? 'Wave' : i === lines.length - 1 ? 'ThumbsUp' : 'Yes'), T.wait(2.2)));
    host.pushIdle(T.call(() => { m.done = true; }), T.wait(1), T.call((a) => { a.meeting = null; }));
    attendees.forEach((p, i) => {
      const seat = seats[i]; claim(p, seat);
      p.pushIdle(...leaveSeat(p), T.go(() => seat.pos), T.sit('chair', seat.pos, seat.face), T.call(() => { m.arrived++; }),
        T.until(() => m.done || m.cancelled, 70),
        ...(i === 0 ? [T.call((a) => onSay(a.key, review ? 'Nice — let us go apply early!' : 'Got it 👍', 2.6, 'chat'))] : []),
        T.wait(rand(0.5, 2.5)), T.call((a) => { a.meeting = null; }));
    });
  }

  let directorT = 0;
  function director(dt) {
    directorT -= dt; if (directorT > 0) return; directorT = 0.5;
    const freeNow = list.filter(free);
    // a finished search: review the results together (only if nobody is busy)
    if (reviewAt && clock > reviewAt && !runActive && freeNow.length === list.length) { reviewAt = 0; meeting(list, true); return; }
    if (!runActive && freeNow.length >= 5 && clock - lastMeeting > 240 && Math.random() < 0.04) { meeting(freeNow, false); return; }
    for (const a of freeNow.sort(() => Math.random() - 0.5)) {
      if (clock < a.nextIdle || a.busy) continue;
      const others = freeNow.filter((o) => o !== a && !o.busy && !o.convo && clock >= o.nextIdle - 4);
      const r = Math.random();
      if (others.length && r < 0.5) {
        const pair = takeSpotPair(runActive ? ['pantryTable', 'cooler', 'lounge'] : ['pantryTable', 'cooler', 'lounge', 'floorA', 'floorB']);
        if (pair) {
          const B = pick(others);
          const lines = pickTalk();
          converse(a, B, lines, pair);
          const dur = lines.reduce((s, l) => s + 2.4 + l[1].length / 22, 0) + 12;
          a.nextIdle = B.nextIdle = clock + dur + rand(6, 16);
          continue;
        }
      }
      if (r < 0.72) coffeeBreak(a); else wander(a);
      a.nextIdle = clock + rand(14, 30);
    }
  }

  // ------------------------------------------------------------------ live boards (real numbers only)
  let boardSig = '';
  function drawBoards() {
    const c = world.counts || {}, st = world.status || 'idle';
    const sig = JSON.stringify([c.search_results, c.candidates, c.recommended, c.scored, c.rejected, st, world.total, document.documentElement.dataset.theme]);
    if (sig === boardSig) return; boardSig = sig;
    const rows = [['Search results', c.search_results], ['Postings read', c.candidates], ['Analysed', world.total ? `${c.scored || 0} / ${world.total}` : c.scored],
      ['Fit you', c.recommended], ['Not a fit', c.rejected]];
    const label = st === 'running' || st === 'queued' ? 'LIVE · searching' : st === 'completed' ? 'Last search' : st === 'idle' || !st ? 'No search yet' : st;
    { const g = boardTex.image.getContext('2d'), W = 1024, H = 512;
      g.fillStyle = '#14161b'; g.fillRect(0, 0, W, H);
      g.fillStyle = st === 'running' || st === 'queued' ? '#ff7a45' : '#7fd1a3'; g.font = '700 40px system-ui, sans-serif'; g.fillText(label, 48, 74);
      g.font = '500 34px system-ui, sans-serif';
      rows.forEach(([k, v], i) => { g.fillStyle = '#9aa3b2'; g.fillText(k, 48, 150 + i * 70); g.fillStyle = '#ffffff'; g.font = '700 40px system-ui, sans-serif'; g.fillText(v == null || v === '' ? '—' : String(v), 640, 150 + i * 70); g.font = '500 34px system-ui, sans-serif'; });
      boardTex.needsUpdate = true; }
    { const g = tickerTex.image.getContext('2d'), W = 1024, H = 320;
      g.fillStyle = '#14161b'; g.fillRect(0, 0, W, H);
      g.fillStyle = st === 'running' || st === 'queued' ? '#ff7a45' : '#7fd1a3'; g.font = '700 46px system-ui, sans-serif'; g.fillText(label, 40, 82);
      g.fillStyle = '#ffffff'; g.font = '600 60px system-ui, sans-serif';
      g.fillText(`${c.search_results ?? '—'} found · ${c.recommended ?? '—'} fit you`, 40, 196);
      g.fillStyle = '#9aa3b2'; g.font = '500 38px system-ui, sans-serif';
      g.fillText(world.total ? `${c.scored || 0} of ${world.total} analysed` : 'Waiting for the next search', 40, 270);
      tickerTex.needsUpdate = true; }
  }

  // ------------------------------------------------------------------ theme
  function setTheme(isDark) {
    if (floorMat.map) floorMat.map.dispose();
    floorMat.map = plankTexture(isDark); floorMat.needsUpdate = true;
    if (pantryFloor.map) pantryFloor.map.dispose();
    pantryFloor.map = tileTexture(isDark ? '#3b3a3f' : '#f3efe6', isDark ? '#2f2e33' : '#e2d9c8'); pantryFloor.needsUpdate = true;
    if (serverFloor.map) serverFloor.map.dispose();
    serverFloor.map = tileTexture(isDark ? '#1d2027' : '#c9ced8', isDark ? '#23272f' : '#bcc2cd', 6); serverFloor.needsUpdate = true;
    wallMat.color.set(isDark ? 0x2c2c33 : 0xf4ede4);
    partMat.color.set(isDark ? 0x35353d : 0xe9e0d4);
    trimMat.color.set(isDark ? 0x3a3a43 : 0xd8cabb);
    carpet.color.set(isDark ? 0x2f3850 : 0x6d7fa3);
    hemi.color.set(isDark ? 0xaab4ff : 0xfff6ec); hemi.groundColor.set(isDark ? 0x15151b : 0xc9b8a6);
    hemi.intensity = isDark ? 0.55 : 1.0; sun.intensity = isDark ? 1.2 : 2.0;
    fill.intensity = isDark ? 30 : 18; pantryLamp.intensity = isDark ? 26 : 12; serverGlow.intensity = isDark ? 22 : 8; meetLamp.intensity = isDark ? 22 : 10;
    renderer.toneMappingExposure = isDark ? 1.15 : 1.05;
    boardSig = '';
  }
  setTheme(dark);

  // ------------------------------------------------------------------ camera & pointer
  const VIEWS = {
    all: { look: V(1, 0.4, 0.2), r: null },
    work: { look: V(0, 0.2, 0.2), r: 34 },
    meeting: { look: V(21, -2, 0.2), r: 21 },
    pantry: { look: V(-20, 6, 0.2), r: 18 },
    server: { look: V(-20, -6, 0.2), r: 18 },
  };
  const cam = { theta: 0, phi: 0.9, r: 52, base: 52, zoomed: false, userUntil: 0, follow: true, rNow: null, view: 'all' };
  const look = VIEWS.all.look.clone();
  let dragging = null;
  const el = renderer.domElement;
  el.style.touchAction = 'none';
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function agentAt(e) {
    const r = el.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables.filter((m) => agents[m.userData.agentKey].holder.visible), false)[0];
    return hit ? hit.object.userData.agentKey : null;
  }
  const onDown = (e) => { dragging = { x: e.clientX, y: e.clientY, theta: cam.theta, phi: cam.phi, moved: false }; el.setPointerCapture(e.pointerId); };
  let hoverT = 0;
  const onMove = (e) => {
    if (dragging) {
      if (Math.hypot(e.clientX - dragging.x, e.clientY - dragging.y) > 4) { dragging.moved = true; el.classList.add('grabbing'); }
      if (!dragging.moved) return;
      cam.theta = Math.max(-1.1, Math.min(1.1, dragging.theta - (e.clientX - dragging.x) * 0.005));
      cam.phi = Math.min(1.3, Math.max(0.42, dragging.phi - (e.clientY - dragging.y) * 0.005));
      cam.userUntil = performance.now() + 9000;
      return;
    }
    const now = performance.now(); if (now - hoverT < 60) return; hoverT = now;
    hovered = agentAt(e);
    el.style.cursor = hovered ? 'pointer' : '';
  };
  const onUp = (e) => {
    const click = dragging && !dragging.moved;
    dragging = null; el.classList.remove('grabbing');
    if (click) select(agentAt(e));
  };
  const onLeave = () => { hovered = null; el.style.cursor = ''; };
  const onWheel = (e) => { e.preventDefault(); cam.r = Math.min(80, Math.max(10, cam.r + Math.sign(e.deltaY) * 2.6)); cam.zoomed = true; cam.userUntil = performance.now() + 9000; };
  el.addEventListener('pointerdown', onDown); el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerup', onUp); el.addEventListener('pointercancel', onUp); el.addEventListener('pointerleave', onLeave);
  el.addEventListener('wheel', onWheel, { passive: false });

  /** Click a robot: the camera goes to it and it says hello (or what it is doing). */
  function select(key) {
    selected = key && agents[key] ? key : null;
    onSelect(selected);
    if (!selected) return;
    const a = agents[selected];
    if (!a.hasWork && !a.convo && !a.meeting) {
      a.pushIdle(...(a.seated ? [] : [T.faceAngle(cam.theta), T.anim('Wave')]), T.say(a.s.intro, 4, 'chat'));
      a.face('Surprised', 1.2);
    }
  }
  function view(name) {
    if (!VIEWS[name]) return;
    cam.view = name; cam.zoomed = false; cam.theta = 0; cam.phi = 0.9;
    cam.userUntil = name === 'all' ? 0 : performance.now() + 25000;
    if (selected) select(null);
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w / h < 1.4 ? 44 : 34;
    camera.updateProjectionMatrix();
    const aspect = w / h;
    cam.base = Math.max(40, Math.min(80, 30 + 62 / aspect));          // the whole floor (all rooms) fits
    if (!cam.zoomed) cam.r = cam.base;
  }
  const ro = new ResizeObserver(resize); ro.observe(container); resize();

  // ------------------------------------------------------------------ main loop
  let raf = 0, last = performance.now(), visible = true, disposed = false;
  const tagPos = new THREE.Vector3();
  let frameCb = null;
  let boardT = 0;
  function frame(now) {
    raf = 0; if (disposed) return;
    let dt = Math.min(0.12, (now - last) / 1000); last = now;      // slow machines still move at real speed
    clock += dt;
    const load = queueLoad();
    speed = load > 40 ? 2.2 : load > 20 ? 1.6 : 1;
    if (reducedMotion) dt *= 0.0001;
    director(dt);
    for (const a of list) {
      for (const act of Object.values(a.actions)) if (act.isRunning()) act.setEffectiveTimeScale(speed);
      a.update(dt);
    }
    for (let i = flying.length - 1; i >= 0; i--) {
      const f = flying[i]; f.t += (dt * speed) / f.d;
      const u = Math.min(1, f.t);
      f.p.position.lerpVectors(f.from, f.to, u); f.p.position.y += Math.sin(Math.PI * u) * 1.6;
      f.p.rotation.set(u * 3, u * 5, u * 2);
      if (u >= 1) { scene.remove(f.p); flying.splice(i, 1); if (f.onLand) f.onLand(); }
    }
    for (let i = tweens.length - 1; i >= 0; i--) { const tw = tweens[i]; tw.t += dt; const k = Math.min(1, tw.t / tw.d); tw.fn(1 - Math.pow(1 - k, 3)); if (k >= 1) tweens.splice(i, 1); }
    // props react to their agent's work
    const P = stations.discover.portal;
    portalFlash = Math.max(0, portalFlash - dt * 1.6);
    const scoutWorking = stateMap.discover === 'running';
    P.veil.material.opacity = 0.22 + (scoutWorking ? 0.15 + Math.sin(clock * 4) * 0.08 : 0) + portalFlash * 0.6;
    P.ringM.emissiveIntensity = 0.8 + (scoutWorking ? Math.sin(clock * 4) * 0.4 : 0) + portalFlash * 2;
    stations.discover.globe.rotation.y += dt * (scoutWorking ? 1.4 : 0.2);
    stampHit = Math.max(0, stampHit - dt * 2.5);
    stations.validate.stamp.position.y = 1.06 + Math.sin(stampHit * Math.PI) * 0.35;
    for (const key of ['understand', 'match']) { const sc = stations[key].screen; if (sc) sc.material.emissiveIntensity = stateMap[key] === 'running' ? 0.8 + Math.sin(clock * 7) * 0.2 : 0.35; }
    stations.plan.lines.forEach((l, i) => { l.scale.x = stateMap.plan === 'running' ? 0.55 + 0.45 * Math.abs(Math.sin(clock * 1.4 + i)) : stateMap.plan === 'done' ? 1 : 0.4; });
    const ratio = world.scoredRatio || 0;
    stations.match.bars.forEach((b, i) => { const goal = stateMap.match === 'done' ? 0.55 + i * 0.25 : 0.15 + ratio * (0.6 + i * 0.3); b.scale.y += (goal - b.scale.y) * Math.min(1, dt * 3); b.position.y = 1.07 + b.scale.y / 2; });
    stations.rank.trophy.rotation.y += dt * (celebrated ? 2.4 : 0.3);
    for (const s of STATIONS) stations[s.key].pad.material.opacity = stateMap[s.key] === 'running' ? 0.22 + Math.sin(clock * 3) * 0.08 : stateMap[s.key] === 'done' ? 0.16 : 0.07;
    // server LEDs blink (faster while the Scout reads company boards), steam while someone makes chai
    serverBusy = Math.max(0, serverBusy - dt);
    const blink = scoutWorking || serverBusy > 0 ? 9 : 2.2;
    ledMats.forEach((m, i) => { m.emissiveIntensity = 0.5 + 0.9 * (Math.sin(clock * blink * (1 + i * 0.37) + i * 2) > 0.2 ? 1 : 0.2); });
    brewing = Math.max(0, brewing - dt);
    for (const s of steam) {
      s.t = (s.t + dt * 0.6) % 1;
      s.p.visible = brewing > 0;
      s.p.position.set(-24.15 + Math.sin(s.t * 9) * 0.05, 1.95 + s.t * 1.1, 4.4);
      s.p.scale.setScalar(0.6 + s.t * 1.6); s.p.material.opacity = (1 - s.t) * 0.45;
    }
    plants.forEach((p, i) => { p.rotation.z = Math.sin(clock * 0.8 + i) * 0.015; });
    boardT -= dt; if (boardT <= 0) { boardT = 1; drawBoards(); drawClock(); }

    // camera: a chosen room, a selected robot, or wherever the action is
    const userHolds = performance.now() < cam.userUntil;
    const sel = selected && agents[selected];
    const following = cam.follow && focus && clock < focusUntil && !userHolds && !sel;
    let goal, r;
    if (sel) { goal = sel.holder.position.clone().setY(0.8); r = 15; }
    else if (following) { goal = V(Math.max(-19, Math.min(20, focus.x)), Math.max(-4, Math.min(5, focus.z)), 0.6); r = cam.zoomed ? cam.r : Math.min(cam.base * 0.62, 34); }
    else { const v = VIEWS[cam.view]; goal = v.look; r = cam.zoomed ? cam.r : v.r || cam.base; }
    look.lerp(goal, Math.min(1, dt * 1.8));
    cam.rNow = cam.rNow == null ? r : cam.rNow + (r - cam.rNow) * Math.min(1, dt * 1.8);
    camera.position.set(look.x + Math.sin(cam.theta) * Math.sin(cam.phi) * cam.rNow, look.y + Math.cos(cam.phi) * cam.rNow, look.z + Math.cos(cam.theta) * Math.sin(cam.phi) * cam.rNow);
    camera.lookAt(look);
    renderer.render(scene, camera);
    if (frameCb) {
      const w = container.clientWidth, h = container.clientHeight, out = {};
      for (const [key, a] of Object.entries(agents)) {
        a.holder.getWorldPosition(tagPos); tagPos.y += (a.seated ? ROBOT_HEIGHT * 0.78 : ROBOT_HEIGHT) + 0.35; tagPos.project(camera);
        out[key] = { x: (tagPos.x + 1) / 2 * w, y: (1 - tagPos.y) / 2 * h, visible: a.holder.visible && tagPos.z < 1 && tagPos.z > -1, depth: tagPos.z,
          where: roomOf(a.holder.position), seated: !!a.seated, chatting: !!a.convo || !!a.meeting };
      }
      frameCb(out);
    }
    schedule();
  }
  function schedule() { if (!raf && visible && !disposed && !document.hidden) raf = requestAnimationFrame(frame); }
  const io = new IntersectionObserver((ents) => { visible = ents.some((e) => e.isIntersecting); last = performance.now(); schedule(); });
  io.observe(container);
  const onVis = () => { last = performance.now(); schedule(); };
  document.addEventListener('visibilitychange', onVis);
  schedule();

  return {
    /** stage states + live numbers from the run */
    update(states, extra = {}) {
      Object.assign(world, extra);
      stateMap = states;
      runActive = ['queued', 'running'].includes(world.status);
      for (const [key, st] of Object.entries(states)) if (agents[key]) agents[key].state = st;
    },
    /** activity items of the run, oldest first; only new ones become scenes */
    feed(items, id, finished, recent) {
      if (id !== runId) reset(id);
      if (lastId === null) {
        const replay = recent ? Math.min(recent === 'all' ? 60 : 20, items.length) : 0;
        if (!replay) { lastId = items.length ? items[items.length - 1].id : 0; if (finished) celebrated = true; return; }
        const first = items.length - replay;
        lastId = first > 0 ? items[first - 1].id : -1;
      }
      for (const it of items) if (it.id > lastId) { lastId = it.id; onEvent(it); }
    },
    setTheme,
    setFollow(on) { cam.follow = on; },
    onFrame(cb) { frameCb = cb; },
    resetView() { Object.assign(cam, { theta: 0, phi: 0.9, r: cam.base, zoomed: false, userUntil: 0, view: 'all' }); select(null); },
    view,
    select,
    dispose() {
      disposed = true; cancelAnimationFrame(raf);
      ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', onVis);
      el.removeEventListener('pointerdown', onDown); el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerup', onUp); el.removeEventListener('pointercancel', onUp); el.removeEventListener('pointerleave', onLeave);
      el.removeEventListener('wheel', onWheel);
      for (const a of list) a.mixer.stopAllAction();
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) owned.add(o.material); });
      for (const m of [floorMat, pantryFloor, serverFloor]) if (m.map) m.map.dispose();
      boardTex.dispose(); tickerTex.dispose(); clockTex.dispose();
      owned.forEach((m) => m.dispose && m.dispose());
      renderer.dispose(); el.remove();
    },
  };
}
