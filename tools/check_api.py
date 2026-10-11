"""cross-check the reader's published geometry API (rvt_geometry, GEOMETRY_API.md) against the viewer's own builders: per class, how many elements the API calls exact/approx/box and how its bbox
compares with ours. Re-run when the reader publishes new classes: a class whose API confidence is 'exact' while ours is approximate/box is a candidate to switch to the API.
usage: tools/check_api.py FILE.rvt"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import numpy as np
import rvt_geometry as GG
from rvtviewer import reader, build
f = sys.argv[1]; ctx = build.Ctx(reader.cached_load(f)); idx = GG.file_geometry_index(f); rows = collections.defaultdict(lambda: collections.Counter())
for e, r in ctx.recs.items():
    if e not in idx: continue
    try: a = GG.element_geometry(f, e)
    except Exception: rows[r['class']]['api-error'] += 1; continue
    if a['confidence'] == 'none': continue
    res = build.element_mesh(ctx, e, r); mine = res[1] if res else 'none'
    rows[r['class']]['api=%s mine=%s' % (a['confidence'], mine)] += 1
for c, v in sorted(rows.items(), key=lambda kv: -sum(kv[1].values())): print(c, dict(v))
