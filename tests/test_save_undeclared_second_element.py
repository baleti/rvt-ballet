"""c2x-rvtmatrix item 5: the writer (edit.apply_full) leaks an UNDECLARED change into a second element (the way name-edit cascades leaked on SWall/Level/DBView): SAVE AS and SAVE! must both refuse (VerifyFailed -> 4xx), the source stays byte-identical and no output file appears. Control: the honest writer saves."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, H)
for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
SRC = os.environ.get('SNAP_FILE') or os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
import rvt_params, rvt_geometry as G
from rvtballet import server, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: x.get('params', x)
async def main():
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    pr = rvt_params.params(SRC); ix = G.file_geometry_index(SRC); KN = set(rvt_params.PNAMES.values())
    fis = [e for e, v in ix.items() if str(v) == 'FamilyInstance' and e in pr]
    def cand(e): return [n for n, v in g(pr[e]).items() if isinstance(v, str) and '|' not in n and n in KN and n not in {'Name', 'Family and Type', 'Type', 'Type Id', 'Family'}]
    real = edit.apply_full
    async def session(leak):
        work = os.path.join(_T, 'w.rvt'); shutil.copy(SRC, work); h0 = sha(work)
        models = server.Models(); md = tempfile.mkdtemp(dir=_T); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
        async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
            assert (await (await c.get('/api/m/m/saveinfo')).json()).get('open')
            tgt = None
            for e in fis:
                for n in cand(e):
                    r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': n, 'value': 'decl'})
                    if r.status == 200: tgt = (e, n); break
                if tgt: break
            srcbuf = open(SRC, 'rb').read(); other = None
            for e in fis:
                if e == tgt[0] or other: continue
                for n in cand(e):
                    try: real(srcbuf, [edit.validate_op({'op': 'set_string', 'eid': e, 'param': n, 'value': 'LEAK'})]); other = (e, n); break
                    except Exception: pass
            assert other, 'no second element that accepts a string edit'
            if leak:
                def leaky(buf, ops, *a, **k):
                    out = real(buf, ops, *a, **k); nb = out[0] if isinstance(out, tuple) else out
                    nb2 = real(nb, [edit.validate_op({'op': 'set_string', 'eid': other[0], 'param': other[1], 'value': 'LEAK'})])[0]
                    return (nb2,) + tuple(out[1:]) if isinstance(out, tuple) else nb2
                edit.apply_full = leaky
            try:
                dest = os.path.join(_T, 'o%d.rvt' % leak); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); st_as = r.status; print(str(j)[:300])
                r = await c.post('/api/m/m/save', json={}); st_ow = r.status
            finally: edit.apply_full = real
            return st_as, st_ow, os.path.exists(dest), sha(work) == h0
    ok = await session(False); print('control', ok); assert ok[0] == 200 and ok[2], ok
    bad = await session(True); print('leak', bad)
    assert bad[0] >= 400 and not bad[2] and bad[1] >= 400 and bad[3], bad
    print('undeclared second element refused OK')
asyncio.run(main())
