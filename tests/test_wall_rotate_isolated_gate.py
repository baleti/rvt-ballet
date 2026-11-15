"""# RVT_TEST_TIMEOUT=3600. c7x-rvtmove item 50: isolated straight wall rotate (write-lab synthetic 2026 seed with one isolated wall, eid 1037167).
With RVTBALLET_ENABLE_WALLROTATE=1 the gate accepts it (only that wall changes, span widened for this op alone); without the opt-in it is refused. Fails without the gate widening."""
import os, sys, subprocess, tempfile
SRC = os.path.expanduser('~/c1x-rm/w26/src26_isowall.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
H = os.path.dirname(os.path.abspath(__file__))
ops = '[{"op":"rotate","eid":1037167,"deg":30.0}]'
def run(env_on, ops=ops):
    d = tempfile.mkdtemp(); out = d + '/t.rvt'
    env = dict(os.environ); env.pop('RVTBALLET_ENABLE_WALLROTATE', None)
    if env_on: env['RVTBALLET_ENABLE_WALLROTATE'] = '1'
    r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', 'rvt_one_edit.py'), SRC, ops, out], capture_output=True, text=True, timeout=1700, env=env)
    return r, out
r, out = run(True)
last = (r.stdout.strip().splitlines() or [r.stderr[-400:]])[-1]
assert "'result': 'OK'" in last and os.path.exists(out), last[-500:]
assert "'elements_changed': 1" in last, last[-500:]
r2, out2 = run(False)
assert not os.path.exists(out2), 'rotate must be refused without the opt-in'
r3, out3 = run(True, '[{"op":"rotate","eid":585072,"deg":30.0}]')      # ordinary wall of the project (neighbours / joins): must stay refused even with the opt-in
assert not os.path.exists(out3), 'rotate of a non-isolated wall must be refused'
print('OK isolated wall rotate accepted with opt-in (1 element changed), refused without')
