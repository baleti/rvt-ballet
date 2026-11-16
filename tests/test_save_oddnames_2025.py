"""c1x-rvtmatrix 159: hostile source file names (spaces, unicode, '#', quotes, 190 chars, UPPER.RVT) on the Autodesk 2025 Construction template: in-place SAVE! gives the edited bytes with a working restore, or is refused with the source intact; no stray files. Also run for 2026."""
import os, sys, glob, shutil, hashlib, tempfile, json, atexit
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); atexit.register(shutil.rmtree, T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for _p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(_p))
json.dump({'rvt': {y: 'open' for y in ('2025', '2026')}}, open(T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE=T + '/s', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=T + '/gate.json')
import rvt_params
from rvtballet import save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
NAMES = ['plain name with spaces.rvt', 'Büro Ärger 日本語.rvt', "a#b&c%d'e\"f.rvt", 'x' * 190 + '.rvt', 'UPPER.RVT']
bad = n = 0
for y in (2025, 2026):
    fs = glob.glob(os.path.expanduser('~/rvtfix/corpus/%d/*Construction-DefaultMetric.rte' % y))
    if not fs: continue
    E = next(e for e, d in rvt_params.params(fs[0]).items() if g(d).get('Comments') == '')
    for nm in NAMES:
        d = tempfile.mkdtemp(dir=T, suffix=' dir with space'); p = os.path.join(d, nm); shutil.copy(fs[0], p); h0 = sha(p); before = set(os.listdir(d))
        ss = save.SaveSessions(); ss.doc('m', p)
        save.add_edit(ss, 'm', p, {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'odd'})
        try:
            r = save.save_overwrite(ss, 'm', p); ok = sha(p) != h0 and g(rvt_params.params(p)[E]).get('Comments') == 'odd'
            n_ = next(b['n'] for b in save.backups(p)); save.restore_backup(ss, 'r', p, n_); ok = ok and sha(p) == h0; res = 'accepted'
        except Exception as e: ok = sha(p) == h0; res = 'refused ' + type(e).__name__ + str(e)[:80]
        extra = set(os.listdir(d)) - before - {'.savegate'}; ok = ok and not extra
        print(y, repr(nm[:20]), res, 'OK' if ok else 'FINDING %s' % extra, flush=True); bad += not ok; n += 1; ss.close()
assert n and not bad, (n, bad); print('OK', n)
