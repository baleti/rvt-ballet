"""which corpus sample models (map.tsv of rvt-extract-test/private: id, original path) have Revit-exported PDFs next to them? prints id, n_pdf in the model's folder / parent folder (depth<=2), local only"""
import sys, os, glob
rows = [l.rstrip('\n').split('\t') for l in open(os.path.expanduser('~/src/rvt-extract-test/private/map.tsv'))]
for r in rows:
    mid, p = r[0], r[1]; d = os.path.dirname(p); n = []
    for base in (d, os.path.dirname(d)):
        try: n.append(sum(len(fs) for _, _, f in os.walk(base) for fs in [[x for x in f if x.lower().endswith('.pdf')]] if True))
        except Exception: n.append(-1)
        if n[-1] > 400: break
    print(mid, n, os.path.basename(p)[:50], flush=True)
