"""regression: a wall MOVE whose output carries a different displacement (or none) must be refused by save._readback; the honest move passes. The wall's placement origin (Trf.m_or) is the witness (the geometry reader has no mesh for a moved wall)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_MOVE_ANY'] = '1'      # wall move has no Revit-verified implementation (policy refuses it at edit time); this test exercises the readback witness, offline
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); E = 301557      # 301557 carries a real location-line move; 301553-301556 only move a cell pattern origin (refused below)
mk = lambda dx, dy, dz: edit.validate_op({'op': 'move', 'eid': E, 'dx': dx, 'dy': dy, 'dz': dz})
a, b = mk(1.0, 2.0, 0.5), mk(2.0, 2.0, 0.5)
na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest wall move refused:', str(x)[:150]); sys.exit(1)
for label, out, ops in (('wrong amount', na, [b]), ('unmoved output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
# walls whose move only shifts the pattern origin (location line unchanged) are refused: 301556 then does not open in Revit 2024
for w in (301553, 301556):
    o = edit.validate_op({'op': 'move', 'eid': w, 'dx': 1.0})
    try: save._readback(buf, edit.apply_full(buf, [o])[0], [o]); print('FAIL accepted pattern-only wall move', w); sys.exit(1)
    except sg.VerifyFailed as x: print('refused pattern-only wall move', w + 0)
print('save readback wall move OK')

# linear dimension (Trf.m_or moves by the displacement as for walls)
ix = None
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
import rvt_geometry as G
dim = next((e for e, v in G.file_geometry_index(F).items() if str(v) == 'LinearDimString'), None)
if dim is None: print('no LinearDimString in the scene: dimension part skipped')
else:
    # policy (edit.py): a moved dimension record is not honoured by Revit, so the move is refused at edit time (the old readback-witness part of this test can no longer be reached)
    da = edit.validate_op({'op': 'move', 'eid': dim, 'dx': 1.0, 'dy': 2.0, 'dz': 0.5})
    try: edit.apply_full(buf, [da]); print('FAIL dimension move was not refused'); sys.exit(1)
    except edit.EditError as x: assert 'dimension' in str(x); print('dimension move refused at edit time:', str(x)[:80])
    print('save readback dim move OK (refusal)')
