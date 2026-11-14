"""c3x-rvttype item 62: set_type_num / set_type_eid / set_type_material must be refused (nothing written) on a Revit 2025 file (only 2024/2026 verified). Autodesk 2025 HVAC sample; skipped if absent."""
import os, sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')]
os.environ.update(RVT_GEOM='1', RVTBALLET_ENABLE_TYPEEID='1', RVTBALLET_ENABLE_TYPEPARAM='1', RVTBALLET_EDIT_BACKEND='rvtedit')
f = os.path.expanduser('~/rvt-research/corpus/2025/48_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(f): print('skip'); sys.exit(0)
from rvtballet import edit
buf = open(f, 'rb').read(); bad = 0
for o in ({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.2}, {'op': 'set_type_eid', 'eid': 1379030, 'pid': 579117, 'target': 579118}, {'op': 'set_type_material', 'eid': 378, 'target': 751}):
    try: edit.apply_full(buf, [edit.validate_op(o)]); print('FAIL: accepted', o['op']); bad += 1
    except edit.EditError as e:
        if '2025' in str(e): print('refused', o['op'])
        else: print('FAIL: refused for another reason', o['op'], str(e)[:80]); bad += 1
sys.exit(1 if bad else 0)
