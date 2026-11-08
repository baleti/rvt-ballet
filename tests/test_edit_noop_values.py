"""c1x-rvtsave 220: no-op set_string (Comments set to the value it already has) on the Autodesk 2024 Construction template: refused or readback of every element unchanged. (Move 0 and rotate 0 not covered.)"""
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
cases = {'set_same': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': ''}}
for name, op in cases.items():
    try: out, _ = edit.apply_full(buf, [edit.validate_op(op)])
    except edit.EditError as e: print(name, 'refused:', str(e)[:80]); continue
    P1 = params(out); bad = [e for e in P0 if e not in P1 or g(P0[e]) != g(P1[e])]
    print(name, 'identical bytes' if out == buf else 'bytes differ', 'changed elements:', len(bad)); assert not bad, bad[:5]
print('OK')
