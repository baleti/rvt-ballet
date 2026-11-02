"""tools/ole_consistency.py (independent CFB structure check): clean Autodesk template = 0 findings; each synthetic container damage is detected:
unused DIFAT entry bit flip (the class Revit rejects with CorruptModelException), chain sector marked free, truncated tail, directory child index out of range, bad magic."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import ole_consistency as O
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skip'); sys.exit(0)
d = bytearray(open(RTE, 'rb').read()); assert O.check(bytes(d)) == [], O.check(bytes(d))
ss = 1 << struct.unpack_from('<H', d, 0x1E)[0]; hdr = max(ss, 512); off = lambda s: hdr + s * ss
def mut(f):
    x = bytearray(d); f(x); return O.check(bytes(x))
nfat = struct.unpack_from('<I', d, 0x2C)[0]; dirstart = struct.unpack_from('<I', d, 0x30)[0]
fat0 = struct.unpack_from('<I', d, 0x4C)[0]
def difat_flip(x): x[0x4C + 4 * nfat] ^= 0x10                     # first unused DIFAT entry 0xFFFFFFFF -> 0xFFFFFFEF
def freed(x): struct.pack_into('<I', x, off(fat0) + 4 * dirstart, 0xFFFFFFFF)
def dirchild(x): struct.pack_into('<I', x, off(dirstart) + 76, 0x7FFFFFFF)
cases = {'unused DIFAT flip': difat_flip, 'dir chain sector freed': freed, 'root child index out of range': dirchild,
         'bad magic': lambda x: x.__setitem__(0, 0), 'truncated tail (partial sector)': lambda x: x.__delitem__(slice(len(x) - 100, len(x)))}
for n, f in cases.items():
    r = mut(f); assert r, ('NOT detected', n); print('  detected:', n, '->', r[0][:90])
r = O.check(bytes(d[:len(d) - ss])); assert r, 'whole last sector cut not detected (size/chain mismatch)'
print('ole consistency OK: clean file 0 findings, %d damage classes detected' % (len(cases) + 1))
