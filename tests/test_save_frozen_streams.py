"""Regression (script, python3 tests/test_save_frozen_streams.py): manifest frozen_streams makes the gate refuse ANY change in a non-partition stream (found: a 1-byte flip in Global/DocumentIncrementTable and Global/Latest of a move output was ACCEPTED, tools/rvt_edit_flip.py EDIT_FLIP_GLOBAL, 2024 HVAC seed 77).
Autodesk 2024 template; skips when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.environ.get('DM_FILE') or os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
import cfb, tempfile
from rvtballet import save
b = open(SRC, 'rb').read()
def flipped(name):
    c = cfb.CFB(b); d = bytearray(c.streams()[name].data); d[len(d) // 2] ^= 1; c.streams()[name].data = bytes(d)
    t = tempfile.mktemp(suffix='.rvt'); cfb.write(c, t); r = open(t, 'rb').read(); os.remove(t); return r
ad = save._cached_adapter()()
def run(out, mf): ad._verify_bufs = (b, out); return ad.extra_checks(mf)
names = [n for n in ('Global/DocumentIncrementTable', 'Global/Latest') if n in cfb.CFB(b).streams()]; assert names
for n in names:
    out = flipped(n)
    assert run(out, {'dirty_members': {}}) == [], 'without the rule the flip passes extra_checks (the old gate accepted it)'
    r = run(out, {'dirty_members': {}, 'frozen_streams': True}); assert any(f[0] == 'frozen_stream' for f in r), r
print('frozen_streams OK', names)
