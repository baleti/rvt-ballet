"""c1x-rvtdel: Snowdon Facades 2024 Columns 593361 / 593363 are joined to 2 elements each. Deleting 593361 alone was accepted by the readback gate but the output failed to open in the Revit 2024 VM
(CorruptModelException 'needs to be recovered', 2026-11-15). The gate must refuse a delete of a joined FamilyInstance. Fails without the 'joined family instance' reason in save.risky_membership."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC): print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src)
    d = save.SaveSessions().doc('m', src)
    for eid in (593361, 593363):
        ops = [{'op': 'delete', 'eid': eid}]
        try:
            nb, dl = edit.apply_full(d.buf, [edit.validate_op(o) for o in ops]); save._readback(d.buf, nb, ops)
        except SystemExit: raise
        except Exception as ex: print(eid, 'refused:', str(ex)[:140]); continue
        raise SystemExit('FAIL joined column %d delete accepted' % eid)
    print('PASS')
finally: shutil.rmtree(_T, ignore_errors=True)
