import test from 'node:test';
import assert from 'node:assert/strict';
import { cropExtent } from '../../web/cropextent.js';
const near = (a, b, e = 1e-9) => assert.ok(Math.abs(a - b) < e, `${a} vs ${b}`);
test('plan crop, long side along x', () => {
  const r = cropExtent([[0, 0, 0], [20, 0, 0], [20, 0, 8], [0, 0, 8]], [0, 1, 0]);
  near(r.w, 20); near(r.h, 8); near(r.c[0], 10); near(r.c[2], 4);
});
test('plan crop, first edge along z', () => {
  const r = cropExtent([[0, 0, 0], [0, 0, 12], [-5, 0, 12], [-5, 0, 0]], [0, -1, 0]);
  near(r.w, 5); near(r.h, 12);
});
test('vertical crop, first edge horizontal', () => {
  const r = cropExtent([[0, 0, 0], [10, 0, 0], [10, 6, 0], [0, 6, 0]], [0, 0, 1]);
  near(r.w, 10); near(r.h, 6); near(r.c[1], 3);
});
test('vertical crop, first edge vertical', () => {
  const r = cropExtent([[0, 0, 0], [0, 6, 0], [10, 6, 0], [10, 0, 0]], [0, 0, 1]);
  near(r.w, 10); near(r.h, 6);
});
test('sloped horizontal edge', () => {
  const r = cropExtent([[0, 0, 0], [10, 2, 0], [10, 8, 0], [0, 6, 0]], [0, 0, 1]);
  near(r.w, Math.hypot(10, 2)); near(r.h, 6);
});
