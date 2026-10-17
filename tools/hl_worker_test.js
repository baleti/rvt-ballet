// node tools/hl_worker_test.js : runs the edge worker of web/hl.js on a cube (12 edges, no diagonals) and a cylinder (silhouette candidates)
const s = require('fs').readFileSync(__dirname + '/../web/hl.js', 'utf8'); const src = s.match(/const WORKER_SRC = `([\s\S]*?)`;/)[1];
function run(pos, index, eidx) { let out; const self = {postMessage: o => out = o}; new Function('self', src)(self); self.onmessage({data: {pos, index, eidx, thr: 30, id: 1}}); return out; }
const P = [0,0,0, 1,0,0, 1,1,0, 0,1,0, 0,0,1, 1,0,1, 1,1,1, 0,1,1], F = [0,2,1, 0,3,2, 4,5,6, 4,6,7, 0,1,5, 0,5,4, 1,2,6, 1,6,5, 2,3,7, 2,7,6, 3,0,4, 3,4,7];
let r = run(new Float32Array(P), new Uint32Array(F), new Float32Array(8)); console.log('cube edges', r.pos.length / 6, '(expect 12)'); if (r.pos.length / 6 !== 12) process.exit(1);
const N = 32, pp = [], ff = []; for (let i = 0; i < N; i++) { const a = i / N * 2 * Math.PI; pp.push(Math.cos(a), Math.sin(a), 0, Math.cos(a), Math.sin(a), 1); }
for (let i = 0; i < N; i++) { const j = (i + 1) % N; ff.push(2*i, 2*j, 2*i+1, 2*j, 2*j+1, 2*i+1); }
r = run(new Float32Array(pp), new Uint32Array(ff), new Float32Array(2 * N)); const sil = Array.from(r.kind).filter(k => k === 1).length / 2; console.log('cylinder: edges', r.pos.length / 6, 'silhouette candidates', sil, '(expect 32 side lines + 64 rims boundary)'); if (sil !== N) process.exit(1);
console.log('HL-WORKER-TEST OK');
