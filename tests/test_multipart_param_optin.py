"""# RVT_TEST_TIMEOUT=1500 (slow: 40 MB 2026 sample). c3x-rvtlink: set_num on a multi-partition element (2026 Electrical 1670604, Partitions 39+41): default must REFUSE; with RVTBALLET_MULTIPART_PARAM=1 BOTH copies must carry the new value and the sibling Double param (-1140140) must stay 3000. Skips if the local sample is absent."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research', '~/src/savegate'): sys.path.append(os.path.expanduser(p))
SEED = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SEED): print('SKIP: no local seed'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit
buf = open(SEED, 'rb').read(); op = edit.validate_op({'op': 'set_num', 'eid': 1670604, 'pid': -1140082, 'kind': 'Double', 'value': 3100.0})
os.environ.pop('RVTBALLET_MULTIPART_PARAM', None)
try: edit.apply(buf, [op]); raise SystemExit('FAIL: default did not refuse')
except SystemExit: raise
except Exception as e: print('default refused:', str(e)[:120])
os.environ['RVTBALLET_MULTIPART_PARAM'] = '1'
out = edit.apply(buf, [op]); assert len(out) > 0
import rvtedit
ed = rvtedit.Edit.__new__(rvtedit.Edit)
open('/tmp/_mpo.rvt', 'wb').write(out)
ed = rvtedit.Edit('/tmp/_mpo.rvt')
for pn in dict.fromkeys(p for p, *_ in ed.g.e.m.find(1670604)):
    os.environ['PART'] = pn; t = ed.g.e.trace(1670604)
    vals = [l for l in t[3] if 'ParamValueDouble' in l[1]]; print(pn, vals)
    assert any('3100' in str(v) for v in vals), (pn, 'new value missing')
    assert sum('3000' in str(v) for v in vals) == 1, (pn, 'sibling changed')
os.remove('/tmp/_mpo.rvt'); print('PASS')
