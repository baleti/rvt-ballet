"""rvt_diff must not report blob entries (ids 0 / 8192000) as removed elements; a real delete (301592) must still show. Uses local Autodesk-sample pairs in ~/c2x-diff; skips if absent."""
import os, sys, subprocess, re
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_diff.py'); D = os.path.expanduser('~/c2x-diff')
def run(a, b): return subprocess.run([sys.executable, T, a, b, '--nofields'], capture_output=True, text=True, timeout=600).stdout
fl = (D + '/c7flr/base.rvt', D + '/c7flr/after.rvt'); dl = (D + '/del1/base.rte', D + '/del1/after.rte')
if not all(os.path.exists(p) for p in fl + dl): print('skip'); sys.exit(0)
o = run(*fl); assert re.search(r'removed 0 \[\]', o), o
o = run(*dl); assert 'removed 1 [301592]' in o, o
print('diff phantom removal OK')
