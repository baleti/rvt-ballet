"""c5x-rvttype: set_type_eid on the Autodesk 2026 HVAC sample (symbol 579392, param 579119, currently -> 579117) refuses: same value, nonexistent target, wrong-class target, wrong pid, non-symbol element, non-positive ids. Nothing may be produced. Skips if the sample is absent."""
import os, sys, glob
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')]
os.environ.update(RVT_GEOM='1', RVTBALLET_ENABLE_TYPEEID='1', RVTBALLET_ENABLE_TYPEPARAM='1', RVTBALLET_EDIT_BACKEND='rvtedit')
fs = glob.glob(os.path.expanduser('~/rvt-research/corpus/2026/54_*HVAC*.rvt'))
if not fs: print('skip'); sys.exit(0)
from rvtballet import edit
buf = open(fs[0], 'rb').read(); bad = 0
B = {'op': 'set_type_eid', 'eid': 579392, 'pid': 579119, 'target': 579118}
cases = {'same_value': dict(B, target=579117), 'nonexistent_target': dict(B, target=987654321), 'wrong_class_target': dict(B, target=22785), 'wrong_pid': dict(B, pid=1234567), 'not_a_symbol': dict(B, eid=22785), 'zero_target': dict(B, target=0), 'negative_pid': dict(B, pid=-5)}
for n, o in cases.items():
    try: edit.apply_full(buf, [edit.validate_op(o)]); print('FAIL accepted', n); bad += 1
    except edit.EditError as e: print('refused', n, '|', str(e)[:70])
    except Exception as e: print('FAIL non-EditError', n, type(e).__name__, str(e)[:60]); bad += 1
try: out, _ = edit.apply_full(buf, [edit.validate_op(B)]); print('control ok', len(out))
except Exception as e: print('FAIL control', e); bad += 1
sys.exit(1 if bad else 0)
