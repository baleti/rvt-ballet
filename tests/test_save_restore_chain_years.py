"""c1x-rvtsave 229: app path (add_edit + save_overwrite) with 3 chained Comments edits, then restore of each historic state byte-exact, on Autodesk Construction templates 2024, 2025, 2026. Readback after each save equals the value."""
import os, sys, glob, shutil, hashlib, tempfile, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
T = tempfile.mkdtemp()
json.dump({'rvt': {y: 'open' for y in ('2024', '2025', '2026')}}, open(T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE=T + '/s', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=T + '/gate.json')
import rvt_params
from rvtballet import save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
n = 0
for y in (2024, 2025, 2026):
    fs = glob.glob(os.path.expanduser('~/rvtfix/corpus/%d/*Construction-DefaultMetric.rte' % y))
    if not fs: continue
    p = '%s/m%d.rte' % (T, y); shutil.copy(fs[0], p); ss = save.SaveSessions(); states = [sha(p)]
    E = next(e for e, d in rvt_params.params(p).items() if g(d).get('Comments') == '')
    for k in range(3):
        mid = 'm%d_%d' % (y, k); ss.doc(mid, p)
        save.add_edit(ss, mid, p, {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'v%d' % k}); save.save_overwrite(ss, mid, p)
        assert g(rvt_params.params(p)[E]).get('Comments') == 'v%d' % k; states.append(sha(p))
    assert len(set(states)) == 4, y
    for k in (2, 1, 0):
        n_ = next(b['n'] for b in save.backups(p) if sha(b['path']) == states[k]); save.restore_backup(ss, 'r', p, n_)
        assert sha(p) == states[k], (y, k)
    print(y, 'chain of 3 saves + 3 byte-exact restores OK'); n += 1
shutil.rmtree(T, ignore_errors=True); assert n; print('OK', n)
