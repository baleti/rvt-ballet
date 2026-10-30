"""Inspector string editor with real clicks: server with RVTBALLET_EDIT_BACKEND=rvtedit; select an element, the pencil appears on string parameter rows only (not on numbers, not on UniqueId),
click it, answer the prompt -> pending edit recorded (Undo edit (1 pending) button), Undo removes it; edit again, Save as writes a file whose converted table differs in exactly that parameter.
usage: tools/uitest_save3.py MODELDIR PORT WORKDIR ELEMENT_ID PARAM_NAME"""
import asyncio, sys, os, subprocess, json, shutil, sqlite3
sys.path.insert(0, os.path.dirname(__file__)); import cdp
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
async def main(model_dir, port, work, eid, pname):
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
        n_pencil = await b.ev("document.querySelectorAll('#ptab button.pedit').length"); chk('pencils appear on string rows (%s)' % n_pencil, n_pencil >= 1)
        chk('no pencil on UniqueId / numeric rows', await b.ev("[...document.querySelectorAll('#ptab tr')].every(tr => !tr.querySelector('button.pedit') || (tr.dataset.t === 'string' && !/^(UniqueId|IfcGUID)$/.test(tr.cells[0].textContent)))"))
        await b.ev("window.prompt = () => 'edited in the inspector'; [...document.querySelectorAll('#ptab tr')].find(tr => tr.cells[0].textContent === %s).querySelector('button.pedit').click(); 0" % json.dumps(pname)); await until("document.getElementById('savepanel').innerText.includes('Pending edit recorded')")
        t = await b.ev("document.getElementById('savepanel').innerText"); print('PANEL:', t.replace(chr(10), ' | ')[:300]); chk('pending edit recorded message', 'Pending edit recorded' in t and pname in t)
        chk('Undo edit (1 pending) shown', await b.ev("!document.getElementById('bUndoEdit').hidden && document.getElementById('bUndoEdit').textContent.includes('1 pending')"))
        await until("!document.getElementById('bUndoEdit').hidden"); await b.ev("document.getElementById('bUndoEdit').click(); 0")
        chk('Undo removes it', await until("document.getElementById('bUndoEdit').hidden", 30))
        await b.ev("[...document.querySelectorAll('#ptab tr')].find(tr => tr.cells[0].textContent === %s).querySelector('button.pedit').click(); 0" % json.dumps(pname)); await until("!document.getElementById('bUndoEdit').hidden && document.getElementById('bUndoEdit').textContent.includes('1 pending')")
        dest = os.path.join(work, 'out.rvt'); await b.ev("document.getElementById('savepanel').hidden = true; window.prompt = () => %s; document.getElementById('bSaveAs').click(); 0" % json.dumps(dest)); await settle()
        chk('Save as wrote the edited file', os.path.exists(dest) and 'Saved: ' in await b.ev("document.getElementById('savepanel').innerText"))
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    if os.path.exists(os.path.join(work, 'out.rvt')):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', os.path.join(work, 'out.rvt'), os.path.join(work, 'c_out')], capture_output=True, text=True, timeout=300)
        q = lambda d: {(r[0], r[1]): r[2] for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select e.id, p.k, p.v from prm p join el e on e.i=p.i')}
        a, c = q(md), q(os.path.join(work, 'c_out')); d = {k for k in a.keys() | c.keys() if a.get(k) != c.get(k)}
        chk('converted output differs in exactly (%s, %s) = edited text' % (eid, pname), d == {(int(eid), pname)} and c[(int(eid), pname)] == 'edited in the inspector')
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]))
