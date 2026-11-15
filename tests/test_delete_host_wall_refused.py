"""# RVT_TEST_TIMEOUT=900. c1x-rvtsave item 268: deleting a wall that hosts doors/windows (write-lab synthetic 2024 house3, SWall 301602) with delete enabled must be refused by the verify gate (422 verify_failed, dependents would change), write no output file and leave the source bytes unchanged."""
import os, sys, subprocess, hashlib, tempfile
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
H = os.path.dirname(os.path.abspath(__file__))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
before = sha(SRC); d = tempfile.mkdtemp(); out = d + '/w.rte'
env = dict(os.environ, RVTBALLET_ENABLE_DELETE='1')
r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', 'rvt_one_edit.py'), SRC, '{"op":"delete","eid":301602}', out], capture_output=True, text=True, timeout=800, env=env)
last = (r.stdout.strip().splitlines() or [r.stderr[-400:]])[-1]
assert 'SAVEAS_REFUSED_422' in last and 'verify_failed' in last, last[-500:]
assert not os.path.exists(out), 'refused delete wrote an output file'
assert sha(SRC) == before, 'source changed'
print('OK host wall delete refused, no output, source unchanged')
