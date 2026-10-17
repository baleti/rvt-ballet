// 3D visual styles: Hidden Line (Revit look: white faces, crisp black feature + silhouette edges, translucent floors, per-category colour overrides),
// Shaded, Consistent Colors, Realistic (the viewer's textured default) and Wireframe.
// Faces use the patched mesh shader of app.js (uniform uStyle, per element override texture tOvr: rgb = surface colour, a = opacity).
// Edges: extracted once per mesh in a worker (sharp edges + element boundaries always drawn, smooth edges drawn only where the adjacent faces
// turn from front to back facing = silhouette, decided per frame in the vertex shader).
import * as THREE from 'three';

const S = window.S, scene = window.__scene, camera = window.__camera, renderer = window.__renderer, world = window.__world, U = window.__U;
const $ = s => document.querySelector(s);
const dirty = () => window.__dirty();
const STYLES = {hidden: 'Hidden Line', shaded: 'Shaded', consistent: 'Consistent Colors', realistic: 'Realistic', wire: 'Wireframe'};
const STYLE_ID = {realistic: 0, shaded: 0, hidden: 1, wire: 2, consistent: 4};
const H = window.__hl = {style: 'realistic', edges: [], twins: [], cat: {}, thresholdDeg: 30, group: null, version: 0};

// default hidden-line graphics per category (until the view's resolved overrides are applied through H.setCat)
H.cat = {'Floors': {a: 0.28}, 'Structural Foundations': {}, 'Roofs': {a: 0.5}};

const WORKER_SRC = `
self.onmessage = ev => {
  const {pos, index, eidx, thr, id} = ev.data; const n = pos.length / 3, nt = index.length / 3;
  const wid = new Int32Array(n), map = new Map(); let nw = 0; const rep = [];
  for (let i = 0; i < n; i++) {
    const x = Math.round(pos[3*i]*1000), y = Math.round(pos[3*i+1]*1000), z = Math.round(pos[3*i+2]*1000);
    const k = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791); let h = map.get(k);
    // collision-safe: chain verified by coordinates
    if (h === undefined) { h = []; map.set(k, h); }
    let f = -1; for (let j = 0; j < h.length; j++) { const r = h[j]; if (rep[3*r] === x && rep[3*r+1] === y && rep[3*r+2] === z) { f = r; break; } }
    if (f < 0) { f = nw++; rep.push(x, y, z); h.push(f); }
    wid[i] = f;
  }
  map.clear();
  const nrm = new Float32Array(nt * 3), cen = new Map();
  for (let t = 0; t < nt; t++) {
    const a = index[3*t], b = index[3*t+1], c = index[3*t+2];
    const ux = pos[3*b]-pos[3*a], uy = pos[3*b+1]-pos[3*a+1], uz = pos[3*b+2]-pos[3*a+2], vx = pos[3*c]-pos[3*a], vy = pos[3*c+1]-pos[3*a+1], vz = pos[3*c+2]-pos[3*a+2];
    let nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx; const l = Math.hypot(nx, ny, nz) || 1; nrm[3*t] = nx/l; nrm[3*t+1] = ny/l; nrm[3*t+2] = nz/l;
    const e = eidx[a]; let s = cen.get(e); if (!s) { s = [0,0,0,0]; cen.set(e, s); }
    s[0] += (pos[3*a]+pos[3*b]+pos[3*c])/3; s[1] += (pos[3*a+1]+pos[3*b+1]+pos[3*c+1])/3; s[2] += (pos[3*a+2]+pos[3*b+2]+pos[3*c+2])/3; s[3]++;
  }
  const em = new Map(); const ea = [], eb = [], t1 = [], t2 = [], cnt = [];   // edge table
  const SH = 67108864;
  for (let t = 0; t < nt; t++) {
    for (let k = 0; k < 3; k++) {
      const va = index[3*t+k], vb = index[3*t+(k+1)%3]; let a = wid[va], b = wid[vb]; if (a === b) continue;
      const lo = Math.min(a, b), hi = Math.max(a, b), key = lo * SH + hi; const s = em.get(key);
      if (s === undefined) { em.set(key, ea.length); ea.push(va); eb.push(vb); t1.push(t); t2.push(-1); cnt.push(1); }
      else { cnt[s]++; if (t2[s] < 0) t2[s] = t; }
    }
  }
  const cosT = Math.cos(thr * Math.PI / 180), cosS = Math.cos(2 * Math.PI / 180);
  const P = [], N1 = [], N2 = [], K = [], EI = [];
  const push = (va, vb, n1, n2, kind) => {
    P.push(pos[3*va], pos[3*va+1], pos[3*va+2], pos[3*vb], pos[3*vb+1], pos[3*vb+2]);
    for (let q = 0; q < 2; q++) { N1.push(n1[0], n1[1], n1[2]); N2.push(n2[0], n2[1], n2[2]); K.push(kind); EI.push(eidx[va]); }
  };
  const Z = [0, 0, 0];
  for (let s = 0; s < ea.length; s++) {
    const va = ea[s], vb = eb[s], A = t1[s], B = t2[s];
    if (cnt[s] !== 2) { push(va, vb, Z, Z, 0); continue; }
    if (eidx[index[3*A]] !== eidx[index[3*B]]) { push(va, vb, Z, Z, 0); continue; }
    let n1 = [nrm[3*A], nrm[3*A+1], nrm[3*A+2]], n2 = [nrm[3*B], nrm[3*B+1], nrm[3*B+2]]; let d = n1[0]*n2[0]+n1[1]*n2[1]+n1[2]*n2[2];
    if (d < 0) { n2 = [-n2[0], -n2[1], -n2[2]]; d = -d; }
    if (d < cosT) { push(va, vb, Z, Z, 0); continue; }
    if (d > cosS) continue;
    // smooth edge: silhouette candidate; orient both normals away from the element centre
    const c = cen.get(eidx[va]); const mx = (pos[3*va]+pos[3*vb])/2 - c[0]/c[3], my = (pos[3*va+1]+pos[3*vb+1])/2 - c[1]/c[3], mz = (pos[3*va+2]+pos[3*vb+2])/2 - c[2]/c[3];
    if (n1[0]*mx+n1[1]*my+n1[2]*mz < 0) { n1 = [-n1[0], -n1[1], -n1[2]]; n2 = [-n2[0], -n2[1], -n2[2]]; }
    push(va, vb, n1, n2, 1);
  }
  const out = {id, pos: new Float32Array(P), n1: new Float32Array(N1), n2: new Float32Array(N2), kind: new Float32Array(K), eidx: new Float32Array(EI)};
  self.postMessage(out, [out.pos.buffer, out.n1.buffer, out.n2.buffer, out.kind.buffer, out.eidx.buffer]);
};`;

const edgeMat = new THREE.ShaderMaterial({
  clipping: true, depthTest: true, uniforms: {tState: U.tState, uCol: {value: new THREE.Color(0)}},
  vertexShader: `#include <common>
#include <clipping_planes_pars_vertex>
attribute float _eidx; attribute vec3 n1; attribute vec3 n2; attribute float kind; uniform sampler2D tState;
void main(){
  vec4 wp = modelMatrix * vec4(position, 1.0); vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
  float eI = floor(_eidx + .5); vec4 stt = texelFetch(tState, ivec2(int(mod(eI, ${2048}.)), int(eI / ${2048}.)), 0); float fl = floor(stt.r * 255. + .5);
  bool hide = mod(fl, 2.) > .5 || mod(floor(fl / 8.), 2.) > .5;
  if (kind > .5) { vec3 v = cameraPosition - wp.xyz; vec3 a = mat3(modelMatrix) * n1, b = mat3(modelMatrix) * n2; if (dot(a, v) * dot(b, v) > 0.) hide = true; }
  if (hide) gl_Position = vec4(2., 2., 2., 1.);
#include <clipping_planes_vertex>
}`,
  fragmentShader: `#include <clipping_planes_pars_fragment>
uniform vec3 uCol;
void main(){
#include <clipping_planes_fragment>
  gl_FragColor = vec4(uCol, 1.);
}`});
edgeMat.polygonOffset = false;

let workers = [], jobs = new Map(), jid = 0;
function runEdge(mesh) {
  return new Promise(res => {
    let w = workers[0]; if (!w) { w = new Worker(URL.createObjectURL(new Blob([WORKER_SRC], {type: 'text/javascript'}))); w.onmessage = ev => { const j = jobs.get(ev.data.id); jobs.delete(ev.data.id); j && j(ev.data); }; workers.push(w); }
    const g = mesh.geometry, id = ++jid; jobs.set(id, res);
    const ei = g.attributes._eidx; const idx = g.index.array;
    w.postMessage({id, pos: g.attributes.position.array, index: idx, eidx: ei ? ei.array : new Float32Array(g.attributes.position.count), thr: H.thresholdDeg});
  });
}

function setupTwins() {
  const meshes = []; world.traverse(o => { if (o.isMesh && !o.userData.hlTwin) meshes.push(o); });
  H.meshes = meshes;
  for (const m of meshes) {
    m.material.polygonOffset = true; m.material.polygonOffsetFactor = 1; m.material.polygonOffsetUnits = 1;
    if (m.userData.twin) continue;
    const mat = window.__patch(new THREE.MeshStandardMaterial({color: m.material.color, roughness: .85, metalness: 0, side: THREE.DoubleSide, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1}));
    mat.userData.pt = {value: 1};
    const t = new THREE.Mesh(m.geometry, mat); t.userData.hlTwin = 1; t.userData.bi = m.userData.bi; t.frustumCulled = false; t.renderOrder = 12; t.visible = false; t.matrixAutoUpdate = false;
    t.customDepthMaterial = m.customDepthMaterial; t.castShadow = false;
    m.parent.add(t); m.userData.twin = t; H.twins.push(t);
  }
}

async function buildEdges() {
  const ver = ++H.version, grp = new THREE.Group(); grp.renderOrder = 11; grp.visible = false; world.add(grp); H.group = grp; window.__hlGroup = grp; H.edgeCount = 0;
  H.ready = false;
  for (const m of H.meshes) {
    if (ver !== H.version) return;
    const r = await runEdge(m); if (ver !== H.version) return;
    if (!r.pos.length) continue;
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(r.pos, 3)); g.setAttribute('_eidx', new THREE.BufferAttribute(r.eidx, 1));
    g.setAttribute('n1', new THREE.BufferAttribute(r.n1, 3)); g.setAttribute('n2', new THREE.BufferAttribute(r.n2, 3)); g.setAttribute('kind', new THREE.BufferAttribute(r.kind, 1));
    const l = new THREE.LineSegments(g, edgeMat); l.frustumCulled = false; l.renderOrder = 11; l.matrixAutoUpdate = false; m.updateWorldMatrix(true, false); l.matrix.copy(m.matrixWorld); l.userData.hlEdge = 1;
    grp.add(l); H.edgeCount += r.pos.length / 6; dirty();
  }
  H.ready = true; window.__hlReady = true; dirty();
}

// per element surface colour + opacity from the category table (and element overrides in H.el)
H.applyOverrides = function () {
  if (!S.meta || !S.ovrData) return; const E = S.meta.elements, d = S.ovrData;
  for (let i = 0; i < S.N; i++) {
    const c = H.cat[E[i][2]] || {}, o = (H.el && H.el[i]) || {}; const col = o.c || c.c || [255, 255, 255], a = o.a ?? c.a ?? 1;
    d[4*i] = col[0]; d[4*i+1] = col[1]; d[4*i+2] = col[2]; d[4*i+3] = Math.round(a * 255);
  }
  S.ovrTex.needsUpdate = true; dirty();
};
H.setCat = function (cat, o) { H.cat[cat] = o; H.applyOverrides(); };

let saved = null;
H.setStyle = function (st) {
  if (!STYLES[st]) st = 'realistic'; const prev = H.style; H.style = st; try { localStorage.setItem('rvtStyle', st); } catch (e) {}
  const hl = st === 'hidden' || st === 'wire';
  if (st !== 'realistic' && U.uStyle.value === 0 && !saved) saved = {bg: scene.background, tex: U.uTex.value};
  U.uStyle.value = STYLE_ID[st];
  if (hl && H.meshes === undefined) { setupTwins(); buildEdges(); }
  if (hl) { if ($('#bShadow')?.classList.contains('on')) { H.shadowWas = true; $('#bShadow').click(); } scene.background = new THREE.Color(0xffffff); }
  else {
    if (H.shadowWas && !$('#bShadow').classList.contains('on')) $('#bShadow').click(); H.shadowWas = false;
    if (saved) { scene.background = saved.bg; if (st === 'realistic') U.uTex.value = saved.tex; }
  }
  if (st === 'shaded' || st === 'consistent') U.uTex.value = 0; else if (st === 'realistic' && saved) U.uTex.value = saved.tex;
  $('#bTex')?.classList.toggle('on', !!U.uTex.value);
  if (st === 'realistic') saved = null;
  edgeMat.depthTest = st !== 'wire';
  if (H.group) H.group.visible = hl; for (const t of H.twins) t.visible = st === 'hidden';
  for (const m of H.meshes || []) { m.material.polygonOffset = st === 'hidden'; }
  if (H.meshes) for (const m of H.meshes) { m.material.needsUpdate = true; }
  const sel = $('#styleSel'); if (sel) sel.value = st; dirty();
};

function onLoaded() {
  H.twins = []; H.group = null; H.meshes = undefined; H.ready = false; window.__hlReady = false; H.version++;
  H.applyOverrides();
  saved = null; H.setStyle(H.style);
}

const sel = document.createElement('select'); sel.id = 'styleSel'; sel.title = 'Visual style';
sel.innerHTML = Object.entries(STYLES).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
$('#bShadow').before(sel); sel.onchange = () => H.setStyle(sel.value);
window.addEventListener('rvt-model-loaded', onLoaded);
let st0 = new URLSearchParams(location.search).get('style'); try { st0 = st0 || localStorage.getItem('rvtStyle'); } catch (e) {}
H.style = STYLES[st0] ? st0 : 'realistic'; sel.value = H.style;
if (S.meta && window.__loaded) onLoaded();
