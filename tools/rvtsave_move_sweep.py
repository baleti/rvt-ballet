"""Sweep: for N FamilyInstances of a real RVT, move dx=1 via edit.apply_full and run the product read-back with the right and a wrong (dx=7 declared 1) declaration. Aggregate output only. usage: rvtsave_move_sweep.py FILE N"""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
from rvtballet import save, edit
buf = open(sys.argv[1], 'rb').read(); pr = save._read_params(buf); N = int(sys.argv[2])
mv = lambda e, dx: edit.validate_op({'op': 'move', 'eid': e, 'dx': dx})
VF = save._import().VerifyFailed
c = dict(tried=0, right_ok=0, right_refused=0, wrong_refused=0, ESCAPE=0, nochange=0)
for e in [e for e, v in sorted(pr.items()) if e >= 1000 and v.get('class') == 'FamilyInstance'][::7][:N]:
    c['tried'] += 1
    try: nb, _ = edit.apply_full(buf, [mv(e, 1.0)]); nb7, _ = edit.apply_full(buf, [mv(e, 7.0)])
    except Exception: c['nochange'] += 1; continue
    try: save._readback(buf, nb, edit.compose([mv(e, 1.0)])); c['right_ok'] += 1
    except VF: c['right_refused'] += 1
    try: save._readback(buf, nb7, edit.compose([mv(e, 1.0)])); c['ESCAPE'] += 1; print('ESCAPE', e)
    except VF: c['wrong_refused'] += 1
    print(c, flush=True)
print('SWEEP_DONE', c)
