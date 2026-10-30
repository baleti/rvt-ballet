"""disk snapshot cache: a repeat snapshot of the same bytes (new process) comes from disk, is equal to the uncached dump, a damaged cache file is a miss (not an error),
RVTBALLET_SNAPSHOT_CACHE=0 disables it. Needs the write-lab scene + savegate (prints skip otherwise)."""
import os, sys, tempfile, time, glob
_T = tempfile.mkdtemp(); os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WL = os.path.expanduser('~/rvt-research/write-lab'); RTE = os.environ.get('SNAP_FILE') or WL + '/scenes/classtests/2024_writer_cols2.rte'
from rvtballet import save
if not os.path.exists(RTE) or not save._import(): print('skip'); sys.exit(0)
buf = open(RTE, 'rb').read(); A = save._cached_adapter()
def snap():
    a = A(); t = time.time(); s = a.snapshot(buf); return s, set(a._keys), time.time() - t
s1, k1, t1 = snap(); files = glob.glob(_T + '/snap/*.pkl'); assert len(files) == 1, files
s2, k2, t2 = snap(); assert s1 == s2 and k1 == k2
assert t2 < t1 / 3 or t1 < 0.5, (t1, t2)
raw = open(files[0], 'rb').read(); open(files[0], 'wb').write(raw[:-5] + b'xxxxx')      # damaged: miss, recomputed, rewritten
s3, k3, t3 = snap(); assert s3 == s1 and k3 == k1
assert save._disk_get(__import__('hashlib').sha256(buf).digest()) is not None
open(files[0], 'wb').write(b'junk'); s4, _, _ = snap(); assert s4 == s1
save._reader_stamp = lambda: 'other'; assert save._disk_get(__import__('hashlib').sha256(buf).digest()) is None     # reader changed -> miss
os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; assert save._disk_get(b'x' * 32) is None
print('cold %.2fs warm %.2fs' % (t1, t2)); print('OK')
