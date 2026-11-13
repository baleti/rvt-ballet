"""usage: rvt_record_diff.py A.rvt B.rvt EID  -> print byte offsets (and reader field names) where the element record of EID differs. Read-only; use on Autodesk samples / synthetic files only."""
import sys, os
for lib in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(lib))
import rvtedit
a, b, eid = sys.argv[1], sys.argv[2], int(sys.argv[3])
def rec(p):
    ed = rvtedit.Edit(p); tr = ed.g.e.trace(eid)
    return ed, tr[3]
ea, la = rec(a); eb, lb = rec(b)
fa = {(l[1], i): l for i, l in enumerate(la)}; fb = {(l[1], i): l for i, l in enumerate(lb)}
print('fields', len(la), len(lb))
for k in sorted(set(fa) | set(fb), key=lambda k: k[1]):
    x, y = fa.get(k), fb.get(k)
    if x is None or y is None: print('ONLY', 'A' if y is None else 'B', k); continue
    va, vb = bytes(ea.g.bj[x[2]:x[3]]), bytes(eb.g.bj[y[2]:y[3]])
    if va != vb: print('DIFF', k[0], x[2], va.hex(), '->', vb.hex())
