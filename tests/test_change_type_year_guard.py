"""c1x-rvttype: change_type is Revit-verified on 2024/2026 only; other years must be refused before any element is touched (2022 / 2025 / 2020 samples), 2024 HVAC still works."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
from rvtballet import edit
n = 0
for y in ('2022', '2025', '2020'):
    d = os.path.expanduser('~/rvt-research/corpus/%s' % y)
    fs = [os.path.join(d, x) for x in sorted(os.listdir(d)) if x.endswith('.rvt')][:1] if os.path.isdir(d) else []
    if not fs: continue
    buf = open(fs[0], 'rb').read(); op = edit.validate_op({'op': 'change_type', 'eid': 1000, 'type_eid': 1001})
    try: edit.apply_full(buf, [op]); print('FAIL accepted', y); sys.exit(1)
    except edit.EditError as x: assert 'only verified' in str(x), (y, str(x)); n += 1
print('ok: %d unverified years refused by the year gate' % n)
