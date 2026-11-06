"""RVTBALLET_EDITSTORE as '~' or a relative path is resolved once at import (pending edits are the user's unsaved work: they must not move with chdir). Synthetic."""
import os, sys, subprocess, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def test_resolved():
    h = tempfile.mkdtemp()
    env = dict(os.environ, HOME=h, RVTBALLET_EDITSTORE='~/es', PYTHONPATH=ROOT); env.pop('USERPROFILE', None)
    r = subprocess.run([sys.executable, '-c', 'import os\nfrom rvtballet import editstore as E\nos.chdir("/")\nprint(E.DIR)'], cwd=h, env=env, capture_output=True, text=True)
    assert r.stdout.split() == [os.path.join(h, 'es')], r.stderr[-300:]
