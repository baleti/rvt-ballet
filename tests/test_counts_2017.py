"""counts on a Revit 2017 corpus file must say categories are UNKNOWN (rc 2), not print an empty table as if the model were empty. c9x-rvtcat"""
import os, sys, glob, subprocess
fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2017/*.rvt')))
if not fs: print('skip'); sys.exit(0)
r = subprocess.run([sys.executable, '-m', 'rvtballet', 'counts', fs[0]], cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), capture_output=True, text=True)
assert r.returncode == 2 and 'UNKNOWN' in r.stderr and r.stdout == '', (r.returncode, r.stderr[:200], r.stdout[:100])
print('ok')
