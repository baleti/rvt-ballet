"""Runs the pure-function checks of web/save.js (same assertions as tests/js/save.test.mjs) in headless Chromium by importing the module from the viewer server (host without node).
usage: tools/jstest_save.py MODELDIR PORT"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
JS = r"""(async () => {
  const m = await import('/save.js'); const out = []; const t = (n, c) => out.push((c ? 'PASS ' : 'FAIL ') + n);
  const l = m.describeResult({ ok: true, dest: '/a/b.rvt', size: 10, sha256: 'abc', version: '2024', backup: '/bk/1', verify: { objects_src: 5, objects_out: 5, n_unexpected: 0, validate: 'ok' } });
  t('result dest', /Saved: \/a\/b.rvt/.test(l[0])); t('result backup', /backup.*\/bk\/1/.test(l[2])); t('result verify', /5 source objects.*0 undeclared/.test(l[3]));
  t('no backup text', /no backup needed/.test(m.describeResult({ ok: true, dest: 'x', size: 1, sha256: 'a', version: '2024' })[2]));
  const e = m.describeError({ code: 'verify_failed', error: 'verify failed: 2', report: { n_unexpected: 2, unexpected: [['changed', 'stream:A'], ['lost', 'stream:B']] } }, 422);
  t('verify_failed head', /original is untouched/.test(e[0])); t('first keys', /2 differences, first: changed stream:A; lost stream:B/.test(e[e.length - 1]));
  t('conflict', /changed on disk/.test(m.describeError({ code: 'conflict' }, 409)[0])); t('http500', /HTTP 500/.test(m.describeError(null, 500)[0]));
  t('bad_dest', /not usable/.test(m.describeError({ code: 'bad_dest' }, 400)[0])); t('unreadable', /could not be read back/.test(m.describeError({ code: 'output_unreadable' }, 422)[0]));
  t('save on', m.actions({ open: true, allow_overwrite: true, gate_open: true }).save.on === true);
  t('why config', /disabled in the configuration/.test(m.actions({ open: true, allow_overwrite: false, gate_open: true }).save.why));
  t('why gate', /gate closed/.test(m.actions({ open: true, allow_overwrite: true, gate_open: false }).save.why));
  const a = m.actions({ open: false, error: 'RVT 2019 cannot be saved' }); t('saveas off + reason', a.saveas.on === false && /2019/.test(a.save.why));
  const e2 = m.describeError({ code: 'verify_failed', changed_detail: [{ cls: 'FamilyInstance', id: 7, name: 'Door' }], edits: [{ field: 'DatumPlane.m_text', eid: 355 }] }, 422);
  t('changed detail', e2.some(x => /FamilyInstance 7 "Door"/.test(x)) && e2.some(x => /DatumPlane.m_text of element 355/.test(x)));
  t('backup line', /#2 .*5 bytes/.test(m.describeBackup({ n: 2, mtime: 'x', size: 5, name: 'n' })));
  return JSON.stringify(out); })()"""
async def main(md, port):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(800, 600)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/save.js' % port); await asyncio.sleep(1)
        r = json.loads(await b.ev(JS)); [print(x) for x in r]; bad = [x for x in r if x.startswith('FAIL')]
    finally: await b.close(); srv.terminate()
    print('JS OK %d checks' % len(r) if not bad else 'JS FAILED'); sys.exit(1 if bad else 0)
asyncio.run(main(sys.argv[1], int(sys.argv[2])))
