"""c1x-rvttype: tools/rvt_param_add_gen.py (shared/project parameter add experiment) must refuse non-2024 files and writing over the input, writing nothing. It used to write a 22 MB file from a 2025 sample."""
import os, sys, glob, subprocess, tempfile
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_param_add_gen.py')
d = tempfile.mkdtemp(); out = d + '/o.rvt'; n = 0
for y in ('2025', '2022', '2026'):
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%s/*.rvt' % y)))
    if not fs: continue
    r = subprocess.run([sys.executable, T, fs[0], out], capture_output=True, text=True, timeout=300)
    assert r.returncode != 0 and not os.path.exists(out) and 'REFUSED' in r.stderr + r.stdout, (y, r.stdout[-200:], r.stderr[-200:]); n += 1
if not n: print('skip: no corpus'); sys.exit(0)
print('ok: %d unverified-year files refused, nothing written' % n)
