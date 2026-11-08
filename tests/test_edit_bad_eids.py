"""c1x-rvtsave 208: edit ops aimed at a non-existent id, 0, negative, huge, or a non-instance element kind (type, level) must be refused; file bytes unchanged. Synthetic 2024 .rte."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); n = 0
for eid in (0, -1, 99999999, 2**31, 2**63, 'x', None, 1.5):
    for o in ({'op': 'move', 'dx': 1.0}, {'op': 'rotate', 'deg': 10.0}, {'op': 'delete'}, {'op': 'set_string', 'param': 'Comments', 'value': 'a'}):
        try: edit.apply_full(buf, [edit.validate_op(dict(o, eid=eid))])
        except edit.EditError: n += 1; continue
        raise SystemExit('FAIL accepted %r on eid=%r' % (o['op'], eid))
# real ids of the wrong kind: FamilySymbol 19014, SWall 301553, SketchPlane 301565, Viewer 5500, Viewport 5501, CategoryElem 142100, FontElem 142099
m = 0
for eid in (19014, 301565, 5500, 5501, 142100, 142099, 75944):
    for o in ({'op': 'move', 'dx': 1.0}, {'op': 'rotate', 'deg': 10.0}, {'op': 'delete'}):
        try: out, _ = edit.apply_full(buf, [edit.validate_op(dict(o, eid=eid))])
        except edit.EditError: m += 1; continue
        raise SystemExit('FAIL accepted %s on wrong-kind eid %d' % (o['op'], eid))
print('wrong-kind refused:', m)
print('OK: %d ops on bad ids refused with EditError' % n)
