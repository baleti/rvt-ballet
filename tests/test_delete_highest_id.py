"""Delete regression (rung 2, c1x-rvtdel item 45): deleting the element with the HIGHEST id of a class (so the file's id high-water mark / Global/Latest tail is touched) must read back clean: id gone, all other params identical; the output re-reads with the same remaining set."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKUPS'] = _T + '/b'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
pr = rvt_params.params(src)
cands = sorted(e for e, d in pr.items() if isinstance(d, dict) and d.get('class') in ('FamilyInstance', 'Floor'))
assert cands
eid = cands[-1]; print('highest-id candidate', eid, pr[eid].get('class'), flush=True)
d = save.SaveSessions().doc('m', src)
ops = [edit.validate_op({'op': 'delete', 'eid': eid})]
nb, deleted = edit.apply_full(d.buf, ops); assert eid in deleted
save._readback(d.buf, nb, ops)
out = os.path.join(_T, 'out.rvt'); open(out, 'wb').write(nb)
p2 = rvt_params.params(out)
assert eid not in p2 and set(p2) == set(pr) - set(deleted), (len(p2), len(pr), len(deleted))
assert all(p2[e] == pr[e] for e in p2 if e not in deleted and all(str(eid) not in str(v) for v in [pr[e]])), 'survivor drift'
print('highest-id delete OK', len(deleted))
