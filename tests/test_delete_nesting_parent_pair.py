"""c1x-rvtdel: Snowdon Facades 2024 FamilyInstance 593287 nests 593288 (membership: nesting parent / nested in). Revit Delete(593287) cascades to exactly 2 ids (paired VM run, rvtsave_cascade). Deleting the parent alone is refused (child survives with drifted params); deleting parent+child together must be accepted by the readback gate with no drift and no dangling references."""
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
    def run(eids):
        ops = [{'op': 'delete', 'eid': e} for e in eids]
        nb, dl = edit.apply_full(d.buf, [edit.validate_op(o) for o in ops])
        save._readback(d.buf, nb, ops); return nb, dl
    try: run([593287]); raise SystemExit('FAIL parent-only delete accepted')
    except SystemExit: raise
    except Exception as ex: print('parent alone refused:', str(ex)[:120])
    nb, dl = run([593287, 593288])
    print('PASS parent+child delete accepted, removed', len(dl))
finally: shutil.rmtree(_T, ignore_errors=True)
