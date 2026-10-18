// materials: palette texture (colour/alpha, texture class + real-world scale, hash colour) and built-in procedural pattern array (the .rvt stores texture asset PATHS, not the bitmaps)
import * as THREE from 'three';

const CLASSES = ['none', 'brick', 'concrete', 'wood', 'stone', 'metal', 'glass', 'tile', 'plaster', 'grass', 'water', 'roof', 'insulation', 'siding', 'carpet'];
const SZ = 128;
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function noiseGrid(n, r) { const g = new Float32Array(n * n); for (let i = 0; i < g.length; i++) g[i] = r(); return g; }
function vnoise(g, n, x, y) { // tileable value noise, x,y in [0,n)
  const x0 = Math.floor(x) % n, y0 = Math.floor(y) % n, x1 = (x0 + 1) % n, y1 = (y0 + 1) % n, fx = x - Math.floor(x), fy = y - Math.floor(y);
  const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  return (g[y0 * n + x0] * (1 - sx) + g[y0 * n + x1] * sx) * (1 - sy) + (g[y1 * n + x0] * (1 - sx) + g[y1 * n + x1] * sx) * sy;
}
function fbm(g, n, x, y, oct = 4) { let s = 0, a = .5, f = 1, tot = 0; for (let o = 0; o < oct; o++) { s += a * vnoise(g, n * f > 64 ? n : n, (x * f) % n, (y * f) % n); tot += a; a *= .5; f *= 2; } return s / tot; }

// every pattern returns brightness multipliers around 1 (stored as 0..255 where 128 = 1.0; shader multiplies by 2*value)
function pattern(cls) {
  const r = rng(CLASSES.indexOf(cls) * 7919 + 13), N = 16, g = noiseGrid(N, r), g2 = noiseGrid(N, r), d = new Uint8Array(SZ * SZ);
  const put = (x, y, v) => { d[y * SZ + x] = Math.max(0, Math.min(255, Math.round(v * 128))); };
  for (let y = 0; y < SZ; y++) for (let x = 0; x < SZ; x++) {
    const u = x / SZ, v = y / SZ; let val = 1;
    if (cls === 'brick') { const rows = 8, row = Math.floor(v * rows), off = (row % 2) * .5, bw = 1 / 4; const bx = ((u + off * bw * 2) % bw) / bw, by = (v * rows) % 1; const mort = (bx < .06 || by < .1) ? 1 : 0; const id = Math.floor((u + off * bw * 2) / bw) + row * 7; const tone = .85 + .3 * ((Math.sin(id * 12.9898) * 43758.5453) % 1 + 1) % 1 * .5; val = mort ? .62 : tone * (.92 + .16 * fbm(g, N, u * N, v * N, 3)); }
    else if (cls === 'siding') { const rows = 8, by = (v * rows) % 1, row = Math.floor(v * rows); val = (by > .9 ? .6 : .82 + .2 * by) * (.96 + .08 * fbm(g, N, u * 2, v * N, 2)) * (.97 + .06 * ((row * 0.618) % 1)); }
    else if (cls === 'carpet') val = .85 + .3 * fbm(g, N, u * N * 2 % N, v * N * 2 % N, 2) * (.7 + .6 * r());
    else if (cls === 'concrete') val = .86 + .28 * fbm(g, N, u * N, v * N, 5) + (r() < .01 ? -.15 : 0);
    else if (cls === 'plaster') val = .95 + .1 * fbm(g, N, u * N, v * N, 3);
    else if (cls === 'wood') { const t = fbm(g, N, u * 2, v * N, 3) * 2.5 + u * 40; val = .86 + .22 * (Math.sin(t * 3.1) * .5 + .5) * (.85 + .3 * fbm(g2, N, u * N, v * 2, 2)); }
    else if (cls === 'stone') { const cx = Math.floor(u * 4), cy = Math.floor(v * 4), id = cx + cy * 4; const bx = (u * 4) % 1, by = (v * 4) % 1; const edge = (bx < .04 || by < .04); val = edge ? .6 : (.8 + .35 * g[id % (N * N)]) * (.92 + .16 * fbm(g2, N, u * N, v * N, 4)); }
    else if (cls === 'metal') val = .88 + .2 * vnoise(g, N, u * 2, v * N) + .05 * Math.sin(v * 220);
    else if (cls === 'glass') val = .96 + .1 * Math.max(0, Math.sin((u + v) * Math.PI * 2) * .5);
    else if (cls === 'tile') { const bx = (u * 4) % 1, by = (v * 4) % 1; val = (bx < .05 || by < .05) ? .55 : .95 + .1 * g[(Math.floor(u * 4) + Math.floor(v * 4) * 4) % (N * N)]; }
    else if (cls === 'grass') val = .7 + .6 * fbm(g, N, u * N, v * N, 5) * (.7 + .6 * r());
    else if (cls === 'water') val = .9 + .2 * (Math.sin((u * 6 + fbm(g, N, u * 4, v * 4, 2) * 3) * Math.PI * 2) * .5 + .5);
    else if (cls === 'roof') { const rows = 10, row = Math.floor(v * rows), by = (v * rows) % 1, tile = Math.floor((u * 6 + (row % 2) * .5)); val = by < .08 ? .55 : (.82 + .3 * ((Math.sin(tile * 78.233 + row * 3.1) * 43758.5453) % 1 + 1) % 1 * .5); }
    else if (cls === 'insulation') val = .85 + .3 * fbm(g, N, u * N * 2 % N, v * N, 3) * (.6 + .8 * r());
    put(x, y, val);
  }
  return d;
}
let patTex = null;
export function patternTexture() {
  if (patTex) return patTex;
  const D = new Uint8Array(SZ * SZ * CLASSES.length);
  CLASSES.forEach((c, k) => D.set(c === 'none' ? new Uint8Array(SZ * SZ).fill(128) : pattern(c), k * SZ * SZ));
  patTex = new THREE.DataArrayTexture(D, SZ, SZ, CLASSES.length); patTex.format = THREE.RedFormat; patTex.type = THREE.UnsignedByteType;
  patTex.wrapS = patTex.wrapT = THREE.RepeatWrapping; patTex.minFilter = THREE.LinearMipmapLinearFilter; patTex.magFilter = THREE.LinearFilter; patTex.generateMipmaps = true; patTex.needsUpdate = true;
  return patTex;
}
// palette (float RGBA, width = number of materials): row0 = rgb colour + alpha, row1 = texture class, real-world tile size x/y (m), angle (rad),
// row2 = distinct hash colour (colour-by-material mode), row3 = image layer (0 = none, n = layer n-1 of imageTextures), offset x/y (m),
// row4 = bump layer (0 = none, n = layer n-1 of bumpTextures), bump tile size x/y (m), relief strength (m), row5 = bump offset x/y (m), bump angle (rad)
const DEF_FT = {brick: 2.2, concrete: 6, wood: 4, stone: 4, metal: 3, glass: 6, tile: 2, plaster: 8, grass: 4, water: 6, roof: 3, insulation: 3, siding: 4, carpet: 3};
export function paletteTexture(mats, layers, blayers) {
  const n = Math.max(1, mats.length), D = new Float32Array(n * 4 * 10);
  mats.forEach((m, i) => {
    D.set([m.rgb[0], m.rgb[1], m.rgb[2], m.alpha], i * 4);
    const cls = Math.max(0, CLASSES.indexOf(m.tex_class)), s = m.tex_scale_ft && m.tex_scale_ft[0] ? m.tex_scale_ft : [DEF_FT[m.tex_class] || 4, DEF_FT[m.tex_class] || 4];
    const mul = m.tex_tile_mul || 1; D.set([cls, s[0] * .3048 * mul, (s[1] || s[0]) * .3048 * mul, (m.tex_angle || 0) * Math.PI / 180], (n + i) * 4);
    const h = (i * 0.61803398875) % 1, c = hsl(h, .62, .52); D.set([c[0], c[1], c[2], 1], (2 * n + i) * 4);
    const o = m.tex_offset_ft || [0, 0]; D.set([layers && layers[i] != null ? layers[i] + 1 : 0, (o[0] || 0) * .3048, (o[1] || 0) * .3048, 0], (3 * n + i) * 4);
    const sp = m.surface_pattern;       // model-space surface pattern (target 1, feet): up to two line grids -> rows 6..9 [angle, spacing m, shift m, 1], [dash m, gap m, origin x m, origin y m]
    if (sp && sp.target === 1 && sp.grids) sp.grids.forEach((g, j) => {
      const sg = (g.segs || []).map(Math.abs), per = sg.length >= 2 ? (sg[0] + sg[1]) * .3048 : 0;
      D.set([g.angle, Math.abs(g.deltas[1]) * .3048, g.deltas[0] * .3048, Math.abs(g.deltas[1]) > 1e-6 ? 1 : 0], (6 * n + 2 * j * n + i) * 4);
      D.set([per ? sg[0] * .3048 : 0, per ? sg[1] * .3048 : 0, g.origin[0] * .3048, g.origin[1] * .3048], ((7 + 2 * j) * n + i) * 4);
    });
    if (blayers && blayers[i] != null) {                 // Revit *_bump_amount (1 = default) -> height scale 0.02 m per unit of the grey map (tuned visually on the 2020 Residential siding / concrete)
      const bs = m.bump_scale_ft && m.bump_scale_ft[0] ? m.bump_scale_ft : s, bo = m.bump_offset_ft || [0, 0], amt = Math.min(4, Math.max(.2, m.bump_amount ?? 1));
      D.set([blayers[i] + 1, bs[0] * .3048 * mul, (bs[1] || bs[0]) * .3048 * mul, .02 * amt], (4 * n + i) * 4);
      D.set([(bo[0] || 0) * .3048, (bo[1] || 0) * .3048, (m.bump_angle || 0) * Math.PI / 180, 0], (5 * n + i) * 4);
    }
  });
  const t = new THREE.DataTexture(D, n, 10, THREE.RGBAFormat, THREE.FloatType); t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t;
}
// image textures (library bitmaps or Revit's flat swatches, 256 px PNGs from /m/<mid>/tex/<k>.png) -> one RGBA DataArrayTexture; returns {tex, layers: {material k: layer}}
const IS = 256;
export async function imageTextures(mid, mats, kind = 'tex') {
  const ks = []; mats.forEach((m, k) => { if (kind === 'tex' ? m.tex_img : m.bump_img) ks.push(k); });
  const layers = {}, D = new Uint8Array(IS * IS * 4 * Math.max(1, ks.length));
  const cv = document.createElement('canvas'); cv.width = cv.height = IS; const g = cv.getContext('2d', {willReadFrequently: true});
  let L = 0;
  for (const k of ks) {
    try {
      const im = new Image(); im.src = `/m/${mid}/${kind}/${k}.png`; await im.decode();
      g.clearRect(0, 0, IS, IS); g.drawImage(im, 0, 0, IS, IS); D.set(g.getImageData(0, 0, IS, IS).data, L * IS * IS * 4); layers[k] = L++;
    } catch (e) { /* missing image: material keeps its colour / procedural pattern */ }
  }
  const t = new THREE.DataArrayTexture(D, IS, IS, Math.max(1, L)); t.format = THREE.RGBAFormat; t.type = THREE.UnsignedByteType; t.colorSpace = kind === 'tex' ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = true; t.needsUpdate = true;
  return {tex: t, layers};
}
function hsl(h, s, l) { const a = s * Math.min(l, 1 - l), f = n => { const k = (n + h * 12) % 12; return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)); }; return [f(0), f(8), f(4)]; }
export { CLASSES, hsl };
