"""c1x-rvtsave 211: savegate stale-temp sweep: an old '.<x>.sgtmp' (crashed save) is removed, a young one and every other file (the .rvt, a user file ending .sgtmp without a leading dot, a backup-like name) is left alone."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
from savegate import atomic
d = tempfile.mkdtemp()
def mk(n, age=0):
    p = os.path.join(d, n); open(p, 'wb').write(b'x'); t = time.time() - age; os.utime(p, (t, t)); return p
old = mk('.model.abc123.sgtmp', 7200); young = mk('.model.def456.sgtmp', 10)
keep = [mk('model.rvt', 9999), mk('notes.sgtmp', 9999), mk('.hidden.rvt', 9999), mk('model.rvt.bak', 9999)]
atomic.sweep_stale_temps(d, 3600)
assert not os.path.exists(old), 'old stale temp not removed'
assert os.path.exists(young), 'young temp (possibly a live save) removed'
assert all(os.path.exists(k) for k in keep), 'a non-temp file was removed'
print('OK: old .sgtmp swept, young kept, 4 other files untouched')
