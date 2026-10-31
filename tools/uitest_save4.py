"""Inspector Move / Rotate / Delete buttons with real clicks (rvtedit backend): select an element; Move... (prompt '2, 0, 0') records a pending edit (Undo edit (1 pending)); Undo removes it; Rotate... records one; Delete... is refused by the server (delete is off by default) and the refusal text is shown, nothing pending; a bad Move input shows an error and records nothing; Save as of a pending move writes a file whose converted bounding box of that element shifted by exactly 2 ft. Derived from uitest_save3. Original docstring: server with RVTBALLET_EDIT_BACKEND=rvtedit; select an element, the pencil appears on string parameter rows only (not on numbers, not on UniqueId),
click it, answer the prompt -> pending edit recorded (Undo edit (1 pending) button), Undo removes it; edit again, Save as writes a file whose converted table differs in exactly that parameter.
usage: tools/uitest_save4.py MODELDIR PORT WORKDIR ELEMENT_ID"""
import asyncio, sys, os, subprocess, json, shutil, sqlite3
sys.path.insert(0, os.path.dirname(__file__)); import cdp
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
async def main(model_dir, port, work, eid):
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work); md = os.path.join(work, 'model'); shutil.copytree(model_dir, md)
    s = json.load(open(md + '/summary.json')); src = os.path.join(work, 'doc.rvt'); shutil.copy(s['src'], src); s['src'] = src; json.dump(s, open(md + '/summary.json', 'w'))
    env = dict(os.environ, SAVEGATE_JOURNAL=work + '/j', SAVEGATE_CACHE=work + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
    srv = subprocess.Popen([os.path.join(HERE, 'rvt-ballet'), 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 900)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    async def until(js, t=90):
        for _ in range(t * 2):
            if await b.ev(js): return True
            await asyncio.sleep(.5)
        return False
    async def settle(t=90):
        for _ in range(t * 2):
            if await b.ev("!document.getElementById('savepanel').hidden && !document.getElementById('savepanel').innerText.startsWith('Saving')"): return
            await asyncio.sleep(.5)
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(3)
        await b.ev("window.postMessage({type:'rvt-select', elementId:%d}, '*'); 0" % int(eid)); await asyncio.sleep(3)
        btn = lambda label: "[...document.querySelectorAll('#ptab ~ .opbar button, .opbar button')].find(x => x.textContent.startsWith('%s')).click(); 0" % label
        chk('Move / Rotate / Delete buttons appear', await until("document.querySelectorAll('.opbar button').length === 3", 30))
        await b.ev("window.prompt = () => 'a, b'; " + btn('Move')); await asyncio.sleep(2)
        t = await b.ev("document.getElementById('savepanel').innerText"); chk('bad move input shows an error, nothing pending', 'three numbers' in t and await b.ev("document.getElementById('bUndoEdit').hidden"))
        await b.ev("window.prompt = () => '2, 0, 0'; " + btn('Move')); await until("!document.getElementById('bUndoEdit').hidden")
        t = await b.ev("document.getElementById('savepanel').innerText"); print('PANEL:', t.replace(chr(10), ' | ')[:240]); chk('move recorded', 'Pending edit recorded' in t and 'move' in t)
        await b.ev("document.getElementById('bUndoEdit').click(); 0"); chk('Undo removes the move', await until("document.getElementById('bUndoEdit').hidden", 30))
        await b.ev("window.prompt = () => '30'; " + btn('Rotate')); await until("!document.getElementById('bUndoEdit').hidden")
        t = await b.ev("document.getElementById('savepanel').innerText"); chk('rotate recorded', 'Pending edit recorded' in t and 'rotate' in t)
        await b.ev("document.getElementById('bUndoEdit').click(); 0"); await until("document.getElementById('bUndoEdit').hidden", 30)
        await b.ev("window.confirm = () => true; " + btn('Delete')); await asyncio.sleep(3)
        t = await b.ev("document.getElementById('savepanel').innerText"); chk('delete refused with the reason, nothing pending', 'delete is disabled' in t and await b.ev("document.getElementById('bUndoEdit').hidden"))
        await b.ev("window.prompt = () => '2, 0, 0'; " + btn('Move')); await until("!document.getElementById('bUndoEdit').hidden")
        dest = os.path.join(work, 'out.rvt'); await b.ev("document.getElementById('savepanel').hidden = true; window.prompt = () => %s; document.getElementById('bSaveAs').click(); 0" % json.dumps(dest)); await settle()
        chk('Save as wrote the moved file', os.path.exists(dest) and 'Saved: ' in await b.ev("document.getElementById('savepanel').innerText"))
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    if os.path.exists(os.path.join(work, 'out.rvt')):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', os.path.join(work, 'out.rvt'), os.path.join(work, 'c_out')], capture_output=True, text=True, timeout=300)
        bb = lambda d: {r[0]: json.loads(r[1]) for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select id, bb from el where bb is not null')}
        a, c = bb(md), bb(os.path.join(work, 'c_out')); moved = {k for k in a if k in c and a[k] != c[k]}
        chk('only element %s moved, by exactly 2 ft in x' % eid, moved == {int(eid)} and abs((c[int(eid)][0][0] - a[int(eid)][0][0]) - 2.0) < 1e-6)
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]))
