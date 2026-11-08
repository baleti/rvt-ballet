"""fail-closed readback: when the OUTPUT cannot be read for the geometry/origin witness (full disk truncating a temp copy, reader error) a move/rotate must be refused, not silently unchecked
(before the fix a reader exception on the output made both witnesses None and the check was skipped). Autodesk sample 2024 writer scene; offline."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path[:0] = [os.path.expanduser('~/src/savegate'), HERE]
from rvtballet import save, edit
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); T = 301595
if not os.path.exists(RTE): print('skip'); raise SystemExit
buf = open(RTE, 'rb').read()
NAMES = ('_bbox_of', '_trf_origin', '_inst_trf', '_tris_of', '_wall_line_origin'); ORIG = {n: getattr(save, n) for n in NAMES}
for opd in ({'op': 'move', 'eid': T, 'dx': 2.0}, {'op': 'rotate', 'eid': T, 'deg': 30.0}):
    op = edit.validate_op(opd); nb, _ = edit.apply_full(buf, [op]); ops = edit.compose([op])
    save._readback(buf, nb, ops)      # sanity: passes with a readable output
    for n in NAMES:
        setattr(save, n, (lambda f: lambda b, *a: (_ for _ in ()).throw(OSError('simulated unreadable output')) if b is nb else f(b, *a))(ORIG[n]))
    try: save._readback(buf, nb, ops); raise SystemExit('FAIL: %s accepted with an unreadable output' % opd['op'])
    except save._import().VerifyFailed: pass
    finally:
        for n in NAMES: setattr(save, n, ORIG[n])
print('OK')
