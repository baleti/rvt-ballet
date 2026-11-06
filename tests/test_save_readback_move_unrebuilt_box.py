"""(severity-1 gap found by c2x-rvtsave, fixed) Autodesk 2026 HVAC sample: for most FamilyInstances the writer does not rebuild the cached tessellation, so the bounding box is unchanged after a move and the displacement check was skipped. Bytes moved by dx=7 under a declared dx=1 passed the read-back unseen. Now the record origin is the fallback witness: a wrong displacement is refused, the correct one still passes."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
S = os.path.expanduser('~/rvtfix/corpus/2026/54_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('skip'); sys.exit(0)
from rvtballet import save, edit
buf = open(S, 'rb').read(); pr = save._read_params(buf)
mv = lambda e, dx: edit.validate_op({'op': 'move', 'eid': e, 'dx': dx})
n = 0
for e in [e for e, v in sorted(pr.items()) if e >= 1000 and v.get('class') == 'FamilyInstance'][:60]:
    b0 = save._bbox_of(buf, e)
    if b0 is None: continue
    nb7, _ = edit.apply_full(buf, [mv(e, 7.0)])
    if save._bbox_of(nb7, e) != b0: continue      # only the unrebuilt-box case matters here
    n += 1
    try: save._readback(buf, nb7, edit.compose([mv(e, 1.0)])); raise SystemExit('ESCAPE: dx=7 bytes accepted under declared dx=1 on element %d' % e)
    except save._import().VerifyFailed: pass
    save._readback(buf, nb7, edit.compose([mv(e, 7.0)]))      # the honest move still passes
    if n >= 3: break
assert n, 'no element with an unrebuilt box found'
print('unrebuilt-box move displacement witnessed on %d elements: wrong refused, right accepted' % n)
