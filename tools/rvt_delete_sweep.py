"""Delete sweep (c5x-rvtmatrix): opt-in delete op over one element per class (up to N classes x K elements) of a scene; each tried alone: SAVE AS must be refused (nothing written) or
verify clean. Accepted outputs are kept in KEEP_DIR for the Revit VM. Aggregate output only.   usage: tools/rvt_delete_sweep.py OUT.json FILE [N_PER_CLASS=2] [KEEP_DIR]"""
import os, sys, asyncio, tempfile, shutil, json, hashlib, collections
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
SWEEP_OP = os.environ.get('SWEEP_OP', 'delete')      # delete (default) or rotate (90 degrees): same accept/refuse sweep for the rotate op
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(out, f, n, keep):
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 's' + os.path.splitext(f)[1]); shutil.copy(f, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    pr = rvt_params.params(src); g = lambda x: x.get('params', x)
    bycls = collections.defaultdict(list)
    for e, d in pr.items(): bycls[(d.get('class') if isinstance(d, dict) and 'class' in d else 'el')].append(e)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}; rows = []; k = 0
    async with TestClient(TestServer(server.make_app(models)), timeout=__import__('aiohttp').ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for cls, ids in sorted(bycls.items()):
            if os.environ.get('SWEEP_FROM') and cls < os.environ['SWEEP_FROM']: continue      # resume a capped sweep at this class (sorted order)
            if os.environ.get('SWEEP_CLASSES') and cls not in os.environ['SWEEP_CLASSES'].split(','): continue
            for eid in ids[:n]:
                r = await c.post('/api/m/m/edit', json=dict({'op': 'delete'} if SWEEP_OP == 'delete' else {'op': 'rotate', 'deg': 90.0}, eid=eid))
                if r.status != 200: rows.append({'class': cls, 'result': 'INPUT_REFUSED'}); continue
                dest = os.path.join(_T, 'o%d%s' % (k, os.path.splitext(f)[1])); k += 1
                r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
                if r.status == 200: res = 'ACCEPTED verify_unexpected=%s' % j.get('verify', {}).get('n_unexpected'); assert os.path.exists(dest)
                else: res = 'REFUSED_%d %s' % (r.status, j.get('code')); print('DETAIL', cls, eid, json.dumps(j)[:1500], flush=True); assert not os.path.exists(dest)
                if r.status == 200 and keep: shutil.copy(dest, os.path.join(keep, '%s_%s_%d%s' % (SWEEP_OP[:3], cls, eid, os.path.splitext(f)[1])))
                rows.append({'class': cls, 'result': res}); print('ROW', cls, res, flush=True); await c.post('/api/m/m/edit/undo')      # per-row log: a capped run still leaves its results
    assert sha(src) == h0; json.dump(rows, open(out, 'w'))
    print(collections.Counter((r['class'], r['result'].split()[0]) for r in rows))
if __name__ == '__main__':
    keep = sys.argv[4] if len(sys.argv) > 4 else None
    if keep: os.makedirs(keep, exist_ok=True)
    asyncio.run(run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2, keep))
