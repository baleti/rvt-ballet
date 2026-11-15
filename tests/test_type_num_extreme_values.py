"""c1x-rvttype: extreme but finite values for set_type_num (negative, 0, subnormal, 1e14, -1e14) absurd magnitudes (|v|>1e6, subnormals) are refused up front (Revit behaviour unverified); the others round-trip exactly through the reader; never a silently different value. Autodesk 2024 HVAC symbol 1379030 'Slot Width'."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path[:0] = [os.path.expanduser('~/rvt-research')]
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); ref = []
for v in (-5.0, 0.0, 5e-324, 1e14, -1e14, 0.1 + 0.2):
    try:
        op = edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': v}); out = edit.apply_full(buf, [op])[0]
        save._readback(buf, out, [op]); print('applied+readback ok', v)
    except Exception as x:
        print('refused', v, type(x).__name__, str(x)[:70]); ref.append(v)
assert sorted(ref) == sorted([-5.0, 5e-324, 1e14, -1e14]), ref      # negatives and absurd magnitudes refused; 0.0 and 0.1+0.2 round-trip (Revit 2024 opened zero clean twice, p_zero3)
print('ok: negatives and absurd magnitudes refused, 0.0 accepted, 0.30000000000000004 round-trips')
