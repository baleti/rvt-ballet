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
H.defCat = {'Floors': {a: 0.85}};   // used when no view graphics are open
H.cat = Object.assign({}, H.defCat);

const WORKER_SRC = `
class G { constructor(T, n) { this.T = T; this.a = new T(n); this.n = 0; } push(...v) { if (this.n + v.length > this.a.length) { const b = new this.T(this.a.length * 2 + v.length); b.set(this.a); this.a = b; } for (let i = 0; i < v.length; i++) this.a[this.n++] = v[i]; } get length() { return this.n; } out() { return this.a.slice(0, this.n); } }
self.onmessage = ev => {
  const {pos, index, eidx, thr, id} = ev.data; const n = pos.length / 3, nt = index.length / 3;
  const wid = new Int32Array(n), qx = new Int32Array(n), qy = new Int32Array(n), qz = new Int32Array(n);      // weld vertices that coincide within 1 mm (open addressing table)
  let size = 1024; while (size < n * 2) size <<= 1; const mask = size - 1, tab = new Int32Array(size).fill(-1);
  for (let i = 0; i < n; i++) {
    const x = qx[i] = Math.round(pos[3*i]*1000), y = qy[i] = Math.round(pos[3*i+1]*1000), z = qz[i] = Math.round(pos[3*i+2]*1000);
    let h = (Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) & mask, f = -1;
    for (;;) { const r = tab[h]; if (r < 0) { tab[h] = i; f = i; break; } if (qx[r] === x && qy[r] === y && qz[r] === z) { f = r; break; } h = (h + 1) & mask; }
    wid[i] = f;
  }
  const nrm = new Float32Array(nt * 3), cen = new Map();
  for (let t = 0; t < nt; t++) {
    const a = index[3*t], b = index[3*t+1], c = index[3*t+2];
    const ux = pos[3*b]-pos[3*a], uy = pos[3*b+1]-pos[3*a+1], uz = pos[3*b+2]-pos[3*a+2], vx = pos[3*c]-pos[3*a], vy = pos[3*c+1]-pos[3*a+1], vz = pos[3*c+2]-pos[3*a+2];
    let nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx; const l = Math.hypot(nx, ny, nz) || 1; nrm[3*t] = nx/l; nrm[3*t+1] = ny/l; nrm[3*t+2] = nz/l;
    const e = eidx[a]; let s = cen.get(e); if (!s) { s = [0,0,0,0]; cen.set(e, s); }
    s[0] += (pos[3*a]+pos[3*b]+pos[3*c])/3; s[1] += (pos[3*a+1]+pos[3*b+1]+pos[3*c+1])/3; s[2] += (pos[3*a+2]+pos[3*b+2]+pos[3*c+2])/3; s[3]++;
  }
  const ea = new G(Int32Array, 1 << 16), eb = new G(Int32Array, 1 << 16), t1 = new G(Int32Array, 1 << 16), t2 = new G(Int32Array, 1 << 16), cnt = new G(Int32Array, 1 << 16), elo = new G(Int32Array, 1 << 16), ehi = new G(Int32Array, 1 << 16);   // edge table, open addressing on the welded vertex pair
  let es = 1024; while (es < nt * 4) es <<= 1; const emask = es - 1, etab = new Int32Array(es).fill(-1);
  for (let t = 0; t < nt; t++) {
    for (let k = 0; k < 3; k++) {
      const va = index[3*t+k], vb = index[3*t+(k+1)%3]; const a = wid[va], b = wid[vb]; if (a === b) continue;
      const lo = a < b ? a : b, hi = a < b ? b : a; let h = (Math.imul(lo, 73856093) ^ Math.imul(hi, 19349663)) & emask, s = -1;
      for (;;) { const r = etab[h]; if (r < 0) break; if (elo.a[r] === lo && ehi.a[r] === hi) { s = r; break; } h = (h + 1) & emask; }
      if (s < 0) { etab[h] = ea.length; elo.push(lo); ehi.push(hi); ea.push(va); eb.push(vb); t1.push(t); t2.push(-1); cnt.push(1); }
      else { cnt.a[s]++; if (t2.a[s] < 0) t2.a[s] = t; }
    }
  }
  const cosT = Math.cos(thr * Math.PI / 180), cosS = Math.cos(2 * Math.PI / 180);
  const P = new G(Float32Array, 1 << 16), N1 = new G(Float32Array, 1 << 16), N2 = new G(Float32Array, 1 << 16), K = new G(Float32Array, 1 << 14), EI = new G(Float32Array, 1 << 14);
  const push = (va, vb, n1, n2, kind) => {
    P.push(pos[3*va], pos[3*va+1], pos[3*va+2], pos[3*vb], pos[3*vb+1], pos[3*vb+2]);
    for (let q = 0; q < 2; q++) { N1.push(n1[0], n1[1], n1[2]); N2.push(n2[0], n2[1], n2[2]); K.push(kind); EI.push(eidx[va]); }
  };
  const Z = [0, 0, 0];
  for (let s = 0; s < ea.length; s++) {
    const va = ea.a[s], vb = eb.a[s], A = t1.a[s], B = t2.a[s];
    if (cnt.a[s] !== 2) { push(va, vb, Z, Z, 0); continue; }
    if (eidx[index[3*A]] !== eidx[index[3*B]]) { push(va, vb, Z, Z, 0); continue; }
    let n1 = [nrm[3*A], nrm[3*A+1], nrm[3*A+2]], n2 = [nrm[3*B], nrm[3*B+1], nrm[3*B+2]]; let d = n1[0]*n2[0]+n1[1]*n2[1]+n1[2]*n2[2];
    if (d < 0) { n2 = [-n2[0], -n2[1], -n2[2]]; d = -d; }
    if (d > cosS && d >= cosT) continue;
    // smooth edge: silhouette candidate (kind 1); sharp edge: kind 2 = always drawn, except on 'soft' elements (foliage, terrain) that only get their silhouette. Normals oriented away from the element centre
    const c = cen.get(eidx[va]); const mx = (pos[3*va]+pos[3*vb])/2 - c[0]/c[3], my = (pos[3*va+1]+pos[3*vb+1])/2 - c[1]/c[3], mz = (pos[3*va+2]+pos[3*vb+2])/2 - c[2]/c[3];
    if (n1[0]*mx+n1[1]*my+n1[2]*mz < 0) { n1 = [-n1[0], -n1[1], -n1[2]]; n2 = [-n2[0], -n2[1], -n2[2]]; }
    push(va, vb, n1, n2, d < cosT ? 2 : 1);
  }
  const out = {id, pos: P.out(), n1: N1.out(), n2: N2.out(), kind: K.out(), eidx: EI.out()};
  self.postMessage(out, [out.pos.buffer, out.n1.buffer, out.n2.buffer, out.kind.buffer, out.eidx.buffer]);
};`;

const TW = 2048, uPx = {value: new THREE.Vector2(.001, .001)}, tLn = {value: null};
// edge material; k = 0 base line, k = 1, 2 extra passes offset by about a pixel that thicken the lines of elements whose line weight needs 2 / 3 px
function mkEdgeMat(k) {
  const m = new THREE.ShaderMaterial({
  clipping: true, depthTest: true, uniforms: {tState: U.tState, tLn, uPx, uK: {value: k}},
  vertexShader: `#include <common>
#include <clipping_planes_pars_vertex>
attribute float _eidx; attribute vec3 n1; attribute vec3 n2; attribute float kind; uniform sampler2D tState; uniform sampler2D tLn; uniform vec2 uPx; uniform float uK; varying vec3 vC;
void main(){
  vec4 wp = modelMatrix * vec4(position, 1.0); vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
  float eI = floor(_eidx + .5); ivec2 ix = ivec2(int(mod(eI, ${TW}.)), int(eI / ${TW}.)); vec4 stt = texelFetch(tState, ix, 0); float fl = floor(stt.r * 255. + .5);
  vec4 ln = texelFetch(tLn, ix, 0); vC = ln.rgb; float la = ln.a * 255.; float wpx = floor(la / 50. + .5); bool soft = mod(la + 25., 50.) >= 30.;
  bool hide = mod(fl, 2.) > .5 || mod(floor(fl / 8.), 2.) > .5 || (uK > .5 && wpx < uK + .5);
  if (kind > .5 && (kind < 1.5 || soft)) { vec3 v = cameraPosition - wp.xyz; vec3 a = mat3(modelMatrix) * n1, b = mat3(modelMatrix) * n2; if (dot(a, v) * dot(b, v) > 0.) hide = true; }
  if (uK > .5) gl_Position.xy += (uK < 1.5 ? vec2(.7, .7) : vec2(-.7, .7)) * uPx * gl_Position.w;
  if (hide) gl_Position = vec4(2., 2., 2., 1.);
#include <clipping_planes_vertex>
}`,
  fragmentShader: `#include <clipping_planes_pars_fragment>
varying vec3 vC;
void main(){
#include <clipping_planes_fragment>
  gl_FragColor = vec4(vC, 1.);
}`});
  return m;
}
const edgeMats = [mkEdgeMat(0), mkEdgeMat(1), mkEdgeMat(2)];
const edgeMat = edgeMats[0];

const _v2 = new THREE.Vector2();
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
    m.material.polygonOffset = true; m.material.polygonOffsetFactor = 2; m.material.polygonOffsetUnits = 4;
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
  H.ready = false; const t0 = performance.now();
  for (const m of H.meshes) {
    if (ver !== H.version) return;
    const r = await runEdge(m); if (ver !== H.version) return;
    if (!r.pos.length) continue;
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(r.pos, 3)); g.setAttribute('_eidx', new THREE.BufferAttribute(r.eidx, 1));
    g.setAttribute('n1', new THREE.BufferAttribute(r.n1, 3)); g.setAttribute('n2', new THREE.BufferAttribute(r.n2, 3)); g.setAttribute('kind', new THREE.BufferAttribute(r.kind, 1));
    m.updateWorldMatrix(true, false);
    for (const em of edgeMats) { const l = new THREE.LineSegments(g, em); l.frustumCulled = false; l.renderOrder = 11; l.matrixAutoUpdate = false; l.matrix.copy(m.matrixWorld); l.userData.hlEdge = 1; grp.add(l);
      if (em === edgeMat) l.onBeforeRender = r => { r.getDrawingBufferSize(_v2); uPx.value.set(2 / _v2.x, 2 / _v2.y); }; }
 H.edgeCount += r.pos.length / 6; dirty();
  }
  H.edgeMs = Math.round(performance.now() - t0); H.ready = true; window.__hlReady = true; dirty();
}

// per element surface colour + opacity from the category table (and element overrides in H.el)
H.applyOverrides = function () {
  if (!S.meta || !S.ovrData) return; const E = S.meta.elements, d = S.ovrData;
  for (let i = 0; i < S.N; i++) {
    const c = H.cat[E[i][2]] || {}, o = (H.el && H.el[i]) || {}; let col = o.c || c.c || [255, 255, 255]; const a = o.a ?? c.a ?? 1; if (o.ht) col = col.map(x => (x + 255) >> 1);
    d[4*i] = col[0]; d[4*i+1] = col[1]; d[4*i+2] = col[2]; d[4*i+3] = Math.round(a * 255);
  }
  S.ovrTex.needsUpdate = true; H.applyLines(); dirty();
};
const SOFT = new Set(['Planting', 'Entourage', 'Topography']);
H.applyLines = function () {
  if (!S.meta) return; const E = S.meta.elements, N = S.N, h = Math.max(1, Math.ceil(N / TW));
  if (!H.lnData || H.lnData.length !== TW * h * 4) { H.lnData = new Uint8Array(TW * h * 4); H.lnTex = new THREE.DataTexture(H.lnData, TW, h, THREE.RGBAFormat, THREE.UnsignedByteType); H.lnTex.minFilter = H.lnTex.magFilter = THREE.NearestFilter; tLn.value = H.lnTex; }
  const d = H.lnData;
  for (let i = 0; i < N; i++) { const o = (H.el && H.el[i]) || {}; let c = o.lc || [0, 0, 0]; const w = o.lw || 1; if (o.ht) c = c.map(x => (x + 255) >> 1); d[4*i] = c[0]; d[4*i+1] = c[1]; d[4*i+2] = c[2]; d[4*i+3] = w * 50 + (SOFT.has(E[i][2]) ? 10 : 0); }
  H.lnTex.needsUpdate = true;
};
H.setCat = function (cat, o) { H.cat[cat] = o; H.applyOverrides(); };

// level outlines and grids in the Revit look: thin dashed lines (levels black, grids magenta), no tinted planes
function restyleOverlays(on) {
  if (!S.lvlGroup) return;
  if (!H.ovl) {
    H.ovl = new THREE.Group(); H.ovl.userData.hl = 1; const mk = (c, d, g) => new THREE.LineDashedMaterial({color: c, dashSize: d, gapSize: g, transparent: true, opacity: .9});
    const lm = mk(0x222222, 3.2, 1.2), gm = mk(0xd020d0, 2.4, 1);
    for (const o of S.lvlGroup.children) if (o.isLineLoop) { const pts = []; const a = o.geometry.attributes.position; for (let i = 0; i <= a.count; i++) pts.push(new THREE.Vector3().fromBufferAttribute(a, i % a.count)); const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lm); l.position.copy(o.position); l.computeLineDistances(); l.userData.src = o; H.ovl.add(l); }
    for (const o of S.gridGroup.children) if (o.isLine) { const l = new THREE.Line(o.geometry, gm); l.computeLineDistances(); l.userData.src = o; H.ovl.add(l); }
    S.lvlGroup.add(H.ovl); H.ovlSrc = [...S.lvlGroup.children.filter(o => o.isLineLoop), ...S.gridGroup.children.filter(o => o.isLine)];
  }
  H.ovl.visible = on; for (const o of H.ovlSrc) o.visible = !on;
  if (S.lvlGroup.children[0]?.isMesh) S.lvlGroup.children.forEach(o => { if (o.isMesh) o.visible = !on; });
  document.body.classList.toggle('hlstyle', on);
}

// resolved view graphics (view template + filters + category overrides + transparency) from the server for the open view (rvtviewer/vg3d.py)
H.el = null; H.viewId = null; let viewHidden = new Set();
H.loadView = async function (v) {
  const vid = v && v.id; if (vid === H.viewId) return; H.viewId = vid;
  for (const i of viewHidden) S.hidden[i] = 0; viewHidden.clear(); H.el = null; H.cat = Object.assign({}, H.defCat);
  if (vid != null) {
    try {
      const r = await fetch(`/api/m/${S.mid}/vg3d/${vid}`); if (!r.ok) throw new Error(r.status); const d = await r.json(); if (H.viewId !== vid) return;
      const E = S.meta.elements, idx = new Map(); E.forEach((e, i) => idx.set(String(e[0]), i)); H.el = {}; H.cat = {};
      for (const [k, a] of Object.entries(d.els)) { const i = idx.get(k); if (i === undefined) continue;
        H.el[i] = {c: [a[0], a[1], a[2]], a: a[3], lc: [a[4], a[5], a[6]], lw: a[7] < .8 ? 1 : a[7] < 1.5 ? 2 : 3, ht: a[8]}; }
      for (const id of d.hidden) { const i = idx.get(String(id)); if (i !== undefined && !S.hidden[i]) { S.hidden[i] = 1; viewHidden.add(i); } }
    } catch (e) { console.warn('view graphics', e); }
  }
  window.__refreshState && window.__refreshState(); H.applyOverrides(); H.viewReady = true;
};
let lastView; setInterval(() => { if (S.openView !== lastView) { lastView = S.openView; H.viewReady = false; H.loadView(S.openView); } }, 400);

let saved = null;
H.setStyle = function (st, user) {
  if (user) H.userChose = true;
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
  for (const em of edgeMats) em.depthTest = st !== 'wire';
  if (H.group) H.group.visible = hl; for (const t of H.twins) t.visible = st === 'hidden';
  for (const m of H.meshes || []) { m.material.polygonOffset = st === 'hidden'; }
  if (H.meshes) for (const m of H.meshes) { m.material.needsUpdate = true; }
  restyleOverlays(hl);
  const sel = $('#styleSel'); if (sel) sel.value = st; window.dispatchEvent(new CustomEvent('vstylechange', {detail: vstyle.get()})); dirty();
};

// window.vstyle contract (docs/VSTYLE-API.md, c3-vctl selector #vsSel): ids hiddenline/shaded/consistent/realistic/wireframe map to this module's styles
const VMAP = {hiddenline: 'hidden', shaded: 'shaded', consistent: 'consistent', realistic: 'realistic', wireframe: 'wire'}, VBACK = Object.fromEntries(Object.entries(VMAP).map(([a, b]) => [b, a]));
let vopts = {edgeAngle: 30, silhouettes: true, hiddenLines: 'faint', lineWeight: 1, transparency: true, patterns: true, halftone: true, faceColor: '#ffffff'};
const vstyle = {
  list: () => [['hiddenline', 'Hidden line'], ['shaded', 'Shaded'], ['consistent', 'Consistent colors'], ['realistic', 'Realistic'], ['wireframe', 'Wireframe']].map(([id, label]) => ({id, label})),
  get: () => ({id: VBACK[H.style], opts: {...vopts}}),
  set(id, opts) { if (!VMAP[id]) throw new Error('unknown style ' + id); vopts = {...vopts, ...(opts || {})}; H.setStyle(VMAP[id], true); },
};
Object.defineProperty(vstyle, 'defaultId', {value: 'hiddenline'}); window.vstyle = vstyle;
function onLoaded() {
  H.ovl = null; H.twins = []; H.group = null; H.meshes = undefined; H.ready = false; window.__hlReady = false; H.version++;
  H.applyOverrides();
  H.viewId = null; H.el = null; lastView = undefined; saved = null;
  if (!H.userChose && H.style === 'hidden' && S.tris > 12e6) H.style = 'realistic';      // very large models open in the cheap style until the user asks for hidden line
  H.setStyle(H.style);
}

const sel = document.createElement('select'); sel.id = 'styleSel'; sel.title = 'Visual style';
sel.innerHTML = Object.entries(STYLES).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
$('#bShadow').before(sel); sel.onchange = () => H.setStyle(sel.value, true);
sel.style.display = 'none';      // c3-vctl's #vsSel (window.vstyle) is the visible selector
window.addEventListener('rvt-model-loaded', onLoaded);
let st0 = new URLSearchParams(location.search).get('style'); try { st0 = st0 || localStorage.getItem('rvtStyle'); } catch (e) {}
H.userChose = !!STYLES[st0]; H.style = STYLES[st0] ? st0 : 'hidden'; sel.value = H.style;      // Revit's default 3D look is hidden line
if (S.meta && window.__loaded) onLoaded();
