"""Regression (script, python3 tests/test_save_member_rules.py): savegate RvtAdapter.extra_checks closes two holes found by tools/rvt_edit_flip.py.
(1) an UNDECLARED partition member whose compressed bytes differ but inflate to the SAME raw (a flip in the gzip header / deflate stream) must be reported (was accepted: 1-bit flip, move fuzz seed 71).
(2) member_span_max: a declared member whose changed raw bytes span more than the cap is reported; within the cap it passes.
Autodesk 2024 template (5 MB); skips when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.environ.get('DM_FILE') or os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
import cfb, rvtw, wlpart
from rvtballet import save
b = open(SRC, 'rb').read(); c0 = cfb.CFB(b); pn = 'Partitions/59'
st = rvtw.Stream(c0.streams()[pn].data); P = wlpart.Partition(st); pay = bytearray(st.payload)

def build(mut_payload=None, mut_raw=None):
    """output file: payload bytes mutated (container-level) or member raw mutated + re-encoded (member marked dirty)"""
    c = cfb.CFB(b); s_ = rvtw.Stream(c.streams()[pn].data); pt = wlpart.Partition(s_)
    if mut_raw:
        for mi, fn in mut_raw.items(): fn(pt.mem[mi]['raw']); pt.mem[mi]['dirty'] = True
        payload = pt.rebuild()
    else: payload = bytearray(s_.payload); mut_payload(payload); payload = bytes(payload)
    c.streams()[pn].data = s_.build(payload, keep_spare=False); import tempfile; t = tempfile.mktemp(suffix='.rvt'); cfb.write(c, t); r = open(t, 'rb').read(); os.remove(t); return r

ad = save._cached_adapter()()
def run(out, mf): ad._verify_bufs = (b, out); return ad.extra_checks(mf)

# (1) gzip header mtime byte of member 107 (not declared), raw unchanged
m = P.mem[107]; out = build(mut_payload=lambda p: p.__setitem__(m['pos'] + 4, p[m['pos'] + 4] ^ 1))
q = wlpart.Partition(rvtw.Stream(cfb.CFB(out).streams()[pn].data)); assert bytes(q.mem[107]['raw']) == bytes(m['raw']), 'precondition: raw must be equal'
r = run(out, {'dirty_members': {pn: [5]}}); assert any('compressed bytes differ' in f[1] for f in r), r
assert run(out, {'dirty_members': {pn: [107]}}) == [], 'declared member may be re-cut'
print('undeclared equal-raw member: reported, declared: allowed')
# (2) span rule: edit declared member 107 at two places far apart
def far(raw): raw[10] ^= 1; raw[len(raw) - 10] ^= 1
out2 = build(mut_raw={107: far}); mf = {'dirty_members': {pn: [107]}}
assert run(out2, mf) == [], 'no span rule: passes'
r = run(out2, dict(mf, member_span_max=2048)); assert any(f[0] == 'member_span' for f in r), r
def near(raw): raw[10] ^= 1; raw[200] ^= 1
assert run(build(mut_raw={107: near}), dict(mf, member_span_max=2048)) == [], 'two edits within the window pass'
print('member_span rule OK')
# (3) framing bytes between members (found: every flip in frames/partition header was accepted)
gap0 = P.mem[107]['end']
fl = lambda off: build(mut_payload=lambda p: p.__setitem__(off, p[off] ^ 1))
r = run(fl(gap0 + 0), {'dirty_members': {pn: [5]}}); assert any('frame after member 107' in f[1] for f in r), r      # byte 0 of an undeclared frame
r = run(fl(gap0 + 20), {'dirty_members': {pn: [5]}}); assert any('frame after member 107' in f[1] for f in r), r     # a size field but neighbours 107/108 undeclared
assert run(fl(gap0 + 20), {'dirty_members': {pn: [108]}}) == [], 'size field of a declared neighbour frame is allowed'
r = run(fl(gap0 + 0), {'dirty_members': {pn: [108]}}); assert any('frame after member 107' in f[1] for f in r), r     # non-size byte even for a declared neighbour
print('frame rule OK')
# (4) exact own-size field: a size byte flipped in a frame whose neighbour IS declared passes the mask but not the exact value check
r = run(fl(gap0 + 3), {'dirty_members': {pn: [108]}}); assert any('size field is not member length' in f[1] for f in r), r
print('frame size exact OK')
