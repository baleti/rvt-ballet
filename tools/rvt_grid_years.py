"""Grid move across Revit years (Autodesk samples, local): move up to 3 Grids by 1 ft along their normal (tries y then x) via edit.apply_full (needs RVTBALLET_ENABLE_LEVELMOVE=1), gate witness save._readback with the right and a wrong declaration.
usage: tools/rvt_grid_years.py FILE.rvt   (aggregate lines only)"""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
import rvt_geometry as G
from rvtballet import save, edit
buf = open(sys.argv[1], 'rb').read(); sg = save._import()
gr = [e for e, v in G.file_geometry_index(sys.argv[1]).items() if str(v) == 'Grid']
print('grids', len(gr))
ok = bad = esc = 0
for e in gr[:3]:
    mk = lambda d, ax: edit.validate_op({'op': 'move', 'eid': e, 'dx': d if ax == 'x' else 0.0, 'dy': d if ax == 'y' else 0.0, 'dz': 0.0})
    for ax in 'yx':
        try: nb = edit.apply_full(buf, [mk(1.0, ax)])[0]; break
        except edit.EditError as x:
            if 'in-plane' not in str(x): print('edit refused', e, str(x)[:100]); nb = None; break
    else: nb = None
    if nb is None: bad += 1; continue
    try: save._readback(buf, nb, [mk(1.0, ax)]); ok += 1
    except sg.VerifyFailed as x: print('honest refused', e, str(x)[:120]); bad += 1
    try: save._readback(buf, nb, [mk(5.0, ax)]); esc += 1; print('ESCAPE', e)
    except sg.VerifyFailed: pass
print('ok', ok, 'refused', bad, 'ESCAPE', esc)
