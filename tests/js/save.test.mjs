import test from 'node:test';
import assert from 'node:assert/strict';
import { describeResult, describeError, describeBackup, actions } from '../../web/save.js';
// Node twin of tools/jstest_save.py (which runs the same assertions in headless Chromium on hosts without node).

test('describeResult lists dest, hash, backup, verify, warnings', () => {
  const l = describeResult({ ok: true, dest: '/a/b.rvt', size: 10, sha256: 'abc', version: '2024', backup: '/bk/1', verify: { objects_src: 5, objects_out: 5, n_unexpected: 0, validate: 'ok' } });
  assert.match(l[0], /Saved: \/a\/b.rvt/); assert.match(l[2], /backup.*\/bk\/1/); assert.match(l[3], /5 source objects.*0 undeclared/);
  assert.match(describeResult({ ok: true, dest: 'x', size: 1, sha256: 'a', version: '2024' })[2], /no backup needed/);
  assert.ok(describeResult({ ok: true, dest: 'x', size: 1, sha256: 'a', version: '2024', warnings: ['layout changed'] }).includes('WARNING: layout changed'));
});
test('describeError maps codes and shows the changed elements and pending edits', () => {
  const l = describeError({ code: 'verify_failed', error: 'verify failed: 2', report: { n_unexpected: 2, unexpected: [['changed', 'stream:A'], ['lost', 'stream:B']] } }, 422);
  assert.match(l[0], /original is untouched/); assert.match(l.at(-1), /2 differences, first: changed stream:A; lost stream:B/);
  assert.match(describeError({ code: 'conflict' }, 409)[0], /changed on disk/);
  assert.match(describeError(null, 500)[0], /HTTP 500/);
  assert.match(describeError({ code: 'bad_dest' }, 400)[0], /not usable/);
  assert.match(describeError({ code: 'output_unreadable' }, 422)[0], /could not be read back/);
  assert.match(describeError({ code: 'layout_changed' }, 409)[0], /not confirmed/);
  const e2 = describeError({ code: 'verify_failed', changed_detail: [{ cls: 'FamilyInstance', id: 7, name: 'Door' }], edits: [{ field: 'DatumPlane.m_text', eid: 355 }] }, 422);
  assert.ok(e2.some(x => /FamilyInstance 7 "Door"/.test(x))); assert.ok(e2.some(x => /DatumPlane.m_text of element 355/.test(x)));
});
test('actions disable buttons with a reason', () => {
  assert.equal(actions({ open: true, allow_overwrite: true, gate_open: true }).save.on, true);
  assert.match(actions({ open: true, allow_overwrite: false, gate_open: true }).save.why, /disabled in the configuration/);
  assert.match(actions({ open: true, allow_overwrite: true, gate_open: false }).save.why, /gate closed/);
  const a = actions({ open: false, error: 'RVT 2019 cannot be saved' }); assert.equal(a.saveas.on, false); assert.match(a.save.why, /2019/);
});
test('describeBackup', () => { assert.match(describeBackup({ n: 2, mtime: 'x', size: 5, name: 'n' }), /#2 .*5 bytes/); });
