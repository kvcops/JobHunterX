// The 3D "agents at work" world (Three.js, loaded only when this view is opened).
// Eight low-poly characters work at their stations on an office island. Their state —
// waiting, working, finished — is driven entirely by the live search run; this file
// only decides how each state looks and moves.
import * as THREE from '../../vendor/three.module.min.js';

// Station layout follows the pipeline order around the island; papers flow along the road between them.
export const STATIONS = [
  { key: 'understand', pos: [-9.5, -4.6], hue: 18, act: 'type', prop: 'desk' },
  { key: 'plan', pos: [-3.4, -6.4], hue: 265, act: 'type', prop: 'board' },
  { key: 'discover', pos: [3.4, -6.4], hue: 205, act: 'walk', prop: 'globe' },
  { key: 'normalize', pos: [9.5, -4.6], hue: 160, act: 'read', prop: 'shelf' },
  { key: 'dedupe', pos: [9.5, 2.6], hue: 40, act: 'type', prop: 'sorter' },
  { key: 'validate', pos: [3.4, 5.6], hue: 140, act: 'stamp', prop: 'stamp' },
  { key: 'match', pos: [-3.4, 5.6], hue: 330, act: 'think', prop: 'chart' },
  { key: 'rank', pos: [-9.5, 2.6], hue: 28, act: 'cheer', prop: 'podium' },
];
const PORTAL = new THREE.Vector3(0, 0, -9.0);     // "the web": where the Scout walks out to search

const hsl = (h, s, l) => new THREE.Color().setHSL(h / 360, s, l);

export function createWorld(container, { dark = false, reducedMotion = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.className = 'aw3d-gl';
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.5, 200);
  const mats = new Map();
  const mat = (color, extra = {}) => {
    const key = `${color.getHexString ? color.getHexString() : color}|${JSON.stringify(extra)}`;
    if (!mats.has(key)) mats.set(key, new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0.04, ...extra }));
    return mats.get(key);
  };
  const box = (w, h, d, m) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.castShadow = true; o.receiveShadow = true; return o; };
  const cyl = (rt, rb, h, m, seg = 20) => { const o = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), m); o.castShadow = true; o.receiveShadow = true; return o; };
  const sphere = (r, m, seg = 20) => { const o = new THREE.Mesh(new THREE.SphereGeometry(r, seg, Math.round(seg * 0.75)), m); o.castShadow = true; return o; };
  const capsule = (r, len, m) => { const o = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 6, 12), m); o.castShadow = true; return o; };

  // ------------------------------------------------------------------ lights
  const hemi = new THREE.HemisphereLight(0xffffff, 0xd9cbbd, 1.15);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff4e6, 1.55);
  sun.position.set(-12, 22, 14);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1536, 1536);
  Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 18, bottom: -18, near: 1, far: 70 });
  sun.shadow.bias = -0.0008;
  sun.shadow.radius = 4;
  scene.add(sun);

  // ------------------------------------------------------------------ island floor + road
  const floorGroup = new THREE.Group();
  scene.add(floorGroup);
  const floorShape = new THREE.Shape();
  const W = 14.6, D = 10.4, R = 3.2;
  floorShape.moveTo(-W + R, -D); floorShape.lineTo(W - R, -D); floorShape.quadraticCurveTo(W, -D, W, -D + R);
  floorShape.lineTo(W, D - R); floorShape.quadraticCurveTo(W, D, W - R, D); floorShape.lineTo(-W + R, D);
  floorShape.quadraticCurveTo(-W, D, -W, D - R); floorShape.lineTo(-W, -D + R); floorShape.quadraticCurveTo(-W, -D, -W + R, -D);
  const floorGeo = new THREE.ExtrudeGeometry(floorShape, { depth: 0.9, bevelEnabled: true, bevelThickness: 0.25, bevelSize: 0.3, bevelSegments: 4 });
  floorGeo.rotateX(Math.PI / 2);
  const floor = new THREE.Mesh(floorGeo, mat(new THREE.Color(0xefe7dd)));
  floor.position.y = -0.25;          // bevel makes the top face sit at +0.25
  floor.receiveShadow = true;
  floorGroup.add(floor);

  // faint floor tiles so it reads as a place
  const grid = new THREE.GridHelper(28, 28, 0x000000, 0x000000);
  grid.material.transparent = true; grid.material.opacity = 0.05; grid.material.depthWrite = false;
  grid.position.y = 0.012; grid.scale.z = 20.6 / 28;
  floorGroup.add(grid);

  // road through the stations in pipeline order (the papers travel on it)
  const roadPts = STATIONS.map((s) => new THREE.Vector3(s.pos[0] * 0.78, 0.03, s.pos[1] * 0.78));
  const road = new THREE.CatmullRomCurve3(roadPts, false, 'catmullrom', 0.3);
  const roadGeo = new THREE.TubeGeometry(road, 120, 0.42, 6, false);
  roadGeo.scale(1, 0.08, 1);
  const roadMesh = new THREE.Mesh(roadGeo, mat(new THREE.Color(0xe2d6c6)));
  roadMesh.receiveShadow = true;
  floorGroup.add(roadMesh);

  // little plants and lamps so it reads as a place, not a chart
  const plantMat = mat(hsl(140, 0.35, 0.42)), potMat = mat(hsl(20, 0.35, 0.55));
  for (const [x, z] of [[-13, -8.6], [13, -8.6], [-13, 8.6], [13, 8.6], [0, -0.2], [0, 9.3]]) {
    const pot = cyl(0.42, 0.32, 0.6, potMat); pot.position.set(x, 0.3, z); floorGroup.add(pot);
    const bush = sphere(0.62, plantMat, 10); bush.position.set(x, 1.05, z); bush.scale.set(1, 1.2, 1); floorGroup.add(bush);
  }

  // ------------------------------------------------------------------ the web portal (Scout's destination)
  const portal = new THREE.Group();
  portal.position.copy(PORTAL);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.25, 0.13, 12, 48), mat(hsl(205, 0.75, 0.55), { emissive: hsl(205, 0.85, 0.45), emissiveIntensity: 0.6 }));
  ring.position.y = 1.6; ring.castShadow = true;
  portal.add(ring);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(1.15, 40), new THREE.MeshBasicMaterial({ color: hsl(205, 0.9, 0.7), transparent: true, opacity: 0.22, side: THREE.DoubleSide }));
  disc.position.y = 1.6;
  portal.add(disc);
  const base = cyl(1.4, 1.6, 0.25, mat(hsl(205, 0.25, 0.82))); base.position.y = 0.12; portal.add(base);
  const bits = [];
  for (let i = 0; i < 7; i++) {
    const b = box(0.24, 0.3, 0.04, mat(new THREE.Color(0xffffff), { emissive: hsl(205, 0.6, 0.5), emissiveIntensity: 0.15 }));
    portal.add(b); bits.push(b);
  }
  scene.add(portal);

  // ------------------------------------------------------------------ station props
  const wood = mat(hsl(28, 0.32, 0.62)), metal = mat(hsl(220, 0.08, 0.35)), white = mat(new THREE.Color(0xfbfbfb));
  function desk(g, hue) {
    const top = box(2.4, 0.14, 1.2, wood); top.position.y = 1.05; g.add(top);
    for (const [x, z] of [[-1.05, -0.45], [1.05, -0.45], [-1.05, 0.45], [1.05, 0.45]]) { const l = box(0.1, 1.0, 0.1, metal); l.position.set(x, 0.5, z); g.add(l); }
    const mon = box(1.1, 0.72, 0.08, metal); mon.position.set(0, 1.65, -0.35); g.add(mon);
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.98, 0.6), mat(hsl(hue, 0.6, 0.6), { emissive: hsl(hue, 0.7, 0.45), emissiveIntensity: 0.5 }));
    screen.position.set(0, 1.65, -0.305); g.add(screen);
    const stand = box(0.12, 0.3, 0.12, metal); stand.position.set(0, 1.25, -0.38); g.add(stand);
    const kb = box(0.8, 0.05, 0.28, metal); kb.position.set(0, 1.14, 0.12); g.add(kb);
    return { screen };
  }
  const PROPS = {
    desk: (g, hue) => desk(g, hue),
    board: (g, hue) => {
      const b = box(2.6, 1.6, 0.1, white); b.position.set(0, 1.9, -0.5); g.add(b);
      const frame = box(2.75, 0.1, 0.16, metal); frame.position.set(0, 1.08, -0.5); g.add(frame);
      for (const x of [-1.2, 1.2]) { const l = box(0.1, 1.9, 0.1, metal); l.position.set(x, 0.95, -0.5); g.add(l); }
      const lines = [];
      for (let i = 0; i < 4; i++) {
        const ln = box(0.6 + i * 0.35, 0.07, 0.02, mat(hsl(hue + i * 40, 0.6, 0.55))); ln.position.set(-0.85 + (0.6 + i * 0.35) / 2 - 0.3, 2.4 - i * 0.3, -0.44);
        g.add(ln); lines.push(ln);
      }
      return { lines };
    },
    globe: (g, hue) => {
      const st = cyl(0.18, 0.5, 0.9, metal); st.position.y = 0.45; g.add(st);
      const gl = sphere(0.75, mat(hsl(hue, 0.55, 0.62), { emissive: hsl(hue, 0.6, 0.35), emissiveIntensity: 0.25 }), 24); gl.position.y = 1.65; g.add(gl);
      const band = new THREE.Mesh(new THREE.TorusGeometry(0.85, 0.04, 8, 40), metal); band.position.y = 1.65; band.rotation.x = Math.PI / 2.4; g.add(band);
      return { globe: gl };
    },
    shelf: (g, hue) => {
      const sh = box(2.4, 2.6, 0.6, wood); sh.position.set(0, 1.3, -0.55); g.add(sh);
      for (let r = 0; r < 3; r++) for (let i = 0; i < 6; i++) {
        const bk = box(0.24, 0.55 + ((i * 7 + r) % 3) * 0.1, 0.42, mat(hsl(hue + i * 37 + r * 60, 0.5, 0.58)));
        bk.position.set(-0.9 + i * 0.34, 0.55 + r * 0.8, -0.32); g.add(bk);
      }
      const table = box(1.6, 0.12, 0.8, wood); table.position.set(0, 0.85, 0.35); g.add(table);
      return {};
    },
    sorter: (g, hue) => {
      const top = box(2.4, 0.14, 1.2, wood); top.position.y = 1.05; g.add(top);
      for (const x of [-1.05, 1.05]) { const l = box(0.1, 1.0, 1.0, metal); l.position.set(x, 0.5, 0); g.add(l); }
      const stacks = [];
      for (let i = 0; i < 3; i++) {
        const s = new THREE.Group(); s.position.set(-0.75 + i * 0.75, 1.13, 0);
        for (let k = 0; k < 3 + i; k++) { const c = box(0.5, 0.04, 0.65, mat(hsl(hue + k * 25, 0.55, 0.75))); c.position.y = k * 0.05; s.add(c); }
        g.add(s); stacks.push(s);
      }
      return { stacks };
    },
    stamp: (g, hue) => {
      const top = box(2.0, 0.14, 1.1, wood); top.position.y = 1.05; g.add(top);
      for (const x of [-0.85, 0.85]) { const l = box(0.1, 1.0, 0.9, metal); l.position.set(x, 0.5, 0); g.add(l); }
      const paper = box(0.7, 0.02, 0.9, white); paper.position.set(0.2, 1.13, 0.05); g.add(paper);
      const stamp = new THREE.Group(); stamp.position.set(0.2, 1.5, 0.05);
      const sb = cyl(0.26, 0.3, 0.16, mat(hsl(hue, 0.6, 0.45))); stamp.add(sb);
      const sh = cyl(0.08, 0.1, 0.45, wood); sh.position.y = 0.3; stamp.add(sh);
      const knob = sphere(0.14, wood); knob.position.y = 0.58; stamp.add(knob);
      g.add(stamp);
      const mark = new THREE.Mesh(new THREE.CircleGeometry(0.22, 24), new THREE.MeshBasicMaterial({ color: hsl(hue, 0.7, 0.45), transparent: true, opacity: 0 }));
      mark.rotation.x = -Math.PI / 2; mark.position.set(0.2, 1.142, 0.05); g.add(mark);
      return { stamp, mark };
    },
    chart: (g, hue) => {
      const d = desk(g, hue);
      const bars = [];
      for (let i = 0; i < 4; i++) {
        const b = box(0.22, 1, 0.22, mat(hsl(hue + i * 18, 0.65, 0.58), { emissive: hsl(hue, 0.6, 0.3), emissiveIntensity: 0.2 }));
        b.position.set(0.66 + (i % 2) * 0.3, 1.2, 0.1 + Math.floor(i / 2) * 0.26); b.scale.y = 0.2; g.add(b); bars.push(b);
      }
      return { ...d, bars };
    },
    podium: (g, hue) => {
      const steps = [[0, 1.0], [-0.95, 0.65], [0.95, 0.4]];
      for (const [x, h] of steps) { const s = box(0.9, h, 0.9, mat(hsl(hue, 0.35, 0.72))); s.position.set(x, h / 2, -0.4); g.add(s); }
      const trophy = new THREE.Group(); trophy.position.set(0, 1.0, -0.4);
      const gold = mat(hsl(45, 0.85, 0.55), { metalness: 0.55, roughness: 0.3, emissive: hsl(45, 0.8, 0.3), emissiveIntensity: 0.15 });
      const tb = cyl(0.22, 0.28, 0.14, gold); tb.position.y = 0.07; trophy.add(tb);
      const stem = cyl(0.06, 0.08, 0.35, gold); stem.position.y = 0.3; trophy.add(stem);
      const cup = cyl(0.32, 0.14, 0.45, gold); cup.position.y = 0.7; trophy.add(cup);
      for (const x of [-0.36, 0.36]) { const h = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.035, 8, 16), gold); h.position.set(x, 0.75, 0); h.rotation.y = Math.PI / 2; trophy.add(h); }
      g.add(trophy);
      return { trophy };
    },
  };

  // ------------------------------------------------------------------ characters
  const own = [];                     // per-character materials (recoloured live), disposed with the world
  const skin = mat(hsl(28, 0.55, 0.74)), hair = mat(hsl(25, 0.25, 0.16)), eyeM = mat(hsl(0, 0, 0.1));
  function person(hue) {
    const g = new THREE.Group();
    const cloth = new THREE.MeshStandardMaterial({ color: hsl(hue, 0.6, 0.55), roughness: 0.7 }), limb = mat(hsl(hue, 0.45, 0.4)), shoe = mat(hsl(0, 0, 0.22));
    const legs = [];
    for (const x of [-0.17, 0.17]) {
      const hip = new THREE.Group(); hip.position.set(x, 0.95, 0);
      const leg = capsule(0.14, 0.55, mat(hsl(220, 0.25, 0.3))); leg.position.y = -0.42; hip.add(leg);
      const foot = box(0.22, 0.1, 0.34, shoe); foot.position.set(0, -0.9, 0.06); hip.add(foot);
      g.add(hip); legs.push(hip);
    }
    const torso = capsule(0.36, 0.5, cloth); torso.position.y = 1.42; g.add(torso);
    const arms = [];
    for (const x of [-0.5, 0.5]) {
      const sh = new THREE.Group(); sh.position.set(x, 1.78, 0);
      const arm = capsule(0.11, 0.48, limb); arm.position.y = -0.33; sh.add(arm);
      const hand = sphere(0.11, skin, 10); hand.position.y = -0.66; sh.add(hand);
      g.add(sh); arms.push(sh);
    }
    const head = new THREE.Group(); head.position.y = 2.32;
    const skull = sphere(0.36, skin); head.add(skull);
    const top = sphere(0.375, hair); top.scale.set(1, 0.62, 1); top.position.y = 0.12; head.add(top);
    for (const x of [-0.13, 0.13]) { const e = sphere(0.045, eyeM, 8); e.position.set(x, 0.0, 0.33); head.add(e); }
    g.add(head);
    // soft status ring under the feet
    const ringMat = new THREE.MeshBasicMaterial({ color: hsl(hue, 0.8, 0.55), transparent: true, opacity: 0, depthWrite: false });
    const statusRing = new THREE.Mesh(new THREE.RingGeometry(0.62, 0.82, 40), ringMat);
    statusRing.rotation.x = -Math.PI / 2; statusRing.position.y = 0.05; g.add(statusRing);
    const held = box(0.32, 0.42, 0.02, white); held.visible = false; held.position.set(0, -0.62, 0.18); arms[1].add(held);
    own.push(cloth, ringMat);
    return { g, legs, arms, head, torso, statusRing, ringMat, held, cloth };
  }

  // ------------------------------------------------------------------ build stations
  const agents = {};
  const pads = [];
  for (const s of STATIONS) {
    const st = new THREE.Group();
    st.position.set(s.pos[0], 0, s.pos[1]);
    // face the island centre so every station is seen from the front
    st.rotation.y = Math.atan2(-s.pos[0], -s.pos[1]) + Math.PI;
    const padMat = new THREE.MeshStandardMaterial({ color: hsl(s.hue, 0.35, 0.86), roughness: 0.8 });
    own.push(padMat); pads.push({ m: padMat, hue: s.hue });
    const pad = cyl(2.35, 2.45, 0.16, padMat); pad.position.y = 0.08; pad.castShadow = false; st.add(pad);
    const rimMat = new THREE.MeshBasicMaterial({ color: hsl(s.hue, 0.7, 0.6), transparent: true, opacity: 0.35 });
    const rim = new THREE.Mesh(new THREE.RingGeometry(2.38, 2.55, 48), rimMat); rim.rotation.x = -Math.PI / 2; rim.position.y = 0.17; st.add(rim);
    const propGroup = new THREE.Group(); propGroup.position.z = -0.4; st.add(propGroup);
    const parts = PROPS[s.prop](propGroup, s.hue) || {};
    const p = person(s.hue);
    p.g.position.set(0, 0.16, 0.75);
    p.g.rotation.y = Math.PI;               // the person faces their work
    st.add(p.g);
    scene.add(st);
    agents[s.key] = { s, st, p, parts, rimMat, home: p.g.position.clone(), state: 'pending', since: 0, seed: Math.random() * 10 };
  }

  // papers flying between stations while the receiving one works
  const paperMat = mat(new THREE.Color(0xffffff));
  const papers = [];
  for (let i = 0; i < 14; i++) { const pp = box(0.34, 0.03, 0.44, paperMat); pp.visible = false; scene.add(pp); papers.push(pp); }

  // ------------------------------------------------------------------ theme
  function setTheme(isDark) {
    floor.material = mat(new THREE.Color(isDark ? 0x2a2a31 : 0xefe7dd));
    roadMesh.material = mat(new THREE.Color(isDark ? 0x34343c : 0xe2d6c6));
    hemi.color.set(isDark ? 0xbfc6ff : 0xffffff);
    hemi.groundColor.set(isDark ? 0x1b1b22 : 0xd9cbbd);
    hemi.intensity = isDark ? 0.75 : 1.15;
    sun.intensity = isDark ? 1.05 : 1.55;
    pads.forEach(({ m, hue }) => m.color.copy(hsl(hue, isDark ? 0.22 : 0.35, isDark ? 0.27 : 0.86)));
  }
  setTheme(dark);

  // ------------------------------------------------------------------ camera: drag to orbit, wheel to zoom
  const cam = { theta: -0.55, phi: 0.98, r: 34, base: 34, zoomed: false, userUntil: 0 };
  let dragging = null;
  const el = renderer.domElement;
  el.style.touchAction = 'none';
  const onDown = (e) => { dragging = { x: e.clientX, y: e.clientY, theta: cam.theta, phi: cam.phi }; el.setPointerCapture(e.pointerId); el.classList.add('grabbing'); };
  const onMove = (e) => {
    if (!dragging) return;
    cam.theta = dragging.theta - (e.clientX - dragging.x) * 0.006;
    cam.phi = Math.min(1.32, Math.max(0.45, dragging.phi - (e.clientY - dragging.y) * 0.005));
    cam.userUntil = performance.now() + 8000;
  };
  const onUp = () => { dragging = null; el.classList.remove('grabbing'); };
  const onWheel = (e) => { e.preventDefault(); cam.r = Math.min(56, Math.max(18, cam.r + Math.sign(e.deltaY) * 2.2)); cam.zoomed = true; cam.userUntil = performance.now() + 8000; };
  el.addEventListener('pointerdown', onDown);
  el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerup', onUp);
  el.addEventListener('pointercancel', onUp);
  el.addEventListener('wheel', onWheel, { passive: false });

  // ------------------------------------------------------------------ resize
  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // keep the whole island in view on narrow panels
    camera.fov = w / h < 1.3 ? 42 : 32;
    camera.updateProjectionMatrix();
    // frame the island: closer in a short panel, a little wider when expanded
    cam.base = h < 300 ? 30 : h < 520 ? 31.5 : 36;
    if (!cam.zoomed) cam.r = cam.base;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  // ------------------------------------------------------------------ state from the live run
  let world = { scoredRatio: 0 };
  function update(states, extra = {}) {
    world = { ...world, ...extra };
    for (const [key, st] of Object.entries(states)) {
      const a = agents[key];
      if (a && a.state !== st) { a.state = st; a.since = performance.now() / 1000; }
    }
  }

  // ------------------------------------------------------------------ animation
  const tmp = new THREE.Vector3();
  const head = new THREE.Vector3();
  let frameCb = null, raf = 0, last = performance.now(), visible = true, disposed = false;
  const clock = { t: 0 };

  function poseAgent(a, t, dt) {
    const { p, parts, s } = a;
    const run = a.state === 'running', done = a.state === 'done', pend = a.state === 'pending';
    const k = reducedMotion ? 0 : 1;
    const ph = t + a.seed;
    // defaults: stand still, arms down
    let walk = 0;
    p.legs[0].rotation.x = 0; p.legs[1].rotation.x = 0;
    p.arms[0].rotation.set(0, 0, 0.08); p.arms[1].rotation.set(0, 0, -0.08);
    p.head.rotation.set(0, 0, 0);
    p.held.visible = false;
    p.g.position.y = 0.16;
    let target = a.home;

    if (run && s.act === 'walk') {
      // Scout walks out to the web portal and back with what it found
      const portalLocal = a.st.worldToLocal(tmp.copy(PORTAL));
      const cyc = (ph * 0.16) % 2;
      const u = cyc < 1 ? cyc : 2 - cyc;
      const e = u * u * (3 - 2 * u);
      target = a.home.clone().lerp(portalLocal.setY(0.16), e);
      walk = (u > 0.02 && u < 0.98) ? 1 : 0;
      p.g.position.x = target.x; p.g.position.z = target.z;
      const dir = cyc < 1 ? 1 : -1;
      const dx = portalLocal.x - a.home.x, dz = portalLocal.z - a.home.z;
      p.g.rotation.y = Math.atan2(dx * dir, dz * dir);
      p.held.visible = cyc >= 1;
    } else if (run && s.act === 'think') {
      const sw = Math.sin(ph * 0.9) * 1.1 * k;
      p.g.position.x = a.home.x + sw; p.g.position.z = a.home.z;
      walk = Math.abs(Math.cos(ph * 0.9)) > 0.25 ? 0.7 : 0;
      p.g.rotation.y = Math.PI + (Math.cos(ph * 0.9) > 0 ? -1.2 : 1.2) * (walk ? 1 : 0.2);
      p.head.rotation.z = Math.sin(ph * 2) * 0.12 * k;
      p.arms[1].rotation.x = -1.3; p.arms[1].rotation.z = -0.5;       // hand on chin
    } else if (run && s.act === 'read') {
      const sw = Math.sin(ph * 0.5) * 0.6 * k;
      p.g.position.x = a.home.x + sw; p.g.position.z = a.home.z;
      p.g.rotation.y = Math.PI;
      p.arms[1].rotation.x = -1.25; p.held.visible = true;
      p.head.rotation.x = 0.25 + Math.sin(ph * 2.4) * 0.08 * k;
    } else {
      p.g.position.x = a.home.x; p.g.position.z = a.home.z;
      p.g.rotation.y = done ? 0 : Math.PI;      // finished agents turn round to face you
    }

    if (walk) {
      const sw = Math.sin(ph * 9) * 0.55 * walk * k;
      p.legs[0].rotation.x = sw; p.legs[1].rotation.x = -sw;
      p.arms[0].rotation.x = -sw * 0.8; p.arms[1].rotation.x = p.held.visible ? -1.1 : sw * 0.8;
      p.g.position.y = 0.16 + Math.abs(Math.sin(ph * 9)) * 0.06 * k;
    }
    if (run && s.act === 'type') {
      p.arms[0].rotation.x = -1.05 + Math.sin(ph * 16) * 0.12 * k;
      p.arms[1].rotation.x = -1.05 + Math.sin(ph * 16 + 1.6) * 0.12 * k;
      p.head.rotation.x = 0.12 + Math.sin(ph * 1.3) * 0.05 * k;
      p.g.position.y = 0.16 + Math.abs(Math.sin(ph * 3)) * 0.02 * k;
    }
    if (run && s.act === 'stamp') {
      const c = (ph * 0.9) % 1;
      const slam = c < 0.55 ? 0 : c < 0.7 ? (c - 0.55) / 0.15 : c < 0.85 ? 1 - (c - 0.7) / 0.15 : 0;
      p.arms[1].rotation.x = -1.2 - (1 - slam) * 0.9 * k;
      if (parts.stamp) parts.stamp.position.y = 1.5 - slam * 0.28 * k;
      if (parts.mark) parts.mark.material.opacity = Math.max(parts.mark.material.opacity * 0.985, slam > 0.95 ? 0.85 : 0);
      p.arms[0].rotation.x = -0.7;
    }
    if ((run || done) && s.act === 'cheer') {
      const wv = Math.sin(ph * (run ? 5 : 3)) * 0.25 * k;
      p.arms[0].rotation.z = 2.6 + wv; p.arms[1].rotation.z = -2.6 - wv;
      if (run) p.g.position.y = 0.16 + Math.abs(Math.sin(ph * 4)) * 0.18 * k;
    }
    if (pend) {
      // waiting: a slow breath, a little slumped
      p.head.rotation.x = 0.28; p.g.position.y = 0.16 + Math.sin(ph * 1.2) * 0.015 * k;
      p.arms[0].rotation.z = 0.02; p.arms[1].rotation.z = -0.02;
    }

    // colour and status ring
    p.cloth.color.copy(hsl(s.hue, pend ? 0.12 : a.state === 'failed' ? 0.0 : 0.6, pend ? 0.66 : 0.55));
    if (a.state === 'failed') p.cloth.color.set(0xd4473a);
    const ringTarget = run ? 0.55 + Math.sin(t * 4) * 0.25 * k : done ? 0.45 : 0;
    p.ringMat.opacity += (ringTarget - p.ringMat.opacity) * Math.min(1, dt * 6);
    p.ringMat.color.copy(done ? hsl(150, 0.65, 0.45) : hsl(s.hue, 0.8, 0.55));
    const scl = run ? 1 + Math.sin(t * 4) * 0.08 * k : 1;
    p.statusRing.scale.set(scl, scl, scl);
    a.rimMat.opacity = run ? 0.75 : done ? 0.45 : 0.18;

    // props come alive while their agent works
    if (parts.screen) parts.screen.material.emissiveIntensity = run ? 0.65 + Math.sin(t * 6) * 0.15 * k : pend ? 0.08 : 0.35;
    if (parts.globe) parts.globe.rotation.y += dt * (run ? 1.1 : 0.15) * k;
    if (parts.lines) parts.lines.forEach((ln, i) => { ln.scale.x = run ? 0.6 + 0.4 * Math.abs(Math.sin(t * 1.5 + i)) : done ? 1 : 0.5; });
    if (parts.stacks) parts.stacks.forEach((st, i) => { st.position.y = 1.13 + (run ? Math.abs(Math.sin(t * 3 + i * 1.3)) * 0.18 * k : 0); });
    if (parts.bars) {
      const ratio = world.scoredRatio || 0;
      parts.bars.forEach((b, i) => {
        const goal = done ? 0.5 + i * 0.25 : run ? 0.2 + (ratio * (1 + i * 0.4)) + Math.abs(Math.sin(t * 2 + i)) * 0.15 * k : 0.15;
        b.scale.y += (goal - b.scale.y) * Math.min(1, dt * 3); b.position.y = b.scale.y / 2 + 1.12;
      });
    }
    if (parts.trophy) { parts.trophy.rotation.y += dt * (done ? 1.2 : run ? 2.2 : 0) * k; parts.trophy.position.y = 1.0 + (done || run ? 0.1 + Math.sin(t * 2) * 0.05 * k : 0); }
  }

  function flowPapers(t) {
    let n = 0;
    STATIONS.forEach((s, i) => {
      if (i < 3 || agents[s.key].state !== 'running') return;
      const from = STATIONS[i - 1].pos, to = s.pos;
      for (let j = 0; j < 3 && n < papers.length; j++, n++) {
        const u = ((reducedMotion ? 0.5 : t * 0.35) + j / 3) % 1;
        const pp = papers[n];
        pp.visible = true;
        pp.position.set(from[0] + (to[0] - from[0]) * u, 1.4 + Math.sin(Math.PI * u) * 2.2, from[1] + (to[1] - from[1]) * u);
        pp.rotation.set(Math.sin(t * 3 + j) * 0.4, t * 2 + j, Math.cos(t * 2.5 + j) * 0.3);
      }
    });
    for (; n < papers.length; n++) papers[n].visible = false;
  }

  let skip = 0;
  function frame(now) {
    raf = 0;
    if (disposed) return;
    // nobody working and nobody dragging: draw ~20 fps instead of 60 to save battery
    const idle = !dragging && !Object.values(agents).some((a) => a.state === 'running');
    if (idle && (skip = (skip + 1) % 3) !== 0) { schedule(); return; }
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    clock.t += dt;
    const t = clock.t;
    // camera: gentle drift unless the user is looking around
    if (!reducedMotion && now > cam.userUntil) cam.theta += dt * 0.025;
    camera.position.set(Math.sin(cam.theta) * Math.sin(cam.phi) * cam.r, Math.cos(cam.phi) * cam.r, Math.cos(cam.theta) * Math.sin(cam.phi) * cam.r);
    camera.lookAt(0, 0.6, 0.4);

    for (const a of Object.values(agents)) poseAgent(a, t, dt);
    flowPapers(t);
    const scoutBusy = agents.discover.state === 'running';
    ring.rotation.z += dt * (scoutBusy ? 1.6 : 0.3) * (reducedMotion ? 0 : 1);
    disc.material.opacity = scoutBusy ? 0.3 + Math.sin(t * 3) * 0.1 : 0.12;
    bits.forEach((b, i) => {
      const ang = t * (scoutBusy ? 0.9 : 0.25) + (i / bits.length) * Math.PI * 2;
      b.position.set(Math.cos(ang) * 1.9, 1.6 + Math.sin(ang * 2) * 0.5, Math.sin(ang) * 0.5);
      b.rotation.y = ang;
    });

    renderer.render(scene, camera);

    if (frameCb) {
      const w = container.clientWidth, h = container.clientHeight, out = {};
      for (const [key, a] of Object.entries(agents)) {
        a.p.head.getWorldPosition(head);
        head.y += 1.0;
        head.project(camera);
        out[key] = { x: (head.x + 1) / 2 * w, y: (1 - head.y) / 2 * h, visible: head.z < 1 && head.z > -1, depth: head.z };
      }
      frameCb(out);
    }
    schedule();
  }
  function schedule() { if (!raf && visible && !disposed && !document.hidden) raf = requestAnimationFrame(frame); }
  const io = new IntersectionObserver((ents) => { visible = ents.some((e) => e.isIntersecting); schedule(); });
  io.observe(container);
  const onVis = () => schedule();
  document.addEventListener('visibilitychange', onVis);
  schedule();

  return {
    update,
    setTheme,
    onFrame(cb) { frameCb = cb; },
    resetView() { Object.assign(cam, { theta: -0.55, phi: 0.98, r: cam.base, zoomed: false, userUntil: 0 }); },
    dispose() {
      disposed = true;
      cancelAnimationFrame(raf);
      ro.disconnect(); io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      el.removeEventListener('pointerdown', onDown); el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerup', onUp); el.removeEventListener('pointercancel', onUp); el.removeEventListener('wheel', onWheel);
      const all = new Set([...mats.values(), ...own]);
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) all.add(o.material); });
      all.forEach((m) => m.dispose && m.dispose());
      renderer.dispose();
      el.remove();
    },
  };
}
