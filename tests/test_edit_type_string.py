"""c6x-rvtmatrix: set_string on a FamilySymbol 'Type Mark' (Autodesk 2024 Construction template) changes exactly that symbol's Type Mark and nothing else; the instance-style names 'Mark'/'Comments' on a symbol are refused or leave every element unchanged except that symbol."""
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
S = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
P0 = rvt_params.params(S)
E = next(e for e, d in P0.items() if isinstance(d, dict) and d.get('class') == 'FamilySymbol' and 'Type Mark' in g(d))
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
for pn in ('Type Mark', 'Mark', 'Comments'):
    try: out, _ = edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': pn, 'value': 'TT'})])
    except edit.EditError as e:
        print(pn, 'refused:', str(e)[:80]); assert pn != 'Type Mark', 'Type Mark must be editable'; continue
    P1 = params(out); ch = [x for x in P0 if g(P0[x]) != g(P1.get(x, {}))]
    print(pn, 'changed elements', ch, 'now', g(P1[E]).get(pn)); assert ch in ([], [E]), ch
    if pn == 'Type Mark': assert ch == [E] and g(P1[E]).get(pn) == 'TT'
print('OK')
