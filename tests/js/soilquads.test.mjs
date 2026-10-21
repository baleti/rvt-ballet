import test from 'node:test';
import assert from 'node:assert/strict';
import { soilQuads } from '../../web/soilquads.js';
test('one segment makes two triangles', () => {
  const r = soilQuads(new Float32Array([0, 5, 1, 4, 6, 1]), -3);
  assert.ok(r instanceof Float32Array); assert.equal(r.length, 18);
  assert.deepEqual(Array.from(r), [0, 5, 1, 4, 6, 1, 4, -3, 1, 0, 5, 1, 4, -3, 1, 0, -3, 1]);
});
test('segments at or below y0 and non-finite ones are skipped', () => {
  const r = soilQuads([0, -3, 0, 1, -4, 0, 0, 2, 0, 1, NaN, 0, 5, 5, 5, 6, 5, 5], -3);
  assert.equal(r.length, 18); assert.equal(r[0], 5);
});
test('empty input', () => { assert.equal(soilQuads([], 0).length, 0); });
