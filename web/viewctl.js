// View control: view-dependent drawing content (annotations, datums, text, linework, hatches) of a plan / section view placed in the 3D scene
// in model space (right orientation, sizes in model feet = paper size x view scale, so they scale with zoom as in Revit), with per-view,
// per-layer / category / subcategory / element controls, picking, presets. Data: /api/m/{mid}/vc/scene/{vid} (rvtviewer/viewctl.py, CONTROL-API.md).
import * as THREE from 'three';

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const FT = 0.3048, EM = 1 / 0.72, LINE_PITCH = 1.22;
const S = window.S, scene = window.__scene, camera = window.__camera, renderer = window.__renderer, controls = window.__controls;
const toV = p => new THREE.Vector3(p[0], p[2], -p[1]);
const dirty = () => controls.dispatchEvent({type: 'change'});

// draw order buckets (fills, lines, annotation fills, text) and which layers are model content (cropped) vs annotation (not cropped, like Revit's annotation crop)
const MODEL_LAYERS = new Set(['cut', 'projection', 'underlay', 'symbolic', 'symbolic_fill', 'cut_fill', 'surface_fill', 'room_fill', 'mask']);
const LAYER_LABEL = {cut: 'Cut linework', projection: 'Projection linework', underlay: 'Underlay', symbolic: 'Symbolic lines', symbolic_fill: 'Symbolic fills', cut_fill: 'Cut hatches/fills',
  surface_fill: 'Surface hatches', room_fill: 'Room fills', mask: 'Masking regions', annotation: 'Annotation symbols', annotation_fill: 'Annotation fills', text: 'Text', datum: 'Grids and levels'};
const PATTERNS = {solid: null, dash: [3.2, 1.6], dot: [0.4, 1.2], dashdot: [3.2, 1.2, 0.4, 1.2], long: [6.4, 1.6]};      // paper mm
const SCALES = [1, 5, 10, 20, 25, 50, 75, 96, 100, 200, 240, 500];

const DEFAULT_STATE = () => ({ghosts: [], ghostOpacity: 0.45, scale: null, detail: null, cut: null, phase: null, pfilter: null, template: true, filters: true, crop: true, layers: {}, cats: {}, elems: {}, classes: {}, types: {}, parts: {}, annoScale: 1, textOn: true, textSize: 1, font: '', textColor: '',
  lineScale: 1, minPx: 1, paper: false, hideHang: false, model: true, nativeOff: true, lift: 0.02, onTop: true, opacity: 1, contrast: true, halo: false});
const V = {mid: null, vid: null, sc: null, group: null, state: DEFAULT_STATE(), sel: null, views: [], loading: false, presets: {}};
window.__vc = V;

// ------------------------------------------------------------------ materials
const crop = {value: new THREE.Vector4(-1e9, -1e9, 1e9, 1e9)};     // local metres u0 v0 u1 v1
const U = {uCrop: crop, uCropOn: {value: 1}, uRes: {value: new THREE.Vector2(1, 1)}, uPxPerMm: {value: 1}, uMinPx: {value: 1}, uOpacity: {value: 1}, uRankMode: {value: 1}};
const lineMat = new THREE.ShaderMaterial({
  uniforms: U, transparent: true, depthWrite: true, depthTest: true, depthFunc: THREE.LessEqualDepth, side: THREE.DoubleSide,
  vertexShader: `
    attribute vec3 aA; attribute vec3 aB; attribute vec2 aC; attribute vec4 aCol; attribute float aW; attribute float aClip; attribute float aRank;
    uniform float uRankMode; uniform vec2 uRes; uniform float uPxPerMm; uniform float uMinPx; varying vec4 vCol; varying vec2 vLoc; varying float vClip;
    void main() {
      vec4 ca = projectionMatrix * modelViewMatrix * vec4(aA, 1.0), cb = projectionMatrix * modelViewMatrix * vec4(aB, 1.0);
      vCol = aCol; vClip = aClip; vLoc = mix(aA.xy, aB.xy, aC.x);
      if (aW <= 0.0 || ca.w < 1e-4 || cb.w < 1e-4) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
      float wpx = max(uMinPx, aW * uPxPerMm);
      vec2 pa = ca.xy / ca.w * uRes * 0.5, pb = cb.xy / cb.w * uRes * 0.5;
      vec2 d = pb - pa; float L = length(d); vec2 dir = L > 1e-4 ? d / L : vec2(1.0, 0.0); vec2 n = vec2(-dir.y, dir.x);
      vec4 c = mix(ca, cb, aC.x); vec2 p = c.xy / c.w * uRes * 0.5;
      p += n * aC.y * wpx * 0.5 + dir * (aC.x * 2.0 - 1.0) * wpx * 0.5;
      gl_Position = vec4(p / (uRes * 0.5) * c.w, c.z, c.w);
      if (uRankMode > 0.5) gl_Position.z = (0.9 - 1.8 * aRank) * gl_Position.w;
    }`,
  fragmentShader: `
    uniform vec4 uCrop; uniform float uCropOn; uniform float uOpacity; varying vec4 vCol; varying vec2 vLoc; varying float vClip;
    void main() {
      if (uCropOn > 0.5 && vClip > 0.5 && (vLoc.x < uCrop.x || vLoc.y < uCrop.y || vLoc.x > uCrop.z || vLoc.y > uCrop.w)) discard;
      gl_FragColor = vec4(vCol.rgb, vCol.a * uOpacity);
    }`,
});
const fillMat = new THREE.ShaderMaterial({
  uniforms: U, transparent: true, depthWrite: true, depthTest: true, depthFunc: THREE.LessEqualDepth, side: THREE.DoubleSide,
  vertexShader: `attribute vec4 aCol; attribute float aClip; attribute float aRank; uniform float uRankMode; varying vec4 vCol; varying vec2 vLoc; varying float vClip;
    void main() { vCol = aCol; vClip = aClip; vLoc = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); if (uRankMode > 0.5) gl_Position.z = (0.9 - 1.8 * aRank) * gl_Position.w; }`,
  fragmentShader: lineMat.fragmentShader,
});

// ------------------------------------------------------------------ geometry from primitives
const rgb = c => (c && c.length >= 3) ? [c[0] / 255, c[1] / 255, c[2] / 255] : [0, 0, 0];
function anchorUV(view, a) {
  const o = view.origin, d = [a[0] - o[0], a[1] - o[1], (a[2] ?? o[2]) - o[2]], dot = (u, v) => u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
  return [dot(d, view.right), dot(d, view.up)];
}
const hex2rgb = h => { const n = parseInt(h.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; };
const lum = c => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];

function pip(pt, loop) { let ins = false; for (let i = 0, j = loop.length - 1; i < loop.length; j = i++) { const a = loop[i], b = loop[j]; if ((a[1] > pt[1]) !== (b[1] > pt[1]) && pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]) ins = !ins; } return ins; }
const area = l => { let s = 0; for (let i = 0, j = l.length - 1; i < l.length; j = i++) s += (l[j][0] + l[i][0]) * (l[j][1] - l[i][1]); return s / 2; };
function triangulate(loopsIn) {
  const loops = loopsIn.map(l => { const q = l.map(p => [p[0], p[1]]); if (q.length > 1 && q[0][0] === q[q.length - 1][0] && q[0][1] === q[q.length - 1][1]) q.pop(); return q; }).filter(l => l.length >= 3);
  const A = loops.map(l => Math.abs(area(l))), order = loops.map((_, i) => i).sort((a, b) => A[b] - A[a]);
  const depth = loops.map(() => 0), parent = loops.map(() => -1);
  for (let k = 0; k < order.length; k++) { const i = order[k]; for (let m = k - 1; m >= 0; m--) { const j = order[m]; if (pip(loops[i][0], loops[j])) { depth[i] = depth[j] + 1; parent[i] = j; break; } } }
  const out = [];
  loops.forEach((l, i) => {
    if (depth[i] % 2) return;
    const holes = loops.filter((_, j) => parent[j] === i && depth[j] % 2 === 1);
    const pts = l.map(p => new THREE.Vector2(p[0], p[1])), hs = holes.map(h => h.map(p => new THREE.Vector2(p[0], p[1])));
    const tris = THREE.ShapeUtils.triangulateShape(pts, hs), all = pts.concat(...hs);
    for (const t of tris) for (const k of t) out.push(all[k].x, all[k].y);
  });
  return out;
}
function dashed(pts, pat) {      // polyline (metres) -> list of [a, b] drawn pieces
  const out = []; let pi = 0, left = pat[0], on = true;
  for (let i = 0; i + 1 < pts.length; i++) {
    let a = pts[i]; const b = pts[i + 1]; let L = Math.hypot(b[0] - a[0], b[1] - a[1]); const dx = (b[0] - a[0]) / (L || 1), dy = (b[1] - a[1]) / (L || 1);
    while (L > 1e-9) {
      const t = Math.min(L, left), e = [a[0] + dx * t, a[1] + dy * t];
      if (on) out.push([a, e]);
      a = e; L -= t; left -= t;
      if (left <= 1e-9) { pi = (pi + 1) % pat.length; on = !on; left = pat[pi]; }
      if (out.length > 20000) return out;
    }
  }
  return out;
}

function build(sc) {
  const view = sc.view, scale = view.scale || 100, mpmm = scale / 1000;      // model metres per paper mm
  const segs = [];       // {a:[u,v], b:[u,v], p: primIndex}
  const tris = [];       // {p, xy: [..]} per fill piece
  const texts = [];
  const meta = [];       // per prim: {eid, cat, layer, kind}
  const lyrs = new Set();
  // tags anchor on the tagged element (host); scaling a tag about that point would move it away from its host, so scale about the tag's own first point
  const own = new Map();
  sc.prims.forEach(p => { if (p.host != null && p.paper && p.elem != null && !own.has(p.elem)) { const q = p.pts ? p.pts[0] : p.segs && p.segs[0] ? p.segs[0][0] : p.origin; if (q) own.set(p.elem, q); } });
  sc.prims.forEach((p, pi) => {
    const eid = p.elem, layer = p.layer || 'x', e = sc.elements[eid] || {};
    const cat = p.cat != null ? p.cat : e.cat;
    meta[pi] = {eid, cat, layer, cls: e.cls, t: p.t, part: p.part, hang: p.hang, clip: MODEL_LAYERS.has(layer) ? 1 : 0};
    lyrs.add(layer);
    const st = p.style || {w: 0.18, rgb: [0, 0, 0]}, ov = V.state.cats[catKey(cat)]?.dash ?? V.state.cats[catKey(e.parent)]?.dash;
    const dsh = ov === undefined || ov === '' ? st.dash : (PATTERNS[ov] || null), pat = dsh && dsh.length ? dsh.map(x => Math.max(x * mpmm, 1e-4)) : null;
    const k = V.state.annoScale || 1, an = k !== 1 && p.paper && p.anchor && sc.view.right ? (p.host != null && own.has(p.elem) ? own.get(p.elem) : anchorUV(sc.view, p.anchor)) : null;
    const sx = q => an ? [(an[0] + (q[0] - an[0]) * k), (an[1] + (q[1] - an[1]) * k)] : q;
    const addPoly = pts => {
      const P = pts.map(q => { const r = sx(q); return [r[0] * FT, r[1] * FT]; });
      if (pat) for (const [a, b] of dashed(P, pat)) segs.push({a, b, p: pi});
      else for (let i = 0; i + 1 < P.length; i++) segs.push({a: P[i], b: P[i + 1], p: pi});
    };
    if (p.t === 'line') addPoly(p.pts);
    else if (p.t === 'segs') (p.segs || []).forEach(addPoly);
    else if (p.t === 'cut') {
      (p.segs || []).forEach(addPoly);
      if (p.fill && p.loops) tris.push({p: pi, xy: triangulate(p.loops.map(l => l.map(q => [q[0] * FT, q[1] * FT]))), col: rgb(p.fill)});
    } else if (p.t === 'fill') {
      const c = Array.isArray(p.color) ? rgb(p.color) : [0.6, 0.6, 0.6];
      tris.push({p: pi, xy: triangulate((p.loops || []).map(l => l.map(q => [q[0] * FT, q[1] * FT]))), col: c});
    } else if (p.t === 'text' && p.text && p.origin) texts.push(pi);
  });
  // painter order = rvt-sheets svg order (detail 'order' first, then layer order, then primitive order); masks hide what was drawn before them
  const LO = {underlay: 0, room_fill: 1, symbolic_fill: 2, cut_fill: 3, surface_fill: 4, projection: 5, cut: 6, symbolic: 7, annotation_fill: 8, mask: -1};
  const hasOrder = sc.prims.some(p => p.order != null), lo = p => LO[p.layer] ?? 99;
  const idx = sc.prims.map((_, i) => i).sort((a, b) => { const pa = sc.prims[a], pb = sc.prims[b]; if (hasOrder) { const d = (pa.order ?? -2) - (pb.order ?? -2); if (d) return d; } return lo(pa) - lo(pb) || a - b; });
  const rank = new Float32Array(sc.prims.length); idx.forEach((pi, k) => rank[pi] = k / Math.max(1, idx.length));
  return {segs, tris, texts, meta, rank, layers: [...lyrs]};
}

// ------------------------------------------------------------------ text
const texCache = new Map();
function textTexture(lines, font, bold, italic) {
  const key = JSON.stringify([lines, font, bold, italic]); if (texCache.has(key)) return texCache.get(key);
  const PX = 48, c = document.createElement('canvas'), g = c.getContext('2d');
  const fam = (font ? font + ', ' : '') + 'Arial, "Liberation Sans", Helvetica, sans-serif';
  // Revit's Arial Narrow is not installed in browsers (falls back to full-width Arial, ~20 % too wide): squeeze the fallback
  const NARROW = 1;      // Revit PDFs print Arial Narrow as plain Arial (reference exports lack the font): no squeeze
  const F = `${italic ? 'italic ' : ''}${bold ? 'bold ' : ''}${PX}px ${fam}`;
  g.font = F;
  const w = Math.max(2, Math.ceil(Math.max(...lines.map(l => g.measureText(l).width)) * NARROW)), lh = PX * LINE_PITCH, h = Math.ceil(lh * lines.length + PX * 0.3);
  c.width = w + 8; c.height = h;
  g.font = F; g.fillStyle = '#fff'; g.textBaseline = 'alphabetic'; g.setTransform(NARROW, 0, 0, 1, 0, 0);
  lines.forEach((l, i) => g.fillText(l, 4 / NARROW, PX * 0.95 + i * lh));
  const tex = new THREE.CanvasTexture(c); tex.anisotropy = 4; tex.minFilter = THREE.LinearMipmapLinearFilter;
  const r = {tex, w: (w + 8) / PX, h: h / PX, lh: LINE_PITCH, asc: 0.95};
  texCache.set(key, r); return r;
}

// ------------------------------------------------------------------ scene object
function disposeGroup() {
  if (!V.group) return;
  V.group.parent && V.group.parent.remove(V.group);
  V.group.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material && o.material.map) o.material.map.dispose?.(); });
  V.group = null; V.lines = V.fills = null; V.textObjs = [];
}
function frameMatrix(view) {
  const X = toV(view.right).normalize(), Y = toV(view.up).normalize(), Z = new THREE.Vector3().crossVectors(X, Y);
  const o = view.origin.slice(); let nz = null;
  if (view.kind === 'plan' && view.range && view.range.cut != null) o[2] = view.range.cut;
  const m = new THREE.Matrix4().makeBasis(X, Y, Z); m.setPosition(toV([o[0] * FT, o[1] * FT, o[2] * FT]));
  return {m, Z};
}

function makeScene(sc) {
  disposeGroup();
  const B = build(sc); V.B = B;
  const g = new THREE.Group(); g.matrixAutoUpdate = false; const fm = frameMatrix(sc.view); V.Z = fm.Z; V.base = fm.m.clone(); g.userData.vc = true;
  // stroke geometry: 4 vertices / segment
  const n = B.segs.length, RK = new Float32Array(n * 4), A = new Float32Array(n * 12), Bv = new Float32Array(n * 12), C = new Float32Array(n * 8), col = new Float32Array(n * 16), W = new Float32Array(n * 4), K = new Float32Array(n * 4), idx = new Uint32Array(n * 6);
  const corners = [[0, -1], [0, 1], [1, -1], [1, 1]];
  B.segs.forEach((s, i) => {
    for (let k = 0; k < 4; k++) {
      const o = i * 4 + k; A.set([s.a[0], s.a[1], 0], o * 3); Bv.set([s.b[0], s.b[1], 0], o * 3); C.set(corners[k], o * 2); K[o] = B.meta[s.p].clip; RK[o] = B.rank[s.p];
    }
    idx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 1, i * 4 + 3, i * 4 + 2], i * 6);
  });
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.BufferAttribute(A, 3));            // required by three (bounds); the shader uses aA/aB
  lg.setAttribute('aA', new THREE.BufferAttribute(A, 3)); lg.setAttribute('aB', new THREE.BufferAttribute(Bv, 3)); lg.setAttribute('aC', new THREE.BufferAttribute(C, 2));
  lg.setAttribute('aCol', new THREE.BufferAttribute(col, 4)); lg.setAttribute('aW', new THREE.BufferAttribute(W, 1)); lg.setAttribute('aClip', new THREE.BufferAttribute(K, 1)); lg.setAttribute('aRank', new THREE.BufferAttribute(RK, 1)); lg.setIndex(new THREE.BufferAttribute(idx, 1));
  const lines = new THREE.Mesh(lg, lineMat); lines.frustumCulled = false; lines.renderOrder = 1001; lines.onBeforeRender = (r, s, cam) => updateUniforms(cam);
  g.add(lines); V.lines = lines;
  // fills
  let nv = 0; B.tris.forEach(t => nv += t.xy.length / 2);
  const P = new Float32Array(nv * 3), FC = new Float32Array(nv * 4), FK = new Float32Array(nv), FR = new Float32Array(nv); let o = 0; B.tris.forEach(t => { t.off = o; t.n = t.xy.length / 2; for (let i = 0; i < t.n; i++, o++) { P.set([t.xy[2 * i], t.xy[2 * i + 1], 0], o * 3); FK[o] = B.meta[t.p].clip; FR[o] = B.rank[t.p]; } });
  const fg = new THREE.BufferGeometry(); fg.setAttribute('position', new THREE.BufferAttribute(P, 3)); fg.setAttribute('aCol', new THREE.BufferAttribute(FC, 4)); fg.setAttribute('aClip', new THREE.BufferAttribute(FK, 1)); fg.setAttribute('aRank', new THREE.BufferAttribute(FR, 1));
  const fills = new THREE.Mesh(fg, fillMat); fills.frustumCulled = false; fills.renderOrder = 1000; fills.onBeforeRender = r => { if (U.uRankMode.value > 0.5) r.clearDepth(); }; g.add(fills); V.fills = fills;
  // texts
  V.textObjs = B.texts.map(pi => makeText(sc.prims[pi], pi)); V.textObjs.forEach(t => g.add(t.obj));
  g.matrix.copy(V.base); g.matrixWorldNeedsUpdate = true; (window.__overlay || scene).add(g); V.group = g;       // inside the app's overlay group: hidden during the id-pick pass
  
  V.sc = sc;
  const cu = sc.view.crop_uv; V.cropUV = cu;
  applyStyles(); dirty();
}

// other views drawn as faint static linework at their own heights (e.g. L1 + L2 + roof plans stacked on the model); strokes only, no text
const ghostMeshes = [];
function clearGhosts() { for (const m of ghostMeshes) { m.parent && m.parent.remove(m); m.geometry.dispose(); } ghostMeshes.length = 0; }
async function loadGhosts() {
  clearGhosts();
  for (const vid of V.state.ghosts) {
    try {
      const sc = await (await fetch(`/api/m/${V.mid}/vc/scene/${vid}`)).json(); if (sc.error) continue;
      const B = build(sc), n = B.segs.length, A = new Float32Array(n * 12), Bv = new Float32Array(n * 12), C = new Float32Array(n * 8), col = new Float32Array(n * 16), W = new Float32Array(n * 4), K = new Float32Array(n * 4), RK = new Float32Array(n * 4), idx = new Uint32Array(n * 6);
      const corners = [[0, -1], [0, 1], [1, -1], [1, 1]], dark = matchMedia('(prefers-color-scheme: dark)').matches;
      B.segs.forEach((sg, i) => {
        const m = B.meta[sg.p], st = sc.prims[sg.p].style || {w: 0.18, rgb: [0, 0, 0]}; let c = rgb(st.rgb); if (dark && lum(c) < 0.18) c = [0.93, 0.93, 0.93];
        for (let k = 0; k < 4; k++) { const o = i * 4 + k; A.set([sg.a[0], sg.a[1], 0], o * 3); Bv.set([sg.b[0], sg.b[1], 0], o * 3); C.set(corners[k], o * 2); K[o] = m.clip; col.set([c[0], c[1], c[2], V.state.ghostOpacity], o * 4); W[o] = m.layer === 'text' ? 0 : st.w; }
        idx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 1, i * 4 + 3, i * 4 + 2], i * 6);
      });
      const g = new THREE.BufferGeometry();
      for (const [k, a, sz] of [['position', A, 3], ['aA', A, 3], ['aB', Bv, 3], ['aC', C, 2], ['aCol', col, 4], ['aW', W, 1], ['aClip', K, 1], ['aRank', RK, 1]]) g.setAttribute(k, new THREE.BufferAttribute(a, sz));
      g.setIndex(new THREE.BufferAttribute(idx, 1));
      const mat = lineMat.clone(); mat.uniforms = Object.assign({}, U, {uCrop: {value: new THREE.Vector4(...(sc.view.crop_uv || [-1e6, -1e6, 1e6, 1e6]).map(x => x * FT))}, uRankMode: {value: 0}, uPxPerMm: {value: 1}});
      mat.depthTest = true; 
      const mesh = new THREE.Mesh(g, mat); mesh.frustumCulled = false; mesh.renderOrder = 998; mesh.matrixAutoUpdate = false; mesh.matrix.copy(frameMatrix(sc.view).m);
      // line widths in px for this view's own scale: pxPerMm uniform is per overlay scale; correct by the scale ratio
      mesh.onBeforeRender = (r, sce, cam) => { updateUniforms(cam); mat.uniforms.uPxPerMm.value = U.uPxPerMm.value * (sc.view.scale || 100) / (V.sc ? V.sc.view.scale || 100 : 100); };
      (window.__overlay || scene).add(mesh); ghostMeshes.push(mesh);
    } catch (e) { console.warn('ghost view', vid, e); }
  }
  dirty();
}

function makeText(p, pi) {
  const lines = String(p.text).split('\n'), tx = textTexture(lines, V.state.font || p.font, p.bold, p.italic);
  const em = (p.size || 0.0098) * EM * FT;          // metres per em (size is Revit text size in model feet; em = size / 0.72)
  // ShaderMaterial (not MeshBasicMaterial): the app clips the model with global clip planes (plan cut plane, crop box) that must not clip annotation text
  const mat = new THREE.ShaderMaterial({uniforms: {uMap: {value: tx.tex}, uColor: {value: new THREE.Vector3(0, 0, 0)}, uOpacity: {value: 1}, uRankMode: U.uRankMode}, transparent: true, depthWrite: false, depthTest: true, depthFunc: THREE.LessEqualDepth, side: THREE.DoubleSide,
    vertexShader: 'uniform float uRankMode; varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); if (uRankMode > 0.5) gl_Position.z = -0.9 * gl_Position.w; }',
    fragmentShader: 'uniform sampler2D uMap; uniform vec3 uColor; uniform float uOpacity; varying vec2 vUv; void main() { float a = texture2D(uMap, vUv).a; if (a < 0.02) discard; gl_FragColor = vec4(uColor, a * uOpacity); }'});
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(tx.w * em, tx.h * em), mat); mesh.renderOrder = 1002;
  // plane centre relative to the anchor (rvt-sheets svg.text rules): anchored notes/labels: origin = anchor on the alignment side, vertical top / middle / bottom of the block;
  // stored rich text: origin = top-left of the layout box, first baseline one em below
  const w = tx.w * em, h = tx.h * em, ascC = tx.asc * em, nl = lines.length, lh = LINE_PITCH * em, pad = 4 / 48 * em, ha = p.halign || 0;
  let first, dx = 0;
  if (p.anchor) { const asc = 0.9 * em; first = {0: asc, 1: asc - ((nl - 1) * lh + asc) / 2, 2: -(nl - 1) * lh}[p.valign || 0]; }
  else { first = em; const bw = ((p.box || [0, 0])[0] || 0) * FT; dx = bw ? {0: 0, 1: bw / 2, 2: bw}[ha] : 0; }
  const ox = dx + {0: w / 2 - pad, 1: 0, 2: -w / 2 + pad}[ha], oy = -first + ascC - h / 2;
  mesh.position.set(ox, oy, 0);
  const grp = new THREE.Group(); grp.add(mesh);
  const ang = p.x ? Math.atan2(p.x[1], p.x[0]) : 0;
  grp.position.set(p.origin[0] * FT, p.origin[1] * FT, 0); grp.rotation.z = ang; grp.userData.pi = pi;
  return {obj: grp, mesh, pi, w, h, ang, ox, oy};
}

function updateUniforms(cam) {
  const size = renderer.getSize(new THREE.Vector2());
  U.uRes.value.set(size.x * renderer.getPixelRatio(), size.y * renderer.getPixelRatio());
  const d = Math.max(0.01, cam.position.distanceTo(controls.target)), pxPerM = U.uRes.value.y / (2 * d * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)));
  const scale = V.sc ? (V.sc.view.scale || 100) : 100;
  U.uPxPerMm.value = pxPerM * (scale / 1000) * V.state.lineScale;
  U.uMinPx.value = V.state.minPx * renderer.getPixelRatio();
  U.uOpacity.value = V.state.opacity;
}

// ------------------------------------------------------------------ state -> buffers
const catKey = c => String(c);
function primVisible(m) {
  const st = V.state;
  if (st.layers[m.layer] === false) return false;
  if (m.cat != null && st.cats[catKey(m.cat)]?.vis === false) { return false; }
  const e = V.sc.elements[m.eid];
  if (e && e.parent != null && st.cats[catKey(e.parent)]?.vis === false) return false;
  if (m.eid != null && st.elems[m.eid]?.vis === false) return false;
  if (m.cls && st.classes[m.cls] === false) return false;
  if (m.part && st.parts[m.part] === false) return false;
  if (m.hang && st.hideHang) return false;
  if (e && e.typeName && st.types[e.typeName] === false) return false;
  if (m.t === 'text' && !st.textOn) return false;
  return true;
}
function applyStyles() {
  if (!V.group) return;
  const st = V.state, sc = V.sc, B = V.B, dark = matchMedia('(prefers-color-scheme: dark)').matches && !st.paper;
  const colA = V.lines.geometry.attributes.aCol, wA = V.lines.geometry.attributes.aW;
  const vis = B.meta.map(m => primVisible(m));
  const selEid = V.sel;
  const style = (pi) => {
    const m = B.meta[pi], p = sc.prims[pi], s = p.style || {w: 0.18, rgb: [0, 0, 0]};
    const e = sc.elements[m.eid] || {}, co = st.cats[catKey(m.cat)] || {}, po = e.parent != null ? st.cats[catKey(e.parent)] || {} : {}, eo = st.elems[m.eid] || {};
    let c = rgb(s.rgb || p.fill), w = s.w;
    if (s.halftone) c = c.map(x => 0.5 + x * 0.5);
    const ov = eo.color || co.color || po.color;
    if (ov) c = hex2rgb(ov);
    else if (dark && st.contrast && lum(c) < 0.18) c = [0.93, 0.93, 0.93];
    w = w * (eo.wscale ?? co.wscale ?? po.wscale ?? 1);
    if (m.eid === selEid && m.eid != null) c = [1, 0.69, 0.13];
    return {c, w};
  };
  const cache = new Map();
  B.segs.forEach((s, i) => {
    let r = cache.get(s.p); if (!r) { r = style(s.p); cache.set(s.p, r); }
    const v = vis[s.p], hl = B.meta[s.p].eid === selEid && selEid != null;
    for (let k = 0; k < 4; k++) { const o = (i * 4 + k); colA.setXYZW(o, r.c[0], r.c[1], r.c[2], 1); wA.setX(o, v ? r.w * (hl ? 1.8 : 1) : 0); }
  });
  colA.needsUpdate = wA.needsUpdate = true;
  const fA = V.fills.geometry.attributes.aCol;
  B.tris.forEach(t => {
    const m = B.meta[t.p], r = style(t.p), v = vis[t.p]; let c = t.col;
    const e = sc.elements[m.eid] || {}, co = st.cats[catKey(m.cat)] || {}, eo = st.elems[m.eid] || {};
    const fc = eo.fill || co.fill; if (fc) c = hex2rgb(fc);
    const a = !v ? 0 : (m.layer === 'mask' ? 1 : 1);
    for (let i = 0; i < t.n; i++) fA.setXYZW(t.off + i, c[0], c[1], c[2], a);
  });
  fA.needsUpdate = true;
  V.fills.visible = true;
  // text
  V.textObjs.forEach(t => {
    const pi = t.pi, p = sc.prims[pi], m = B.meta[pi], v = vis[pi], e = sc.elements[m.eid] || {}, co = st.cats[catKey(m.cat)] || {}, po = e.parent != null ? st.cats[catKey(e.parent)] || {} : {}, eo = st.elems[m.eid] || {};
    t.obj.visible = v; t.obj.scale.setScalar(st.textSize * (eo.tscale ?? co.tscale ?? po.tscale ?? 1));
    let c = st.textColor || eo.color || co.color || po.color || (dark && st.contrast ? '#eeeeee' : '#000000');
    if (m.eid === selEid && selEid != null) c = '#ffb020';
    t.mesh.material.uniforms.uColor.value.set(...hex2rgb(c)); t.mesh.material.uniforms.uOpacity.value = st.opacity;
  });
  U.uRankMode.value = st.onTop ? 1 : 0;
  if (window.__world) window.__world.visible = !!st.model && !st.paper;
  if (window.__caps) window.__caps.visible = !!st.model && !st.paper;      // section caps are model content too
  if (st.paper) { if (V.prevBg === undefined) V.prevBg = scene.background; scene.background = new THREE.Color(0xffffff); }
  else if (V.prevBg !== undefined) { scene.background = V.prevBg; V.prevBg = undefined; }
  // the view's own grids / levels (extents, heads per view) replace the viewer's whole-model grid and level planes
  const hideNative = st.paper || (st.nativeOff && st.layers.datum !== false && B.layers.includes('datum'));
  if (hideNative && !V.prevNative) V.prevNative = {g: S.gridGroup?.visible, l: S.lvlGroup?.visible};
  if (V.prevNative) { if (S.gridGroup) S.gridGroup.visible = hideNative ? false : V.prevNative.g; if (S.lvlGroup) S.lvlGroup.visible = hideNative ? false : V.prevNative.l; if (!hideNative) V.prevNative = null; }
  // lift along the view normal (metres), crop
  const lift = new THREE.Matrix4().makeTranslation(0, 0, st.lift); V.group.matrix.copy(V.base).multiply(lift); V.group.matrixWorldNeedsUpdate = true;
  const cu = V.cropUV, cropOn = st.crop && cu; U.uCropOn.value = cropOn ? 1 : 0;
  if (cu) crop.value.set(cu[0] * FT, cu[1] * FT, cu[2] * FT, cu[3] * FT);
  dirty();
}

// ------------------------------------------------------------------ picking (2D, in the view plane)
function localPoint(cx, cy) {
  const r = $('#gl').getBoundingClientRect(), ndc = new THREE.Vector2((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
  const rc = new THREE.Raycaster(); rc.setFromCamera(ndc, camera);
  const inv = new THREE.Matrix4().copy(V.group.matrixWorld).invert(), o = rc.ray.origin.clone().applyMatrix4(inv), d = rc.ray.direction.clone().transformDirection(inv);
  if (Math.abs(d.z) < 1e-6) return null;
  const t = -o.z / d.z; if (t < 0) return null;
  const pt = o.addScaledVector(d, t), world = pt.clone().applyMatrix4(V.group.matrixWorld);
  return {u: pt.x, v: pt.y, mPerPx: 2 * camera.position.distanceTo(world) * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / r.height};
}
function hitTest(cx, cy) {
  if (!V.group) return null;
  const lp = localPoint(cx, cy); if (!lp) return null;
  const B = V.B, sc = V.sc, tol = Math.max(5 * lp.mPerPx, 0.002);
  const cu = V.cropUV, cropOn = V.state.crop && cu;
  const inCrop = m => !cropOn || !m.clip || (lp.u >= cu[0] * FT && lp.u <= cu[2] * FT && lp.v >= cu[1] * FT && lp.v <= cu[3] * FT);
  let best = null;
  // text first (labels are what people aim at)
  for (const t of V.textObjs) {
    if (!t.obj.visible) continue; const s = t.obj.scale.x, c = Math.cos(-t.ang), sn = Math.sin(-t.ang);
    const dx = lp.u - t.obj.position.x, dy = lp.v - t.obj.position.y, x = (dx * c - dy * sn) / s - t.ox, y = (dx * sn + dy * c) / s - t.oy;
    if (Math.abs(x) <= t.w / 2 + tol / s && Math.abs(y) <= t.h / 2 + tol / s) { const d = 0; if (!best || d < best.d) best = {d, pi: t.pi, kind: 'text'}; }
  }
  if (best) return finishHit(best);
  const wA = V.lines.geometry.attributes.aW;
  for (let i = 0; i < B.segs.length; i++) {
    if (wA.getX(i * 4) <= 0) continue; const s = B.segs[i], m = B.meta[s.p]; if (!inCrop(m)) continue;
    const ax = s.a[0], ay = s.a[1], bx = s.b[0], by = s.b[1], dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
    const t = L2 ? Math.max(0, Math.min(1, ((lp.u - ax) * dx + (lp.v - ay) * dy) / L2)) : 0, d = Math.hypot(lp.u - (ax + t * dx), lp.v - (ay + t * dy));
    if (d <= tol && (!best || d < best.d)) best = {d, pi: s.p, kind: 'line'};
  }
  if (!best) {
    for (const t of B.tris) {
      const m = B.meta[t.p]; if (m.layer === 'mask' || !inCrop(m) || V.fills.geometry.attributes.aCol.getW(t.off) <= 0) continue;
      for (let k = 0; k < t.xy.length; k += 6) {
        const a = [t.xy[k], t.xy[k + 1]], b = [t.xy[k + 2], t.xy[k + 3]], c = [t.xy[k + 4], t.xy[k + 5]];
        const d1 = (lp.u - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (lp.v - b[1]), d2 = (lp.u - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (lp.v - c[1]), d3 = (lp.u - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (lp.v - a[1]);
        if (!((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0))) { best = {d: tol, pi: t.p, kind: 'fill'}; break; }
      }
      if (best) break;
    }
  }
  return best ? finishHit(best) : null;
}
function finishHit(h) { const m = V.B.meta[h.pi], p = V.sc.prims[h.pi], e = V.sc.elements[m.eid] || {}; return {...h, eid: m.eid, meta: m, prim: p, el: e}; }

// ------------------------------------------------------------------ interaction
let down = null;
const cv = $('#gl');
cv.addEventListener('pointerdown', e => { down = {x: e.clientX, y: e.clientY}; }, true);
cv.addEventListener('pointerup', e => {
  const d = down; down = null; if (!d || !V.group || !V.on || e.button !== 0 || S.measure || Math.hypot(e.clientX - d.x, e.clientY - d.y) > 4) return;
  const h = hitTest(e.clientX, e.clientY);
  if (!h || h.eid == null) { if (V.sel != null) { V.sel = null; applyStyles(); showPicked(null); } return; }
  e.stopImmediatePropagation(); e.preventDefault();
  V.sel = h.eid; applyStyles(); showPicked(h);
  const idx = elementIndex(h.eid); if (idx != null && window.selectEl) window.selectEl(idx, e.ctrlKey || e.shiftKey);
}, true);
let hoverT = 0;
cv.addEventListener('pointermove', e => {
  if (!V.group || !V.on || down) return; const now = performance.now(); if (now - hoverT < 90) return; hoverT = now;
  const h = hitTest(e.clientX, e.clientY), tip = $('#tip');
  if (h && h.eid != null && (h.kind !== 'fill')) {
    e.stopImmediatePropagation();
    const r = cv.getBoundingClientRect(); tip.style.display = 'block'; tip.style.left = (e.clientX - r.left + 14) + 'px'; tip.style.top = (e.clientY - r.top + 14) + 'px';
    const txt = h.prim.t === 'text' ? `<br>"${esc(String(h.prim.text).slice(0, 60))}"` : '';
    tip.innerHTML = `<b>${esc(h.el.catName || h.el.cls || 'element')}</b>${h.el.parentName ? ' / ' + esc(h.el.parentName) : ''}${txt}<br><span class="dim">${esc(h.el.cls || '')} &middot; id ${h.eid} &middot; ${esc(h.meta.layer)}</span>`;
  }
}, true);
let idxMap = null;
function elementIndex(eid) {
  if (!idxMap || idxMap.mid !== V.mid) { idxMap = new Map(); idxMap.mid = V.mid; (S.meta.elements || []).forEach((r, i) => idxMap.set(r[0], i)); }
  return idxMap.get(Number(eid));
}
// Revit's resolved graphics (V/G: view template, filters, overrides) of the picked element, from the sheets vg.json (c3-vg); silently absent when the route is missing
const vgCache = new Map();
function getVG(vid, full) {
  const k = `${V.mid}:${vid}:${full ? 1 : 0}`; if (!vgCache.has(k)) vgCache.set(k, fetch(`/api/m/${V.mid}/vc/vg/${vid}${full ? '?full=1' : ''}`).then(r => r.ok ? r.json() : null).catch(() => null));
  return vgCache.get(k);
}
async function vgInfo(h) {
  const vg = await getVG(V.vid); if (!vg || !vg.styles) return '';
  const ov = vg.elements && vg.elements[h.eid], cat = h.meta.cat;
  const idx = ov != null ? (typeof ov === 'object' ? ov.style : ov) : (vg.cat_style && vg.cat_style[cat] != null ? vg.cat_style[cat] : vg.plain_style), s = vg.styles[idx || 0]; if (!s) return '';
  const col = c => c ? `rgb(${c.join(',')})` : '#000', line = (n, l) => l ? `${n} <span style="display:inline-block;width:10px;height:10px;background:${col(l.rgb)};border:1px solid #888;vertical-align:-1px"></span> ${(+l.w).toFixed(2)} mm${l.dash ? ' dashed' : ''}${l.halftone ? ' halftone' : ''}` : '';
  const pat = f => f && f.pattern != null ? `${esc((vg.fill_patterns[f.pattern] || {}).name || 'pattern ' + f.pattern)}` : '';
  const rows = [line('projection', s.proj), line('cut', s.cut), s.transparency ? `transparency ${s.transparency} %` : '', pat(s.surf_fg) ? 'surface ' + pat(s.surf_fg) : '', pat(s.cut_fg) ? 'cut fill ' + pat(s.cut_fg) : ''].filter(Boolean);
  const hid = (vg.hidden_categories || []).includes(cat) ? ' <b>(category hidden in Revit)</b>' : '';
  let src = '';
  if (ov != null) {      // which filter / category / phase produced each overridden member (full report, fetched only for overridden elements)
    const fv = await getVG(V.vid, true), m = fv && fv.elements_src && fv.elements_src[h.eid];
    if (m) { const fname = id => ((fv.filters || []).find(f => String(f.id) === String(id)) || {}).name;
      src = '<br>' + Object.entries(m).map(([mem, from]) => { const [kind, id] = String(from).split(':'); return `${esc(mem.replace(/_/g, ' '))}: ${kind === 'filter' ? 'filter <b>' + esc(fname(id) || id) + '</b>' : esc(kind === 'category' ? 'category ' + ((vg.categories || {})[id] || {}).name : from)}`; }).join('<br>'); }
  }
  return `<details open><summary>Revit graphics (V/G)${ov != null ? ' - element override' : ''}${hid}</summary><div class="dim" style="line-height:1.6">${rows.join('<br>')}${src}${vg.template ? '<br>view template: ' + esc(vg.template.name) : ''}</div></details>`;
}
async function showPicked(h) {
  const box = $('#vcPicked'); if (!box) return;
  if (!h) { box.innerHTML = '<span class="dim">click a drawn element</span>'; return; }
  const e = h.el, p = h.prim;
  box.innerHTML = `<b>${esc(e.catName || '?')}</b>${e.parentName ? ' <span class="dim">/ ' + esc(e.parentName) + '</span>' : ''}<br>${esc(e.cls || '')} &middot; id ${h.eid} &middot; layer ${esc(h.meta.layer)}${e.typeName ? '<br>type: <b>' + esc((e.familyName ? e.familyName + ' : ' : '') + e.typeName) + '</b>' : ''}${e.levelName ? ' &middot; level ' + esc(e.levelName) : ''}${e.hostId ? ' &middot; <a href="#" id="vcHost">tagged element ' + e.hostId + '</a>' : ''}${e.text && p.t !== 'text' ? '<br>text: ' + esc(e.text) : ''}${p.t === 'text' ? '<br>text: <b>' + esc(p.text) + '</b> (' + (p.size * 12).toFixed(2) + ' in, ' + esc(p.font || '') + ')' : ''}
    <div class="vcbtns"><button id="vcHideEl">hide element</button><button id="vcHideCat">hide category</button><button id="vcIsoCat">only this category</button><button id="vcHideCls">hide ${esc(e.cls || 'type')}</button></div><div id="vcRaw" class="dim">...</div>`;
  const hl = $('#vcHost'); if (hl) hl.onclick = ev => { ev.preventDefault(); const i = elementIndex(e.hostId); if (i != null && window.selectEl) window.selectEl(i); };
  const pe = Object.entries(e.params || {}).filter(([k, v]) => !/\|ElementId$|^(Family|Type|Family and Type|Type Id)$/.test(k) || typeof v !== 'number');
  if (pe.length) { const rows = pe.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="mono">${esc(typeof v === 'number' ? +v.toFixed(5) : v)}</td></tr>`).join(''); box.insertAdjacentHTML('beforeend', `<details open><summary>parameters (${pe.length})</summary><table class="kv">${rows}</table></details>`); }
  vgInfo(h).then(html => { if (html && V.sel === h.eid) box.insertAdjacentHTML('beforeend', html); });
  $('#vcHideEl').onclick = () => { (V.state.elems[h.eid] ||= {}).vis = false; V.sel = null; applyStyles(); renderTree(); };
  $('#vcHideCat').onclick = () => { (V.state.cats[catKey(h.meta.cat)] ||= {}).vis = false; applyStyles(); renderTree(); };
  $('#vcIsoCat').onclick = () => { for (const k of Object.keys(V.sc.elements)) { const c = V.sc.elements[k].cat; (V.state.cats[catKey(c)] ||= {}).vis = c === h.meta.cat; } applyStyles(); renderTree(); };
  $('#vcHideCls').onclick = () => { V.state.classes[e.cls] = false; applyStyles(); renderTree(); };
  try {
    const j = await (await fetch(`/api/m/${V.mid}/vc/element/${h.eid}`)).json(); if (V.sel !== h.eid) return;
    const rows = Object.entries(j.props || {}).slice(0, 80).map(([k, v]) => `<tr><td>${esc(k.replace(/^m_/, ''))}</td><td class="mono">${esc(typeof v === 'number' ? +v.toFixed(5) : v)}</td></tr>`).join('');
    $('#vcRaw').innerHTML = `<details><summary>stored fields (${Object.keys(j.props || {}).length})</summary><table class="kv">${rows}</table></details>`;
  } catch (er) { const r = $('#vcRaw'); if (r) r.textContent = ''; }
}

// ------------------------------------------------------------------ scene loading
const viewQuery = () => { const s = V.state, q = new URLSearchParams(); if (s.scale) q.set('scale', s.scale); if (s.detail) q.set('detail', s.detail); if (s.cut != null) q.set('cut', s.cut / FT); if (s.phase) q.set('phase', s.phase); if (s.pfilter) q.set('phaseFilter', s.pfilter); if (!s.template) q.set('template', 0); if (!s.filters) q.set('filters', 0); return q.toString(); };
// drafting / legend: look straight down at the drawing and fit it
function frameFlat() {
  const cam = window.__camera, ctl = window.__controls; if (!cam || !ctl || !V.B.segs.length) return;
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const s of V.B.segs) for (const q of [s.a, s.b]) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); }
  const c = new THREE.Vector3((x0 + x1) / 2, (y0 + y1) / 2, 0).applyMatrix4(V.base), w = Math.max(x1 - x0, 1e-3), h = Math.max(y1 - y0, 1e-3);
  const t = Math.tan(cam.fov * Math.PI / 360), d = 1.15 * Math.max(h / (2 * t), w / (2 * t * (cam.aspect || 1.5)));
  ctl.target.copy(c); cam.position.set(c.x, c.y + d, c.z + 1e-3 * d); cam.near = Math.min(cam.near, d / 1000); cam.updateProjectionMatrix(); ctl.update();
}
async function loadScene(vid, refresh = false) {
  V.loading = true; setStatus(`loading view ${vid}...`);
  try {
    const r = await fetch(`/api/m/${V.mid}/vc/scene/${vid}?${viewQuery()}${refresh ? '&refresh=1' : ''}`);
    const sc = await r.json(); if (sc.error) throw new Error(sc.error);
    V.stale = r.headers.get('X-Vc-Stale') === '1'; V.vid = vid; makeScene(sc); if (/^(drafting|legend)$/.test(sc.view.kind)) frameFlat(); renderPanel(); loadGhosts();
    setStatus(`${sc.view.name}: ${sc.prims.length} primitives, 1:${sc.view.scale} (${sc.seconds}s)`);
  } catch (e) { setStatus('view control: ' + e.message); }
  V.loading = false;
}
function setStatus(t) { const s = $('#vcStatus'); if (s) s.textContent = t; }
function stateKey() { return `vctl:${V.mid}:${V.vid}`; }
function saveLocal() { try { localStorage[stateKey()] = JSON.stringify(V.state); } catch (e) {} }

async function openVC(vid, preset) {
  if (preset) V.state = Object.assign(DEFAULT_STATE(), JSON.parse(JSON.stringify(preset)));
  if (preset && preset.style) vsSet(preset.style.id, preset.style.opts, true);
  else if (V.vid !== vid) {
    try { const j = localStorage[`vctl:${V.mid}:${vid}`]; V.state = Object.assign(DEFAULT_STATE(), j ? JSON.parse(j) : {}); } catch (e) { V.state = DEFAULT_STATE(); }
    // drafting / legend views have no model position: show them as a white sheet by default
    const vk = (V.views.find(v => v.id === vid) || {}).kind; if (/^(drafting|legend)$/.test(vk) && !(localStorage[`vctl:${V.mid}:${vid}`] || '').includes('"paper"')) V.state.paper = true;
  }
  const mv = (S.meta.views || []).find(x => x.id === vid); if (mv && window.openView) window.openView(mv);
  await loadScene(vid);
}

// ------------------------------------------------------------------ panel
function injectCss() {
  const st = document.createElement('style'); st.textContent = `
#vcpanel{position:absolute;right:8px;top:8px;width:330px;max-height:calc(100% - 60px);overflow:auto;overflow-x:hidden;background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 10px;font-size:12px;z-index:30;box-shadow:0 4px 18px #0006}
#vcpanel h4{margin:9px 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--dim);display:flex;flex-wrap:wrap;align-items:center;gap:6px}
#vcpanel h4 .sp{flex:1}
#vcpanel .r{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin:2px 0}#vcpanel .r label{color:var(--dim);min-width:84px}
#vcpanel select,#vcpanel input[type=number],#vcpanel input[type=text]{background:var(--panel2);color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:2px 4px;font:inherit}
#vcpanel input[type=number]{width:62px}#vcpanel input[type=color]{width:24px;height:18px;padding:0;border:1px solid var(--line);background:none}
#vcpanel .vcbtns{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}#vcpanel button{padding:2px 7px;font-size:11px}
#vcpanel .vctree{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:4px;padding:2px}
#vcpanel .vcrow{display:flex;align-items:center;gap:4px;padding:1px 2px;white-space:nowrap}#vcpanel .vcrow:hover{background:var(--panel2)}#vcpanel .vcrow .nm{flex:1;overflow:hidden;text-overflow:ellipsis}
#vcpanel .vcrow.sel{background:#ffb02033}#vcpanel .ind{margin-left:14px}#vcpanel .cnt{color:var(--dim);font-size:11px}
#vcStatus{color:var(--dim);margin-top:6px}`; document.head.appendChild(st);
}
const rowOf = (key, label, o) => `<div class="vcrow" data-k="${esc(key)}"><input type="checkbox" ${o.vis !== false ? 'checked' : ''} data-a="vis"><span class="nm" title="${esc(label)}">${esc(label)}</span>
  <span class="cnt">${o.n ?? ''}</span><input type="color" value="${o.color || '#000000'}" data-a="color" title="override colour"><input type="number" step="0.25" min="0" value="${o.wscale ?? 1}" data-a="wscale" title="line weight multiplier" style="width:46px"><input type="number" step="0.25" min="0.1" value="${o.tscale ?? 1}" data-a="tscale" title="text size multiplier (this category)" style="width:42px"><select data-a="dash" title="line pattern override" style="width:44px;font-size:10px"><option value="">pat</option>${Object.keys(PATTERNS).map(k => `<option ${o.dash === k ? 'selected' : ''}>${k}</option>`).join('')}</select><span data-a="reset" title="reset overrides" style="cursor:pointer">&#8634;</span></div>`;

function renderTree() {
  const box = $('#vcTree'); if (!box || !V.sc) return;
  const mode = V.treeMode || 'cat', sc = V.sc, st = V.state, counts = {}, perEl = {};
  const eNames = {};
  sc.prims.forEach(p => { if (p.elem != null) { perEl[p.elem] = (perEl[p.elem] || 0) + 1; } });
  let html = '';
  if (mode === 'layer') {
    const cnt = {}; sc.prims.forEach(p => cnt[p.layer || 'x'] = (cnt[p.layer || 'x'] || 0) + 1);
    html = Object.keys(cnt).sort().map(l => `<div class="vcrow" data-l="${l}"><input type="checkbox" ${st.layers[l] !== false ? 'checked' : ''} data-a="layer"><span class="nm">${esc(LAYER_LABEL[l] || l)}</span><span class="cnt">${cnt[l]}</span></div>`).join('');
  } else if (mode === 'cat') {
    const cats = {};   // category id -> {name, parent, elems:Set}
    for (const [eid, e] of Object.entries(sc.elements)) { const k = e.cat; if (k == null) continue; (cats[k] ||= {name: e.catName, parent: e.parent, parentName: e.parentName, elems: [], cls: new Set()}).elems.push(eid); cats[k].cls.add(e.cls); }
    const top = {};
    for (const [k, c] of Object.entries(cats)) { const pk = c.parent != null ? c.parent : k; (top[pk] ||= {name: c.parent != null ? c.parentName : c.name, subs: []}).subs.push([k, c]); }
    html = Object.entries(top).sort((a, b) => String(a[1].name).localeCompare(String(b[1].name))).map(([pk, t]) => {
      const n = t.subs.reduce((s, [, c]) => s + c.elems.length, 0), o = Object.assign({n}, st.cats[pk] || {});
      let h = rowOf('c' + pk, t.name || '(no category)', o).replace('class="vcrow"', `class="vcrow" data-cat="${pk}"`);
      const subs = t.subs.filter(([k]) => k !== pk || t.subs.length > 1);
      if (subs.length) h += '<div class="ind">' + subs.sort((a, b) => String(a[1].name).localeCompare(String(b[1].name))).map(([k, c]) => rowOf('c' + k, c.name || '(no category)', Object.assign({n: c.elems.length}, st.cats[k] || {})).replace('class="vcrow"', `class="vcrow" data-cat="${k}"`)).join('') + '</div>';
      return h;
    }).join('');
  } else if (mode === 'ftype') {
    const cnt = {}; for (const e of Object.values(sc.elements)) if (e.typeName) cnt[e.typeName] = (cnt[e.typeName] || 0) + 1;
    html = Object.entries(cnt).sort().map(([t, n]) => `<div class="vcrow" data-ft="${esc(t)}"><input type="checkbox" ${st.types[t] !== false ? 'checked' : ''} data-a="ftype"><span class="nm">${esc(t)}</span><span class="cnt">${n}</span></div>`).join('') || '<span class="dim">no family / type names in this view\'s data</span>';
  } else if (mode === 'part') {
    const cnt = {}; sc.prims.forEach(p => cnt[p.part || 'line'] = (cnt[p.part || 'line'] || 0) + 1);
    html = Object.keys(cnt).sort().map(l => `<div class="vcrow" data-part="${esc(l)}"><input type="checkbox" ${st.parts[l] !== false ? 'checked' : ''} data-a="part"><span class="nm">${esc(l)}</span><span class="cnt">${cnt[l]}</span></div>`).join('');
  } else if (mode === 'type') {
    const cls = {}; for (const e of Object.values(sc.elements)) cls[e.cls] = (cls[e.cls] || 0) + 1;
    html = Object.entries(cls).sort().map(([c, n]) => `<div class="vcrow" data-cls="${esc(c)}"><input type="checkbox" ${st.classes[c] !== false ? 'checked' : ''} data-a="cls"><span class="nm">${esc(c)}</span><span class="cnt">${n}</span></div>`).join('');
  } else {      // elements
    const q = ($('#vcQ')?.value || '').toLowerCase();
    const list = Object.entries(sc.elements).filter(([id, e]) => !q || (id + ' ' + e.cls + ' ' + e.catName).toLowerCase().includes(q)).slice(0, 400);
    html = list.map(([id, e]) => `<div class="vcrow ${V.sel == id ? 'sel' : ''}" data-eid="${id}"><input type="checkbox" ${st.elems[id]?.vis !== false ? 'checked' : ''} data-a="el"><span class="nm">${esc(e.cls)} ${id}</span><span class="cnt">${esc(e.catName || '')}</span><input type="color" value="${st.elems[id]?.color || '#000000'}" data-a="elcolor"></div>`).join('');
  }
  box.innerHTML = html || '<span class="dim">nothing in this view</span>';
  box.querySelectorAll('input,select,span[data-a]').forEach(inp => {
    const row = inp.closest('.vcrow'), a = inp.dataset.a, ev = inp.type === 'checkbox' || inp.type === 'color' || inp.type === 'number' || inp.tagName === 'SELECT' ? 'onchange' : 'onclick';
    inp[ev] = () => {
      if (a === 'layer') st.layers[row.dataset.l] = inp.checked;
      else if (a === 'cls') st.classes[row.dataset.cls] = inp.checked;
      else if (a === 'part') st.parts[row.dataset.part] = inp.checked;
      else if (a === 'ftype') st.types[row.dataset.ft] = inp.checked;
      else if (a === 'el') (st.elems[row.dataset.eid] ||= {}).vis = inp.checked;
      else if (a === 'elcolor') (st.elems[row.dataset.eid] ||= {}).color = inp.value;
      else { const k = row.dataset.cat, o = (st.cats[k] ||= {});
        if (a === 'vis') o.vis = inp.checked; else if (a === 'color') o.color = inp.value; else if (a === 'wscale') o.wscale = +inp.value; else if (a === 'tscale') o.tscale = +inp.value || 1; else if (a === 'dash') { o.dash = inp.value; saveLocal(); makeScene(V.sc); return; } else if (a === 'reset') { delete st.cats[k]; renderTree(); } }
      applyStyles(); saveLocal();
    };
  });
  box.querySelectorAll('[data-eid] .nm').forEach(n => n.onclick = () => { const id = n.closest('.vcrow').dataset.eid; V.sel = Number(id); applyStyles(); });
}

async function loadPresets() { try { V.presets = await (await fetch('/api/vc/presets')).json(); } catch (e) { try { V.presets = JSON.parse(localStorage['vctl:presets'] || '{}'); } catch (e2) { V.presets = {}; } } }
async function savePresets() { try { localStorage['vctl:presets'] = JSON.stringify(V.presets); } catch (e) {} try { await fetch('/api/vc/presets', {method: 'PUT', body: JSON.stringify(V.presets), headers: {'Content-Type': 'application/json'}}); } catch (e) {} }

function renderPanel() {
  let p = $('#vcpanel'); if (!p) { p = document.createElement('div'); p.id = 'vcpanel'; $('#view').appendChild(p); }
  p.hidden = !V.on; if (!V.on) return;
  if (!p.style.left) { try { const pos = JSON.parse(localStorage['vctl:pos'] || 'null'); if (pos) { p.style.left = pos[0]; p.style.top = pos[1]; p.style.right = 'auto'; } } catch (e) {} }
  const st = V.state, sc = V.sc, vs = V.views.filter(v => v.drawable && /^(plan|section|drafting|legend)$/.test(v.kind));
  const opt = (v, cur, lab) => `<option value="${v}" ${String(cur) === String(v) ? 'selected' : ''}>${lab}</option>`;
  p.innerHTML = `<div id="vcHead" style="display:flex;align-items:center;cursor:move" title="drag to move the panel"><b>View control</b><span class="sp" style="flex:1"></span><button id="vcOff" title="remove the overlay and close the panel">close</button></div>
  <div class="r"><label>View</label><select id="vcView" style="flex:1;min-width:0"><option value="">select a plan / section...</option>${vs.map(v => opt(v.id, V.vid, `${v.name} (${v.kind}${v.scale ? ' 1:' + v.scale : ''})`)).join('')}</select></div>
  <div class="r" style="${window.vstyle ? '' : 'display:none'}"><label>Visual style</label><select id="vcVS" style="flex:1;min-width:0" title="Revit visual style of the 3D scene (saved per view)">${vsOptions()}</select><button id="vcVSDef" title="use this style for every view that has none saved">default</button></div>
  <h4>Display (re-draws the view)</h4>
  <div class="r"><label>Annotation scale</label><select id="vcScale">${opt('', st.scale || '', 'view default' + (sc ? ' (1:' + (sc.view.scale_stored || sc.view.scale) + ')' : ''))}${SCALES.map(s => opt(s, st.scale, '1:' + s)).join('')}</select></div>
  <div class="r"><label>Detail level</label><select id="vcDetail">${opt('', st.detail || '', 'view default')}${opt(1, st.detail, 'Coarse')}${opt(2, st.detail, 'Medium')}${opt(3, st.detail, 'Fine')}</select></div>
  ${sc && sc.view.range && sc.view.range.cut != null ? `<div class="r"><label>Cut plane (m)</label><input type="number" id="vcCut" step="0.1" value="${st.cut != null ? st.cut : +(sc.view.range.cut * FT).toFixed(3)}" title="absolute elevation of the plan cut plane, metres"> <button id="vcCutReset" title="back to the view range">reset</button></div>` : ''}
  <div class="r"><label>Phase</label><select id="vcPhase" style="max-width:100px"><option value="">view</option>${(V.phases || []).map(x => opt(x.id, st.phase, x.name)).join('')}</select> <select id="vcPF" style="max-width:110px"><option value="">filter: view</option>${(V.phaseFilters || []).map(x => opt(x.id, st.pfilter, x.name)).join('')}</select></div>
  <div class="r"><label>Apply</label><label class="chk"><input type="checkbox" id="vcTpl" ${st.template ? 'checked' : ''}> view template</label><label class="chk"><input type="checkbox" id="vcFil" ${st.filters ? 'checked' : ''}> filters</label></div>
  <h4>Display (instant)</h4>
  <div class="r"><label>Crop region</label><input type="checkbox" id="vcCrop" ${st.crop ? 'checked' : ''}><span class="dim">${sc && sc.view.crop_uv ? 'model content only' : 'no stored crop'}</span></div>
  <div class="r"><label>Text</label><input type="checkbox" id="vcText" ${st.textOn ? 'checked' : ''}> size &times;<input type="number" id="vcTS" step="0.1" min="0.1" value="${st.textSize}"> symbols &times;<input type="number" id="vcAS" step="0.1" min="0.1" value="${st.annoScale}" title="annotation symbol size about their anchor (instant); use Annotation scale for the exact re-draw"> <input type="text" id="vcFont" placeholder="font" value="${esc(st.font)}" style="width:80px"></div>
  <div class="r"><label>Line weight &times;</label><input type="number" id="vcLS" step="0.25" min="0" value="${st.lineScale}"> min px<input type="number" id="vcMP" step="0.5" min="0" value="${st.minPx}"></div>
  <div class="r"><label>Paper look</label><label class="chk" title="white background, no 3D model, black linework: the drawing as printed"><input type="checkbox" id="vcPaper" ${st.paper ? 'checked' : ''}> white sheet, model hidden</label></div>
  <div class="r"><label>Markers</label><label class="chk" title="section / elevation / callout heads that sit outside the model extents"><input type="checkbox" id="vcHang" ${st.hideHang ? 'checked' : ''}> hide far-out heads</label></div>
  <div class="r"><label>3D model</label><input type="checkbox" id="vcModel" ${st.model ? 'checked' : ''}><span class="dim">under the drawing</span> <label class="chk" title="hide the viewer's own whole-model grids and level planes while the view's datums are shown"><input type="checkbox" id="vcNat" ${st.nativeOff ? 'checked' : ''}> own datums off</label></div>
  <div class="r"><label>Also show</label><select id="vcGhost" multiple size="3" style="flex:1;min-width:0" title="other plan / section views drawn faintly at their own position (ctrl-click for several)">${vs.filter(v => v.id !== V.vid).map(v => `<option value="${v.id}" ${st.ghosts.includes(v.id) ? 'selected' : ''}>${esc(v.name)} (${v.kind})</option>`).join('')}</select></div>
  <div class="r"><label>Placement</label><label class="chk"><input type="checkbox" id="vcTop" ${st.onTop ? 'checked' : ''}> on top</label> lift<input type="number" id="vcLift" step="0.05" value="${st.lift}" title="metres along the view normal"> &alpha;<input type="number" id="vcOp" step="0.1" min="0" max="1" value="${st.opacity}"></div>
  <h4>Visibility <span class="sp"></span><span class="chk" style="gap:2px"><button data-m="cat" class="${(V.treeMode || 'cat') === 'cat' ? 'on' : ''}">category</button><button data-m="layer" class="${V.treeMode === 'layer' ? 'on' : ''}">layer</button><button data-m="type" class="${V.treeMode === 'type' ? 'on' : ''}">type</button><button data-m="ftype" class="${V.treeMode === 'ftype' ? 'on' : ''}" title="family type (tag / dimension / note types)">family type</button><button data-m="part" class="${V.treeMode === 'part' ? 'on' : ''}" title="leaders, witness lines, arrows, heads...">part</button><button data-m="el" class="${V.treeMode === 'el' ? 'on' : ''}">element</button></span></h4>
  ${V.treeMode === 'el' ? '<input type="text" id="vcQ" placeholder="filter id / class / category" style="width:100%;margin-bottom:3px">' : ''}
  <div class="vctree" id="vcTree"></div>
  <div class="vcbtns"><button id="vcAllOn">all on</button><button id="vcAnnOff">annotations off</button><button id="vcModelOff">linework off</button><button id="vcResetAll">reset all</button></div>
  <h4>Picked</h4><div id="vcPicked"><span class="dim">click a drawn element</span></div>
  <h4>Presets</h4><div class="r"><select id="vcPre" style="flex:1"><option value="">saved presets</option>${Object.keys(V.presets).sort().map(n => `<option>${esc(n)}</option>`).join('')}</select><button id="vcPreLoad">load</button><button id="vcPreDel">delete</button></div>
  <div class="r"><input type="text" id="vcPreName" placeholder="preset name" style="flex:1"><button id="vcPreSave">save</button><button id="vcExport" title="download this view's settings as JSON">export</button></div>
  <div id="vcStatus">${esc(V.status || '')}</div>${V.stale ? '<div class="dim">drawn by an older drawing-code version (cached) <button id="vcRefresh">redraw now</button></div>' : ''}`;
  const hd = $('#vcHead'); if (hd) hd.onpointerdown = e => { if (e.target.tagName === 'BUTTON') return; const r = p.getBoundingClientRect(), pr = $('#view').getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    hd.setPointerCapture(e.pointerId); hd.onpointermove = m => { p.style.left = Math.max(0, Math.min(pr.width - 60, m.clientX - pr.left - dx)) + 'px'; p.style.top = Math.max(0, Math.min(pr.height - 30, m.clientY - pr.top - dy)) + 'px'; p.style.right = 'auto';
      try { localStorage['vctl:pos'] = JSON.stringify([p.style.left, p.style.top]); } catch (er) {} }; hd.onpointerup = () => { hd.onpointermove = null; }; };
  const on = (id, fn, ev = 'onchange') => { const e = $('#' + id); if (e) e[ev] = fn; };
  on('vcRefresh', () => loadScene(V.vid, true), 'onclick');
  on('vcOff', () => closeVC(), 'onclick');
  on('vcView', e => { const v = +$('#vcView').value; if (v) openVC(v); });
  const redraw = () => { saveLocal(); loadScene(V.vid); };
  on('vcScale', () => { st.scale = +$('#vcScale').value || null; redraw(); });
  on('vcDetail', () => { st.detail = +$('#vcDetail').value || null; redraw(); });
  on('vcCut', () => { st.cut = +$('#vcCut').value; redraw(); });
  on('vcCutReset', () => { st.cut = null; redraw(); }, 'onclick');
  on('vcPhase', () => { st.phase = +$('#vcPhase').value || null; redraw(); });
  on('vcPF', () => { st.pfilter = +$('#vcPF').value || null; redraw(); });
  on('vcGhost', () => { st.ghosts = [...$('#vcGhost').selectedOptions].map(o => +o.value); saveLocal(); loadGhosts(); });
  on('vcTpl', () => { st.template = $('#vcTpl').checked; redraw(); });
  on('vcFil', () => { st.filters = $('#vcFil').checked; redraw(); });
  const inst = (id, fn) => on(id, () => { fn($('#' + id)); saveLocal(); applyStyles(); });
  inst('vcCrop', e => st.crop = e.checked); inst('vcText', e => st.textOn = e.checked); inst('vcTS', e => st.textSize = +e.value || 1); inst('vcFont', e => { st.font = e.value; if (V.sc) makeScene(V.sc); });
  inst('vcPaper', e => st.paper = e.checked); inst('vcHang', e => st.hideHang = e.checked); inst('vcModel', e => st.model = e.checked); inst('vcNat', e => st.nativeOff = e.checked); on('vcAS', () => { st.annoScale = +$('#vcAS').value || 1; saveLocal(); if (V.sc) makeScene(V.sc); }); inst('vcLS', e => st.lineScale = +e.value); inst('vcMP', e => st.minPx = +e.value); inst('vcTop', e => st.onTop = e.checked); inst('vcLift', e => st.lift = +e.value); inst('vcOp', e => st.opacity = +e.value);
  p.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { V.treeMode = b.dataset.m; renderPanel(); });
  on('vcQ', () => renderTree(), 'oninput');
  on('vcAllOn', () => { st.types = {}; st.parts = {}; st.layers = {}; st.cats = {}; st.elems = {}; st.classes = {}; st.textOn = true; applyStyles(); saveLocal(); renderPanel(); }, 'onclick');
  on('vcAnnOff', () => { ['annotation', 'text', 'datum', 'annotation_fill'].forEach(l => st.layers[l] = false); applyStyles(); saveLocal(); renderPanel(); }, 'onclick');
  on('vcModelOff', () => { [...MODEL_LAYERS].forEach(l => st.layers[l] = false); applyStyles(); saveLocal(); renderPanel(); }, 'onclick');
  on('vcResetAll', () => { const keep = {scale: st.scale, detail: st.detail}; V.state = Object.assign(DEFAULT_STATE(), keep); saveLocal(); loadScene(V.vid); }, 'onclick');
  on('vcVS', () => vsSet($('#vcVS').value, undefined, true));
  on('vcVSDef', () => { vsSetDefault(); setStatus('default visual style: ' + vsLabel(vsCur.id)); }, 'onclick');
  on('vcPreSave', async () => { const n = $('#vcPreName').value.trim(); if (!n) return; V.presets[n] = JSON.parse(JSON.stringify(V.state)); V.presets[n].style = {id: vsCur.id, opts: vsCur.opts}; await savePresets(); renderPanel(); }, 'onclick');
  on('vcPreLoad', async () => { const n = $('#vcPre').value; if (!n || !V.presets[n]) return; const needs = JSON.stringify([V.presets[n].scale, V.presets[n].detail, V.presets[n].template, V.presets[n].filters]) !== JSON.stringify([st.scale, st.detail, st.template, st.filters]); V.state = Object.assign(DEFAULT_STATE(), JSON.parse(JSON.stringify(V.presets[n]))); if (V.presets[n].style) vsSet(V.presets[n].style.id, V.presets[n].style.opts, true); saveLocal(); if (needs) await loadScene(V.vid); else { makeScene(V.sc); renderPanel(); } }, 'onclick');
  on('vcPreDel', async () => { const n = $('#vcPre').value; if (!n) return; delete V.presets[n]; await savePresets(); renderPanel(); }, 'onclick');
  on('vcExport', () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify({view: V.vid, state: V.state}, null, 1)], {type: 'application/json'})); a.download = `view-${V.vid}-controls.json`; a.click(); }, 'onclick');
  renderTree();
}
function closeVC() { V.on = false; if (V.prevBg !== undefined) { scene.background = V.prevBg; V.prevBg = undefined; } clearGhosts(); if (V.prevNative) { if (S.gridGroup) S.gridGroup.visible = V.prevNative.g; if (S.lvlGroup) S.lvlGroup.visible = V.prevNative.l; V.prevNative = null; } if (window.__world) window.__world.visible = true; if (window.__caps) window.__caps.visible = true; disposeGroup(); V.sc = null; const p = $('#vcpanel'); if (p) p.hidden = true; $('#bVC')?.classList.remove('on'); dirty(); }

// ------------------------------------------------------------------ entry
async function toggle() {
  if (V.on) { closeVC(); return; }
  V.on = true; $('#bVC').classList.add('on'); V.mid = S.mid; idxMap = null;
  if (!document.getElementById('vcStyle')) { injectCss(); }
  await loadPresets();
  try { const j = await (await fetch(`/api/m/${V.mid}/vc/views`)).json(); V.views = j.views || []; V.phases = j.phases || []; V.phaseFilters = j.phaseFilters || []; } catch (e) { V.views = []; }
  renderPanel();
  const cur = S.openView && V.views.find(v => v.id === S.openView.id && v.drawable && /^(plan|section|drafting|legend)$/.test(v.kind));
  if (cur) openVC(cur.id);
}
const btn = document.createElement('button'); btn.id = 'bVC'; btn.textContent = 'Annotations'; btn.title = 'View-dependent elements: tags, text, dimensions, grids, hatches - per view / category / element controls';
btn.onclick = toggle; $('#navSel').before(btn);      // left end of the right-hand buttons: stays visible in a narrow window
// ------------------------------------------------------------------ visual style (selector, per-view autosave, default; contract: docs/VSTYLE-API.md)
// c3-viewer implements window.vstyle (list / get / set + 'vstylechange'); this part stores and restores the choice and drives the selectors.
const VS_FALLBACK = [{id: 'hiddenline', label: 'Hidden line'}, {id: 'shaded', label: 'Shaded'}, {id: 'consistent', label: 'Consistent colors'}, {id: 'realistic', label: 'Realistic'}, {id: 'wireframe', label: 'Wireframe'}];
const vsList = () => { try { const l = window.vstyle && window.vstyle.list && window.vstyle.list(); if (l && l.length) return l; } catch (e) {} return VS_FALLBACK; };
const vsLabel = id => (vsList().find(x => x.id === id) || {label: id}).label;
const vsRead = k => { try { const j = JSON.parse(localStorage[k] || 'null'); return j && j.id ? j : null; } catch (e) { return null; } };
const vsWrite = (k, v) => { try { localStorage[k] = JSON.stringify(v); } catch (e) {} };
const vsViewKey = () => `vstyle:${S.mid || 'x'}:${S.openView ? S.openView.id : 'model'}`;
function vsDefault() {
  const u = new URLSearchParams(location.search).get('vs'); if (u && vsList().some(x => x.id === u)) return {id: u, opts: {}};
  return vsRead('vstyle:default') || {id: (window.vstyle && window.vstyle.defaultId) || 'hiddenline', opts: {}};
}
let vsCur = vsDefault(), vsKey = null;
const vsOptions = () => vsList().map(x => `<option value="${x.id}" ${x.id === vsCur.id ? 'selected' : ''}>${esc(x.label)}</option>`).join('');
function vsSync() { document.querySelectorAll('#vsSel,#vcVS').forEach(s => { if (s.value !== vsCur.id) s.value = vsCur.id; }); }
function vsSet(id, opts, save) {
  if (!id) return; vsCur = {id, opts: opts || (vsCur.id === id ? vsCur.opts : {})};
  try { if (window.vstyle && window.vstyle.set) window.vstyle.set(vsCur.id, vsCur.opts); } catch (e) { console.warn('vstyle.set', e); }
  vsSync(); if (save) vsWrite(vsViewKey(), vsCur);
}
function vsSetDefault() { vsWrite('vstyle:default', vsCur); }
// opening / closing a view (also from the Views tab) switches to that view's saved style, else the default
let vsHad = false;
setInterval(() => {
  const vs = document.getElementById('vsSel'); if (vs) vs.style.display = window.vstyle ? '' : 'none';
  const k = vsViewKey(), first = !!window.vstyle && !vsHad; if (window.vstyle) vsHad = true;
  if (k === vsKey && !first) return; vsKey = k; const st = vsRead(k) || vsDefault(); vsSet(st.id, st.opts);
}, 400);
window.addEventListener('vstylechange', e => { const d = e.detail; if (d && d.id && d.id !== vsCur.id) { vsCur = {id: d.id, opts: d.opts || {}}; vsSync(); vsWrite(vsViewKey(), vsCur); } });
{ const sel = document.createElement('select'); sel.id = 'vsSel'; sel.title = 'Visual style (Revit): saved per view, "default" in the View control panel sets the style for new views';
  sel.innerHTML = vsOptions(); sel.style.display = 'none'; sel.onchange = () => vsSet(sel.value, undefined, true); $('#navSel').before(sel); }
setTimeout(() => { vsKey = null; }, 0);

window.vctl = {vg: getVG, vstyle: {get: () => vsCur, set: vsSet, setDefault: vsSetDefault}, rebuild: () => V.sc && makeScene(V.sc), loadGhosts, state: () => V.state, V, openView: openVC, toggle, apply: applyStyles, set: patch => { Object.assign(V.state, patch); applyStyles(); }, pick: hitTest};
// switching model closes the overlay
setInterval(() => { if (V.on && V.mid !== S.mid) { closeVC(); } }, 1000);

// ?vc=VIEWID[&vcp=PRESET] opens the panel on that view (demo scripting / shareable link)
(async () => {
  const q = new URLSearchParams(location.search), vid = +q.get('vc'); if (!vid) return;
  for (let k = 0; k < 200 && !(window.__loaded && S.meta && S.meta.phase); k++) await new Promise(r => setTimeout(r, 300));
  await toggle(); const pn = q.get('vcp');
  await openVC(vid, pn && V.presets[pn] ? V.presets[pn] : null);
})();

// Views tab: an 'annotations' link on every plan / section row opens the view with its view-dependent elements
new MutationObserver(() => {
  document.querySelectorAll('#tabbody [data-vk]:not([data-vc])').forEach(row => {
    row.dataset.vc = 1; const v = (S.meta.views || [])[+row.dataset.vk];
    if (!v || !v.origin || !/^(plan|section|elevation)$/i.test(v.kind || '') || !row.firstElementChild) return;
    const a = document.createElement('a'); a.href = '#'; a.className = 'drawlink'; a.textContent = 'annotations'; a.title = 'open with the view-dependent elements (tags, text, grids...) and the view control panel';
    a.style.marginLeft = '6px'; a.onclick = async e => { e.preventDefault(); e.stopPropagation(); if (!V.on) await toggle(); openVC(v.id); };
    row.firstElementChild.appendChild(a);
  });
}).observe($('#tabbody'), {childList: true, subtree: true});
