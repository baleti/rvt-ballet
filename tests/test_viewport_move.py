"""c4x-rvtmatrix 58: Viewport move shifts exactly Viewport.m_offset and m_labelOrigin by (dx,dy); default (opt-in flag unset) refuses; dz refused. Autodesk Snowdon Structural 2024 sample (skip if absent). Revit VM verdict recorded separately (ledger)."""
import os, sys, tempfile, struct
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab')]
from rvtballet import edit
import rvtedit
S = os.path.expanduser('~/c3x-tmp-c4x/vpout/src.rvt'); E = 779995
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read()
mv = lambda **k: [edit.validate_op(dict({'op': 'move', 'eid': E}, **k))]
os.environ.pop('RVTBALLET_ENABLE_VIEWPORTMOVE', None)
try: edit.apply_full(buf, mv(dx=0.5)); raise AssertionError('viewport move applied without the opt-in flag')
except edit.EditError: pass
os.environ['RVTBALLET_ENABLE_VIEWPORTMOVE'] = '1'
try: edit.apply_full(buf, mv(dx=0.5, dz=1.0)); raise AssertionError('viewport dz move accepted')
except edit.EditError: pass
def fields(b):
    p = os.path.join(tempfile.mkdtemp(), 'x.rvt'); open(p, 'wb').write(b); ed = rvtedit.Edit(p); tr = ed.g.e.trace(E)
    body = ed.g.e.m.parts[tr[0]]['joined']; r = {}
    for l in tr[3]:
        if l[1] in ('Viewport.m_offset', 'Viewport.m_labelOrigin') and l[3] - l[2] == 24: r[l[1]] = struct.unpack_from('<3d', body, l[2])
    return r
f0 = fields(buf); out, _ = edit.apply_full(buf, mv(dx=0.5, dy=0.25)); f1 = fields(out)
for k in f0:
    d = [f1[k][i] - f0[k][i] for i in range(3)]
    assert abs(d[0] - 0.5) < 1e-9 and abs(d[1] - 0.25) < 1e-9 and d[2] == 0, (k, d)
assert len(f0) == 2
print('OK')
