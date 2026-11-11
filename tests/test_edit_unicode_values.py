"""c6x-rvtmatrix item 9: set_string with non-ASCII values (CJK, accents, emoji beyond BMP, long) on Comments of the Autodesk 2024 Construction template: exact readback of the edited element, every other element's params identical, or an honest refusal."""
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
cases = {'cjk': '日本語テスト 漢字', 'accents': 'Ünïcödé àéîõü ß', 'emoji': 'ok \U0001F600\U0001F680 end', 'long': '界' * 300}
for name, val in cases.items():
    try: out, _ = edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': val})])
    except edit.EditError as e: print(name, 'refused:', str(e)[:80]); continue
    P1 = params(out); got = g(P1[E]).get('Comments')
    bad = [e for e in P0 if e != E and (e not in P1 or g(P0[e]) != g(P1[e]))]
    print(name, 'readback', 'EXACT' if got == val else repr(got)[:60], 'other changed:', len(bad)); assert got == val and not bad, (name, bad[:5])
print('OK')
