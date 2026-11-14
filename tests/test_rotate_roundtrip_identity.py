"""# RVT_TEST_TIMEOUT=900. c1x-rvtsave: rotate +30 then -30 of the same placed instance (write-lab synthetic 2024 house1, eid 301605) must give a byte-identical file (no float drift, no stray bytes), and a plain +30 must be deterministic across two runs and change exactly 1 element."""
import os, sys, subprocess, hashlib, tempfile
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_house1.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
H = os.path.dirname(os.path.abspath(__file__))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(op, out):
    r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', 'rvt_one_edit.py'), SRC, op, out], capture_output=True, text=True, timeout=800)
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:]
    assert "'result': 'OK'" in last, last[-500:]
    return last
d = tempfile.mkdtemp()
rt = run('[{"op":"rotate","eid":301605,"deg":30.0},{"op":"rotate","eid":301605,"deg":-30.0}]', d + '/rt.rte')
assert sha(d + '/rt.rte') == sha(SRC), 'rotate +30/-30 not byte identical'
a = run('{"op":"rotate","eid":301605,"deg":30.0}', d + '/a.rte'); run('{"op":"rotate","eid":301605,"deg":30.0}', d + '/b.rte')
assert "'elements_changed': 1" in a and sha(d + '/a.rte') == sha(d + '/b.rte') and sha(d + '/a.rte') != sha(SRC)
print('OK rotate round trip identical, rotate deterministic')
