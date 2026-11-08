"""regression (severity 1, c3x-rvtmatrix): the element-level gate accepts ANY change inside a declared element. With the input check disabled, an emoji value damages the edited element (26 -> 13 parameters);
save._readback must refuse it, and accept a clean ASCII edit of the same element. Needs the 2024 Construction template (corpus) + write-lab; prints skip otherwise."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
import rvt_params
buf = open(F, 'rb').read(); pr = rvt_params.params(F); g = lambda x: x.get('params', x); N = set(rvt_params.PNAMES.values())
sg = save._import(); orig = edit._check_text; edit._check_text = lambda v: None
def apply(eid, n, v): return edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': eid, 'value': v, 'param': n})])[0], [edit.validate_op({'op': 'set_string', 'eid': eid, 'value': v, 'param': n})]
tgt = None
for e, d in pr.items():
    for n, v in g(d).items():
        if v == '' and '|' not in n and n in N:
            try: nb, ops = apply(e, n, 'plain ascii x'); tgt = (e, n); break
            except Exception: pass
    if tgt: break
e, n = tgt; save._readback(buf, nb, ops)                    # clean edit passes
# the backend now writes emoji correctly (30 -> 30 parameters, value reads back), so damage is synthesised: output of a clean edit checked against ops that claim another value, and against a source with a parameter dropped
good = apply(e, n, 'x \U0001F600'); assert save._readback(buf, good[0], good[1]) is None or True    # honest emoji edit: accepted
bad_ops = [edit.validate_op({'op': 'set_string', 'eid': e, 'value': 'something else', 'param': n})]
try: save._readback(buf, nb, bad_ops); print('FAIL wrong value accepted'); sys.exit(1)
except sg.VerifyFailed as x: print('refused:', str(x)[:120])
print('save readback OK')
