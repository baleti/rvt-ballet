#!/usr/bin/env python3
"""rvt_aw_auto.py SRC.rvt DST.rvt X0 Y0 X1 Y1 [HEIGHT] [YEAR]: add one straight wall to an ARBITRARY project by discovering level/type/phase/likeWall
from its first existing wall (SWall), then calling the write-lab clone-and-patch (rvtedit aw). Autodesk samples / synthetic only; writes DST only."""
import os, sys, subprocess
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'):
    sys.path.insert(0, os.path.expanduser(p))
import rvt_geometry as G
import rvtedit
src, dst = sys.argv[1], sys.argv[2]; x0, y0, x1, y1 = sys.argv[3:7]
h = sys.argv[7] if len(sys.argv) > 7 else '10'; year = sys.argv[8] if len(sys.argv) > 8 else '2024'
import math
try: _v = [float(x) for x in (x0, y0, x1, y1, h)]
except ValueError: sys.exit('REFUSED: wall coordinates and height must be numbers')
if not all(math.isfinite(v) for v in _v) or any(abs(v) > 1e6 for v in _v): sys.exit('REFUSED: non-finite or absurd (> 1e6 ft) wall coordinate/height')
if math.hypot(_v[2] - _v[0], _v[3] - _v[1]) < 0.01: sys.exit('REFUSED: wall shorter than 0.01 ft (Revit minimum is ~0.0026 ft; zero length is a degenerate wall)')
if _v[4] <= 0 or _v[4] > 3000: sys.exit('REFUSED: wall height must be in (0, 3000] ft')
ix = G.file_geometry_index(src)
walls = sorted(e for e, v in ix.items() if str(v) == 'SWall')
if not walls: sys.exit('no existing wall to take type/level/phase from')
import re
ed = rvtedit.Edit(src); e = ed.g.e
def eid(v):
    m = re.match(r"EID\((\d+)\)", str(v)); return int(m.group(1)) if m else None
w = walls[0]; tr = e.trace(w)
f = {l[1]: l[4] for l in tr[3] if len(l) > 4}
typ = eid(f['VWall.m_WallAttributesId']); ph = eid(f['Element.m_createdPhaseId']); lv = eid(f['Element.m_assocLevelId'])
org = [l[4] for l in e.trace(lv)[3] if len(l) > 4 and l[1] == 'Plane.m_origin'][0]
lz = float(str(org).strip('[]').split(',')[2])
op = 'aw:%s:%s:%s:%s:%s:%d:%r:%d:%d:%d' % (x0, y0, x1, y1, h, lv, lz, typ, ph, w)
print('OP', op, flush=True)
env = dict(os.environ, YEAR=year)
sys.exit(subprocess.call([sys.executable, os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py'), src, dst, op], env=env))
