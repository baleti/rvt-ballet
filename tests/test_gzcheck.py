"""member_report finds a damaged gzip member in a synthetic partition payload (frames of 32 bytes between members); clean payload reports none.
Real-file evidence (Autodesk Snowdon 2024 sample, local): see c7x-rvtwrite notes; here synthetic data only."""
import sys, os, zlib, struct, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.gzcheck import member_report, GZ


def member(raw):
    co = zlib.compressobj(9, zlib.DEFLATED, -15); z = co.compress(raw) + co.flush()
    return GZ + b'\x00\x00\x00\x00\x00\x0b' + z + struct.pack('<II', zlib.crc32(raw) & 0xffffffff, len(raw))


rnd = random.Random(1)
raws = [bytes(rnd.randrange(0, 40) for _ in range(5000)) for _ in range(5)]
mems = [member(r) for r in raws]
payload = b'\x00' * 44 + (b'\xaa' * 32).join(mems)
assert member_report(payload) == (5, [], None), member_report(payload)
# flip one bit inside the deflate body of member 2 that still inflates (CRC then differs); search for such a bit
start = 44 + sum(len(m) + 32 for m in mems[:2]); found = None
for off in range(start + 12, start + len(mems[2]) - 12):
    for bit in range(8):
        bad = bytearray(payload); bad[off] ^= 1 << bit
        n, b, st = member_report(bytes(bad))
        if b == [2] and st is None: found = (off, bit); break
    if found: break
assert found, 'no inflatable single-bit damage found in the synthetic member'
# flip in the trailer CRC of member 4
bad = bytearray(payload); bad[-1] ^= 1
assert member_report(bytes(bad)) == (5, [4], None)
# a deflate flip that breaks inflate is reported as a stop at that member
for off in range(start + 12, start + len(mems[2]) - 12):
    bad = bytearray(payload); bad[off] ^= 0xff
    n, b, st = member_report(bytes(bad))
    if st == 2: break
else: raise AssertionError('no inflate-breaking damage found')
print('OK')
