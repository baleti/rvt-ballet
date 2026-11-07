"""rvt_idlist.add_to_lists: synthetic id-list append (count bump, order, untouched bytes, no-list case)."""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import rvt_idlist as L

def lst(ids): return struct.pack('<I', len(ids)) + struct.pack('<%dQ' % len(ids), *ids)

pre = b'\xaa' * 13; post = b'\xbb' * 17
buf = pre + lst([100, 205, 300, 400]) + b'\x00' * 5 + lst([7, 205, 9000]) + post
out, found = L.add_to_lists(buf, 205, 20000)
assert len(found) == 2, found
assert len(out) == len(buf) + 16
assert out.startswith(pre) and out.endswith(post)
exp = pre + lst([100, 205, 300, 400, 20000]) + b'\x00' * 5 + lst([7, 205, 9000, 20000]) + post
assert out == exp
# new id below an existing last id (5000 < 9000): the helper must refuse, not corrupt
try:
    L.add_to_lists(buf, 205, 5000); raise SystemExit('FAIL: ordering assert did not fire')
except AssertionError:
    pass
out2, found2 = L.add_to_lists(pre + post, 205, 5000)
assert out2 == pre + post and not found2
print('idlist add OK')
