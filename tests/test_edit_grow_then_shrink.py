"""c6x-rvtmatrix: grow Comments to 4096 chars, then set it back to the original empty value on the edited bytes (two successive edits): all params of every element equal the original again; reports whether the bytes are also identical. Autodesk 2024 Construction template."""
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
S = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
P0 = rvt_params.params(S); E = next(e for e, d in P0.items() if g(d).get('Comments') == '')
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
b1, _ = edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': '界' * 4096})])
b2, _ = edit.apply_full(b1, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': '', 'match': '界' * 4096})])
P2 = params(b2); bad = [e for e in P0 if e not in P2 or g(P0[e]) != g(P2[e])]
print('len', len(buf), len(b1), len(b2), 'bytes identical to original:', b2 == buf, 'params differing:', len(bad))
assert not bad, bad[:5]
print('OK')
try: edit.apply_full(b1, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'z', 'match': '界' * 59 + 'X'})]); raise SystemExit('FAIL: stale match accepted')
except edit.EditError as e: print('stale match refused:', str(e)[:40])
try: edit.apply_full(b1, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'z', 'match': '界' * 4095 + 'X'})]); raise SystemExit('FAIL: tail-different match accepted')
except edit.EditError as e: print('tail-different match refused')
