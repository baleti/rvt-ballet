import test from 'node:test';
import assert from 'node:assert/strict';
import { clipSegment, cutSegments } from '../../web/cutsegs.js';

const cube = (s = 1) => {
  const pos = [0,0,0, s,0,0, s,s,0, 0,s,0, 0,0,s, s,0,s, s,s,s, 0,s,s];
  const index = [0,2,1, 0,3,2, 4,5,6, 4,6,7, 0,1,5, 0,5,4, 1,2,6, 1,6,5, 2,3,7, 2,7,6, 3,0,4, 3,4,7];
  return { pos: new Float32Array(pos), index: new Uint32Array(index) };
};
const len = (a) => { let t = 0; for (let i = 0; i < a.length; i += 6) t += Math.hypot(a[i+3]-a[i], a[i+4]-a[i+1], a[i+5]-a[i+2]); return t; };
const near = (a, b, e = 1e-5) => assert.ok(Math.abs(a - b) < e, `${a} vs ${b}`);

test('clipSegment: no planes returns the segment', () => {
  assert.deepEqual(clipSegment([0,0,0], [1,2,3], []), [0,0,0,1,2,3]);
});
test('clipSegment: fully inside / fully outside', () => {
  const pl = [{ nx: 1, ny: 0, nz: 0, c: 0 }];
  assert.deepEqual(clipSegment([1,0,0], [2,0,0], pl), [1,0,0,2,0,0]);
  assert.equal(clipSegment([-2,0,0], [-1,5,5], pl), null);
});
test('clipSegment: crossing plane keeps the inside part, either direction', () => {
  const pl = [{ nx: 1, ny: 0, nz: 0, c: 0 }];
  let r = clipSegment([-1,0,0], [3,0,0], pl); assert.ok(r); near(r[0], 0); near(r[3], 3);
  r = clipSegment([3,0,0], [-1,0,0], pl); assert.ok(r); near(r[0], 3); near(r[3], 0);
});
test('clipSegment: two planes and degenerate result', () => {
  const pls = [{ nx: 1, ny: 0, nz: 0, c: 0 }, { nx: -1, ny: 0, nz: 0, c: 2 }];
  const r = clipSegment([-5,1,1], [9,1,1], pls); assert.ok(r); near(r[0], 0); near(r[3], 2); near(r[1], 1);
  assert.equal(clipSegment([-1,0,0], [0,0,0], [{ nx: 1, ny: 0, nz: 0, c: 0 }]), null, 'touching point only');
});

test('cube cut at z=0.5: perimeter of the unit square', () => {
  const out = cutSegments([cube()], { nx: 0, ny: 0, nz: 1, c: -0.5 });
  assert.ok(out instanceof Float32Array); assert.equal(out.length % 6, 0);
  near(len(out), 4);
  for (let i = 0; i < out.length; i += 3) near(out[i + 2], 0.5);
});
test('scaled and translated through the matrix', () => {
  const m = [2,0,0,0, 0,2,0,0, 0,0,2,0, 10,0,0,1];      // scale 2, move x by 10
  const out = cutSegments([{ ...cube(), matrix: m }], { nx: 0, ny: 0, nz: 1, c: -1 });
  near(len(out), 8);
  for (let i = 0; i < out.length; i += 3) { assert.ok(out[i] >= 10 - 1e-5 && out[i] <= 12 + 1e-5); near(out[i + 2], 1); }
});
test('plane that misses the model', () => {
  assert.equal(cutSegments([cube()], { nx: 0, ny: 0, nz: 1, c: -5 }).length, 0);
});
test('non-indexed triangles', () => {
  const pos = new Float32Array([0,0,-1, 1,0,1, 0,1,1]);
  const out = cutSegments([{ pos }], { nx: 0, ny: 0, nz: 1, c: 0 });
  assert.equal(out.length, 6); near(len(out), Math.hypot(0.5, 0.5));
});
test('accept filter skips triangles', () => {
  const pl = { nx: 0, ny: 0, nz: 1, c: -0.5 };
  const all = cutSegments([cube()], pl);
  const none = cutSegments([{ ...cube(), accept: () => false }], pl);
  assert.equal(none.length, 0);
  const some = cutSegments([{ ...cube(), accept: (t) => t >= 4 }], pl);   // only the side faces (triangles 4..11)
  near(len(some), len(all));
  const sides = cutSegments([{ ...cube(), accept: (t) => t >= 4 && t < 6 }], pl);
  assert.ok(len(sides) > 0 && len(sides) < len(all));
});
test('others clip the outline', () => {
  const out = cutSegments([cube()], { nx: 0, ny: 0, nz: 1, c: -0.5 }, [{ nx: 1, ny: 0, nz: 0, c: -0.5 }]);   // keep x >= 0.5
  for (let i = 0; i < out.length; i += 3) assert.ok(out[i] >= 0.5 - 1e-5);
  near(len(out), 2, 1e-4);
});
test('vertex exactly on the plane counts as the negative side (reference behaviour)', () => {
  // triangle with one vertex at d = 0 and two above: the two edges at that vertex cross, giving a zero-length segment at the vertex
  const pos = new Float32Array([0,0,0, 1,0,1, 0,1,1]);
  near(len(cutSegments([{ pos }], { nx: 0, ny: 0, nz: 1, c: 0 })), 0);
  // a triangle lying in the plane produces nothing
  assert.equal(cutSegments([{ pos: new Float32Array([0,0,0, 1,0,0, 0,1,0]) }], { nx: 0, ny: 0, nz: 1, c: 0 }).length, 0);
});
test('does not mutate inputs and handles several meshes in order', () => {
  const a = cube(), b = { ...cube(), matrix: [1,0,0,0, 0,1,0,0, 0,0,1,0, 5,0,0,1] };
  const posCopy = Array.from(a.pos);
  const out = cutSegments([a, b], { nx: 0, ny: 0, nz: 1, c: -0.5 });
  assert.deepEqual(Array.from(a.pos), posCopy);
  near(len(out), 8);
  assert.ok(out[0] <= 1 + 1e-5, 'first segments come from the first mesh');
  assert.ok(out[out.length - 6] >= 5 - 1e-5, 'last segments come from the second mesh');
});
