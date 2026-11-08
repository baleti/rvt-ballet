"""In-place SAVE! (overwrite ON) of pre-2024 Autodesk sample projects (local corpus, one per year 2017-2023): must be refused cleanly (415 unsupported_version), source byte-identical, no leftovers. Guards the 'writer covers 2024-2026 only' boundary: a regression that let an old-year file through unverified would be a corruption risk. Skips when the corpus is absent."""
import os, sys, glob, subprocess
here = os.path.dirname(os.path.abspath(__file__))
fs = []
for y in range(2017, 2024):
    g = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%d/*rst_basic*.rvt' % y)))
    if g: fs.append(g[0])
if not fs: print('skip'); sys.exit(0)
r = subprocess.run([sys.executable, os.path.join(here, '..', 'tools', 'rvtsave_noedit_sweep.py')] + fs, capture_output=True, text=True, timeout=1200)
out = r.stdout; print(out)
assert 'bad=0' in out and out.count('415 unsupported_version identical=True leftovers=[]') == len(fs), out + r.stderr[-500:]
print('old-year in-place SAVE! refused cleanly on', len(fs))
