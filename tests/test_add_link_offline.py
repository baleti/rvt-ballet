"""c5x-rvtlink: rvt_add_link on the Autodesk Snowdon HVAC 2024 sample (local file, skipped if absent): the output must add exactly the 3 link records
(RvtLinkSymbol, RvtLinkInstance, detail) and change NO existing element (savegate element diff). Revit VM verdict is recorded separately in the ledger."""
import os, sys, subprocess, tempfile
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
out = os.path.join(tempfile.mkdtemp(), 'o.rvt')
r = subprocess.run([sys.executable, os.path.join(HERE, 'tools/rvt_add_link.py'), SEED, out, '--src', '1363937'], capture_output=True, text=True)
assert r.returncode == 0 and os.path.exists(out), r.stderr[-300:]
from savegate import rvt_elements as R
a = R.elements(open(SEED, 'rb').read()); b = R.elements(open(out, 'rb').read())
changed = [e for e in a if a[e] != b.get(e)]; new = [e for e in b if e not in a]
assert not changed, changed[:5]
assert len(new) == 3 and [b[e].split('|')[0] for e in sorted(new)] == ['RvtLinkSymbol', 'RvtLinkInstance', 'CopyWatchProperties'], new
# refusal: an element that is not a link symbol
r = subprocess.run([sys.executable, os.path.join(HERE, 'tools/rvt_add_link.py'), SEED, out + '2', '--src', '1363939'], capture_output=True, text=True)
assert r.returncode != 0 and not os.path.exists(out + '2'), 'bad --src must be refused with nothing written'
print('OK add_link offline: 3 new, 0 changed, bad src refused')
