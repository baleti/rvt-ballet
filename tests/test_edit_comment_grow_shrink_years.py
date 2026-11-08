"""c1x-rvtsave 222: Comments edit grow then shrink then clear on Autodesk Construction templates 2021..2026: each step's readback equals the value, every other element's readback is unchanged, and clearing returns to a state whose element readbacks equal the source."""
import os, sys, glob, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
n = 0
for y in range(2021, 2027):
    fs = glob.glob(os.path.expanduser('~/rvtfix/corpus/%d/*Construction-DefaultMetric.rte' % y))
    if not fs: continue
    buf = open(fs[0], 'rb').read(); P0 = rvt_params.params(fs[0])
    E = next((e for e, d in P0.items() if g(d).get('Comments') == ''), None)
    if E is None: continue
    cur = buf
    try:
        for v in ('x' * 3000, 'y', ''):
            cur, _ = edit.apply_full(cur, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': v})])
            P = params(cur); assert g(P[E]).get('Comments') == v, (y, len(v), g(P[E]).get('Comments'))
            bad = [e for e in P0 if e != E and (e not in P or g(P0[e]) != g(P[e]))]; assert not bad, (y, len(v), bad[:5])
    except edit.EditError as e: print(y, 'refused:', str(e)[:80]); continue
    assert g(P[E]) == g(P0[E]), (y, 'cleared element differs from source'); print(y, 'OK'); n += 1
assert n; print('OK', n)
