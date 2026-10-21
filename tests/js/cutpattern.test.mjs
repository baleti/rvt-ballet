import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCutGroups, scaleGrid, viewScaleN } from '../../web/cutpattern.js';
const near = (a, b, e = 1e-9) => assert.ok(Math.abs(a - b) < e, `${a} vs ${b}`);
const gA = [{ angle: 0.5, origin: [0.1, 0.2], deltas: [0.01, -0.02], segs: [0.003, -0.027] }];
test('groups are distinct patterns and matGroup is 1-based', () => {
  const r = buildCutGroups([{ cut_pattern: { name: 'A', target: 0, grids: gA } }, {}, { cut_pattern: { name: 'A2', target: 0, grids: JSON.parse(JSON.stringify(gA)) } }, { cut_pattern: { name: 'B', target: 1, grids: gA } }, { cut_pattern: { name: 'C', target: 0, grids: [] } }]);
  assert.equal(r.groups.length, 1);
  assert.deepEqual(Array.from(r.matGroup), [1, 0, 1, 0, 0]);
  const g = r.groups[0].grids[0];
  near(g.a[0], 0.5); near(g.a[1], 0.02 * 0.3048); near(g.a[2], 0.01 * 0.3048); assert.equal(g.a[3], 1);
  near(g.b[0], 0.003 * 0.3048); near(g.b[1], 0.027 * 0.3048); near(g.b[2], 0.1 * 0.3048); near(g.b[3], 0.2 * 0.3048);
});
test('no segs gives zero dash, zero spacing clears flag, third grid dropped', () => {
  const mk = a => ({ angle: a, origin: [0, 0], deltas: [0, 0.01], segs: [] });
  const r = buildCutGroups([{ cut_pattern: { name: 'x', target: 0, grids: [mk(0), mk(1), mk(2)] } }, { cut_pattern: { name: 'z', target: 0, grids: [{ angle: 0, origin: [0, 0], deltas: [0, 0], segs: [] }] } }]);
  assert.equal(r.groups[0].grids.length, 2); assert.equal(r.groups[0].grids[1].a[0], 1);
  assert.equal(r.groups[0].grids[0].b[0], 0); assert.equal(r.groups[0].grids[0].b[1], 0);
  assert.equal(r.groups[1].grids[0].a[3], 0);
  assert.equal(buildCutGroups([]).matGroup.length, 1);
});
test('scaleGrid and viewScaleN', () => {
  const s = scaleGrid({ a: [0.3, 2, 3, 1], b: [4, 5, 6, 7] }, 10);
  assert.deepEqual(s, { a: [0.3, 20, 30, 1], b: [40, 50, 60, 70] });
  near(viewScaleN({ scale: 1 / 48 }), 48, 1e-6); assert.equal(viewScaleN(null), 50); assert.equal(viewScaleN({ scale: 1e-9 }), 500); assert.equal(viewScaleN({ scale: 2 }), 1);
});
