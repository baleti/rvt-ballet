"""moving elements inside a family file (.rfa, Autodesk racbasicsamplefamily 2023, local copy): RefPlane / ExtrusionElem / CurveElem / LinearDimString must not be accepted silently (no validated move for family-editor geometry); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = '~/rvt-samples/racbasicsamplefamily-2023.rfa'
from rvtballet import edit
if not os.path.exists(F): print('skip'); sys.exit(0)
buf = open(F, 'rb').read(); bad = 0
for name, eid in (('RefPlane', 46), ('ExtrusionElem', 82), ('CurveElem', 85), ('LinearDimString', 442)):
    try: edit.apply_full(buf, [edit.validate_op({'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})]); print('ACCEPTED', name); bad += 1
    except edit.EditError as e: print('refused', name, str(e)[:80])
    except Exception as e: print('raised', name, type(e).__name__); bad += 1
sys.exit(1 if bad else 0)
