"""save.source_damage (SAVE AS / copy path) also reports a page whose ECC fails: a byte flipped in the LAST bytes of a stored page (ECC parity, which
gzip/CRC never sees) is carried into the copy otherwise. Clean Autodesk samples report nothing. c7x-rvtread queue 63. Run: python3 tests/test_source_damage_ecc.py"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
from rvtballet.edit import WL
sys.path.insert(0, WL)
import cfb, rvtw
fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2024/4[2-5]_Snowdon*.rvt')))
if not fs: print('skip'); sys.exit(0)
b = open(fs[0], 'rb').read()
assert save.source_damage(b) == []
S = cfb.CFB(b).streams(); name = max((k for k in S if k.startswith('Partitions/')), key=lambda k: len(S[k].data))
st = S[name]; d = bytearray(st.data); pos = rvtw.PAGE_STORED * 2 + rvtw.PAGE_STORED - 1       # last byte of page 2
d[pos] ^= 0x01
c = cfb.CFB(b); 
# rebuild the container with the flipped stream through the same-size stream writer
import io, olefile, tempfile, shutil
p = tempfile.mktemp(suffix='.rvt'); open(p, 'wb').write(b)
o = olefile.OleFileIO(p, write_mode=True); o.write_stream(name, bytes(d)); o.close()
bad = save.source_damage(open(p, 'rb').read()); os.unlink(p)
assert any('page ECC' in k for k, _ in bad), bad[:3]
print('PASS', bad[:2])
