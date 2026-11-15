"""# RVT_TEST_TIMEOUT=900. c1x-rvtsave item 264: four +90 degree rotates of one placed instance in a single save (write-lab synthetic 2024 house1, eid 301605) must leave the file byte-identical to the source (no angle drift across a full turn, 0 elements changed)."""
import os, sys, subprocess, hashlib, tempfile
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_house1.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
H = os.path.dirname(os.path.abspath(__file__))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = tempfile.mkdtemp(); out = d + '/t.rte'
ops = '[' + ','.join(['{"op":"rotate","eid":301605,"deg":90.0}'] * 4) + ']'
r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', 'rvt_one_edit.py'), SRC, ops, out], capture_output=True, text=True, timeout=800)
last = (r.stdout.strip().splitlines() or [r.stderr[-400:]])[-1]
assert "'result': 'OK'" in last, last[-500:]
assert "'elements_changed': 0" in last, last[-500:]
assert sha(out) == sha(SRC), 'full turn not byte identical'
print('OK 4x90 rotate in one save is byte identical to the source')
