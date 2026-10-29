"""SAVE AS / SAVE UI with real clicks: usage tools/uitest_save.py MODELDIR PORT OUT_DIR (MODELDIR = converted cache dir whose summary.json src is a writable .rvt).
Checks: buttons present, Save as writes a byte-identical copy and the panel shows dest/size/sha/verify, source untouched, Save disabled with a reason
(overwrite off), forced VerifyFailed (mocked 422) renders the first differing keys, conflict offers Reload / Overwrite anyway."""
import asyncio, sys, os, subprocess, json, hashlib
sys.path.insert(0, os.path.dirname(__file__)); import cdp
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(model_dir, port, out):
    os.makedirs(out, exist_ok=True); src = json.load(open(os.path.join(model_dir, 'summary.json')))['src']; h0 = sha(src)
    env = dict(os.environ, SAVEGATE_JOURNAL=out + '/j', SAVEGATE_CACHE=out + '/c'); env.pop('RVTBALLET_ALLOW_OVERWRITE', None)
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 900)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    panel = lambda: b.ev("document.getElementById('savepanel').hidden ? '' : document.getElementById('savepanel').innerText")
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(2)
        chk('Save as enabled', await b.ev("!document.getElementById('bSaveAs').disabled"))
        chk('Save disabled with a reason', await b.ev("document.getElementById('bSaveOver').disabled && /disabled in the configuration/.test(document.getElementById('bSaveOver').title)"))
        dest = os.path.join(out, 'copy ä.rvt')
        if os.path.exists(dest): os.remove(dest)
        await b.ev("window.prompt = () => %s; document.getElementById('bSaveAs').click(); 0" % json.dumps(dest)); await asyncio.sleep(2)
        t = await panel(); print(t.replace('\n', ' | '))
        chk('panel reports dest + size + verify', 'Saved: ' in t and dest in t and 'verify: passed' in t and 'bytes' in t)
        chk('output byte-identical, source untouched', os.path.exists(dest) and sha(dest) == h0 and sha(src) == h0 and sha(dest)[:12] in t)
        await b.ev("document.getElementById('bSaveAs').click(); 0"); await asyncio.sleep(2); t = await panel()
        chk('existing destination refused (nothing overwritten)', 'already exists' in t and sha(dest) == h0)
        await b.ev("""window.__of = window.fetch; window.fetch = (u, o) => /saveas$/.test(u) ? Promise.resolve(new Response(JSON.stringify({ok:false, code:'verify_failed', error:'verify failed', report:{n_unexpected:2, unexpected:[['changed','stream:Global/Latest'],['lost','stream:Partitions/1']]}}), {status:422})) : window.__of(u, o); document.getElementById('bSaveAs').click(); 0"""); await asyncio.sleep(1.5); t = await panel()
        chk('VerifyFailed shows first differing keys', 'original is untouched' in t and 'changed stream:Global/Latest' in t and sha(src) == h0)
        await b.ev("""window.fetch = (u, o) => /saveas$/.test(u) ? Promise.resolve(new Response(JSON.stringify({ok:false, code:'conflict', error:'changed'}), {status:409})) : window.__of(u, o); document.getElementById('bSaveAs').click(); 0"""); await asyncio.sleep(1.5)
        chk('conflict offers Reload / Overwrite anyway', await b.ev("[...document.querySelectorAll('#savepanel button')].map(x => x.textContent).join() .includes('Overwrite anyway')"))
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
