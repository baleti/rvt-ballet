// materials: palette texture (colour/alpha, texture class + real-world scale, hash colour) and built-in procedural pattern array (the .rvt stores texture asset PATHS, not the bitmaps)
import * as THREE from 'three';

const CLASSES = ['none', 'brick', 'concrete', 'wood', 'stone', 'metal', 'glass', 'tile', 'plaster', 'grass', 'water', 'roof', 'insulation'];
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
    else if (cls === 'concrete') val = .86 + .28 * fbm(g, N, u * N, v * N, 5) + (r() < .01 ? -.15 : 0);
    else if (cls === 'plaster') val = .95 + .1 * fbm(g, N, u * N, v * N, 3);
    else if (cls === 'wood') { const t = fbm(g, N, u * 3, v * N, 3) * 6 + u * 20; val = .8 + .35 * (Math.sin(t * 3.1) * .5 + .5) * (.8 + .4 * fbm(g2, N, u * N, v * 3, 2)); }
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
// palette: width = number of materials, 3 rows: row0 = rgb colour + alpha, row1 = texture class, real-world tile size (m), 0, 1, row2 = distinct hash colour (colour-by-material mode)
export function paletteTexture(mats) {
  const n = Math.max(1, mats.length), D = new Uint8Array(n * 3 * 4);
  mats.forEach((m, i) => {
    D.set([m.rgb[0] * 255, m.rgb[1] * 255, m.rgb[2] * 255, m.alpha * 255], i * 4);
    const cls = Math.max(0, CLASSES.indexOf(m.tex_class)); const scaleFt = m.tex_scale_ft && m.tex_scale_ft[0] ? m.tex_scale_ft[0] : ({brick: 2.2, concrete: 6, wood: 4, stone: 4, metal: 3, glass: 6, tile: 2, plaster: 8, grass: 4, water: 6, roof: 3, insulation: 3}[m.tex_class] || 4);
    D.set([cls * 16, Math.min(255, scaleFt * .3048 * 20), 0, 255], (n + i) * 4);
    const h = (i * 0.61803398875) % 1, c = hsl(h, .62, .52); D.set([c[0] * 255, c[1] * 255, c[2] * 255, 255], (2 * n + i) * 4);
  });
  const t = new THREE.DataTexture(D, n, 3, THREE.RGBAFormat, THREE.UnsignedByteType); t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t;
}
function hsl(h, s, l) { const a = s * Math.min(l, 1 - l), f = n => { const k = (n + h * 12) % 12; return l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)); }; return [f(0), f(8), f(4)]; }
export { CLASSES, hsl };
