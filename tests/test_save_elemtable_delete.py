"""Regression (script, python3 tests/test_save_elemtable_delete.py): for a delete, the gate compares the DECODED Global/ElemTable with the source minus exactly the deleted ids' rows (found: random and crafted byte flips inside the one stream a delete may change were accepted, tools/rvt_edit_flip.py EDIT_FLIP_ELEMTABLE_RAW, 2024 HVAC seed 82: elemtable_raw_0 ACCEPTED).
Autodesk 2024 template; skips when absent."""
import os, sys, struct, zlib, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.environ.get('DM_FILE') or os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
import cfb, rvtw
from rvtballet import save
b = open(SRC, 'rb').read()
def build(fn):
    c = cfb.CFB(b); st = rvtw.Stream(c.streams()['Global/ElemTable'].data); P = bytes(st.payload); i = P.find(rvtw.GZ)
    do = zlib.decompressobj(-15); raw = do.decompress(P[i + 10:]); tail = do.unused_data; raw = bytes(fn(bytearray(raw)))
    co = zlib.compressobj(6, zlib.DEFLATED, -15); z = co.compress(raw) + co.flush() + struct.pack('<II', zlib.crc32(raw) & 0xffffffff, len(raw)) + tail[8:]
    c.streams()['Global/ElemTable'].data = st.build(P[:i + 10] + z, keep_spare=False)
    t = tempfile.mktemp(suffix='.rvt'); cfb.write(c, t); r = open(t, 'rb').read(); os.remove(t); return r
_P = bytes(rvtw.Stream(cfb.CFB(b).streams()['Global/ElemTable'].data).payload); a = bytearray(zlib.decompressobj(-15).decompress(_P[_P.find(rvtw.GZ) + 10:])); n = struct.unpack_from('<I', a, 2)[0]
RW, W = next((rw, w) for rw, w in ((28, 4), (40, 8)) if 0 <= len(a) - 6 - rw * n < 64)
K = n // 2; rid = int.from_bytes(a[6 + RW * K:6 + RW * K + W], 'little')
def drop(raw, k=K):
    n_ = struct.unpack_from('<I', raw, 2)[0]; return raw[:2] + struct.pack('<I', n_ - 1) + raw[6:6 + RW * k] + raw[6 + RW * (k + 1):]
ad = save._cached_adapter()()
def run(out, mf): ad._verify_bufs = (b, out); return ad.extra_checks(mf)
mf = {'dirty_members': {}, 'deleted': [rid], 'frozen_except': ['Global/ElemTable']}
assert run(build(drop), mf) == [], run(build(drop), mf)      # the true delete result
def bad_flip(raw):
    raw = drop(raw); raw[6 + RW * 3 + 5] ^= 1; return raw
r = run(build(bad_flip), mf); assert any(f[0] == 'elemtable' for f in r), r
r = run(build(lambda raw: drop(raw, K + 1)), mf); assert any(f[0] == 'elemtable' for f in r), 'wrong row removed: %r' % (r,)
def keep_count(raw): raw = bytearray(raw); raw[100] ^= 1; return raw
r = run(build(keep_count), mf); assert any(f[0] == 'elemtable' for f in r), r
print('elemtable delete rule OK (row id %d of %d)' % (rid, n))
assert run(build(bad_flip), {'dirty_members': {}}) == [], 'without the rule (no frozen_except) the crafted table passes extra_checks: the old behaviour'
print('red without rule: confirmed')
