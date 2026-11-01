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
assert member_report(payload) == (5, []), member_report(payload)
# flip one bit inside the deflate body of member 2 (not header, not trailer)
start = 44 + sum(len(m) + 32 for m in mems[:2]); off = start + 10 + (len(mems[2]) - 18) // 2
bad = bytearray(payload); bad[off] ^= 0x10
n, b = member_report(bytes(bad))
assert b and b[0] == 2, (n, b)          # member 2 is reported (inflate error, or CRC mismatch)
# flip in the trailer CRC of member 4
bad = bytearray(payload); bad[-1] ^= 1
assert member_report(bytes(bad)) == (5, [4])
print('OK')
