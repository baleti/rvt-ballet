"""c1x-rvtdel: Snowdon Facades 2024 hosted FamilyInstance 593274: deleting the hosted instance alone removes exactly that id, leaves every survivor (incl. its host wall 593193) unchanged and mentioned nowhere. Pins the PARAMETER-level behaviour only. CAVEAT: another agent reports 593274 is the nested child of parent 593273 (c5x-link rbnest1); the parent's raw sub-component reference is NOT covered by this check, so this is not evidence the delete is semantically safe. No dashboard PASS until the Revit VM verdict and a nested-child analysis."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    nb, dl = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': 593274})])
    a, b = save._read_params(d.buf), save._read_params(nb); g = lambda x: x.get('params', x) if isinstance(x, dict) else {}
    assert sorted(dl) == [593274], dl
    drift = sorted(e for e in a if e != 593274 and (e not in b or g(a[e]) != g(b[e])))
    assert drift == [], drift
    assert 593274 not in b and 593193 in b
    print('PASS hosted instance delete is local:', len(a), '->', len(b))
finally: shutil.rmtree(_T, ignore_errors=True)
