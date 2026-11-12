"""c9x-rvttype: set_type_material refuses files of unverified Revit years (2022, 2025) with a clear EditError and returns nothing; picks the smallest .rvt of each corpus year; skips years without samples."""
import os, sys, glob
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEEID'] = '1'; os.environ['RVT_GEOM'] = '1'
sys.path[:0] = [H, os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
from rvtballet import edit
tried = 0
for y in (2022, 2025):
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%d/*.rvt' % y)), key=os.path.getsize)
    if not fs: print('skip', y, 'no sample'); continue
    buf = open(fs[0], 'rb').read()
    op = edit.validate_op({'op': 'set_type_material', 'eid': 378, 'target': 751})
    try: edit.apply_full(buf, [op]); print('FAIL: %d file accepted' % y); sys.exit(1)
    except edit.EditError as e:
        assert 'only verified on Revit 2024/2026' in str(e) or 'does not exist' in str(e), str(e)[:120]
        print('refused', y, str(e)[:80]); tried += 1
print('ok: %d unverified-year files refused' % tried)
