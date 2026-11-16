"""rvt_join_cleanup refuses Facades 2024 column 593361 (joins live in m_affectedEdgesTags, no output written, source untouched)."""
import os, sys, hashlib, subprocess, tempfile, shutil
S = os.path.expanduser('~/rvtfix/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
if not os.path.exists(S): print('skip'); sys.exit(0)
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = tempfile.mkdtemp(dir=os.path.expanduser('~/c3x-tmp-c4x'))
try:
    b = sha(S); o = d + '/o.rvt'
    p = subprocess.run([sys.executable, R + '/tools/rvt_join_cleanup.py', S, o, '593361'], capture_output=True, text=True)
    print('rc', p.returncode, (p.stderr or p.stdout).strip().splitlines()[-1][:160])
    assert p.returncode != 0 and not os.path.exists(o) and sha(S) == b
    print('ok refused')
finally: shutil.rmtree(d, ignore_errors=True)
