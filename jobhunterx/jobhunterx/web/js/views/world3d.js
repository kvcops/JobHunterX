// "Agents at work" — a 3D office where the eight pipeline agents (animated robots) actually work
// together. Every scene is triggered by a real event of the running search:
//
//   profile understood  → Profile analyst walks over and hands the profile to the Planner
//   searches planned    → Planner hands the plan to the Scout
//   searching / boards  → Scout runs out through the web portal and comes back carrying job posts
//   page read           → Reader reads that posting ("Reading “AI Engineer”…")
//   dedupe              → Reader brings the stack to the Curator, who merges duplicates
//   validate good / bad → Verifier stamps it, or shakes its head and bins it
//   verdicts            → Analyst gives a thumbs-up and passes fits to the Ranker, or bins the rest
//   search complete     → the Ranker dances, everyone waves
//
// The engine only decides how a real event *looks*; it never invents progress.
import * as THREE from '../../vendor/three.module.min.js';
import { GLTFLoader } from '../../vendor/three-addons/GLTFLoader.js';
import * as SkeletonUtils from '../../vendor/three-addons/SkeletonUtils.js';

const ROBOT_URL = '/assets/models/robot.glb';
const ROBOT_HEIGHT = 2.35;

// Room: floor x ∈ [-15, 15], z ∈ [-11, 11]; walls on the north (z = -11) and west (x = -15) sides.
export const STATIONS = [
  { key: 'understand', name: 'Profile analyst', home: [-12, 4.5], face: [1, 0], hue: 18, prop: 'desk' },
  { key: 'plan', name: 'Planner', home: [-12, -2.5], face: [1, 0], hue: 265, prop: 'board' },
  { key: 'discover', name: 'Scout', home: [-8.5, -7.6], face: [0, 1], hue: 205, prop: 'portal' },
  { key: 'normalize', name: 'Reader', home: [-3, -7.6], face: [0, 1], hue: 160, prop: 'shelf' },
  { key: 'dedupe', name: 'Curator', home: [3, -7.6], face: [0, 1], hue: 40, prop: 'sorter' },
  { key: 'validate', name: 'Verifier', home: [8.5, -7.6], face: [0, 1], hue: 140, prop: 'stamp' },
  { key: 'match', name: 'Analyst', home: [11.6, -2.8], face: [-1, 0], hue: 330, prop: 'chart' },
  { key: 'rank', name: 'Ranker', home: [11.6, 3.4], face: [-1, 0], hue: 28, prop: 'podium' },
];
const hsl = (h, s, l) => new THREE.Color().setHSL((((h % 360) + 360) % 360) / 360, s, l);
const V = (x, z, y = 0) => new THREE.Vector3(x, y, z);
const short = (t, n = 46) => (t && t.length > n ? `${t.slice(0, n - 1)}…` : t || '');
const titleOf = (msg) => {
  const q = /[“"]([^”"]+)[”"]/.exec(msg || '');
  if (q) return q[1];
  const f = /(?:requirements for|Read|·)\s+(.+?)\s+at\s+/.exec(msg || '');
  return f ? f[1].trim() : '';
};

export async function createWorld(container, { dark = false, reducedMotion = false, onSay = () => {} } = {}) {
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
  const camera = new THREE.PerspectiveCamera(34, 1, 0.5, 220);

  const owned = new Set();
  const M = (color, extra = {}) => { const m = new THREE.MeshStandardMaterial({ color, roughness: 0.75, metalness: 0.03, ...extra }); owned.add(m); return m; };
  const shade = (o) => { o.traverse((c) => { if (c.isMesh) { c.castShadow = true; c.receiveShadow = true; } }); return o; };
  const box = (w, h, d, m) => shade(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m));
  const cyl = (rt, rb, h, m, seg = 24, open = false) => shade(new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg, 1, open), m));
  const sphere = (r, m, seg = 20) => shade(new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.7)), m));

  // ------------------------------------------------------------------ light
  const hemi = new THREE.HemisphereLight(0xfff6ec, 0xc9b8a6, 1.0);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff0dc, 2.0);
  sun.position.set(10, 24, 16);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 16, bottom: -16, near: 1, far: 70 });
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.02;
  scene.add(sun);
  const fill = new THREE.PointLight(0xffd9b0, 18, 30, 1.6);
  fill.position.set(-6, 7, 2);
  scene.add(fill);

  // ------------------------------------------------------------------ room
  function plankTexture(isDark) {
    const c = document.createElement('canvas'); c.width = 512; c.height = 512;
    const g = c.getContext('2d');
    const base = isDark ? [58, 48, 42] : [212, 182, 146];
    for (let row = 0; row < 16; row++) {
      let x = -((row * 97) % 180);
      while (x < 512) {
        const w = 150 + ((row * 31 + Math.abs(x)) % 90);
        const v = ((row * 13 + Math.abs(x) * 7) % 21) - 10;
        g.fillStyle = `rgb(${base[0] + v},${base[1] + v},${base[2] + v * 0.8})`;
        g.fillRect(x, row * 32, w, 32);
        g.fillStyle = `rgba(0,0,0,${isDark ? 0.35 : 0.14})`;
        g.fillRect(x, row * 32, 2, 32);
        x += w;
      }
      g.fillStyle = `rgba(0,0,0,${isDark ? 0.4 : 0.16})`;
      g.fillRect(0, row * 32 + 31, 512, 1.5);
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(5, 4);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  }
  const floorMat = M(0xffffff);
  const floor = box(31, 0.6, 23, floorMat); floor.position.set(0, -0.3, 0); scene.add(floor);
  const wallMat = M(0xf4ede4), trimMat = M(0xd8cabb), glass = M(0xbfe0ff, { emissive: 0x9fd0ff, emissiveIntensity: 0.55, roughness: 0.15 });
  const northWall = box(31, 4.6, 0.5, wallMat); northWall.position.set(0, 2.3, -11.25); scene.add(northWall);
  const westWall = box(0.5, 4.6, 23, wallMat); westWall.position.set(-15.25, 2.3, 0); scene.add(westWall);
  for (const [x, z, w, d] of [[0, -10.95, 31, 0.12], [-14.95, 0, 0.12, 23]]) { const b = box(w, 0.28, d, trimMat); b.position.set(x, 0.14, z); scene.add(b); }
  for (const x of [5.6, 12]) { const w = box(3.4, 2.1, 0.08, glass); w.position.set(x, 2.6, -10.98); scene.add(w); const f = box(3.6, 0.12, 0.2, trimMat); f.position.set(x, 1.5, -10.95); scene.add(f); }
  { const w = box(0.08, 2.1, 3.4, glass); w.position.set(-14.98, 2.6, 8.4); scene.add(w); }
  const rug = new THREE.Mesh(new THREE.PlaneGeometry(13, 7.5), M(0xc96f4a, { roughness: 0.95 }));
  rug.rotation.x = -Math.PI / 2; rug.position.set(0, 0.012, 0.6); rug.receiveShadow = true; scene.add(rug);
  const rugIn = new THREE.Mesh(new THREE.PlaneGeometry(11.6, 6.1), M(0xe6c4a0, { roughness: 0.95 }));
  rugIn.rotation.x = -Math.PI / 2; rugIn.position.set(0, 0.016, 0.6); rugIn.receiveShadow = true; scene.add(rugIn);
  const leaf = M(0x4f8f5a), pot = M(0xb5684a);
  for (const [x, z, s] of [[-14, -10, 1.2], [14, -10, 1.0], [-14, 10, 1.1], [7.5, 10, 0.9], [-7.5, 10, 0.9]]) {
    const p = cyl(0.5 * s, 0.38 * s, 0.75 * s, pot); p.position.set(x, 0.38 * s, z); scene.add(p);
    for (let i = 0; i < 4; i++) { const b = sphere(0.55 * s, leaf, 12); b.position.set(x + Math.cos(i * 1.7) * 0.25 * s, (1.1 + i * 0.32) * s, z + Math.sin(i * 1.7) * 0.25 * s); b.scale.set(1, 1.25, 1); scene.add(b); }
  }

  // ------------------------------------------------------------------ station furniture
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
  function chairAt(group, x, z) {
    const c = new THREE.Group(); c.position.set(x, 0, z);
    const seat = box(0.8, 0.1, 0.8, chairM); seat.position.y = 0.62; c.add(seat);
    const back = box(0.8, 0.8, 0.1, chairM); back.position.set(0, 1.05, -0.36); c.add(back);
    const leg = cyl(0.05, 0.05, 0.6, metal, 8); leg.position.y = 0.31; c.add(leg);
    const base = cyl(0.36, 0.36, 0.05, metal, 16); base.position.y = 0.03; c.add(base);
    group.add(c);
  }
  // Each station has its own frame: the agent stands at (0,0,0) facing +z (into the room),
  // the desk is in front of it and wall props behind it.
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
      // results board: one green card per job that fits
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

  // ------------------------------------------------------------------ robots
  const gltf = await new GLTFLoader().loadAsync(ROBOT_URL);
  const src = gltf.scene;
  const bbox = new THREE.Box3().setFromObject(src);
  const robotScale = ROBOT_HEIGHT / (bbox.max.y - bbox.min.y);
  const clips = Object.fromEntries(gltf.animations.map((a) => [a.name, a]));
  const ONCE = new Set(['Wave', 'Yes', 'No', 'ThumbsUp', 'Punch', 'Jump', 'Standing', 'Sitting', 'Death', 'WalkJump']);
  let speed = 1;

  class Agent {
    constructor(s) {
      this.s = s; this.key = s.key;
      this.holder = new THREE.Group();
      const model = SkeletonUtils.clone(src);
      model.scale.setScalar(robotScale);
      model.traverse((o) => {
        if (!o.isMesh) return;
        o.castShadow = true; o.receiveShadow = true;
        if (o.material && o.material.name === 'Main') {
          o.material = o.material.clone(); o.material.color = hsl(s.hue, 0.62, 0.55); owned.add(o.material);
        }
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
      const side = V(s.face[1], -s.face[0]);   // walk round the desk on this side
      this.sideOut = this.home.clone().add(side.clone().multiplyScalar(1.9));
      this.sideFront = this.front.clone().add(side.clone().multiplyScalar(1.9));
      this.queue = [];
      this.task = null;
      this.carry = new THREE.Group(); this.carry.position.set(0, 1.25, 0.62); this.carry.visible = false; this.holder.add(this.carry);
      this.carried = 0;
      this.sitting = false;
      this.state = 'pending';
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
    setCarry(n) {
      this.carried = Math.max(0, n);
      const want = Math.min(6, this.carried);
      while (this.carry.children.length < want) { const p = new THREE.Mesh(paperGeo, paperM); p.castShadow = true; p.position.y = this.carry.children.length * 0.035; p.rotation.y = (Math.random() - 0.5) * 0.25; this.carry.add(p); }
      while (this.carry.children.length > want) this.carry.remove(this.carry.children[this.carry.children.length - 1]);
      this.carry.visible = this.carried > 0;
    }
    get busy() { return !!this.task || this.queue.length > 0; }
    push(...tasks) { this.queue.push(...tasks); }
    update(dt) {
      if (!this.task && this.queue.length) { this.task = this.queue.shift(); if (this.task.start) this.task.start(this); }
      if (this.task && this.task.update(this, dt)) this.task = null;
      if (!this.task && !this.queue.length) this.rest();
      this.mixer.update(dt);
    }
    // nothing to do: waiting agents sit at their desk; once their part starts they stand up and work
    rest() {
      const wantSit = this.state === 'pending';
      if (wantSit && !this.sitting) {
        this.sitting = true; this.holder.position.copy(this.home).add(V(-this.s.face[0] * 0.25, -this.s.face[1] * 0.25)); this.holder.rotation.y = this.faceAngle; this.play('Sitting', 0.4);
      } else if (!wantSit && this.sitting) {
        this.sitting = false; this.holder.position.copy(this.home); this.push(T.anim('Standing'));
      } else if (!wantSit && (!this.cur || (this.cur !== this.actions.Idle && !this.cur.isRunning()))) {
        this.play('Idle');
      }
    }
  }

  // ------------------------------------------------------------------ tasks: small steps of a scene
  let focus = null, focusUntil = 0, clock = 0;
  const T = {
    walkTo(points, run = false) {
      const pts = points.map((p) => p.clone());
      return {
        start(a) { a.sitting = false; a.play(run ? 'Running' : 'Walking', 0.2); },
        update(a, dt) {
          const target = pts[0];
          if (!target) { a.play('Idle', 0.25); return true; }
          const pos = a.holder.position;
          const dx = target.x - pos.x, dz = target.z - pos.z;
          const dist = Math.hypot(dx, dz);
          const step = (run ? 5.8 : 3.0) * speed * dt;
          if (dist <= step) { pos.set(target.x, 0, target.z); pts.shift(); return false; }
          pos.x += (dx / dist) * step; pos.z += (dz / dist) * step; pos.y = 0;
          turnTo(a, Math.atan2(dx, dz), dt * 10);
          return false;
        },
      };
    },
    faceAgent(other) { return { update(a, dt) { const p = other.holder.position; return turnTo(a, Math.atan2(p.x - a.holder.position.x, p.z - a.holder.position.z), dt * 8); } }; },
    faceHome() { return { update(a, dt) { return turnTo(a, a.faceAngle, dt * 8); } }; },
    anim(name) { let left = 0; return { start(a) { left = a.play(name, 0.2) * 0.95; }, update(a, dt) { left -= dt; if (left <= 0) { a.play('Idle', 0.3); return true; } return false; } }; },
    loop(name, secs) { let left = secs; return { start(a) { a.play(name, 0.3); }, update(a, dt) { left -= dt * speed; if (left <= 0) { a.play('Idle', 0.3); return true; } return false; } }; },
    wait(secs) { let left = secs; return { update(a, dt) { left -= dt * speed; return left <= 0; } }; },
    say(text, secs = 3.6) { return { start(a) { onSay(a.key, text, secs / speed); }, update() { return true; } }; },
    call(fn) { return { start(a) { fn(a); }, update() { return true; } }; },
    until(cond, timeout = 10) { let t = 0; return { update(a, dt) { t += dt; return cond() || t > timeout; } }; },
    focus(fn) { return { start(a) { focus = fn(a); focusUntil = clock + 6; }, update() { return true; } }; },
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

  const agents = Object.fromEntries(STATIONS.map((s) => [s.key, new Agent(s)]));

  // ------------------------------------------------------------------ scenes
  /** A walks over to B; they meet in front of B's desk, face each other, hand over the papers, go back. */
  function handoff(fromKey, toKey, n, lineA, lineB) {
    const A = agents[fromKey], B = agents[toKey];
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
  /** The Scout runs out through the web portal and comes back carrying job posts. */
  let portalFlash = 0, stampHit = 0;
  function scoutTrip(line, found) {
    const S = agents.discover, portal = stations.discover.portal;
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
  const world = { scoredRatio: 0 };
  function queueLoad() { return Object.values(agents).reduce((n, a) => n + a.queue.length, 0); }
  function passToNext(fromKey, toKey, toBin) {
    const st = stations[fromKey];
    setPile(fromKey, st.count - 1);
    if (toBin) throwPaper(worldPos(st.pile), worldPos(st.bin).setY(0.7), () => addToBin(fromKey));
    else throwPaper(worldPos(st.pile), worldPos(stations[toKey].pile), () => setPile(toKey, stations[toKey].count + 1));
  }

  function onEvent(it) {
    const msg = it.message || '';
    const k = it.kind;
    const ag = (key) => agents[key];
    switch (it.stage) {
      case 'understand':
        if (k === 'work') ag('understand').push(T.say(short(msg, 64)), T.anim('Yes'));
        else if (k === 'good') { setPile('understand', 1); handoff('understand', 'plan', 1, 'Here is who we are searching for', 'Thanks — planning the searches now'); }
        break;
      case 'plan':
        if (k === 'work') ag('plan').push(T.say(short(msg, 64)), T.anim('Wave'));
        else if (k === 'info' && /planned/.test(msg)) {
          const n = (/(\d+) searches planned/.exec(msg) || [])[1];
          setPile('plan', 1); handoff('plan', 'discover', 1, `Here is the plan${n ? `: ${n} searches` : ''}`, 'On it — heading out to look!');
        }
        break;
      case 'discover': {
        const S = ag('discover');
        if (k === 'work' && S.queue.length < 12) {
          const found = /Opening (.+?)'s careers board/.exec(msg);
          scoutTrip(found ? `Checking ${found[1]}'s own job board` : msg, found ? 2 : 3);
        } else if (k === 'good' || k === 'info') S.push(T.say(short(msg, 70)));
        break;
      }
      case 'normalize': {
        const R = ag('normalize');
        if (k === 'work') handoff('discover', 'normalize', Math.max(2, stations.discover.count), `Here are the ${stations.discover.count || ''} job posts I found`.replace('  ', ' '), 'Great — I will open every page');
        else if (/^Read /.test(msg) && R.queue.length < 10) R.push(T.say(`Reading “${short(titleOf(msg), 34)}”`), T.anim('Yes'));
        break;
      }
      case 'dedupe':
        if (k === 'work') handoff('normalize', 'dedupe', Math.max(2, stations.normalize.count), 'All the postings, read and ready', 'Let me merge the duplicates');
        else ag('dedupe').push(T.say(short(msg, 70)), T.anim('ThumbsUp'));
        break;
      case 'validate': {
        const Vf = ag('validate');
        if (k === 'work') {
          if (!Vf.handed) { Vf.handed = true; handoff('dedupe', 'validate', Math.max(2, stations.dedupe.count), 'Unique jobs — please check they are real', 'Checking each one is live'); }
          Vf.push(T.say(short(msg, 64)));
        } else if (Vf.queue.length < 16) {
          const t = short(titleOf(msg) || msg.replace(/ (is live|has closed|looks old).*$/, ''), 34);
          if (k === 'good') Vf.push(T.anim('Punch'), T.call(() => { stampHit = 1; passToNext('validate', 'match'); }), T.say(`✓ ${t} is live`, 2.6));
          else if (k === 'reject') Vf.push(T.anim('No'), T.call(() => passToNext('validate', 'match', true)), T.say(`✗ ${short(msg, 46)}`, 2.6));
          else Vf.push(T.say(short(msg, 56), 2.6), T.call(() => passToNext('validate', 'match')));
        }
        break;
      }
      case 'extract':
        gateAnalyst();
        if (k === 'work' && ag('match').queue.length < 12) ag('match').push(T.say(`Reading what “${short(titleOf(msg) || 'this job', 28)}” asks for`), T.anim('Yes'));
        break;
      case 'match': {
        gateAnalyst();
        const A = ag('match');
        if (A.queue.length > 16) break;
        const fit = /^(Strong match|Good match|Stretch)/.test(msg);
        const bad = /^Not a fit/.test(msg) || k === 'reject';
        if (fit) {
          A.push(T.anim('ThumbsUp'), T.say(short(msg, 70), 3));
          handoff('match', 'rank', 1, `“${short(titleOf(msg) || (msg.split('·')[1] || 'This one').trim(), 30)}” fits you!`, 'Adding it to your results');
          agents.rank.push(T.call(() => addResultCard()));
        } else if (bad) {
          A.push(T.anim('No'), T.say(short(msg, 70), 3), T.call(() => passToNext('match', null, true)));
        } else A.push(T.say(short(msg, 70), 3));
        break;
      }
      case 'rank':
        if (k === 'done') celebrate(msg);
        break;
      default:
    }
  }
  // the Analyst starts once the Verifier has checked the jobs it receives (the story follows the papers)
  function gateAnalyst() {
    const A = agents.match;
    if (A.gated) return;
    A.gated = true;
    A.push(T.until(() => !agents.validate.busy, 45));
  }
  function celebrate(msg) {
    if (celebrated) return; celebrated = true;
    const R = agents.rank;
    let cheered = false;
    // wait until the last papers have reached the Ranker, then celebrate together
    R.push(T.until(() => !agents.match.busy && !agents.validate.busy && !agents.dedupe.busy, 90),
      T.focus(() => R.front.clone()), T.call(() => { cheered = true; }), T.say(short(msg, 80), 6), T.loop('Dance', 5));
    let i = 0;
    for (const a of Object.values(agents)) {
      if (a === R) continue;
      a.push(T.until(() => cheered, 120), T.wait(0.4 + (i++) * 0.25), T.anim(i % 2 ? 'Wave' : 'ThumbsUp'));
    }
  }
  function reset(newRun) {
    runId = newRun; celebrated = false; lastId = null;
    for (const a of Object.values(agents)) {
      a.queue.length = 0; a.task = null; a.setCarry(0); a.handed = false; a.gated = false; a.holder.visible = true;
      a.holder.position.copy(a.home); a.holder.rotation.y = a.faceAngle; a.sitting = false; a.play('Idle', 0.1);
    }
    for (const k of Object.keys(stations)) { setPile(k, 0); if (stations[k].bin) { stations[k].bin.clear(); stations[k].binCount = 0; } }
    stations.rank.cards.clear();
  }

  // ------------------------------------------------------------------ theme
  function setTheme(isDark) {
    if (floorMat.map) floorMat.map.dispose();
    floorMat.map = plankTexture(isDark); floorMat.needsUpdate = true;
    wallMat.color.set(isDark ? 0x2c2c33 : 0xf4ede4);
    trimMat.color.set(isDark ? 0x3a3a43 : 0xd8cabb);
    hemi.color.set(isDark ? 0xaab4ff : 0xfff6ec); hemi.groundColor.set(isDark ? 0x15151b : 0xc9b8a6);
    hemi.intensity = isDark ? 0.55 : 1.0; sun.intensity = isDark ? 1.2 : 2.0;
    fill.intensity = isDark ? 30 : 18;
    renderer.toneMappingExposure = isDark ? 1.15 : 1.05;
  }
  setTheme(dark);

  // ------------------------------------------------------------------ camera
  const OVERVIEW = new THREE.Vector3(0, 0.2, 0.2);
  const cam = { theta: 0, phi: 0.9, r: 38, base: 38, zoomed: false, userUntil: 0, follow: true, rNow: null };
  const look = OVERVIEW.clone();
  let dragging = null;
  const el = renderer.domElement;
  el.style.touchAction = 'none';
  const onDown = (e) => { dragging = { x: e.clientX, y: e.clientY, theta: cam.theta, phi: cam.phi }; el.setPointerCapture(e.pointerId); el.classList.add('grabbing'); };
  const onMove = (e) => {
    if (!dragging) return;
    cam.theta = Math.max(-1.1, Math.min(1.1, dragging.theta - (e.clientX - dragging.x) * 0.005));
    cam.phi = Math.min(1.3, Math.max(0.42, dragging.phi - (e.clientY - dragging.y) * 0.005));
    cam.userUntil = performance.now() + 9000;
  };
  const onUp = () => { dragging = null; el.classList.remove('grabbing'); };
  const onWheel = (e) => { e.preventDefault(); cam.r = Math.min(60, Math.max(12, cam.r + Math.sign(e.deltaY) * 2.4)); cam.zoomed = true; cam.userUntil = performance.now() + 9000; };
  el.addEventListener('pointerdown', onDown); el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerup', onUp); el.addEventListener('pointercancel', onUp);
  el.addEventListener('wheel', onWheel, { passive: false });

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w / h < 1.4 ? 44 : 34;
    camera.updateProjectionMatrix();
    // fit the whole room: wider panels need less distance, tall/narrow ones more
    const aspect = w / h;
    cam.base = Math.max(30, Math.min(50, 22 + 38 / aspect));
    if (!cam.zoomed) cam.r = cam.base;
  }
  const ro = new ResizeObserver(resize); ro.observe(container); resize();

  // ------------------------------------------------------------------ main loop
  let raf = 0, last = performance.now(), visible = true, disposed = false;
  const tagPos = new THREE.Vector3();
  let frameCb = null;
  function frame(now) {
    raf = 0; if (disposed) return;
    let dt = Math.min(0.05, (now - last) / 1000); last = now;
    clock += dt;
    // when many events pile up, the office works faster so it stays close to real time
    const load = queueLoad();
    speed = load > 40 ? 2.2 : load > 20 ? 1.6 : 1;
    if (reducedMotion) dt *= 0.0001;
    for (const a of Object.values(agents)) {
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

    // camera glides to where the action is (unless the user is looking around)
    const userHolds = performance.now() < cam.userUntil;
    const following = cam.follow && focus && clock < focusUntil && !userHolds;
    // stay inside the room: never look so far to a side that empty space shows
    const goal = following ? V(Math.max(-5.5, Math.min(5.5, focus.x)), Math.max(-4, Math.min(3, focus.z)), 0.6) : OVERVIEW;
    look.lerp(goal, Math.min(1, dt * 1.6));
    const r = following && !cam.zoomed ? cam.base * 0.84 : cam.r;
    cam.rNow = cam.rNow == null ? r : cam.rNow + (r - cam.rNow) * Math.min(1, dt * 1.6);
    camera.position.set(look.x + Math.sin(cam.theta) * Math.sin(cam.phi) * cam.rNow, look.y + Math.cos(cam.phi) * cam.rNow, look.z + Math.cos(cam.theta) * Math.sin(cam.phi) * cam.rNow);
    camera.lookAt(look);
    renderer.render(scene, camera);
    if (frameCb) {
      const w = container.clientWidth, h = container.clientHeight, out = {};
      for (const [key, a] of Object.entries(agents)) {
        a.holder.getWorldPosition(tagPos); tagPos.y += ROBOT_HEIGHT + 0.35; tagPos.project(camera);
        out[key] = { x: (tagPos.x + 1) / 2 * w, y: (1 - tagPos.y) / 2 * h, visible: a.holder.visible && tagPos.z < 1 && tagPos.z > -1, depth: tagPos.z };
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
    /** stage states + live counts from the run */
    update(states, extra = {}) {
      Object.assign(world, extra);
      stateMap = states;
      for (const [key, st] of Object.entries(states)) if (agents[key]) agents[key].state = st;
    },
    /** activity items of the run, oldest first; only new ones become scenes */
    feed(items, id, finished, recent) {
      if (id !== runId) reset(id);
      if (lastId === null) {
        // Opened while the search runs (or just finished): act out the latest real events so nothing is
        // missed while the office loads. An old finished search is shown calmly, without replaying it.
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
    resetView() { Object.assign(cam, { theta: 0, phi: 0.9, r: cam.base, zoomed: false, userUntil: 0 }); },
    dispose() {
      disposed = true; cancelAnimationFrame(raf);
      ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', onVis);
      el.removeEventListener('pointerdown', onDown); el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerup', onUp); el.removeEventListener('pointercancel', onUp); el.removeEventListener('wheel', onWheel);
      for (const a of Object.values(agents)) a.mixer.stopAllAction();
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) owned.add(o.material); });
      if (floorMat.map) floorMat.map.dispose();
      owned.forEach((m) => m.dispose && m.dispose());
      renderer.dispose(); el.remove();
    },
  };
}
