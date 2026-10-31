"""MIXED-op fuzz on a REAL project (rvtedit backend): chains of 1-3 ops drawn from {by-name string edit, numeric edit (stored named Double, by name), move +dx ft}; SAVE AS with element-level verify; checks:
strings/numerics by reader read-back (exactly the edited (element, parameter) rows changed, values as set), moves by re-converting (only the moved elements' bounding boxes changed, by exactly dx). Aggregate output only.
usage: tools/save_real_fuzz2.py FILE CHAINS SEED OUT.json   (TMPDIR on a disk path)"""
import os, sys, asyncio, tempfile, time, json, random, collections, subprocess, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def bbs(d): return {r[0]: json.loads(r[1]) for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select id, bb from el where bb is not null')}
async def main(src, n, seed, out):
    rnd = random.Random(seed); stat = collections.Counter(); rows = []
    conv = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c_src'], capture_output=True, text=True, timeout=3600); assert conv.returncode == 0
    db = sqlite3.connect(_T + '/c_src/model.sqlite'); movable = [r[0] for r in db.execute("select id from el where cls='FamilyInstance' and bb is not null order by id limit 30")]; ids = [r[0] for r in db.execute("select id from el where cls in ('Wall','Floor','Level','FamilyInstance','DBViewPlan','TextNoteAttributes')")]
    pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; del pr
    strs = [e for e, d in base.items() if d.get('Comments') == '']
    ed = rvtedit.Edit(src); nums = []
    for eid in ids:
        if len(nums) >= 12: break
        try: log = ed.g.e.trace(eid)[3]
        except Exception: continue
        for k, l in enumerate(log):
            if l[1] == 'ParamValueDouble.m_paramId':
                pid = int(l[4][4:-1]); pid = pid - (1 << 64) if pid >= (1 << 63) else pid; nm = rvt_params.PNAMES.get(str(pid))
                v = base.get(eid, {}).get(nm) if nm else None
                if nm and isinstance(v, (int, float)): nums.append((eid, nm, float(v))); break
    leafs = []
    if os.environ.get('FUZZ_DELETE'):
        os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'      # experiments only, inside this test process
        for eid in [r[0] for r in db.execute("select id from el where cls='FamilyInstance' order by id limit 400")]:
            if len(leafs) >= 8: break
            try:
                pn = ed.g.e.trace(eid)[0]
                if ed.latest_partition(eid) == pn and ed.cascade(eid) == [eid] and eid in base: leafs.append(eid)
            except Exception: continue
    stat['delete_candidates'] = len(leafs)
    del ed; stat['num_candidates'] = len(nums); stat['move_candidates'] = len(movable); stat['string_candidates'] = len(strs)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for k in range(n):
            t0 = time.time()
            while (await (await c.get('/api/m/m/edits')).json())['ops']: await c.post('/api/m/m/edit/undo')
            sets = {}; nset = {}; moves = {}; rots = {}; dels = {}
            for _ in range(rnd.randint(1, 3)):
                kind = rnd.choice((['s', 'n', 'm', 'r'] if os.environ.get('FUZZ_ROTATE') else ['s', 'n', 'm']) + (['d'] if leafs else []))
                if kind == 's' and strs:
                    e = rnd.choice(strs); v = rnd.choice(['x', 'Ünï ✓', 'a' * 40, 'Mark-9'])
                    if e in dels: continue
                    r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Comments', 'value': v}); stat['edit_%d' % r.status] += 1
                    if r.status == 200: sets[e] = v
                elif kind == 'n' and nums:
                    e, nm, v0 = rnd.choice(nums)
                    if e in dels: continue
                    nv = round(v0 + rnd.choice([1.0, 2.5, -0.5]), 6)
                    r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': e, 'param': nm, 'value': nv}); stat['edit_%d' % r.status] += 1
                    if r.status == 200: nset[(e, nm)] = nv
                elif kind == 'd' and leafs:
                    e = rnd.choice(leafs)
                    if e in dels or e in moves or e in rots or e in sets: continue
                    r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': e}); stat['edit_%d' % r.status] += 1
                    if r.status == 200: dels[e] = 1
                    else: stat['delete_refused:' + str((await r.json()).get('error', ''))[:70]] += 1
                elif kind == 'r' and movable:
                    e = rnd.choice(movable)
                    if e in moves or e in rots or e in dels: continue
                    dg = rnd.choice([15, 30, -45, 90]); r = await c.post('/api/m/m/edit', json={'op': 'rotate', 'eid': e, 'deg': dg}); stat['edit_%d' % r.status] += 1
                    if r.status == 200: rots[e] = dg
                elif kind == 'm' and movable:
                    e = rnd.choice(movable)
                    if e in moves or e in rots or e in dels: continue
                    r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 1.0}); stat['edit_%d' % r.status] += 1
                    if r.status == 200: moves[e] = 1.0
            if not (sets or nset or moves or rots or dels): stat['no_edit'] += 1; continue
            dest = os.path.join(_T, 'o%d.rvt' % k); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); stat['save_%d_%s' % (r.status, j.get('code', 'ok'))] += 1
            row = {'chain': k, 'strings': len(sets), 'nums': len(nset), 'moves': len(moves), 'rots': len(rots), 'dels': len(dels), 'status': r.status}
            if r.status == 200:
                exact = True
                if sets or nset or dels:
                    now = rvt_params.params(dest); exact &= all(e not in now for e in dels)
                    for e in set(sets) | {e for e, _ in nset}:
                        a = base[e]; b = g(now.get(e)); ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
                        want = ({'Comments'} if e in sets else set()) | {nm for (ee, nm) in nset if ee == e}
                        exact &= ch == want and (e not in sets or b.get('Comments') == sets[e]) and all(abs(b.get(nm) - v) < 1e-9 for (ee, nm), v in nset.items() if ee == e)
                if moves or rots:
                    subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', dest, _T + '/c_o%d' % k], capture_output=True, text=True, timeout=3600)
                    a2, b2 = bbs(_T + '/c_src'), bbs(_T + '/c_o%d' % k); moved = {i for i in a2 if i in b2 and a2[i] != b2[i]}
                    row['extra_boxes_changed'] = len(moved - set(moves) - set(rots)); row['target_boxes_unchanged'] = len((set(moves) | set(rots)) - moved); row['unchanged_rot_degs'] = sorted(rots[e] for e in rots if e not in moved); row['rot_degs'] = sorted(rots.values())
                    exact &= moved == set(moves) | set(rots) and all(abs((b2[e][0][0] - a2[e][0][0]) - 1.0) < 1e-6 for e in moves) and all(a2[e] != b2[e] for e in rots if rots[e] % 90)
                row['exact'] = bool(exact); stat['exact' if exact else 'MISMATCH'] += 1
                kd = os.environ.get('KEEP_DIR')
                if kd and exact and len(sets) + len(nset) + len(moves) + len(rots) + len(dels) >= 2 and stat['kept'] < int(os.environ.get('KEEP_N', '5')):      # local only, for the Revit harness
                    import shutil; os.makedirs(kd, exist_ok=True); shutil.copy(dest, os.path.join(kd, 'chain%d.rvt' % k)); stat['kept'] += 1
                os.remove(dest)
            else: row['code'] = j.get('code'); row['n_unexpected'] = (j.get('report') or {}).get('n_unexpected'); row['detail'] = str(j.get('error'))[:100]
            row['seconds'] = round(time.time() - t0, 1); rows.append(row); print(row, flush=True)
    json.dump({'stats': dict(stat), 'rows': rows}, open(out, 'w')); print('REAL-FUZZ2', dict(stat))
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]))
