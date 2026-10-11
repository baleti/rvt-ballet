import * as THREE from 'three';
import {OrbitControls} from 'three/controls/OrbitControls.js';
import {GLTFLoader} from 'three/loaders/GLTFLoader.js';

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const TW = 2048;                       // state texture width
const FID = ['solid', 'mesh', 'matched', 'param', 'approx', 'bbox', 'line', 'none'];
const FIDCOL = {solid: '#2e9e5b', mesh: '#1f8f6f', matched: '#6cc24a', param: '#3a7bd5', approx: '#1fa7b0', bbox: '#d08a2a', line: '#8a5fd0', none: '#666'};
const S = {meta: null, mid: null, N: 0, sel: new Set(), hidden: new Uint8Array(0), catHidden: new Set(), lvlHidden: new Set(), isolate: null, showNoGeo: false,
           byCat: new Map(), catOf: [], tab: 'tree', fidMode: 0, measure: false, mpts: [], hoverI: -1, hits: []};
window.S = S;

// ------------------------------------------------------------------ three setup
const canvas = $('#gl');
const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
const isDark = matchMedia('(prefers-color-scheme: dark)').matches;
scene.background = new THREE.Color(isDark ? 0x1a1e25 : 0xdfe4ea);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
camera.position.set(30, 25, 30);
const controls = new OrbitControls(camera, canvas);
function setNav(mode) {
  const M = THREE.MOUSE;
  if (mode === 'revit') { controls.mouseButtons = {LEFT: -1, MIDDLE: M.PAN, RIGHT: M.ROTATE}; controls.zoomToCursor = true; }      // Revit: middle-drag pan, Shift+middle-drag orbit, wheel zooms at the cursor
  else { controls.mouseButtons = {LEFT: M.ROTATE, MIDDLE: M.DOLLY, RIGHT: M.PAN}; controls.zoomToCursor = false; }
  try { localStorage.setItem('rvtNav', mode); } catch (e) {}
  const sel = document.getElementById('navSel'); if (sel) sel.value = mode;
}
controls.enableDamping = true; controls.dampingFactor = 0.12; controls.screenSpacePanning = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0x556070, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); scene.add(sun, sun.target);
const world = new THREE.Group(); scene.add(world);
const overlay = new THREE.Group(); scene.add(overlay);
let selBoxDummy;
let stateTex, stateData;
const U = {tState: {value: null}, uMode: {value: 0}};

function patch(mat) {
  mat.flatShading = true;
  mat.onBeforeCompile = sh => {
    sh.uniforms.tState = U.tState; sh.uniforms.uMode = U.uMode;
    sh.vertexShader = 'attribute float _eidx; varying float vE;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvE=_eidx;');
    sh.fragmentShader = `varying float vE; uniform sampler2D tState; uniform float uMode;
vec4 fidCol(float f){ if(f<.5) return vec4(.18,.62,.36,1.); if(f<1.5) return vec4(.12,.56,.44,1.); if(f<2.5) return vec4(.42,.76,.29,1.); if(f<3.5) return vec4(.23,.48,.84,1.); if(f<4.5) return vec4(.12,.65,.69,1.); if(f<5.5) return vec4(.82,.54,.16,1.); if(f<6.5) return vec4(.54,.37,.82,1.); return vec4(.5,.5,.5,1.);}
` + sh.fragmentShader
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
float eI = floor(vE+.5); vec4 stt = texelFetch(tState, ivec2(int(mod(eI,${TW}.)), int(eI/${TW}.)), 0);
float fl = floor(stt.r*255.+.5); if(mod(fl,2.)>.5) discard;`)
      .replace('#include <color_fragment>', `#include <color_fragment>
if(uMode>1.5){ float dv=floor(stt.b*255.+.5); diffuseColor.rgb = dv<.5?vec3(.55):dv<1.5?vec3(.18,.7,.3):dv<2.5?vec3(.9,.8,.2):dv<3.5?vec3(.95,.55,.15):vec3(.9,.2,.2); } else if(uMode>.5) diffuseColor.rgb = fidCol(floor(stt.g*255.+.5)).rgb;
if(mod(floor(fl/8.),2.)>.5){ if(mod(floor(gl_FragCoord.x)+2.*floor(gl_FragCoord.y),5.)>.5) discard; diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.6), .5); }
if(mod(floor(fl/2.),2.)>.5) diffuseColor.rgb = mix(diffuseColor.rgb, vec3(1.,.69,.1), .75);
else if(mod(floor(fl/4.),2.)>.5) diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.3,.7,1.), .5);`);
  };
  mat.customProgramCacheKey = () => 'rvtpatch1';
  return mat;
}

const pickMat = new THREE.ShaderMaterial({
  clipping: true, side: THREE.DoubleSide, uniforms: {tState: U.tState, uPass: {value: 0}},
  vertexShader: `#include <common>
#include <clipping_planes_pars_vertex>
attribute float _eidx; varying float vE;
void main(){ vE=_eidx; vec4 mvPosition = modelViewMatrix*vec4(position,1.0); gl_Position=projectionMatrix*mvPosition;
#include <clipping_planes_vertex>
}`,
  fragmentShader: `#include <clipping_planes_pars_fragment>
varying float vE; uniform sampler2D tState; uniform int uPass;
void main(){
#include <clipping_planes_fragment>
float e=floor(vE+.5); vec4 st=texelFetch(tState, ivec2(int(mod(e,${TW}.)), int(e/${TW}.)), 0);
float fl=floor(st.r*255.+.5); if(mod(fl,2.)>.5) discard;
if(uPass==0){ float id=e+1.; gl_FragColor=vec4(mod(id,256.)/255., mod(floor(id/256.),256.)/255., floor(id/65536.)/255., 1.); }
else { float d=floor(gl_FragCoord.z*16777215.); gl_FragColor=vec4(mod(d,256.)/255., mod(floor(d/256.),256.)/255., floor(d/65536.)/255., 1.); }
}`});
const pickRT = new THREE.WebGLRenderTarget(1, 1, {minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: true});

function pickAt(cx, cy) {
  const r = canvas.getBoundingClientRect(); const W = r.width, H = r.height, x = cx - r.left, y = cy - r.top;
  if (x < 0 || y < 0 || x >= W || y >= H) return null;
  const buf = new Uint8Array(4), out = {};
  world.visible = true; overlay.visible = false;
  const prevBg = scene.background; scene.background = null;
  scene.overrideMaterial = pickMat;
  renderer.setClearColor(0x000000, 0); renderer.setRenderTarget(pickRT);
  camera.setViewOffset(W, H, Math.floor(x), Math.floor(y), 1, 1);
  for (const pass of [0, 1]) {
    pickMat.uniforms.uPass.value = pass; renderer.clear(); renderer.render(scene, camera);
    renderer.readRenderTargetPixels(pickRT, 0, 0, 1, 1, buf);
    if (pass === 0) out.id = buf[0] + buf[1] * 256 + buf[2] * 65536 - 1; else out.d = (buf[0] + buf[1] * 256 + buf[2] * 65536) / 16777215;
  }
  camera.clearViewOffset(); renderer.setRenderTarget(null); scene.overrideMaterial = null; scene.background = prevBg; overlay.visible = true;
  if (out.id < 0 || out.id >= S.N) return null;
  const ndc = new THREE.Vector3((x + .5) / W * 2 - 1, -((y + .5) / H) * 2 + 1, out.d * 2 - 1);
  camera.updateMatrixWorld(); camera.updateProjectionMatrix();
  out.p = ndc.unproject(camera); return out;
}

// ------------------------------------------------------------------ state texture / visibility
function initState(N) {
  const h = Math.max(1, Math.ceil(N / TW)); stateData = new Uint8Array(TW * h * 4);
  stateTex = new THREE.DataTexture(stateData, TW, h, THREE.RGBAFormat, THREE.UnsignedByteType);
  stateTex.minFilter = stateTex.magFilter = THREE.NearestFilter; stateTex.needsUpdate = true; U.tState.value = stateTex;
}
function refreshState() {
  const E = S.meta.elements, N = S.N;
  for (let i = 0; i < N; i++) {
    const el = E[i]; let f = 0;
    const cat = el[2];
    if (S.hidden[i] || (cat && S.catHidden.has(cat)) || (S.lvlHidden.size && S.lvlHidden.has(el[5] || '')) ) f |= 1;
    else if (S.isolate && !S.isolate.has(i)) f |= S.isoGhost ? 8 : 1;
    if (S.sel.has(i)) f |= 2; else if (i === S.hoverI) f |= 4;
    stateData[i * 4] = f; stateData[i * 4 + 1] = FID.indexOf(el[6]); stateData[i * 4 + 2] = S.devCode ? S.devCode[i] : 0;
  }
  stateTex.needsUpdate = true; dirty = true;
}
let dirty = true;

// ------------------------------------------------------------------ load
const sleep = ms => new Promise(r => setTimeout(r, ms));
function showProgress(pr, floating) {
  const el = $('#progress'); const st = pr.stages || []; const idx = Math.max(0, st.indexOf(pr.stage));
  const overall = pr.stage === 'done' ? 1 : (idx + (pr.pct || 0)) / Math.max(1, st.length - 1);
  const labels = {reading: 'Reading file (decoding records)', tables: 'Building element tables', preview: 'Box preview', geometry: 'Building geometry', packing: 'Packing meshes', done: 'Done'};
  el.hidden = false; el.className = floating ? 'float' : '';
  el.innerHTML = (floating ? '' : '<h3>Opening model</h3>') + `<div class="pbar"><div style="width:${(overall * 100).toFixed(0)}%"></div></div>` +
    (floating ? `<span>Refining geometry: ${esc(labels[pr.stage] || pr.stage)} ${Math.round(overall * 100)}%</span>` :
     st.filter(x => x !== 'done').map((x, i) => `<div class="stg ${i < idx ? 'ok' : i === idx ? 'cur' : ''}">${i < idx ? '\u2713' : i === idx ? '\u25b6' : '\u00b7'} ${labels[x] || x}</div>`).join('') +
     `<div class="dim">${esc(pr.msg || '')}<br>${(pr.elapsed || 0).toFixed(0)} s elapsed. The first open of a file decodes it with the reader (minutes for big files); later opens are instant.</div>`);
}
async function loadModel(mid, opts = {}) {
  S.mid = mid; { const cur = location.hash.slice(1); if (!(cur === mid || cur.startsWith(mid + '?'))) { S.hashRestored = true; history.replaceState(null, '', '#' + mid); } } $('#status').textContent = 'loading...';
  const t0 = performance.now(); let meta = null;
  while (!meta) {                              // the conversion may still be running: show its stages until the first usable model (box preview) exists
    const r = await fetch(`/m/${mid}/meta.json`);
    if (r.ok) { meta = await r.json(); break; }
    const pr = await (await fetch(`/api/m/${mid}/progress`)).json(); showProgress(pr, false);
    if (pr.stage === 'error') { $('#status').textContent = pr.msg; return; }
    await sleep(700);
  }
  $('#progress').hidden = true;
  S.meta = meta; const keepSel = opts.keepCamera ? [...S.sel] : [];
  const E = S.meta.elements; S.N = E.length; S.hidden = new Uint8Array(S.N); S.sel = new Set(keepSel); S.isolate = null;
  S.byCat = new Map();
  E.forEach((el, i) => { const c = el[2] || '(no category)'; if (!S.byCat.has(c)) S.byCat.set(c, []); S.byCat.get(c).push(i); });
  S.hay = E.map(el => [el[0], el[1], el[2], el[3], el[4], el[5], el[8]].join(' ').toLowerCase());
  S.catHidden = opts.keepCamera ? S.catHidden : new Set(S.meta.defaultHidden || []);
  initState(S.N); refreshState();
  $('#status').textContent = 'loading geometry...';
  world.clear(); overlay.clear(); S.bbCache = null;
  const gltf = await new GLTFLoader().loadAsync(`/m/${mid}/${(S.meta.phase || 'done') === 'done' ? 'model' : 'preview'}.glb`);
  let tris = 0;
  gltf.scene.traverse(o => {
    if (!o.isMesh && !o.isLine && !o.isLineSegments) return;
    const old = o.material;
    if (o.isMesh) {
      o.material = patch(new THREE.MeshStandardMaterial({color: old.color, roughness: .85, metalness: 0, side: THREE.DoubleSide, transparent: old.transparent, opacity: old.opacity, depthWrite: !old.transparent}));
      tris += o.geometry.index.count / 3;
    } else {
      const lm = new THREE.LineBasicMaterial({color: old.color}); lm.onBeforeCompile = patch(new THREE.MeshStandardMaterial()).onBeforeCompile; lm.customProgramCacheKey = () => 'rvtline1'; o.material = lm;
    }
    o.frustumCulled = false; o.userData.bi = o.userData.batch ?? o.parent?.userData?.batch ?? 0;
  });
  world.add(gltf.scene); buildElRanges();
  buildOverlays(); if (!opts.keepCamera) fitAll(); buildTabs(); setupLegend(); refreshState();
  $('#status').textContent = `${S.N.toLocaleString()} elements, ${tris.toLocaleString()} triangles - ${((performance.now() - t0) / 1000).toFixed(1)}s` + ((S.meta.phase || 'done') === 'done' ? '' : ' (box preview)');
  if (!opts.keepCamera && !S.hashRestored) { S.hashRestored = true; restoreHash(); }
  dirty = true; window.__loaded = true;
  if ((S.meta.phase || 'done') !== 'done') refineLoop(mid);
}
async function refineLoop(mid) {
  // geometry is still being built: poll, then swap the preview for the full model without moving the camera
  for (;;) {
    await sleep(1000); if (S.mid !== mid) return;
    let pr; try { pr = await (await fetch(`/api/m/${mid}/progress`)).json(); } catch (e) { continue; }
    if (pr.stage === 'done') break; if (pr.stage === 'error') { $('#progress').hidden = true; return; }
    showProgress(pr, true);
  }
  $('#progress').hidden = true; window.__loaded = false; await loadModel(mid, {keepCamera: true});
}

function modelBox() { const b = S.meta.bbox; return new THREE.Box3(new THREE.Vector3(b[0][0], b[0][2], -b[1][1]), new THREE.Vector3(b[1][0], b[1][2], -b[0][1])); }
const toV = p => new THREE.Vector3(p[0], p[2], -p[1]);    // meta uses revit-axes metres (x,y,z up) -> three y-up
function fitBox(box, dir) {
  const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3()), r = Math.max(s.length() / 2, 0.5);
  const d = (dir || new THREE.Vector3(1, .8, 1)).clone().normalize();
  const dist = r / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.1;
  controls.target.copy(c); camera.position.copy(c).addScaledVector(d, dist);
  camera.near = Math.max(dist / 2000, 0.02); camera.far = dist * 20 + 2000; camera.updateProjectionMatrix(); controls.update(); dirty = true;
}
function fitAll(dir) { fitBox(modelBox(), dir); }
function elBox(i) { const bb = S.bb?.[i]; return bb; }

// ------------------------------------------------------------------ overlays: levels, grids, rooms
const lbls = []; let showLvl = true, showGrid = true;
function buildOverlays() {
  lbls.length = 0; $('#labels').innerHTML = '';
  const mb = modelBox(), sz = mb.getSize(new THREE.Vector3()), c = mb.getCenter(new THREE.Vector3());
  const lvlMat = new THREE.MeshBasicMaterial({color: 0x2d6cdf, transparent: true, opacity: .02, side: THREE.DoubleSide, depthWrite: false});
  const lineMat = new THREE.LineBasicMaterial({color: 0x2d6cdf, transparent: true, opacity: .22});
  S.lvlGroup = new THREE.Group(); S.gridGroup = new THREE.Group(); overlay.add(S.lvlGroup, S.gridGroup);
  for (const l of S.meta.levels) {
    const w = sz.x * 1.1 + 4, d = sz.z * 1.1 + 4;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), lvlMat); m.rotation.x = -Math.PI / 2; m.position.set(c.x, l.elev, c.z); S.lvlGroup.add(m);
    const e = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].map(p => new THREE.Vector3(p[0], 0, p[1]))), lineMat);
    e.position.set(c.x, l.elev, c.z); S.lvlGroup.add(e);
    addLabel(`${l.name}  ${l.elev.toFixed(2)} m`, new THREE.Vector3(c.x - w / 2, l.elev, c.z + d / 2), 'lvl', S.lvlGroup);
  }
  const gm = new THREE.LineBasicMaterial({color: 0x1f8f4f});
  for (const g of S.meta.grids) {
    const a = toV(g.pts[0]), b = toV(g.pts[1]); a.y = b.y = mb.min.y;
    S.gridGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), gm));
    addLabel(g.name, b, 'grid', S.gridGroup);
  }
  S.roomGroup = new THREE.Group(); overlay.add(S.roomGroup); S.roomGroup.visible = false;
  for (const r of S.meta.rooms || []) if (r.pt) addLabel(`${r.number} ${r.name}`.trim(), toV(r.pt), 'room', S.roomGroup);
}
function addLabel(text, pos, cls, group) {
  const d = document.createElement('div'); d.className = 'lbl ' + cls; d.textContent = text; $('#labels').appendChild(d); lbls.push({d, pos, group});
}
function updateLabels() {
  const r = canvas.getBoundingClientRect(), v = new THREE.Vector3();
  for (const l of lbls) {
    if (!l.group.visible || !l.group.parent) { l.d.style.display = 'none'; continue; }
    v.copy(l.pos).project(camera);
    if (v.z > 1 || v.z < -1 || Math.abs(v.x) > 1.05 || Math.abs(v.y) > 1.05) { l.d.style.display = 'none'; continue; }
    l.d.style.display = ''; l.d.style.left = ((v.x + 1) / 2 * r.width) + 'px'; l.d.style.top = ((1 - v.y) / 2 * r.height) + 'px';
  }
}

// ------------------------------------------------------------------ selection / inspector
let selBox = null;
async function updateSelBox() {
  if (selBox) { overlay.remove(selBox); selBox.geometry.dispose(); selBox = null; }
  if (S.sel.size < 1 || S.sel.size > 50) { dirty = true; return; }
  const box = new THREE.Box3();
  for (const i of S.sel) { const b = await bbOf(i); if (b) box.union(b); }
  if (box.isEmpty()) return;
  const h = new THREE.Box3Helper(box, 0xffb020); h.material.depthTest = false; h.renderOrder = 5; selBox = h; overlay.add(h); dirty = true;
}
async function bbOf(i) {
  let b = S.bbCache?.get(i);
  if (!b) { const info = await elInfo(i); if (info.el.bb) { const bb = JSON.parse(info.el.bb).map(p => p.map(x => x * 0.3048)); b = new THREE.Box3().setFromPoints([toV(bb[0]), toV(bb[1])]); (S.bbCache ||= new Map()).set(i, b); } }
  return b;
}
async function select(i, add = false) {
  if (!add) S.sel.clear();
  if (i != null && i >= 0) { if (add && S.sel.has(i)) S.sel.delete(i); else S.sel.add(i); }
  refreshState(); markTree(); updateSelBox(); await showInspector();
}
function setSelection(ids) { S.sel = new Set(ids); refreshState(); markTree(); updateSelBox(); showInspector(); }
async function elInfo(i) { return await (await fetch(`/api/m/${S.mid}/el/${i}`)).json(); }
const LEN_RE = /length|width|height|offset|elevation|thickness|diameter|depth|radius|distance|extension|size|top|bottom|base/i;
function fmtVal(k, v) {
  if (v === '' || v == null) return '<span class="dim">-</span>';
  const n = Number(v);
  if (typeof v === 'string' && v !== '' && !isNaN(n) && /^-?\d+(\.\d+)?(e-?\d+)?$/i.test(v) && v.includes('.') || (typeof v === 'string' && /\d\.\d{5,}/.test(v))) {
    const ft = n; return `${n.toFixed(4)}` + (LEN_RE.test(k) ? ` <span class="dim">(${(ft * 0.3048).toFixed(3)} m if ft)</span>` : '');
  }
  return esc(v);
}
async function showInspector() {
  const el = $('#insp'); const ids = [...S.sel];
  if (!ids.length) { el.innerHTML = '<p class="dim">Click an element to inspect it.</p>'; return; }
  if (ids.length > 1) {
    const cats = {}; ids.forEach(i => { const c = S.meta.elements[i][2] || '-'; cats[c] = (cats[c] || 0) + 1; });
    el.innerHTML = `<h2>${ids.length} elements selected</h2><table class="kv">${Object.entries(cats).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join('')}</table>`; return;
  }
  const i = ids[0], m = S.meta.elements[i];
  const info = await elInfo(i); if (S.sel.size !== 1 || !S.sel.has(i)) return;
  const e = info.el, bb = e.bb ? JSON.parse(e.bb) : null;
  const dims = bb ? bb[0].map((_, k) => ((bb[1][k] - bb[0][k]) * 0.3048).toFixed(3)).join(' x ') + ' m (x,y,z)' : null;
  const fidLabel = S.meta.fidLabels[e.fid] || e.fid;
  const rows = [['Category', e.cat], ['Family', e.family], ['Geometry bbox agreement', e.iou != null ? e.iou.toFixed(3) + ' (IoU vs Revit-stored bounding box)' : null], ['Class', e.cls], ['Type', e.type], ['Level', e.level], ['ElementId', e.id], ['UniqueId', e.uid], ['IfcGUID', e.ifc], ['Bounding box', dims]]
    .filter(r => r[1] != null && r[1] !== '').map(r => `<tr><td>${r[0]}</td><td class="mono">${esc(r[1])}</td></tr>`).join('');
  el.innerHTML = `<h2>${esc(e.name || e.type || e.cls + ' ' + e.id)}</h2><div class="dim">${esc(e.cat || '')}${e.family ? ' | ' + esc(e.family) : ''}${e.type ? ' : ' + esc(e.type) : ''}</div>
  <div style="margin:6px 0"><span class="fid f-${e.fid}">${e.fid}</span> <span class="dim">${esc(fidLabel)}</span></div>
  <table class="kv">${rows}</table>
  ${(info.typeParams || []).length ? `<h3>Type parameters / profile dimensions (${info.typeParams.length})</h3><table class="kv">${info.typeParams.filter(p => !/^(UniqueId|IfcGUID|Family|Type Id|Type|Family and Type)$/.test(p[0])).map(p => `<tr><td>${esc(p[0])}</td><td class="mono">${fmtVal(p[0], p[1])}</td></tr>`).join('')}</table>` : ''}
  <h3>Parameters (${info.params.length})</h3><input id="pf" type="search" placeholder="filter parameters" style="width:100%;margin-bottom:5px">
  <table class="kv" id="ptab">${info.params.map(p => `<tr data-k="${esc((p[0] + ' ' + p[1]).toLowerCase())}"><td>${esc(p[0])}</td><td class="mono">${fmtVal(p[0], p[1])}</td></tr>`).join('')}</table>
  <div class="dim" style="margin-top:6px;font-size:11px">Doubles are Revit internal units (feet, radians) as stored in the file.</div>`;
  $('#pf').oninput = ev => { const q = ev.target.value.toLowerCase(); document.querySelectorAll('#ptab tr').forEach(tr => tr.hidden = q && !tr.dataset.k.includes(q)); };
}
function elementBox(i) {
  // world-space box of an element from its bounding box (metadata row 8th col not shipped: use batch ranges? fall back to sqlite bb)
  return S.bbCache?.get(i);
}
async function zoomTo(ids) {
  const box = new THREE.Box3();
  for (const i of ids) { const b = await bbOf(i); if (b) box.union(b); }
  if (!box.isEmpty()) fitBox(box, camera.position.clone().sub(controls.target));
}

// ------------------------------------------------------------------ left panel tabs
function buildTabs() {
  document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => { S.tab = b.dataset.t; renderTab(); });
  renderTab();
}
function renderTab() {
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === S.tab));
  const tb = $('#tabbody'); tb.innerHTML = '';
  ({tree: renderTree, levels: renderLevels, views: renderViews, rooms: renderRooms, search: renderResults, cov: renderCov}[S.tab])(tb);
}
const openNodes = new Set();
let treeMode = 'category';
function renderTree(tb) {
  const E = S.meta.elements;
  const bar = document.createElement('div');
  bar.innerHTML = `<label class="chk"><input type="radio" name="tm" value="category" ${treeMode === 'category' ? 'checked' : ''}> category</label> <label class="chk"><input type="radio" name="tm" value="level" ${treeMode === 'level' ? 'checked' : ''}> level</label>
   <label class="chk"><input type="checkbox" id="noGeo" ${S.showNoGeo ? 'checked' : ''}> elements without geometry</label>`;
  bar.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;margin-bottom:6px'; tb.appendChild(bar);
  bar.querySelectorAll('input[name=tm]').forEach(r => r.onchange = () => { treeMode = r.value; renderTab(); });
  bar.querySelector('#noGeo').onchange = ev => { S.showNoGeo = ev.target.checked; renderTab(); };
  const groups = new Map();
  E.forEach((el, i) => {
    if (el[7] && !S.showNoGeo) return;                                  // types
    if (el[6] === 'none' && !S.showNoGeo) return;
    const g1 = treeMode === 'category' ? (el[2] || '(no category)') : (el[5] || '(no level)');
    const g2 = treeMode === 'category' ? ((el[8] ? el[8] + ' : ' : '') + (el[4] || el[1])) : (el[2] || '(no category)');
    if (!groups.has(g1)) groups.set(g1, new Map());
    const m = groups.get(g1); if (!m.has(g2)) m.set(g2, []); m.get(g2).push(i);
  });
  const root = document.createElement('div'); tb.appendChild(root);
  [...groups.keys()].sort().forEach(g1 => {
    const sub = groups.get(g1); let n = 0; sub.forEach(a => n += a.length);
    const node = mkNode(g1, n, 'c:' + g1, treeMode === 'category' ? catColor(g1) : null, () => {
      const kids = document.createElement('div');
      [...sub.keys()].sort().forEach(g2 => {
        const arr = sub.get(g2);
        kids.appendChild(mkNode(g2, arr.length, 't:' + g1 + '|' + g2, null, () => {
          const k2 = document.createElement('div');
          arr.slice(0, 400).forEach(i => k2.appendChild(mkLeaf(i)));
          if (arr.length > 400) { const more = document.createElement('div'); more.className = 'dim'; more.textContent = `... ${arr.length - 400} more (use search)`; k2.appendChild(more); }
          return k2;
        }, arr));
      });
      return kids;
    }, [...sub.values()].flat(), treeMode === 'category' ? g1 : null);
    root.appendChild(node);
  });
}
function catColor(c) { const b = S.meta.batches.find(b => b.cat === c); return b ? b.color : null; }
function mkNode(label, count, key, color, mkKids, idsForSelect, catKey) {
  const d = document.createElement('div'); d.className = 'node';
  const row = document.createElement('div'); row.className = 'row';
  const tw = document.createElement('span'); tw.className = 'tw'; tw.textContent = openNodes.has(key) ? '▾' : '▸';
  row.appendChild(tw);
  if (catKey) { const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = !S.catHidden.has(catKey); cb.title = 'visible'; cb.onchange = () => { cb.checked ? S.catHidden.delete(catKey) : S.catHidden.add(catKey); refreshState(); }; cb.onclick = e => e.stopPropagation(); row.appendChild(cb); }
  if (catKey) { const only = document.createElement('span'); only.className = 'tw'; only.textContent = '\u25ce'; only.title = 'show only this category'; only.onclick = ev => { ev.stopPropagation(); S.catHidden = new Set([...S.byCat.keys()].filter(c => c !== catKey)); refreshState(); renderTab(); }; row.appendChild(only); }
  if (color) { const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = color; row.appendChild(sw); }
  const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = label; row.appendChild(nm);
  const c = document.createElement('span'); c.className = 'cnt'; c.textContent = count; row.appendChild(c);
  d.appendChild(row);
  let kids = null;
  const toggle = () => {
    if (kids) { kids.remove(); kids = null; openNodes.delete(key); tw.textContent = '▸'; }
    else { kids = mkKids(); kids.className = 'kids'; d.appendChild(kids); openNodes.add(key); tw.textContent = '▾'; markTree(); }
  };
  tw.onclick = toggle; row.ondblclick = toggle;
  row.onclick = ev => { if (ev.target.tagName === 'INPUT') return; setSelection(idsForSelect.slice(0, 20000)); };
  if (openNodes.has(key)) { kids = mkKids(); kids.className = 'kids'; d.appendChild(kids); }
  return d;
}
function mkLeaf(i) {
  const el = S.meta.elements[i]; const r = document.createElement('div'); r.className = 'row'; r.dataset.i = i;
  r.innerHTML = `<span class="fid f-${el[6]}">${el[6][0]}</span><span class="nm">${esc(el[3] || el[4] || el[1])}</span><span class="cnt">${el[0]}</span>`;
  r.onclick = ev => select(i, ev.ctrlKey || ev.shiftKey); r.ondblclick = () => zoomTo([i]);
  const eye = document.createElement('span'); eye.className = 'tw'; eye.textContent = S.hidden[i] ? '○' : '●'; eye.title = 'toggle visibility';
  eye.onclick = ev => { ev.stopPropagation(); S.hidden[i] ^= 1; eye.textContent = S.hidden[i] ? '○' : '●'; refreshState(); };
  r.prepend(eye); return r;
}
function markTree() { document.querySelectorAll('#tabbody .row[data-i]').forEach(r => r.classList.toggle('sel', S.sel.has(+r.dataset.i))); }

function renderLevels(tb) {
  const L = S.meta.levels, E = S.meta.elements; const cnt = {}; E.forEach(el => { if (el[5] && el[6] !== 'none') cnt[el[5]] = (cnt[el[5]] || 0) + 1; });
  tb.innerHTML = `<div style="margin-bottom:6px"><label class="chk"><input type="checkbox" id="sl" ${showLvl ? 'checked' : ''}> level planes</label> <label class="chk"><input type="checkbox" id="sg" ${showGrid ? 'checked' : ''}> grids</label></div>
  <h3>Levels (${L.length})</h3>` + [...L].reverse().map(l => `<div class="li" data-l="${esc(l.name)}"><input type="checkbox" ${S.lvlHidden.has(l.name) ? '' : 'checked'} title="show elements of this level"><b>${esc(l.name)}</b><button class="only" title="show only this level">only</button><span class="cnt">${l.elev.toFixed(3)} m &middot; ${cnt[l.name] || 0}</span></div>`).join('') +
  `<h3>Phases (created in)</h3>` + ((S.meta.phases || []).map((p, k) => `<div class="li" data-ph="${k}"><b>${esc(p)}</b><span class="cnt">isolate</span></div>`).join('') || '<div class="dim">none stored</div>') + `<h3>Grids (${S.meta.grids.length})</h3><div class="dim">` + S.meta.grids.map(g => esc(g.name)).sort().join(', ') + '</div>';
  tb.querySelector('#sl').onchange = e => { showLvl = e.target.checked; S.lvlGroup.visible = showLvl; dirty = true; };
  tb.querySelector('#sg').onchange = e => { showGrid = e.target.checked; S.gridGroup.visible = showGrid; dirty = true; };
  tb.querySelectorAll('[data-ph]').forEach(d => d.onclick = () => { const k = +d.dataset.ph, set = new Set(); S.meta.elements.forEach((el, i) => { if (el[9] === k && el[6] !== 'none') set.add(i); }); setIsolate(set); });
  tb.querySelectorAll('.li[data-l]').forEach(d => {
    const name = d.dataset.l;
    d.querySelector('input').onchange = e => { e.target.checked ? S.lvlHidden.delete(name) : S.lvlHidden.add(name); refreshState(); };
    d.querySelector('.only').onclick = ev => { ev.stopPropagation(); S.lvlHidden = new Set([...L.map(x => x.name), ''].filter(n => n !== name)); refreshState(); renderTab(); };
    d.onclick = ev => { if (ev.target.tagName === 'INPUT') return; const l = L.find(x => x.name === name); setSection('Y', l.elev + 1.2); };
    d.title = 'click: horizontal section 1.2 m above the level';
  });
}
function renderViews(tb) {
  const V = S.meta.views || [], Sh = S.meta.sheets || [];
  tb.innerHTML = `<h3>Sheets (${Sh.length})</h3>` + Sh.map(s => `<div class="li"><b>${esc(s.number)}</b> ${esc(s.name)}<span class="cnt">${(s.views || []).length} views</span></div>` + ((s.views || []).length ? `<div class="dim" style="margin:-2px 0 3px 22px;font-size:11px">${s.views.map(esc).join(' &middot; ')}</div>` : '')).join('') +
    `<h3>Views (${V.length})</h3>` + V.map((v, k) => `<div class="li" data-vk="${k}" style="${v.origin ? '' : 'opacity:.55'}" title="${v.origin ? 'click: open this view in the 3D scene' : 'no camera stored'}"><span>${esc(v.name)}</span><span class="cnt">${esc(v.kind)}${v.scale ? ' 1:' + Math.round(1 / v.scale) : ''}${v.template ? ' (template)' : ''}</span></div>`).join('');
  tb.querySelectorAll('[data-vk]').forEach(d => d.onclick = () => openView(V[+d.dataset.vk]));
}
function renderRooms(tb) {
  const R = S.meta.rooms || [];
  tb.innerHTML = `<div><label class="chk"><input type="checkbox" id="rl" ${S.roomGroup?.visible ? 'checked' : ''}> room labels in 3D</label></div><h3>Rooms / spaces / areas (${R.length})</h3>` +
    R.map((r, k) => `<div class="li" data-k="${k}"><b>${esc(r.number)}</b> ${esc(r.name)}<span class="cnt">${esc(r.kind)} &middot; ${esc(r.level || '')}</span></div>`).join('');
  tb.querySelector('#rl').onchange = e => { S.roomGroup.visible = e.target.checked; dirty = true; };
  tb.querySelectorAll('.li').forEach(d => d.onclick = () => { const r = R[+d.dataset.k]; S.roomGroup.visible = true; if (r.pt) { const p = toV(r.pt); fitBox(new THREE.Box3(p.clone().addScalar(-4), p.clone().addScalar(4)), camera.position.clone().sub(controls.target)); } if (r.i != null) select(r.i); });
}
function renderResults(tb) {
  const hits = S.hits;
  tb.innerHTML = `<div style="display:flex;gap:5px;margin-bottom:6px"><button id="rSel">Select all</button><button id="rIso">Isolate</button><button id="rZoom">Zoom</button><span class="dim" style="align-self:center">${hits.length} results</span></div>` +
    hits.slice(0, 600).map(h => { const el = S.meta.elements[h.i]; return `<div class="li" data-i="${h.i}"><span class="fid f-${el[6]}">${el[6][0]}</span><span class="nm">${esc(el[3] || el[4] || el[1])}</span><span class="dim">${esc(el[2] || '')}</span><span class="cnt">${h.why ? esc(h.why) : el[0]}</span></div>`; }).join('') + (hits.length > 600 ? `<div class="dim">... ${hits.length - 600} more</div>` : '');
  tb.querySelectorAll('.li').forEach(d => { d.onclick = async ev => { await select(+d.dataset.i, ev.ctrlKey); zoomTo([...S.sel]); }; d.ondblclick = () => zoomTo([+d.dataset.i]); });
  tb.querySelector('#rSel').onclick = () => setSelection(hits.map(h => h.i));
  tb.querySelector('#rIso').onclick = () => { setIsolate(new Set(hits.map(h => h.i))); };
  tb.querySelector('#rZoom').onclick = () => zoomTo(hits.slice(0, 200).map(h => h.i));
}
let covMode = 'cat';
function renderCov(tb) {
  const C = covMode === 'cat' ? S.meta.coverage : (S.meta.coverageByClass || S.meta.coverage); const tot = {solid: 0, mesh: 0, matched: 0, param: 0, approx: 0, bbox: 0, line: 0, none: 0};
  for (const v of Object.values(S.meta.coverage)) for (const k in v) tot[k] = (tot[k] || 0) + v[k];
  const sum = Object.values(tot).reduce((a, b) => a + b, 0), geo = sum - tot.none;
  const drawn = v => (v.solid || 0) + (v.mesh || 0) + (v.matched || 0) + (v.param || 0) + (v.approx || 0) + (v.bbox || 0) + (v.line || 0);
  const pct = (n, d) => d ? (n / d * 100).toFixed(0) + '%' : '';
  const grp = v => ({exact: (v.solid || 0) + (v.mesh || 0), matched: v.matched || 0, approx: (v.param || 0) + (v.approx || 0), box: v.bbox || 0});
  const hid = new Set(S.meta.defaultHidden || []); const ptot = {};
  for (const [c, v] of Object.entries(S.meta.coverage)) if (!hid.has(c)) for (const k in v) ptot[k] = (ptot[k] || 0) + v[k];
  const g = grp(ptot), gd = g.exact + g.matched + g.approx + g.box;
  tb.innerHTML = `<h3>Geometry coverage</h3><div class="bar">${FID.map(f => `<div style="width:${tot[f] / sum * 100}%;background:${FIDCOL[f]}" title="${f}"></div>`).join('')}</div>
  <table class="cov"><tr><th>fidelity</th><th>elements</th><th></th></tr>${FID.map(f => `<tr><td><span class="fid f-${f}">${f}</span> ${esc(S.meta.fidLabels[f] || '')}</td><td>${tot[f] || 0}</td><td>${(tot[f] / sum * 100).toFixed(1)}%</td></tr>`).join('')}</table>
  <p><b>Of ${gd.toLocaleString()} building-geometry elements</b> (analytical, reference, room and annotation-like categories excluded):<br> <b>true geometry</b> (decoded B-rep / saved mesh) ${pct(g.exact, gd)} &middot; <b>parametric, extents match</b> (rebuilt from stored data, shape unproven) ${pct(g.matched, gd)} &middot; approximate ${pct(g.approx, gd)} &middot; <b>box only</b> ${pct(g.box, gd)}<br><span class="dim">${geo.toLocaleString()} of ${sum.toLocaleString()} database elements have anything drawn (others are types, views, parameters, annotations...). Lines excluded from the percentages.</span></p>
  <div style="margin:6px 0"><label class="chk"><input type="radio" name="cm" value="cat" ${covMode === 'cat' ? 'checked' : ''}> by category</label> <label class="chk"><input type="radio" name="cm" value="cls" ${covMode === 'cls' ? 'checked' : ''}> by Revit class</label></div>
  <table class="cov"><tr><th>${covMode === 'cat' ? 'category' : 'class'}</th><th>n</th><th>true</th><th>param-match</th><th>approx</th><th>box</th></tr>` +
    Object.entries(C).filter(([k, v]) => grp(v).exact + grp(v).matched + grp(v).approx + grp(v).box > 0).sort((a, b) => { const x = grp(a[1]), y = grp(b[1]); return (y.exact + y.matched + y.approx + y.box) - (x.exact + x.matched + x.approx + x.box); })
      .map(([k, v]) => { const x = grp(v), n = x.exact + x.matched + x.approx + x.box; return `<tr class="covrow" data-k="${esc(k)}" title="click: show only this ${covMode === 'cat' ? 'category' : 'class'} in fidelity colours"><td>${esc(k)}</td><td>${n}</td><td>${pct(x.exact, n)}</td><td>${pct(x.matched, n)}</td><td>${pct(x.approx, n)}</td><td>${pct(x.box, n)}</td></tr>`; }).join('') + '</table>';
  tb.querySelectorAll('input[name=cm]').forEach(r => r.onchange = () => { covMode = r.value; renderTab(); });
  tb.querySelectorAll('.covrow').forEach(tr => tr.onclick = () => {
    const k = tr.dataset.k, idx = [];
    S.meta.elements.forEach((el, i) => { if ((covMode === 'cat' ? el[2] : el[1]) === k && el[6] !== 'none') idx.push(i); });
    setIsolate(new Set(idx)); if (!S.fidMode) $('#bFid').click();
  });
}
function setupLegend() {
  $('#legend').innerHTML = FID.slice(0, 7).map(f => `<div><i style="background:${FIDCOL[f]}"></i>${f}</div>`).join('');
}

// ------------------------------------------------------------------ search
let qt;
$('#q').addEventListener('input', () => { clearTimeout(qt); qt = setTimeout(runSearch, 150); });
async function runSearch() {
  const q = $('#q').value.trim().toLowerCase(); if (!S.meta) return;
  if (!q) { S.hits = []; return renderIfSearch(); }
  const terms = q.split(/\s+/); const hits = [];
  for (let i = 0; i < S.N; i++) { const h = S.hay[i]; if (terms.every(t => h.includes(t))) hits.push({i}); }
  if ($('#qParams').checked) {
    const seen = new Set(hits.map(h => h.i));
    const res = await (await fetch(`/api/m/${S.mid}/search?q=${encodeURIComponent(q)}`)).json();
    for (const [i, v] of res) if (!seen.has(i)) hits.push({i, why: v[0][0] + '=' + String(v[0][1]).slice(0, 24)});
  }
  S.hits = hits; S.tab = 'search'; renderTab();
}
function renderIfSearch() { if (S.tab === 'search') renderTab(); }
$('#qParams').onchange = runSearch;

// ------------------------------------------------------------------ section, isolate, measure
// ---- clipping: section plane (axis + offset), section box (6 planes), and the cut plane of an opened Revit view
const secPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0); let secOn = false, secFlip = 1, secMode = 'plane';
const boxPlanes = [0, 1, 2, 3, 4, 5].map(() => new THREE.Plane()); S.viewClip = null;
function setSection(axis, posM) {
  secOn = true; secMode = 'plane'; $('#secui').hidden = false; $('#secAxis').value = axis; $('#secMode').value = 'plane';
  const mb = modelBox(), k = axis === 'X' ? 'x' : axis === 'Y' ? 'y' : 'z';
  const lo = mb.min[k], hi = mb.max[k]; $('#secPos').value = Math.round((posM - lo) / (hi - lo) * 1000); applySection();
}
function applySection() {
  const planes = [];
  const mb = modelBox(), ax = $('#secAxis').value, k = ax === 'X' ? 'x' : ax === 'Y' ? 'y' : 'z';
  $('#secPlaneUi').hidden = secMode !== 'plane'; $('#secBoxUi').hidden = secMode !== 'box';
  if (secOn && secMode === 'plane') {
    const pos = mb.min[k] + (mb.max[k] - mb.min[k]) * $('#secPos').value / 1000;
    const n = new THREE.Vector3(); n[k] = -secFlip; secPlane.normal.copy(n); secPlane.constant = secFlip * pos; planes.push(secPlane);
  } else if (secOn && secMode === 'box') {
    ['x', 'y', 'z'].forEach((kk, i) => {
      const lo = mb.min[kk], hi = mb.max[kk]; const a = +$(`#bx${kk}0`).value / 1000, b = +$(`#bx${kk}1`).value / 1000;
      const nlo = new THREE.Vector3(); nlo[kk] = 1; boxPlanes[2 * i].normal.copy(nlo); boxPlanes[2 * i].constant = -(lo + (hi - lo) * Math.min(a, b));
      const nhi = new THREE.Vector3(); nhi[kk] = -1; boxPlanes[2 * i + 1].normal.copy(nhi); boxPlanes[2 * i + 1].constant = (lo + (hi - lo) * Math.max(a, b));
      planes.push(boxPlanes[2 * i], boxPlanes[2 * i + 1]);
    });
  }
  if (S.viewClip) planes.push(S.viewClip);
  renderer.clippingPlanes = planes; dirty = true; scheduleHash();
}
$('#bSection').onclick = () => { secOn ? (secOn = false, $('#secui').hidden = true, applySection()) : setSection('Y', (modelBox().min.y + modelBox().max.y) / 2); };
$('#secAxis').onchange = applySection; $('#secPos').oninput = applySection;
$('#secMode').onchange = () => { secMode = $('#secMode').value; secOn = true; applySection(); };
['x', 'y', 'z'].forEach(kk => { $(`#bx${kk}0`).oninput = applySection; $(`#bx${kk}1`).oninput = applySection; });
$('#secFlip').onclick = () => { secFlip *= -1; applySection(); };
$('#secOff').onclick = () => { secOn = false; $('#secui').hidden = true; applySection(); };


function setIsolate(set) { S.isolate = set; S.isoGhost = true; refreshState(); $('#bIsolate').classList.toggle('on', !!set); }
$('#bIsolate').onclick = () => { if (S.isolate) setIsolate(null); else if (S.sel.size) setIsolate(new Set(S.sel)); };
$('#bHide').onclick = () => { S.sel.forEach(i => S.hidden[i] = 1); S.sel.clear(); refreshState(); showInspector(); renderIfTree(); };
$('#bShowAll').onclick = () => { S.hidden.fill(0); S.catHidden.clear(); S.lvlHidden.clear(); S.isolate = null; $('#bIsolate').classList.remove('on'); secOn = false; $('#secui').hidden = true; applySection(); refreshState(); renderTab(); };
function renderIfTree() { if (S.tab === 'tree') renderTab(); }
$('#bFid').onclick = () => { S.fidMode ^= 1; U.uMode.value = S.fidMode; $('#bFid').classList.toggle('on', !!S.fidMode); $('#legend').hidden = !S.fidMode; dirty = true; };
$('#bFit').onclick = () => S.sel.size ? zoomTo([...S.sel]) : fitAll();
$('#bTop').onclick = () => fitAll(new THREE.Vector3(0, 1, 0.001));
$('#bFront').onclick = () => fitAll(new THREE.Vector3(0, 0.15, 1));
$('#bIso').onclick = () => fitAll();
const mGroup = new THREE.Group(); scene.add(mGroup);
$('#bMeasure').onclick = () => { S.measure = !S.measure; S.mpts = []; mGroup.clear(); $('#bMeasure').classList.toggle('on', S.measure); $('#status').textContent = S.measure ? 'Measure: click two points' : ''; };
function measureClick(p) {
  S.mpts.push(p.clone());
  const mk = new THREE.Mesh(new THREE.SphereGeometry(camera.position.distanceTo(p) * 0.006, 10, 8), new THREE.MeshBasicMaterial({color: 0xff3b30, depthTest: false})); mk.position.copy(p); mk.renderOrder = 10; mGroup.add(mk);
  if (S.mpts.length === 2) {
    const [a, b] = S.mpts; const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), new THREE.LineBasicMaterial({color: 0xff3b30, depthTest: false})); ln.renderOrder = 10; mGroup.add(ln);
    const d = a.distanceTo(b), dx = Math.abs(a.x - b.x), dy = Math.abs(a.z - b.z), dz = Math.abs(a.y - b.y);
    $('#status').textContent = `Distance ${d.toFixed(3)} m   (dx ${dx.toFixed(3)}, dy ${dy.toFixed(3)}, dz ${dz.toFixed(3)})`;
    addLabel(d.toFixed(2) + ' m', a.clone().add(b).multiplyScalar(.5), 'room', mGroup); S.mpts = [];
  }
}

// ------------------------------------------------------------------ pointer interaction
let down = null;
canvas.addEventListener('pointerdown', e => { down = {x: e.clientX, y: e.clientY, t: performance.now()}; });
canvas.addEventListener('pointerup', e => {
  if (!down) return; const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y); down = null;
  if (moved > 4 || e.button !== 0) return;
  const h = pickAt(e.clientX, e.clientY);
  if (S.measure) { if (h) { const sn = e.altKey ? null : snapTo(h.id, h.p); if (sn) $('#status').textContent = 'snapped to ' + sn.kind; measureClick(sn ? sn.pt : h.p); } return; }
  if (h) select(h.id, e.ctrlKey || e.shiftKey); else if (!e.ctrlKey) select(null);
});
canvas.addEventListener('dblclick', e => { const h = pickAt(e.clientX, e.clientY); if (h) zoomTo([h.id]); });
let hoverT = 0;
canvas.addEventListener('pointermove', e => {
  if (down || S.measure) return; const now = performance.now(); if (now - hoverT < 70) return; hoverT = now;
  const h = pickAt(e.clientX, e.clientY); const i = h ? h.id : -1; const tip = $('#tip');
  if (i !== S.hoverI) { S.hoverI = i; refreshState(); }
  if (i >= 0) { const el = S.meta.elements[i]; tip.style.display = 'block'; tip.style.left = (e.clientX - canvas.getBoundingClientRect().left + 14) + 'px'; tip.style.top = (e.clientY - canvas.getBoundingClientRect().top + 14) + 'px';
    tip.innerHTML = `<b>${esc(el[3] || el[4] || el[1])}</b><br>${esc(el[2] || '')}${el[4] ? ' : ' + esc(el[4]) : ''}<br><span class="dim">id ${el[0]} &middot; ${el[6]}</span>`; } else tip.style.display = 'none';
});
canvas.addEventListener('pointerleave', () => { $('#tip').style.display = 'none'; if (S.hoverI >= 0) { S.hoverI = -1; refreshState(); } });
addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'f' || e.key === 'F') $('#bFit').click(); else if (e.key === 'h' || e.key === 'H') $('#bHide').click();
  else if (e.key === 'i' || e.key === 'I') $('#bIsolate').click(); else if (e.key === 'm' || e.key === 'M') $('#bMeasure').click();
  else if (e.key === 'Escape') { select(null); if (S.measure) $('#bMeasure').click(); }
});
controls.addEventListener('change', () => dirty = true);

// ------------------------------------------------------------------ render loop
function resize() {
  const r = canvas.getBoundingClientRect(); const w = Math.max(1, r.width | 0), h = Math.max(1, r.height | 0);
  if (canvas.width !== w * renderer.getPixelRatio() | 0 || canvas.height !== h * renderer.getPixelRatio() | 0) { renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true; }
}
function frame() {
  requestAnimationFrame(frame); resize(); controls.update();
  if (!dirty) return; dirty = false;
  sun.position.copy(camera.position).add(new THREE.Vector3(.3, 1, .2).multiplyScalar(50)); sun.target.position.copy(controls.target);
  renderer.render(scene, camera); updateLabels();
}
requestAnimationFrame(frame);

(async () => {
  let models = [];
  for (let k = 0; k < 8; k++) { try { models = await (await fetch('/api/models')).json(); break; } catch (e) { await new Promise(r => setTimeout(r, 400)); } }
  const sel = $('#modelSel'); sel.innerHTML = models.map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join('');
  sel.onchange = () => loadModel(sel.value);
  const want = location.hash.slice(1).split('?')[0]; if (models.some(m => m.id === want)) sel.value = want;
  if (models.length) await loadModel(sel.value); else $('#status').textContent = 'no models';
})();
window.pickAt = pickAt; window.selectEl = select; window.setSection = setSection; window.zoomTo = zoomTo;
window.refreshState = refreshState;

window.__renderer = renderer; window.__scene = scene; window.__camera = camera;

$('#bHelp').onclick = () => { $('#help').hidden = !$('#help').hidden; };
window.__controls = controls;
window.fitAll = fitAll; window.THREE = THREE;
window.toVd = toV; window.fitBox = fitBox;

// reader / viewer upgrade watcher: when the reader (or this converter) changes, models converted with an older version are stale -> offer a reconvert
setInterval(async () => {
  if (!S.meta || !S.meta.stamps || (S.meta.phase || 'done') !== 'done') return;
  try {
    const r = await (await fetch('/api/reader')).json();
    const stale = r.reader !== S.meta.stamps.reader || r.viewer !== S.meta.stamps.viewer;
    let b = $('#stale'); if (!stale) { if (b) b.hidden = true; return; }
    if (!b) { b = document.createElement('div'); b.id = 'stale'; $('#view').appendChild(b); }
    b.hidden = false; b.innerHTML = `Reader/converter updated${r.geometryApi ? ' (GEOMETRY_API.md present)' : ''}: this model was converted with an older version. <button id="reconv">Reconvert</button>`;
    $('#reconv').onclick = async () => { b.hidden = true; const j = await (await fetch(`/api/m/${S.mid}/reconvert`, {method: 'POST'})).json(); if (j.ok) { window.__loaded = false; const sel = $('#modelSel'); if (![...sel.options].some(o => o.value === j.id)) sel.add(new Option(S.meta.file, j.id)); sel.value = j.id; await loadModel(j.id); } else b.innerHTML = 'No source file known for this model: reopen the .rvt with rvt-viewer open.'; };
  } catch (e) {}
}, 20000);

// model picker: every converted model (fidelity summary, stale flag), open another .rvt by path, switch without reloading the page
async function openPicker() {
  const el = $('#picker'); el.hidden = false; el.innerHTML = '<div class="pk"><h3>Models</h3><div class="dim">loading...</div></div>';
  const lib = await (await fetch('/api/library')).json();
  const f = x => (x * 100).toFixed(0) + '%';
  el.innerHTML = `<div class="pk"><div style="display:flex;justify-content:space-between"><h3>Models</h3><button id="pkClose">close</button></div>
  <div style="display:flex;gap:6px;margin-bottom:8px"><input id="pkPath" type="text" placeholder="open another file: /path/to/model.rvt" style="flex:1"><button id="pkOpen">Open</button></div><div id="pkErr" class="dim"></div>
  <table class="cov"><tr><th>model</th><th>MB</th><th>elements</th><th>exact</th><th>approx</th><th>box</th><th>converted</th><th></th></tr>` +
  lib.map(m => `<tr class="covrow" data-id="${esc(m.id)}"><td>${esc(m.file)}${m.id === S.mid ? ' <b>(open)</b>' : ''}</td><td>${m.size ? (m.size / 1e6).toFixed(0) : ''}</td><td>${m.elements}</td><td>${f(m.exact)}</td><td>${f(m.approx)}</td><td>${f(m.box)}</td><td>${m.built ? new Date(m.built * 1000).toLocaleString() : ''}</td><td>${m.stale ? '<span class="fid f-bbox" title="reader/converter changed since">stale</span>' : ''}</td></tr>`).join('') + '</table></div>';
  $('#pkClose').onclick = () => el.hidden = true;
  $('#pkOpen').onclick = async () => { const j = await (await fetch('/api/open', {method: 'POST', body: JSON.stringify({path: $('#pkPath').value.trim()})})).json(); if (!j.ok) { $('#pkErr').textContent = j.error || 'could not open'; return; } el.hidden = true; await switchModel(j.id, j.name); };
  el.querySelectorAll('.covrow').forEach(tr => tr.onclick = async () => { const j = await (await fetch('/api/load', {method: 'POST', body: JSON.stringify({id: tr.dataset.id})})).json(); if (j.ok) { el.hidden = true; await switchModel(j.id); } });
}
async function switchModel(id, name) {
  const sel = $('#modelSel'); if (![...sel.options].some(o => o.value === id)) sel.add(new Option(name || id.replace(/-[0-9a-f]{12}$/, ''), id));
  sel.value = id; window.__loaded = false; await loadModel(id);
}
$('#bModels').onclick = openPicker;
addEventListener('keydown', e => { if (e.target.tagName !== 'INPUT' && (e.key === 'o' || e.key === 'O')) openPicker(); });

// ------------------------------------------------------------------ opening a Revit view (3D camera / plan cut / section-elevation plane) from its stored frame
const dirV = d => new THREE.Vector3(d[0], d[2], -d[1]).normalize();
function openView(v) {
  if (!v || !v.origin) { $('#status').textContent = 'this view stores no camera/cut plane'; return; }
  const o = toV(v.origin), mb = modelBox(), c = mb.getCenter(new THREE.Vector3()), size = mb.getSize(new THREE.Vector3()).length();
  S.viewClip = null; S.openView = v;
  if (v.kind === '3d') {
    const d = dirV(v.dir); camera.position.copy(o); controls.target.copy(o).addScaledVector(d, Math.max(5, size / 4));
  } else if (v.kind === 'Plan' && v.cut) {
    const z = v.cut.origin[2]; S.viewClip = new THREE.Plane(new THREE.Vector3(0, -1, 0), z);
    controls.target.set(c.x, z, c.z); camera.position.set(c.x, z + size * 0.9, c.z + 0.001);
  } else if (v.dir) {
    const d = dirV(v.dir); S.viewClip = new THREE.Plane(d.clone(), -d.dot(o));
    controls.target.copy(o); camera.position.copy(o).addScaledVector(d, -size * 0.8);
  }
  camera.near = 0.05; camera.far = size * 20 + 500; camera.updateProjectionMatrix(); controls.update();
  const vb = $('#viewbar'); vb.hidden = false; vb.innerHTML = `<b>${esc(v.name)}</b> <span class="dim">${esc(v.kind)}${S.viewClip ? ' (cut plane active)' : ''}</span> <button id="vbOff">close view</button>`;
  $('#vbOff').onclick = () => { S.viewClip = null; vb.hidden = true; S.openView = null; applySection(); fitAll(); };
  applySection(); dirty = true;
}
window.openView = openView;

// ------------------------------------------------------------------ share state in the URL: #model?c=camera,target&s=selected ids&hc=hidden categories&sec=..&v=view id
let hashT = 0;
function scheduleHash() { clearTimeout(hashT); hashT = setTimeout(writeHash, 500); }
function writeHash() {
  if (!S.meta || !S.mid) return;
  const q = new URLSearchParams(); const f = x => +x.toFixed(2);
  q.set('c', [...camera.position.toArray(), ...controls.target.toArray()].map(f).join(','));
  if (S.sel.size && S.sel.size <= 50) q.set('s', [...S.sel].map(i => S.meta.elements[i][0]).join(','));
  if (S.catHidden.size) q.set('hc', [...S.catHidden].join('|'));
  if (secOn) q.set('sec', secMode === 'plane' ? `p,${$('#secAxis').value},${$('#secPos').value},${secFlip}` : 'b,' + ['x', 'y', 'z'].map(k => $(`#bx${k}0`).value + '-' + $(`#bx${k}1`).value).join(','));
  if (S.openView) q.set('v', S.openView.id);
  try { history.replaceState(null, '', '#' + S.mid + '?' + q.toString()); } catch (e) {}
}
function restoreHash() {
  const h = location.hash.slice(1); const qi = h.indexOf('?'); if (qi < 0) return false;
  const q = new URLSearchParams(h.slice(qi + 1)); let used = false;
  const hc = q.get('hc'); if (hc) { S.catHidden = new Set(hc.split('|')); used = true; }
  const sec = q.get('sec');
  if (sec) { const t = sec.split(','); secOn = true; $('#secui').hidden = false;
    if (t[0] === 'p') { secMode = 'plane'; $('#secMode').value = 'plane'; $('#secAxis').value = t[1]; $('#secPos').value = t[2]; secFlip = +t[3] || 1; }
    else { secMode = 'box'; $('#secMode').value = 'box'; ['x', 'y', 'z'].forEach((k, i) => { const [a, b] = (t[1 + i] || '0-1000').split('-'); $(`#bx${k}0`).value = a; $(`#bx${k}1`).value = b; }); }
    applySection(); used = true; }
  const v = q.get('v'); if (v) { const vv = (S.meta.views || []).find(x => String(x.id) === v); if (vv) openView(vv); }
  const c = q.get('c'); if (c) { const a = c.split(',').map(Number); if (a.length === 6) { camera.position.set(a[0], a[1], a[2]); controls.target.set(a[3], a[4], a[5]); controls.update(); used = true; } }
  const sl = q.get('s'); if (sl) { const ids = new Set(sl.split(',').map(Number)); const idx = []; S.meta.elements.forEach((e, i) => { if (ids.has(e[0])) idx.push(i); }); if (idx.length) { S.sel = new Set(idx); used = true; } }
  if (used) { refreshState(); markTree(); updateSelBox(); showInspector(); }
  return used;
}
controls.addEventListener('change', scheduleHash);
$('#bLink').onclick = async () => { writeHash(); try { await Promise.race([navigator.clipboard.writeText(location.href), new Promise((_, rej) => setTimeout(() => rej(new Error('clipboard timeout')), 1500))]); $('#status').textContent = 'link copied: camera, selection, hidden categories, section'; } catch (e) { $('#status').textContent = 'link in the address bar (clipboard unavailable): ' + location.href; } };
window.restoreHash = restoreHash;

// ------------------------------------------------------------------ measuring with snapping to vertices / edges of the picked element
function buildElRanges() {
  S.elRanges = new Map();
  world.traverse(o => {
    if (!(o.isMesh)) return; const b = S.meta.batches[o.userData.bi]; if (!b || b.kind !== 'tri') return;
    const R = b.ranges; for (let k = 0; k < R.length; k += 3) { const i = R[k]; if (!S.elRanges.has(i)) S.elRanges.set(i, []); S.elRanges.get(i).push({mesh: o, start: R[k + 1], count: R[k + 2]}); }
  });
}
function snapTo(i, p, tol = 0.3) {
  const rs = S.elRanges?.get(i); if (!rs) return null;
  let best = null, bd = tol; const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), t = new THREE.Vector3();
  for (const r of rs) {
    const pos = r.mesh.geometry.attributes.position, ix = r.mesh.geometry.index;
    for (let k = r.start; k < r.start + r.count; k++) {
      a.fromBufferAttribute(pos, ix.getX(3 * k)); b.fromBufferAttribute(pos, ix.getX(3 * k + 1)); c.fromBufferAttribute(pos, ix.getX(3 * k + 2));
      for (const q of [a, b, c]) { const d = q.distanceTo(p); if (d < bd) { bd = d - 0.001; best = {pt: q.clone(), kind: 'vertex'}; } }
      for (const [u, w] of [[a, b], [b, c], [c, a]]) {
        const e = w.clone().sub(u), L2 = e.lengthSq(); if (L2 < 1e-12) continue;
        const s = THREE.MathUtils.clamp(p.clone().sub(u).dot(e) / L2, 0, 1); t.copy(u).addScaledVector(e, s); const d = t.distanceTo(p);
        if (d < bd - 0.05) { bd = d; best = {pt: t.clone(), kind: 'edge'}; }
      }
    }
  }
  return best;
}
window.snapTo = snapTo;

// ------------------------------------------------------------------ keyboard help overlay (? toggles, Esc closes)
addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.key === '?') $('#help').hidden = !$('#help').hidden; else if (e.key === 'Escape') $('#help').hidden = true;
});

// ------------------------------------------------------------------ compare with Revit oracle (tools/compare_gt.py -> compare.json): colour by deviation, per-class table
$('#bCmp').onclick = async () => {
  if (S.cmpOn) { S.cmpOn = false; S.devCode = null; U.uMode.value = S.fidMode; $('#bCmp').classList.remove('on'); $('#cmpPanel').hidden = true; refreshState(); return; }
  const r = await fetch(`/m/${S.mid}/compare.json`);
  if (!r.ok) { $('#status').textContent = 'no compare.json for this model: run tools/compare_gt.py MODELDIR GTDIR (oracle files in rvt-research/gt_geom)'; return; }
  const c = await r.json(); S.cmpOn = true; S.devCode = new Uint8Array(S.N); const E = S.meta.elements; const byCls = {};
  for (const [i, v] of Object.entries(c.elements)) {
    const iou = v.iou, vr = v.vratio, hd = v.hausdorff_ft; let code = iou >= 0.97 && (vr == null || Math.abs(vr - 1) < 0.05) && (hd == null || hd < 0.1) ? 1 : iou >= 0.85 ? 2 : iou >= 0.6 ? 3 : 4;
    S.devCode[+i] = code; const k = E[+i][1]; (byCls[k] ||= []).push(v);
  }
  U.uMode.value = 2; $('#bCmp').classList.add('on'); refreshState();
  const med = a => { a = a.filter(x => x != null).sort((x, y) => x - y); return a.length ? a[a.length >> 1] : null; };
  const f = x => x == null ? '' : x.toFixed(2);
  const p = $('#cmpPanel'); p.hidden = false;
  p.innerHTML = `<b>Compare with Revit</b> <span class="dim">${c.n} elements; green = within 5% / IoU>=0.97, yellow >=0.85, orange >=0.6, red worse, grey no oracle</span><table class="cov"><tr><th>class</th><th>n</th><th>median IoU</th><th>median vol ratio</th><th>median hausdorff ft</th></tr>` +
    Object.entries(byCls).sort((a, b) => b[1].length - a[1].length).map(([k, a]) => `<tr><td>${esc(k)}</td><td>${a.length}</td><td>${f(med(a.map(v => v.iou)))}</td><td>${f(med(a.map(v => v.vratio)))}</td><td>${f(med(a.map(v => v.hausdorff_ft)))}</td></tr>`).join('') + '</table>';
};

{ let m = 'revit'; try { m = localStorage.getItem('rvtNav') || 'revit'; } catch (e) {} setNav(m);
  $('#navSel').onchange = e => setNav(e.target.value); window.setNav = setNav; }

// ------------------------------------------------------------------ ViewCube (top-right): shows the camera orientation, click a face / edge-corner to look from there, home = isometric fit
{
  const cv = document.createElement('canvas'); cv.id = 'vcube'; cv.width = cv.height = 220; $('#view').appendChild(cv);
  const r2 = new THREE.WebGLRenderer({canvas: cv, alpha: true, antialias: true}); r2.setSize(110, 110, false); r2.setPixelRatio(2);
  const sc = new THREE.Scene(), cam2 = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
  const label = (t, dark) => { const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d'); x.fillStyle = dark ? '#cfd6e2' : '#eef1f6'; x.fillRect(0, 0, 128, 128); x.strokeStyle = '#8a93a2'; x.lineWidth = 6; x.strokeRect(3, 3, 122, 122); x.fillStyle = '#1d232c'; x.font = 'bold 26px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(t, 64, 66); const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; return tx; };
  // BoxGeometry face order: +x, -x, +y, -y, +z, -z  (three axes: y up; Revit front = -Y Revit = +z three)
  const names = ['RIGHT', 'LEFT', 'TOP', 'BOTTOM', 'FRONT', 'BACK'];
  const cube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), names.map((n, i) => new THREE.MeshBasicMaterial({map: label(n, i === 3)}))); sc.add(cube);
  sc.add(new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry), new THREE.LineBasicMaterial({color: 0x5a6578})));
  const ray = new THREE.Raycaster();
  function drawCube() { const d = camera.position.clone().sub(controls.target).normalize(); cam2.position.copy(d.multiplyScalar(3.4)); cam2.up.copy(camera.up); cam2.lookAt(0, 0, 0); r2.render(sc, cam2); }
  function look(dir) { const d = camera.position.distanceTo(controls.target); camera.position.copy(controls.target).addScaledVector(dir.clone().normalize(), d); camera.up.set(0, 1, 0); if (Math.abs(dir.y) > 0.99) camera.up.set(0, 0, -1); controls.update(); dirty = true; }
  cv.addEventListener('pointerdown', e => {
    e.stopPropagation(); const rc = cv.getBoundingClientRect(); const m = new THREE.Vector2(((e.clientX - rc.left) / rc.width) * 2 - 1, -(((e.clientY - rc.top) / rc.height) * 2 - 1));
    ray.setFromCamera(m, cam2); const hit = ray.intersectObject(cube)[0]; if (!hit) return;
    const p = hit.point, ax = ['x', 'y', 'z'].map(k => Math.abs(p[k]) > 0.38);       // near an edge/corner: look from the diagonal, else from the face
    const dir = new THREE.Vector3(ax[0] ? Math.sign(p.x) : 0, ax[1] ? Math.sign(p.y) : 0, ax[2] ? Math.sign(p.z) : 0); look(dir);
  });
  const home = document.createElement('button'); home.id = 'vhome'; home.textContent = '\u2302'; home.title = 'Home: isometric, fit all'; home.onclick = () => { camera.up.set(0, 1, 0); fitAll(); }; $('#view').appendChild(home);
  controls.addEventListener('change', drawCube); setInterval(drawCube, 400); drawCube(); window.drawCube = drawCube;
}
