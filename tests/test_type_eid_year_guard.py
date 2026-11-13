"""set_type_eid / set_type_material refuse 2023 and 2025 Autodesk samples (nothing written); skips if samples are absent."""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEEID'] = '1'
from rvtballet import edit
n = 0
for y in (2023, 2025):
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%d/*.rvt' % y)), key=os.path.getsize)
    if not fs: continue
    buf = open(fs[0], 'rb').read()
    for spec in ({'op': 'set_type_eid', 'eid': 1, 'pid': 2, 'target': 3}, {'op': 'set_type_material', 'eid': 1, 'target': 3}):
        try:
            op = edit.validate_op(dict(spec)); edit.apply_full(buf, [op])
        except edit.EditError as e:
            m = str(e); assert "only verified on Revit 2024/2026" in m, (y, spec["op"], m[:120]); n += 1
        else: raise AssertionError('accepted on %d: %s' % (y, spec['op']))
print('ok: %d refusals' % n if n else 'skip: no samples')
