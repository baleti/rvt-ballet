"""c5x-rvtlink: with RVTBALLET_ENABLE_DELETE=1 the delete op must still refuse link types, CAD/IFC import instances, families and family symbols (cascades not reproduced; only verified classes may be deleted). Autodesk 2024 HVAC sample, skipped if absent."""
import os, sys, glob, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import save, edit
import rvt_params
c = glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt'))
if not c or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 'src.rvt'); shutil.copy(c[0], src); d = save.SaveSessions().doc('m', src)
    P = rvt_params.params(src); n = 0
    for cls in ('RvtLinkSymbol', 'ImportInstance', 'Family', 'FamilySymbol'):
        ids = [e for e, v in P.items() if isinstance(v, dict) and v.get('class') == cls][:2]
        for i in ids:
            n += 1
            try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': i})]); raise SystemExit('FAIL: %s %s deleted' % (cls, i))
            except edit.EditError as e: assert 'only enabled' in str(e), str(e)
    assert n >= 2, n
    print('OK %d link/family deletes refused' % n)
finally: shutil.rmtree(_T, ignore_errors=True)
