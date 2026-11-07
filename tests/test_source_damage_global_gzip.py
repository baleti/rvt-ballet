"""save.source_damage flags a flipped byte inside Global/ElemTable whose page ECC was restamped (c7x-rvtread 106).
Run: python3 tests/test_source_damage_global_gzip.py"""
import os, sys, glob, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
from rvtballet.edit import WL
sys.path.insert(0, WL)
import cfb, rvtw, olefile
fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2024/4[2-5]_Snowdon*.rvt')))
if not fs: print('skip'); sys.exit(0)
b = open(fs[0], 'rb').read(); assert save.source_damage(b) == []
st = rvtw.Stream(cfb.CFB(b).streams()['Global/ElemTable'].data); P = bytearray(st.payload)
i = P.find(rvtw.GZ); P[i + 10 + (len(P) - i) // 2] ^= 1
new = st.build(bytes(P)); p = tempfile.mktemp(suffix='.rvt'); open(p, 'wb').write(b)
o = olefile.OleFileIO(p, write_mode=True); assert len(new) == len(o.openstream('Global/ElemTable').read())
o.write_stream('Global/ElemTable', new); o.close()
bad = save.source_damage(open(p, 'rb').read()); os.unlink(p)
assert any(k.startswith('Global/ElemTable') for k, _ in bad), bad[:3]
print('PASS', bad[:2])
