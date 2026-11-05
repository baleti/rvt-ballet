"""One process: set_string Comments + in-place SAVE! on FILE (argv1) with value argv2; prints status. Run two at once on the same file to test the save lock. Autodesk samples only."""
import os, sys, asyncio, tempfile, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=os.environ.get('SAVEGATE_CACHE') or _T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def _inject():
    """INJECT=backup_copy|backup_hash|commit|commit_eio|replace: raise OSError (ENOSPC, EIO for commit_eio) at that step of the savegate write path; INJECT_ONCE=1 fails only the first call"""
    w = os.environ.get('INJECT')
    if not w: return
    import errno
    sys.path.insert(0, os.path.expanduser('~/src/savegate'))
    from savegate import backup, atomic, core
    fired = []
    def err(): raise OSError(errno.EIO if w == 'commit_eio' else errno.ENOSPC, 'injected ' + w)
    def wrap(real, only=lambda *a: True):
        def f(*a, **k):
            if only(*a) and not (os.environ.get('INJECT_ONCE') and fired): fired.append(1); err()
            return real(*a, **k)
        return f
    if w == 'backup_copy': backup.shutil.copyfileobj = wrap(backup.shutil.copyfileobj, lambda a, b, *x: str(getattr(b, 'name', '')).endswith('.part'))
    elif w == 'backup_hash': backup.sha256_file = wrap(backup.sha256_file, lambda p: str(p).endswith('.part'))
    elif w in ('commit', 'commit_eio'):
        atomic.commit_temp = wrap(atomic.commit_temp)
        if hasattr(core, 'commit_temp'): core.commit_temp = atomic.commit_temp
    elif w == 'replace': os.replace = wrap(os.replace, lambda a, b, *x: str(a).endswith('.sgtmp'))
async def main(src, val):
    _inject()
    eid = next(e for e, d in rvt_params.params(src).items() if g(d).get('Comments') == '')
    md = tempfile.mkdtemp(); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as cl:
        cl.session._timeout = aiohttp.ClientTimeout(total=None); await cl.get('/api/m/m/saveinfo')
        r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val}); print(val, 'edit', r.status, flush=True)
        if os.environ.get('GO_AT'):
            import time; time.sleep(max(0, float(os.environ['GO_AT']) - time.time()))
        if os.environ.get('EXTERNAL_BEFORE'):      # an outside program rewrites the file between our edit and our first SAVE!
            import hashlib; b = bytearray(open(src, 'rb').read()); b[-1] ^= 0x55; open(src, 'wb').write(b); print('external_sha', hashlib.sha256(b).hexdigest()[:12], flush=True)
        r = await cl.post('/api/m/m/save', json={}); print(val, 'SAVE!', r.status, str((await r.json()).get('error'))[:160], flush=True)
        if os.environ.get('API_RESTORE'):      # list backups and restore through the viewer's own endpoints
            import hashlib; r = await cl.get('/api/m/m/backups'); j = await r.json(); print('backups', r.status, str(j)[:200], flush=True)
            if os.environ.get('DAMAGE_BACKUP'):      # truncate / flip the newest backup (its name tag still records the true hash)
                bp = j[0]['path']; sz = os.path.getsize(bp)
                if os.environ['DAMAGE_BACKUP'] == 'trunc': os.truncate(bp, sz // 2)
                else:
                    bb = bytearray(open(bp, 'rb').read()); bb[sz // 2] ^= 1; open(bp, 'wb').write(bb)
            pre = hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12]
            r = await cl.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); print('restore', r.status, (await r.text())[:160], flush=True)
            print('current_unchanged_by_restore=%s' % (hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12] == pre) if os.environ.get('DAMAGE_BACKUP') else '', flush=True)
            print('restored_sha', hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12], flush=True)
        if os.environ.get('OLDER_BACKUP'):      # two backups exist after save+restore; damage the newest, restore n=1 (older, intact) through the endpoint
            import hashlib; sh = lambda: hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12]
            r = await cl.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); print('restore#1', r.status, 'sha', sh(), flush=True)
            j = await (await cl.get('/api/m/m/backups')).json(); print('backups', [(b['n'], b['name'][-8:], b['size']) for b in j], flush=True)
            bp = j[0]['path']; os.truncate(bp, os.path.getsize(bp) // 2); pre = sh()
            r = await cl.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); print('restore n=0 (damaged)', r.status, 'unchanged', sh() == pre, flush=True)
            r = await cl.post('/api/m/m/restore', json={'confirm': True, 'n': 1}); print('restore n=1', r.status, (await r.text())[-120:], 'sha', sh(), flush=True)
        if os.environ.get('RETRY'):      # a failed SAVE! must leave the session usable: same edit still pending, save again
            h = __import__('hashlib').sha256(open(src, 'rb').read()).hexdigest()[:12]
            r = await cl.post('/api/m/m/save', json={}); print('SAVE retry', r.status, str((await r.json()).get('error'))[:160], 'changed=%s' % (__import__('hashlib').sha256(open(src, 'rb').read()).hexdigest()[:12] != h), flush=True)
        if os.environ.get('EXTERNAL_AFTER'):      # an outside program rewrites the file after our save; the next SAVE! must not overwrite it
            import hashlib; b = bytearray(open(src, 'rb').read()); b[-1] ^= 0x55; open(src, 'wb').write(b); h = hashlib.sha256(b).hexdigest()[:12]
            r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val + '2'}); print('edit2', r.status, flush=True)
            r = await cl.post('/api/m/m/save', json={}); print('SAVE2', r.status, str((await r.json()).get('error'))[:160], 'file_still_external=%s' % (hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12] == h), flush=True)
asyncio.run(main(sys.argv[1], sys.argv[2]))
