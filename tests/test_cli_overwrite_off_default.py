"""c1x-rvtsave: in-place saving is OFF by default. `rvt-ballet edit --in-place` must refuse (exit 2, policy text, file bytes unchanged, no temp left) when RVTBALLET_ALLOW_OVERWRITE is unset, 0, true, or empty; only '1' enables it. Uses a write-lab synthetic scene copy (skips if absent)."""
import os, sys, subprocess, hashlib, tempfile, shutil
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_house1.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = tempfile.mkdtemp(); f = d + '/m.rte'; shutil.copy(SRC, f)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); h0 = sha(f); before = sorted(os.listdir(d))
for v in (None, '0', 'true', '', 'yes'):
    env = {k: x for k, x in os.environ.items() if k != 'RVTBALLET_ALLOW_OVERWRITE'}
    if v is not None: env['RVTBALLET_ALLOW_OVERWRITE'] = v
    r = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', f, '--in-place', '--rotate', '301605', '30'], cwd=H, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 2 and 'SAVE! policy' in (r.stdout + r.stderr), (v, r.returncode, (r.stdout + r.stderr)[-300:])
    assert sha(f) == h0 and sorted(os.listdir(d)) == before, ('file or dir changed', v)
print('OK in-place refused for policy values', [None, '0', 'true', '', 'yes'])
