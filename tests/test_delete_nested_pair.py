"""c3x-rvtdel item 59: Snowdon Facades 2024 nesting parent 593273 alone is REFUSED by the readback gate (child 593274 params change); parent+child together is ACCEPTED (consistent cascade). Offline only, no VM verdict."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.getcwd())
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import save, edit
src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src)
d = save.SaveSessions().doc('m', src)
if not os.path.exists(SRC): print('skip'); sys.exit(0)
res = {}
for ids in ([593273], [593273, 593274]):
    ops = [{'op': 'delete', 'eid': i} for i in ids]
    try:
        nb, dl = edit.apply_full(d.buf, [edit.validate_op(o) for o in ops]); save._readback(d.buf, nb, ops); print(ids, 'ACCEPTED'); res[len(ids)] = 'A'
    except BaseException as ex: print(ids, 'REFUSED', str(ex)[:300]); res[len(ids)] = 'R'
shutil.rmtree(_T, ignore_errors=True)
assert res == {1: 'R', 2: 'A'}, res
print('PASS nested parent alone refused, parent+child accepted')
