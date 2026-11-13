"""Pinned element (Element.m_locked=1, Revit-made witness: Grid 1363058 of the Snowdon HVAC 2024 sample pinned through the API) must be refused for move and rotate, like Revit does; the unpinned base file must not be refused for that reason.
Needs RVT_PIN_BASE / RVT_PIN_AFTER (default ~/c2x-diff/pinprobe/{base,after}.rvt, local Autodesk sample derivatives), else skipped."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
pb = os.environ.get('RVT_PIN_BASE', os.path.expanduser('~/c2x-diff/pinprobe/base.rvt'))
pa = os.environ.get('RVT_PIN_AFTER', os.path.expanduser('~/c2x-diff/pinprobe/after.rvt'))
if not (os.path.exists(pb) and os.path.exists(pa)): print('SKIP: pin witness files not present'); sys.exit(0)
from rvtballet import edit
E1 = 1363058
for op in ({'op': 'move', 'eid': E1, 'dx': 0.0, 'dy': 1.0, 'dz': 0.0}, {'op': 'rotate', 'eid': E1, 'deg': 30.0}):
    try: edit.apply_full(open(pa, 'rb').read(), [op]); raise SystemExit('FAIL: pinned %s accepted' % op['op'])
    except edit.EditError as e: assert 'pinned' in str(e), e
    try: edit.apply_full(open(pb, 'rb').read(), [op])
    except edit.EditError as e: assert 'pinned' not in str(e), e
    except Exception: pass
print('pinned move/rotate refused, unpinned not refused for pinning: OK')
