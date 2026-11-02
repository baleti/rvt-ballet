"""disk memo of the reader params (rvt_params.params) per source sha256 + reader stamp: second process-fresh call is equal and faster; damaged file / other stamp / SNAPSHOT_CACHE=0 = miss."""
import os, sys, tempfile, time, glob, hashlib
_T = tempfile.mkdtemp(); os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WL = os.path.expanduser('~/rvt-research/write-lab'); RTE = os.environ.get('SNAP_FILE') or WL + '/scenes/classtests/2024_writer_cols2.rte'
from rvtballet import save
if not os.path.exists(RTE) or not os.path.isdir(os.path.expanduser('~/rvt-research')): print('skip'); sys.exit(0)
buf = open(RTE, 'rb').read(); k = hashlib.sha256(buf).digest()
t = time.time(); v1 = save._read_params(buf); t1 = time.time() - t
f = glob.glob(_T + '/snap/*.rpk'); assert len(f) == 1, f
save._RB_MEMO.clear(); t = time.time(); v2 = save._read_params(buf); t2 = time.time() - t
assert v1 == v2 and (t2 < t1 / 3 or t1 < 0.5), (t1, t2)
raw = open(f[0], 'rb').read(); open(f[0], 'wb').write(raw[:-5] + b'xxxxx'); assert save._rp_disk_get(k) is None
save._RB_MEMO.clear(); assert save._read_params(buf) == v1 and save._rp_disk_get(k) is not None      # recomputed + rewritten
real = save._reader_stamp; save._reader_stamp = lambda: 'other'; assert save._rp_disk_get(k) is None; save._reader_stamp = real
os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; assert save._rp_disk_get(k) is None
print('cold %.2fs warm %.2fs' % (t1, t2)); print('OK')
