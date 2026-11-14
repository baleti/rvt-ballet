"""c3x-rvttype item 58: set_type_num with the value the type already stores is refused (no needless whole-file rewrite); a real change still applies. Autodesk 2024 HVAC sample, sym 1379030 'Slot Width' = 1/12 ft. Skipped if absent."""
import os, sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')]
os.environ.update(RVT_GEOM='1', RVTBALLET_ENABLE_TYPEPARAM='1', RVTBALLET_EDIT_BACKEND='rvtedit')
f = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(f): print('skip'); sys.exit(0)
from rvtballet import edit
buf = open(f, 'rb').read(); bad = 0
try: edit.apply_full(buf, [edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.08333333333333333})]); print('FAIL: same value accepted'); bad += 1
except edit.EditError as e: print('refused same value:', str(e)[:60])
try: out = edit.apply_full(buf, [edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.2})])[0]; print('real change applied', len(out))
except Exception as e: print('FAIL: real change refused', e); bad += 1
sys.exit(1 if bad else 0)
