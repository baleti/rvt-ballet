"""Chain of N in-place SAVE!s (Mark edit each time) on a PRIVATE copy of a real Autodesk .rvt. Per save: status/code, size, layout drift refusal (file must be byte-identical when refused), only the target Mark changed. At the end: backups, oldest == original. usage: rvtsave_inplace_chain.py SRC.rvt [N=3]"""
import os, sys, asyncio, tempfile, json, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(orig, n):
    import aiohttp
    from rvtballet import save, server
    from aiohttp.test_utils import TestClient, TestServer
    if os.environ.get('CH_WRAP'):      # per-function RSS delta in the save path (locates native retention that gc / tracemalloc do not see)
        import functools; from rvtballet._vendor.rvtplat import mem as _mw
        def _wrap(mod, name):
            f = getattr(mod, name)
            @functools.wraps(f)
            def w(*a, **k):
                r0 = _mw.rss_bytes() >> 20
                try: return f(*a, **k)
                finally: print('WRAP', name, (_mw.rss_bytes() >> 20) - r0, 'MB', flush=True)
            setattr(mod, name, w)
        import rvtballet.edit as _ed
        for _n in os.environ['CH_WRAP'].split(','): _wrap(_ed if _n.startswith('edit.') else save, _n[5:] if _n.startswith('edit.') else _n)
    src = _T + '/p.rvt'; shutil.copy(orig, src); h0 = sha(src)
    if os.environ.get('LINK_MODE'):      # item 69: loaded path is a symlink; SAVE! must edit the real file and keep the link
        os.replace(src, _T + '/real.rvt'); os.symlink(_T + '/real.rvt', src)
    pr = save._read_params(open(src, 'rb').read())
    c0 = [(e, v['params']['Mark']) for e, v in sorted(pr.items()) if e >= 1000 and isinstance(v.get('params', {}).get('Mark'), str)]
    if not c0: print('NO_CANDIDATE'); return
    e, old = c0[0]; md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    ok = 0; cur = old; rows = []
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for k in range(1, n + 1):
            if os.environ.get('LINK_MODE') and not os.path.islink(src): print('LINK_BROKEN before save', k, flush=True)
            new = 'CH%d' % (k + int(os.environ.get('CH_OFF', '0')))
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Mark', 'value': new, 'match': cur}); assert r.status == 200, r.status
            from rvtballet._vendor.rvtplat import mem as _m0; rss_edit = _m0.rss_bytes() >> 20
            b = sha(src); sz = os.path.getsize(src)
            r = await c.post('/api/m/m/save', json={}, timeout=aiohttp.ClientTimeout(total=None)); j = await r.json()
            row = {'k': k, 'rss_after_edit': rss_edit, 'status': r.status, 'code': j.get('code', 'ok'), 'size_before': sz, 'size_after': os.path.getsize(src)}
            if r.status == 200:
                ok += 1; cur = new; pr2 = save._read_params(open(src, 'rb').read()); row['only_target'] = [x for x in pr if pr[x] != pr2.get(x)] == [e] and pr2[e]['params']['Mark'] == new
            else: row['untouched'] = sha(src) == b; row['error'] = str(j.get('error'))[:200]
            if os.environ.get('CH_TM'):
                import tracemalloc, gc; gc.collect()
                if not tracemalloc.is_tracing(): tracemalloc.start(8)
                elif k == 3: _tm0 = tracemalloc.take_snapshot()
                elif k == 7:
                    snap = tracemalloc.take_snapshot(); [print('TM', st) for st in snap.compare_to(_tm0, 'traceback')[:6]]
            if os.environ.get('CH_BIG'):      # live large buffers and who holds them (finds per-save retention without tracemalloc's slowdown)
                import gc; gc.collect(); big = [o for o in gc.get_objects() if isinstance(o, (bytes, bytearray, memoryview)) and len(o) > (1 << 20)]
                import collections; cn = collections.Counter(type(o).__name__ for o in gc.get_objects()); print('TYPES', k, len(gc.get_objects()), cn.most_common(8), flush=True)
                print('BIG', k, len(big), sum(len(o) for o in big) >> 20, 'MB', [type(r).__name__ for o in big[:6] for r in gc.get_referrers(o)[:2]], flush=True)
            if os.environ.get('CH_TRIM'):
                import gc, ctypes; gc.collect(); ctypes.CDLL('libc.so.6').malloc_trim(0)
            from rvtballet._vendor.rvtplat import mem as _mem; row['rss_mb'] = _mem.rss_bytes() >> 20      # process RSS per round: growth across rounds = leak that eventually trips the memory guard
            rows.append(row); print(row, flush=True)
            if r.status != 200: break
        if os.environ.get('KEEP_OUT') and ok: os.makedirs(os.environ['KEEP_OUT'], exist_ok=True); shutil.copy(src, os.path.join(os.environ['KEEP_OUT'], 'chain_last.rvt'))
        bl = await (await c.get('/api/m/m/backups')).json()
        print({'link_kept': os.path.islink(src), 'real_changed': sha(_T + '/real.rvt') != h0} if os.environ.get('LINK_MODE') else '', end=' '); print({'saves_ok': ok, 'backups': len(bl), 'oldest_is_original': bool(bl) and sha(bl[-1]['path']) == h0})
asyncio.run(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3))
