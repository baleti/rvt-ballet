"""one-shot: python datums3d_worker.py FILE.rvt (rvt-sheets python) -> JSON {levels: {eid: {o, x, y, env}}, grids: {...}}: the datum planes (origin, in-plane axes, envelope rectangle in plane coordinates, feet)
that Revit draws in 3D views as dashed lines along the envelope edges."""
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/src/rvt-sheets'))
from rvtsheets.reader import File, ob, path, INVALID

f = File(sys.argv[1]); out = {'levels': {}, 'grids': {}}
for r in f.recs('Level', 'Grid'):
    fl = r['fields']; srf = ob(fl.get('m_pSurface')) or {}
    if not srf.get('m_origin'): continue
    uo = f.eid(fl.get('m_unplacedOwnerId'))
    if uo not in (None, INVALID, -1): continue
    env = path(srf, 'm_Envelope', 'm_corners')
    if not env: continue
    out['levels' if r['class'] == 'Level' else 'grids'][str(r['id'])] = {'o': [float(v) for v in srf['m_origin']], 'x': [float(v) for v in srf['m_xVec']], 'y': [float(v) for v in srf['m_yVec']], 'env': [[float(a), float(b)] for a, b in env]}
json.dump(out, sys.stdout)
