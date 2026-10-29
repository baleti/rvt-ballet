"""UI: Save! on a file modified behind the viewer -> conflict panel -> 'Overwrite anyway' (confirm) -> byte outcome; then restore from the backups endpoint.
usage: tools/uitest_save2.py MODELDIR PORT WORKDIR   (MODELDIR is copied; its summary.json src is re-pointed to a copy of the .rvt in WORKDIR; temp gate, real gate untouched)"""
import asyncio, sys, os, subprocess, json, hashlib, shutil
sys.path.insert(0, os.path.dirname(__file__)); import cdp
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(model_dir, port, work):
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work); md = os.path.join(work, 'model'); shutil.copytree(model_dir, md)
    s = json.load(open(md + '/summary.json')); src = os.path.join(work, 'doc.rvt'); shutil.copy(s['src'], src); s['src'] = src; json.dump(s, open(md + '/summary.json', 'w')); h0 = sha(src)
    json.dump({'rvt': {'2024': 'open'}}, open(work + '/gate.json', 'w'))
    env = dict(os.environ, SAVEGATE_JOURNAL=work + '/j', SAVEGATE_CACHE=work + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=work + '/gate.json')
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 900)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    async def settle(t=60):
        for _ in range(t * 2):
            if await b.ev("!document.getElementById('savepanel').hidden && !document.getElementById('savepanel').innerText.startsWith('Saving')"): return
            await asyncio.sleep(.5)
    panel = lambda: b.ev("document.getElementById('savepanel').hidden ? '' : document.getElementById('savepanel').innerText")
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(2)
        chk('Save enabled (allow_overwrite + gate)', await b.ev("!document.getElementById('bSaveOver').disabled"))
        await b.ev("window.confirm = () => true; document.getElementById('bSaveOver').click(); 0"); await settle()
        t = await panel(); print(t.replace('\n', ' | ')[:300]); chk('plain Save succeeds with a backup line', 'Saved: ' in t and 'backup of the previous file' in t and sha(src) == h0)
        with open(src, 'ab') as f: f.write(b'\0' * 4096)          # someone else touches the file
        h_mod = sha(src)
        await b.ev("document.getElementById('savepanel').hidden = true; document.getElementById('bSaveOver').click(); 0"); await asyncio.sleep(.5); await settle(); t = await panel()
        chk('conflict panel with Reload / Overwrite anyway, file not touched', 'changed on disk' in t and await b.ev("[...document.querySelectorAll('#savepanel button')].map(x=>x.textContent).join().includes('Overwrite anyway')") and sha(src) == h_mod)
        await b.ev("[...document.querySelectorAll('#savepanel button')].find(x => x.textContent === 'Overwrite anyway').click(); 0"); await asyncio.sleep(.5); await settle(); t = await panel()
        chk('Overwrite anyway writes the loaded bytes', 'Saved: ' in t and sha(src) == h0)
        bl = json.loads(await b.ev("fetch('/api/m/'+S.mid+'/backups').then(r=>r.text())")); chk('backups listed (%d): newest = the externally modified file, next = the original' % len(bl), len(bl) >= 2 and sha(bl[0]['path']) == h_mod and sha(bl[1]['path']) == h0)
        with open(src, 'ab') as f: f.write(b'garbage')
        r = json.loads(await b.ev("fetch('/api/m/'+S.mid+'/restore',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({n:1,confirm:true})}).then(r=>r.text())"))
        chk('restore of backup 1 brings back the original bytes', r.get('ok') and sha(src) == h0)
        with open(src, 'ab') as f: f.write(b'garbage2')
        await b.ev("document.getElementById('bBackups').click(); 0"); await asyncio.sleep(2); t = await panel()
        chk('Backups panel lists entries with Restore buttons', 'Backups (newest first)' in t and await b.ev("document.querySelectorAll('#savepanel button').length") >= 3)
        bl = json.loads(await b.ev("fetch('/api/m/'+S.mid+'/backups').then(r=>r.text())")); k = next(x['n'] for x in bl if sha(x['path']) == h0)
        await b.ev("window.confirm = () => true; [...document.querySelectorAll('#savepanel button')].filter(x => x.textContent === 'Restore')[%d].click(); 0" % k); await asyncio.sleep(3); t = await panel()
        chk('UI Restore of the backup holding the original restores and reports', 'Restored backup #%d' % k in t and sha(src) == h0)
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
