"""c1x-rvtdel: Snowdon Facades 2024 SWall 593193: the raw delete (owned_set, 4 ids) leaves 4 hosted FamilyInstances alive with Host Id 593193 -> -1 (a semantically wrong file; Revit's Delete removes hosted instances). The survivor-drift check must see exactly that drift, which is what makes the save gate refuse (verify_failed). Pins the finding; if the cascade ever covers them, drift becomes 0 and this test must be updated deliberately."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    nb, dl = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': 593193})])
    a, b = save._read_params(d.buf), save._read_params(nb); g = lambda x: x.get('params', x) if isinstance(x, dict) else {}
    dead = set(dl); drift = sorted(e for e in a if e not in dead and e in b and g(a[e]) != g(b[e]))
    assert drift == [593274, 593287, 593289, 593291], drift
    assert all(str(g(a[e]).get('Host Id|ElementId')) == '593193' and str(g(b[e]).get('Host Id|ElementId')) == '-1' for e in drift)
    print('PASS orphaned hosted instances detected:', drift)
finally: shutil.rmtree(_T, ignore_errors=True)
