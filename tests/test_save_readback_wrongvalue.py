"""regression: right element, right parameter, WRONG value. The output carries 'value A' but the declared op says 'value B': save._readback must refuse (the element-level gate alone accepts any change inside a declared element); a no-op output too."""
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
e, n = tgt
nbA, opsA = apply(e, n, 'value A')
_, opsB = apply(e, n, 'value B')
save._readback(buf, nbA, opsA)                         # honest edit passes
for label, out, ops in (('wrong value', nbA, opsB), ('no-op output', buf, opsA)):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
print('save readback wrong-value OK')

# numeric: right element and parameter, WRONG number
sys.path.insert(0, os.path.expanduser('~/rvt-research/edit-lab')); import rvtedit
base = {e: dict(g(d)) for e, d in pr.items()}; ed = rvtedit.Edit(F); pick = None
for eid in list(pr)[:3000]:
    try: pn, i, r, log, q = ed.g.e.trace(eid)
    except Exception: continue
    if ed.latest_partition(eid) != pn: continue
    for l in log:
        if l[1] == 'ParamValueDouble.m_paramId':
            v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v - (1 << 32) if (1 << 31) <= v < (1 << 32) else v; nm = rvt_params.PNAMES.get(str(pid)); val = base.get(eid, {}).get(nm) if nm else None
            if nm and isinstance(val, float): pick = (eid, nm, val); break
    if pick: break
eid, nm, v0 = pick; del ed
mk = lambda x: edit.validate_op({'op': 'set_num', 'eid': eid, 'param': nm, 'value': x, 'kind': 'Double'})
nbN, _ = edit.apply_full(buf, [mk(v0 + 0.25)])
save._readback(buf, nbN, [mk(v0 + 0.25)])              # honest number passes
try: save._readback(buf, nbN, [mk(v0 + 7.0)]); print('FAIL wrong number accepted'); sys.exit(1)
except sg.VerifyFailed as x: print('refused wrong number:', str(x)[:100])
print('save readback wrong-number OK')

# Int: right element and parameter, WRONG integer (reader returns int; honest 2 passes, requested 3 vs written 2 refused)
mi = lambda x: edit.validate_op({'op': 'set_num', 'eid': 356, 'param': 'Detail Level', 'value': x, 'kind': 'Int'})
nbI, _ = edit.apply_full(buf, [mi(2)])
save._readback(buf, nbI, [mi(2)])                      # honest integer passes
try: save._readback(buf, nbI, [mi(3)]); print('FAIL wrong integer accepted'); sys.exit(1)
except sg.VerifyFailed as x: print('refused wrong integer:', str(x)[:100])
print('save readback wrong-int OK')
