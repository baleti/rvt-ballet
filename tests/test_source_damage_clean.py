"""save.source_damage reports NO damaged member on undamaged Autodesk 2024 samples (no false refusals), and DOES report one after a byte inside a Partitions gzip member is flipped (fails if source_damage always returned [])."""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2024/4[2-5]_Snowdon*.rvt')))
if not fs: print('skip'); sys.exit(0)
for f in fs:
    b = open(f, 'rb').read(); d = save.source_damage(b)
    assert d == [], (os.path.basename(f), d[:3])
    print('clean', os.path.basename(f)[:30], 'ok')
# damage: scan for a flip that source_damage detects (members are located by the walker, so try a spread of offsets)
b = bytearray(open(fs[0], 'rb').read()); hit = 0
for off in range(len(b) // 8, len(b), len(b) // 40):
    c = bytearray(b); c[off] ^= 0x40
    if save.source_damage(bytes(c)): hit += 1
assert hit >= 1, 'no flip detected at all'
print('flips detected', hit, 'of ~40; source_damage test OK')
