"""save.source_damage (SAVE AS path) reports a failing page ECC in non-Partition paged streams (Global/Latest etc.), as the savegate gate does.
c7x-rvtread queue 68. Run: python3 tests/test_source_damage_ecc_global.py"""
import os, sys, glob, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
from rvtballet.edit import WL
sys.path.insert(0, WL)
import cfb, rvtw, olefile
fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2024/4[2-5]_Snowdon*.rvt')))
if not fs: print('skip'); sys.exit(0)
b = open(fs[0], 'rb').read(); assert save.source_damage(b) == []
p = tempfile.mktemp(suffix='.rvt'); open(p, 'wb').write(b)
o = olefile.OleFileIO(p, write_mode=True); d = bytearray(o.openstream('Global/Latest').read())
assert len(d) > rvtw.PAGE_STORED and d[:2] != b'\x1f\x8b' and d[:5] != b'<?xml', 'stream not paged'
d[rvtw.PAGE_STORED - 1] ^= 1; o.write_stream('Global/Latest', bytes(d)); o.close()
bad = save.source_damage(open(p, 'rb').read()); os.unlink(p)
assert any(k.startswith('Global/Latest') for k, _ in bad), bad[:3]
print('PASS', bad[:2])
