import test from 'node:test';
import assert from 'node:assert/strict';
import { fitDistance, boxFrame } from '../../web/viewframe.js';
const near = (a, b, e = 1e-9) => assert.ok(Math.abs(a - b) < e, `${a} vs ${b}`);
const T = Math.tan(45 * Math.PI / 360);
test('fitDistance', () => {
  near(fitDistance(10, 5, 2, 45), 5 / 2 / T * 1.08 + 1);
  near(fitDistance(10, 8, 2, 45), 8 / 2 / T * 1.08 + 1);
});
test('boxFrame towards +z', () => {
  const r = boxFrame([-10, 0, -2], [30, 10, 6], [0, 0, 1], [0, 0, 3], 2, 45);
  // centre (10, 5, 2); right = cross([0,1,0],[0,0,1]) = [1, 0, 0]; hw = 20, hh = 5
  near(r.target[0], 10); near(r.target[1], 5); near(r.target[2], 3);
  near(r.dist, Math.max(20 / 2, 5) / T * 1.08 + 1);
  near(r.eye[2], 3 + r.dist);
});
test('boxFrame towards +x uses z extent across the screen', () => {
  const r = boxFrame([0, 0, 0], [4, 2, 30], [1, 0, 0], [1, 9, 9], 1.5, 45);
  // right = cross([0,1,0],[1,0,0]) = [0, 0, -1]; hw = 15; target x = 1 (plane), y = centre
  near(r.target[0], 1); near(r.target[1], 1); near(r.target[2], 15);
  near(r.dist, Math.max(15 / 1.5, 1) / T * 1.08 + 1);
  near(r.eye[0], 1 + r.dist);
});
test('degenerate box', () => {
  const r = boxFrame([2, 2, 2], [2, 2, 2], [0, 0, 1], [0, 0, 2], 1, 45);
  near(r.dist, 1 / T * 1.08 + 1);
});
