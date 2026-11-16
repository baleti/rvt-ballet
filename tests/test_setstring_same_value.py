"""c4x-rvtdiff 199: set-string with the value the element already has is refused with a clear message (not a gate 'not_applied'); a different value is accepted. Synthetic house3 2024 window 301610 Mark W1.0.1."""
import os, sys, tempfile, shutil, subprocess
SRC = os.path.expanduser('~/c3x-rvtdel-work/house3.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(); env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c')
try:
    shutil.copy(SRC, T + '/in.rte')
    def run(v, out):
        return subprocess.run(['rvt-ballet', 'edit', T + '/in.rte', '-o', T + '/' + out, '--set-string', '301610', 'Mark', v], capture_output=True, text=True, env=env)
    r = run('W1.0.1', 'same.rte'); t = r.stdout + r.stderr
    assert 'already has the value' in t and not os.path.exists(T + '/same.rte'), t[-400:]
    r = run('W9.9.9', 'diff.rte'); assert os.path.exists(T + '/diff.rte'), (r.stdout + r.stderr)[-400:]
    print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
