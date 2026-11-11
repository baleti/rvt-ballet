"""c9x-rvttype: set_type_material reproduces the Revit-made record of pair c1xmatas (SysMullionFamSym 378, Material 1075 -> 751, Structural 2024): record equals the Revit after-record except the 2-byte back-pointer; same material, non-material target, missing target and bad element are refused. Needs ~/c2x-diff/c1xmatas; skips if absent."""
import os, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.expanduser('~/c2x-diff/c1xmatas/base.rvt'); A = os.path.expanduser('~/c2x-diff/c1xmatas/after.rvt')
if not (os.path.exists(B) and os.path.exists(A)): print('skip: pair absent'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEEID'] = '1'; os.environ['RVT_GEOM'] = '1'
sys.path[:0] = [H, os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
from rvtballet import edit
import rvtgen
buf = open(B, 'rb').read()
def rec(f, eid=378):
    g = rvtgen.Gen(f); pn, i, r, log, q = g.e.trace(eid); return bytes(g.bj[i:q])
def run(**kw): return edit.apply_full(buf, [edit.validate_op(dict({'op': 'set_type_material', 'eid': 378, 'target': 751}, **kw))])
for lab, kw in (('same', {'target': 1075}), ('missing', {'target': 999999999}), ('not material', {'target': 378}), ('bad eid', {'eid': 999999999})):
    try: run(**kw); print('FAIL accepted', lab); sys.exit(1)
    except edit.EditError as e: print('refused', lab, str(e)[:70])
out = run(); t = tempfile.mkdtemp() + '/o.rvt'; open(t, 'wb').write(out[0])
a, b, c = rec(t), rec(A), rec(B)
d = [i for i in range(len(b)) if a[i] != b[i]]
assert len(a) == len(b) and all(i < 2 for i in d), ('differs from Revit record at', d[:20]); assert a != c
print('ok: material record equals Revit pair record; refusals fine')
