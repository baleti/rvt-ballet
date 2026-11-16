"""Temp .rte files of the geometry checks live in a private per-user dir named with the owner pid; a file whose owner is dead (leaked by kill -9) is swept on the next call, a file of a live process is kept. Offline, no sample needed."""
import os, sys, tempfile, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
d = os.path.join(tempfile.gettempdir(), 'rvtballet-tmp-%d' % os.getuid()); os.makedirs(d, mode=0o700, exist_ok=True)
p = subprocess.Popen([sys.executable, '-c', 'pass']); p.wait(); dead = p.pid      # a pid that just ended
stale = os.path.join(d, 'p%d-stale.rte' % dead); open(stale, 'wb').write(b'x')
live = subprocess.Popen(['sleep', '30']); keep = os.path.join(d, 'p%d-live.rte' % live.pid); open(keep, 'wb').write(b'x')
fd, tmp = save._mk_tmp_rte(); os.close(fd)
try:
    assert not os.path.exists(stale), 'stale temp of a dead process not swept'
    assert os.path.exists(keep), 'temp of a live process was removed'
    assert os.path.dirname(tmp) == d and os.path.basename(tmp).startswith('p%d-' % os.getpid()), tmp
    assert oct(os.stat(d).st_mode & 0o777) == '0o700', oct(os.stat(d).st_mode)
finally:
    for f in (tmp, keep, stale):
        try: os.remove(f)
        except OSError: pass
    live.kill(); live.wait()
print('stale temp sweep ok')
