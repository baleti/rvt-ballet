import test from 'node:test';
import assert from 'node:assert/strict';
import { drawsGridsAsVertical, elevGridLines } from '../../web/elevgrids.js';

const near = (a, b, e = 1e-6) => assert.ok(Math.abs(a - b) < e, `${a} vs ${b}`);
// south elevation: dir points to the eye = -y in Revit (eye south of the model, looking north), origin on the cut plane y = -15
const south = { kind: 'Section', dir: [0, -1, 0], origin: [-12, -15, 0] };
const grids = [
  { name: '1', pts: [[-30, -16, -8], [-30, 22, -8]] },       // runs along y: seen edge-on
  { name: '2', pts: [[-20, -16, -8], [-20, 22, -8]] },
  { name: 'A', pts: [[-40, 5, -5], [28, 5, -5]] },           // runs along x: perpendicular to the view, not drawn
  { name: '9', pts: [[17.6, 21.8, -5.5], [22.6, -15.7, -5.5]] },   // slightly slanted (cos about 0.99): drawn
];

test('which views draw vertical grids', () => {
  assert.equal(drawsGridsAsVertical(south), true);
  assert.equal(drawsGridsAsVertical({ kind: '3d', dir: [0, -1, 0] }), false);
  assert.equal(drawsGridsAsVertical({ kind: 'Plan', dir: [0, 0, 1] }), false);
  assert.equal(drawsGridsAsVertical({ kind: 'Section' }), false);
  assert.equal(drawsGridsAsVertical(null), false);
  assert.equal(drawsGridsAsVertical(undefined), false);
});
test('perpendicular grids are skipped, along-view grids kept in input order', () => {
  const r = elevGridLines(grids, south, [-5, 0, 10], -13);
  assert.deepEqual(r.map(g => g.name), ['1', '2', '9']);
});
test('lateral position: world x of the grid, z 0.3 m behind the cut plane', () => {
  const r = elevGridLines(grids, south, [0], -1);
  // toV: world z = -revit y; cut plane at revit y = -15 -> world z = 15; behind (away from the eye, the eye is at +z) -> 15 - 0.3
  near(r[0].x, -30); near(r[0].z, 14.7);
  near(r[1].x, -20); near(r[1].z, 14.7);
  assert.ok(Math.abs(r[2].x - 17.6) < 1e-6, 'slanted grid keeps the x of its first point projected along the view direction');
  near(r[2].z, 14.7);
});
test('vertical extent from levels and model bottom', () => {
  const r = elevGridLines(grids, south, [-5, 0, 10], -13);
  const y0 = -13, top = 10, y1 = top + (top - y0) * 0.12 + 1;
  for (const g of r) { near(g.y0, y0); near(g.y1, y1); }
  const r2 = elevGridLines(grids, south, [], 2);       // no levels: only the model bottom
  near(r2[0].y0, 2); near(r2[0].y1, 2 + 0 + 1);
  const r3 = elevGridLines(grids, south, [-30, 40], 0);
  near(r3[0].y0, -30); near(r3[0].y1, 40 + 70 * 0.12 + 1);
});
test('east-looking elevation: grids along x are the edge-on ones', () => {
  const east = { kind: 'Section', dir: [1, 0, 0], origin: [30, 0, 0] };      // eye east of the model: dir points to the eye
  const r = elevGridLines(grids, east, [0], 0);
  assert.deepEqual(r.map(g => g.name), ['A']);
  // world x of the cut plane is 30; behind it (away from the eye, towards -x) is 29.7; world z of grid A is -5
  near(r[0].x, 29.7); near(r[0].z, -5);
});
test('no grids, non-drawing view, and no mutation', () => {
  assert.deepEqual(elevGridLines([], south, [0], 0), []);
  assert.deepEqual(elevGridLines(grids, { kind: 'Plan', dir: [0, 0, -1], origin: [0, 0, 0] }, [0], 0), []);
  assert.deepEqual(elevGridLines(grids, { kind: '3d', dir: [0, -1, 0], origin: [0, 0, 0] }, [0], 0), []);
  const g2 = JSON.parse(JSON.stringify(grids)), v2 = JSON.parse(JSON.stringify(south)), l2 = [3, 1];
  elevGridLines(g2, v2, l2, 0);
  assert.deepEqual(g2, grids); assert.deepEqual(v2, south); assert.deepEqual(l2, [3, 1]);
});
