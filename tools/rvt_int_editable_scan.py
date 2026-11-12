"""Which reader-level Int choice candidates are really editable (stored ParamValueInt)? For each candidate param (2..8 distinct small values in the file) try a same-value set_num through edit.apply_full on its first element: prints ACCEPT/REFUSE + reason. Usage: rvt_int_editable_scan.py file.rvt [maxparams]. Autodesk samples only for public use."""
import sys, os, collections, json
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
from rvtballet import save, edit
b = open(sys.argv[1], 'rb').read(); pr = save._read_params(b); N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
PER = int(os.environ.get('PER', '1')); vals = collections.defaultdict(collections.Counter); first = {}; elems = collections.defaultdict(list)
for e, d in sorted(pr.items()):
    if e < 1000: continue
    for n, v in d.get('params', d).items():
        if isinstance(v, int) and not isinstance(v, bool) and '|' not in n: vals[n][v] += 1; first.setdefault(n, (e, v)); (len(elems[n]) < PER and elems[n].append((e, v)))
cands = sorted([(n, sorted(c), sum(c.values())) for n, c in vals.items() if 2 <= len(c) <= 8 and min(c) >= 0 and max(c) <= 64], key=lambda x: -x[2])[:N]
for n, vs, k in cands:
    for e, v in elems[n]:
        try: edit.apply_full(b, [edit.validate_op({'op': 'set_num', 'eid': e, 'param': n, 'value': v, 'kind': 'Int'})]); print('ACCEPT', n, vs, k, 'eid', e, flush=True); break
        except Exception as ex: print('REFUSE', n, vs, k, 'eid', e, type(ex).__name__, str(ex)[:90].replace('\n', ' '), flush=True)
print('done')
