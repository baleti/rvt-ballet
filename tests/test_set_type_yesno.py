"""c1x-rvttype: edit op set_type_yesno (opt-in) creates the Int set on plain FamilySymbol 378 (Structural 2024 pair c1xyn9, Export Type to IFC 0 -> 1) and the record equals Revit's after-record except the first 4 bytes (partition slot). Refusals: gate off, wrong pid, bad value, non-symbol."""
import os, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.expanduser('~/c2x-diff/c1xyn9/base.rvt'); A = os.path.expanduser('~/c2x-diff/c1xyn9/after.rvt')
if not (os.path.exists(B) and os.path.exists(A)): print('skip: pair absent'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVT_GEOM'] = '1'
sys.path[:0] = [H, os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
from rvtballet import edit
import rvtgen
op = {'op': 'set_type_yesno', 'eid': 378, 'pid': -1019013, 'value': 1}
try: edit.validate_op(op); print('FAIL gate off accepted'); sys.exit(1)
except edit.EditError as e: print('refused gate off')
os.environ['RVTBALLET_ENABLE_TYPEYESNO'] = '1'
for lab, kw in (('pid', {'pid': -1}), ('value', {'value': 2}), ('float', {'value': 1.0})):
    try: edit.validate_op(dict(op, **kw)); print('FAIL accepted', lab); sys.exit(1)
    except edit.EditError: print('refused', lab)
buf = open(B, 'rb').read()
out = edit.apply_full(buf, [edit.validate_op(op)])
data = out[0] if isinstance(out[0], (bytes, bytearray)) else out[1]
t = tempfile.mkdtemp() + '/o.rvt'; open(t, 'wb').write(data)
def rec(f):
    g = rvtgen.Gen(f); pn, i, r, log, q = g.e.trace(378); return bytes(g.bj[i:q])
a, b = rec(t), rec(A)
assert len(a) == len(b), (len(a), len(b))
d = [i for i in range(len(a)) if a[i] != b[i]]
assert all(i < 4 for i in d), d[:10]
try: edit.apply_full(data, [edit.validate_op(op)]); print('FAIL second create accepted'); sys.exit(1)
except edit.EditError: print('refused existing set')
print('PASS')
