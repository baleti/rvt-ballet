import test from 'node:test';
import assert from 'node:assert/strict';
import { catKey, typeKey, primVisible, enrichTypes } from '../../web/vcvis.js';

const base = () => ({ layers: {}, cats: {}, classes: {}, parts: {}, types: {}, elems: {}, hideHang: false, textOn: true });
const els = { 7: { cls: 'IndependentTag', cat: -2005, parent: -2000, typeName: 'Tag 1', familyName: 'Door Tag' }, 8: { cls: 'Grid' } };

test('catKey and typeKey', () => {
  assert.equal(catKey(-2000), '-2000');
  assert.equal(typeKey(null), null);
  assert.equal(typeKey({}), null);
  assert.equal(typeKey({ typeName: 'A' }), 'A');
  assert.equal(typeKey({ typeName: 'A', familyName: 'F' }), 'F : A');
});

test('everything visible by default, missing fields do not throw', () => {
  assert.equal(primVisible(base(), els, { layer: 'x', cat: -2005, eid: 7, cls: 'IndependentTag', part: 'text', t: 'text' }), true);
  assert.equal(primVisible({ textOn: true }, {}, {}), true);
  assert.equal(primVisible(base(), els, { eid: 999 }), true);
});

test('each switch hides', () => {
  const m = { layer: 'annotation', cat: -2005, eid: 7, cls: 'IndependentTag', part: 'text', t: 'text' };
  let s = base(); s.layers.annotation = false; assert.equal(primVisible(s, els, m), false);
  s = base(); s.cats['-2005'] = { vis: false }; assert.equal(primVisible(s, els, m), false);
  s = base(); s.cats['-2005'] = { color: '#f00' }; assert.equal(primVisible(s, els, m), true);
  s = base(); s.cats['-2000'] = { vis: false }; assert.equal(primVisible(s, els, m), false);      // parent category
  s = base(); s.elems[7] = { vis: false }; assert.equal(primVisible(s, els, m), false);
  s = base(); s.classes.IndependentTag = false; assert.equal(primVisible(s, els, m), false);
  s = base(); s.parts.text = false; assert.equal(primVisible(s, els, m), false);
  s = base(); s.types['Door Tag : Tag 1'] = false; assert.equal(primVisible(s, els, m), false);
  s = base(); s.types['Tag 1'] = false; assert.equal(primVisible(s, els, m), true);
  s = base(); s.textOn = false; assert.equal(primVisible(s, els, m), false);
  assert.equal(primVisible(s, els, { ...m, t: 'line' }), true);
});

test('hang markers follow hideHang', () => {
  const s = base(); s.hideHang = true;
  assert.equal(primVisible(s, els, { hang: true }), false);
  assert.equal(primVisible(s, els, { hang: false }), true);
});

test('enrichTypes fills names from the element table', () => {
  const rows = [[1, 'FamilyInstance', 'Doors', 'D1', 'Single 36', 'L1', 'x', false, 'Door Fam', 'new'], [2, 'Wall', 'Walls', 'W', '', 'L2', 'x', false, '', 'new']];
  const idx = { 11: 0, 12: 1 };
  const e = { 11: { cls: 'FamilyInstance' }, 12: { cls: 'Wall' }, 13: { cls: 'Grid' }, 14: { typeName: 'Keep', levelName: 'L9' } };
  const out = enrichTypes(e, rows, id => idx[id]);
  assert.equal(out, e);
  assert.deepEqual([e[11].typeName, e[11].familyName, e[11].levelName], ['Single 36', 'Door Fam', 'L1']);
  assert.equal(e[12].typeName, undefined);          // empty type name: nothing set
  assert.equal(e[13].typeName, undefined);
  assert.deepEqual(e[14], { typeName: 'Keep', levelName: 'L9' });
  const f = { 11: { cls: 'x', familyName: 'Mine', levelName: 'Mine L' } };
  enrichTypes(f, rows, id => idx[id]);
  assert.deepEqual([f[11].familyName, f[11].levelName, f[11].typeName], ['Mine', 'Mine L', 'Single 36']);
  assert.doesNotThrow(() => enrichTypes({ 1: {} }, undefined, () => 0));
});
