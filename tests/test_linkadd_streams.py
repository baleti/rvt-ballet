"""tools/rvt_linkadd_streams.py: synthetic checks (always run) + byte-exact reproduction of the Revit-made link-add payloads when the local Autodesk-sample pair exists (skipped otherwise). Offline helper only, not wired to any save path."""
import os, sys, struct
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'tools'))
import rvt_linkadd_streams as m
def table(ids, last):
    b = struct.pack('<HI', 0x0583, len(ids))
    for i in ids: b += struct.pack('<IIIIIIIIII', i, 0, 7, 7, 7, i, 0, 0xffffffff, 0xffffffff, 0)
    return b + struct.pack('<IIII', 0, 0xffffffff, 0x0901, last) + b'\0' * 8
t = table([10, 20], 20)
o = m.elemtable_append(t, [(30, 9, 9), (31, 9, 0xffffffff)])
assert struct.unpack_from('<I', o, 2)[0] == 4 and len(o) == len(t) + 80 and struct.unpack_from('<I', o, len(o) - 12)[0] == 31
assert o[:6 + 80] == t[:6 + 80][:2] + struct.pack('<I', 4) + t[6:6 + 80]
for bad in ([(20, 1, 1)], [(5, 1, 1)]):
    try: m.elemtable_append(t, bad); raise SystemExit('non-ascending id accepted')
    except ValueError: pass
try: m.elemtable_append(t + b'\0', [(30, 1, 1)]); raise SystemExit('bad trailer accepted')
except ValueError: pass
x = '<?xml version="1.0"?>\r\n<TransmissionData version="5"></TransmissionData>'
raw = struct.pack('<I', len(x)) + x.encode('utf-16le'); r = m.transmission_append(raw, 5, 'a.rvt')
assert r.decode('utf-16le', 'ignore').count('<ExternalFileReference>') == 1 and struct.unpack_from('<I', r)[0] == (len(r) - 4) // 2
try: m.transmission_append(struct.pack('<I', 3) + x.encode('utf-16le'), 5, 'a.rvt'); raise SystemExit('bad char count accepted')
except ValueError: pass
a, b = [os.path.expanduser('~/c5x-link/fl/la_%s.rvt' % n) for n in ('noop', 'added')]
if os.path.exists(a) and os.path.exists(b):
    try: import rvt_linkadd_streams as _m; _m._main(a, b)
    except SystemExit as e:
        if e.code not in (0, None): raise SystemExit('byte-exact reproduction of the Revit-made pair FAILED')
else: print('real pair absent: synthetic checks only')
print('PASS')
