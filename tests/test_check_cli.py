"""rvt-ballet check: intact Autodesk 2024 sample -> rc 0; 16 zeroed 4 KB blocks -> rc 1 with an ECC problem; size limit -> rc 2. Skipped when the sample is absent. python tests/test_check_cli.py"""
import os, sys, shutil, subprocess, tempfile
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S) or not os.path.isdir(os.path.expanduser('~/src/savegate')): print('sample or savegate absent: skipped'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); rb = os.path.join(HERE, 'bin', 'rvt-ballet')
T = tempfile.mkdtemp()
try:
    r = subprocess.run([rb, 'check', S], capture_output=True, text=True, timeout=600); assert r.returncode == 0 and 'no damage' in r.stdout, (r.returncode, r.stdout, r.stderr[-200:])
    P = T + '/zb.rvt'; shutil.copy(S, P)
    with open(P, 'r+b') as f: f.seek(2000 * 4096); f.write(bytes(16 * 4096))
    r = subprocess.run([rb, 'check', P], capture_output=True, text=True, timeout=600); assert r.returncode == 1 and 'ECC' in r.stdout, (r.returncode, r.stdout, r.stderr[-200:])
    r = subprocess.run([rb, 'check', S], capture_output=True, text=True, env=dict(os.environ, RVT_CHECK_MB='1')); assert r.returncode == 2, r.returncode
    print('check ok')
finally: shutil.rmtree(T, ignore_errors=True)
