"""c5x-rvttype item 59: tools/rvt_dup_type_gen.py must refuse Revit 2020/2023/2025 files and write NO output file. Autodesk samples only; each year skipped if the sample is absent."""
import os, sys, glob, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); gen = os.path.join(H, '..', 'tools', 'rvt_dup_type_gen.py')
bad = 0; ran = 0
for y in (2020, 2023, 2025):
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%d/*.rvt' % y)))
    if not fs: print('skip', y); continue
    out = os.path.join(tempfile.mkdtemp(), 'o.rvt'); ran += 1
    r = subprocess.run([sys.executable, gen, fs[0], out, '1000', 'ZZ'], capture_output=True, text=True, timeout=600)
    msg = (r.stdout + r.stderr)
    if r.returncode == 0 or os.path.exists(out) or 'REFUSED' not in msg or str(y) not in msg: print('FAIL', y, r.returncode, msg[-150:]); bad += 1
    else: print('refused', y)
sys.exit(1 if bad else 0)
