"""c1x-rvttype: set_type_eid reproduces the Revit-made record of pair c1xeid (HVAC 2024 base: symbol 579392 'Arrow Type' param 579117 -> 579118): all bytes of the record equal Revit's after-record except the 2-byte back-pointer; same-id, missing, wrong-class and non-type targets are refused. Needs ~/c2x-diff/c1xeid (local pair files); skips if absent."""
import os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.expanduser('~/c2x-diff/c1xeid/base.rvt'); A = os.path.expanduser('~/c2x-diff/c1xeid/after.rvt')
if not (os.path.exists(B) and os.path.exists(A)): print('skip: pair absent'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEEID'] = '1'; os.environ['RVT_GEOM'] = '1'
sys.path[:0] = [H, os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
from rvtballet import edit
import rvtgen
buf = open(B, 'rb').read()
def rec(f, eid=579392):
    g = rvtgen.Gen(f); pn, i, r, log, q = g.e.trace(eid); return bytes(g.bj[i:q]), log
# find the parameter id of 'Arrow Type' on the symbol: the NamedParam whose elemId is 579117
_, log = rec(B)
k = [j for j, l in enumerate(log) if l[1] == 'NamedParam.m_elemId' and edit._eid_val(l[4]) == 579117]; assert len(k) == 1, k
pid = next(edit._eid_val(log[j][4]) for j in range(k[0], min(k[0] + 12, len(log))) if log[j][1] == 'NamedParam.m_paramId')
def run(**kw):
    op = dict({'op': 'set_type_eid', 'eid': 579392, 'pid': pid, 'target': 579118}, **kw); return edit.apply_full(buf, [edit.validate_op(op)])
for lab, kw in (('same', {'target': 579117}), ('missing', {'target': 999999999}), ('not a type', {'eid': 579118 if False else 579117}), ('bad pid', {'pid': 1})):
    try: run(**kw); print('FAIL accepted', lab); sys.exit(1)
    except edit.EditError as e: print('refused', lab, str(e)[:70])
out = run(); import tempfile
t = tempfile.mkdtemp() + '/o.rvt'; open(t, 'wb').write(out[0] if isinstance(out[0], (bytes, bytearray)) else out[1])
r_out, _ = rec(t); r_rev, _ = rec(A); r_base, _ = rec(B)
diff = [i for i in range(len(r_rev)) if r_out[i] != r_rev[i]]
assert len(r_out) == len(r_rev) and all(i < 2 for i in diff), ('record differs from the Revit-made one at', diff[:20])
assert r_out != r_base
print('ok: record equals Revit pair record (except back-pointer); refusals fine')
