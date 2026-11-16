"""set_type_yesno refuses 2023, 2025 and 2026 Autodesk samples (only Revit 2024 is witnessed); nothing written; skips if samples are absent."""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEYESNO'] = '1'
from rvtballet import edit
n = 0
for y in (2023, 2025, 2026):
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%d/*.rvt' % y)), key=os.path.getsize)
    if not fs: continue
    buf = open(fs[0], 'rb').read()
    try: edit.apply_full(buf, [edit.validate_op({'op': 'set_type_yesno', 'eid': 1, 'pid': -1019013, 'value': 1})])
    except edit.EditError as e:
        assert 'only verified on Revit 2024' in str(e), (y, str(e)[:120]); n += 1
    else: raise AssertionError('accepted on %d' % y)
print('ok: %d refusals' % n if n else 'skip: no samples')
