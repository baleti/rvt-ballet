"""TextNote move across Revit years (Autodesk samples, local): move the first TextNote by (1,2,0) via edit.apply_full, gate witness save._readback with the right and a wrong declaration.
usage: tools/rvt_textnote_years.py FILE.rvt   (aggregate lines only)"""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
import rvt_geometry as G
from rvtballet import save, edit
buf = open(sys.argv[1], 'rb').read(); sg = save._import()
tn = [e for e, v in G.file_geometry_index(sys.argv[1]).items() if str(v) == 'TextNote']
print('textnotes', len(tn))
if not tn: sys.exit(0)
ok = bad = esc = 0
for e in tn[:3]:
    mk = lambda dx: edit.validate_op({'op': 'move', 'eid': e, 'dx': dx, 'dy': 2.0, 'dz': 0.0})
    try: nb = edit.apply_full(buf, [mk(1.0)])[0]
    except Exception as x: print('edit refused', e, str(x)[:100]); bad += 1; continue
    try: save._readback(buf, nb, [mk(1.0)]); ok += 1
    except sg.VerifyFailed as x: print('honest refused', e, str(x)[:120]); bad += 1
    try: save._readback(buf, nb, [mk(5.0)]); esc += 1; print('ESCAPE', e)
    except sg.VerifyFailed: pass
print('ok', ok, 'refused', bad, 'ESCAPE', esc)
