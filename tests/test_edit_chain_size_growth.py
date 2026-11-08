"""c1x-rvtsave 224: 15 chained Comments edits (alternating long/short values) on the Autodesk 2024 Construction template: file size must not grow without bound (<= source + 5%), olefile opens the final file, and the final readback equals the last value with all other elements equal to the source."""
import os, sys, io, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import olefile, rvt_params
from rvtballet import edit
S = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
buf = open(S, 'rb').read(); P0 = rvt_params.params(S); E = next(e for e, d in P0.items() if g(d).get('Comments') == '')
cur = buf; sizes = []
for i in range(15):
    v = ('L%d' % i) * (1000 if i % 2 else 3)
    cur, _ = edit.apply_full(cur, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': v})]); sizes.append(len(cur))
print('source', len(buf), 'sizes', sizes[:3], '...', sizes[-3:])
assert max(sizes) <= len(buf) * 1.05, ('size grew', max(sizes), len(buf))
olefile.OleFileIO(io.BytesIO(cur)).close()
P = params(cur); assert g(P[E]).get('Comments') == v
bad = [e for e in P0 if e != E and (e not in P or g(P0[e]) != g(P[e]))]; assert not bad, bad[:5]
print('OK')
