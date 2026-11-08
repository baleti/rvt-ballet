"""c1x-rvtsave 219: olefile (independent of our reader) check of a Comments edit output on Autodesk Construction templates 2021..2026: same stream set, every stream readable to declared size, number of differing streams reported (expect small). Years the edit path refuses are reported as refused."""
import os, sys, io, glob, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import olefile, rvt_params
from rvtballet import edit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def streams(b):
    o = olefile.OleFileIO(io.BytesIO(b)); d = {}
    for p in o.listdir(streams=True, storages=False):
        data = o.openstream(p).read(); assert len(data) == o.get_size(p), p; d[tuple(p)] = data
    o.close(); return d
n = 0
for y in range(2021, 2027):
    fs = glob.glob(os.path.expanduser('~/rvtfix/corpus/%d/*Construction-DefaultMetric.rte' % y))
    if not fs: continue
    buf = open(fs[0], 'rb').read()
    eid = next((e for e, d in rvt_params.params(fs[0]).items() if g(d).get('Comments') == ''), None)
    if eid is None: print(y, 'no empty Comments element'); continue
    try: out, _ = edit.apply_full(buf, [edit.validate_op({'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'ole-%d' % y})])
    except edit.EditError as e: print(y, 'refused:', str(e)[:80]); continue
    A, B = streams(buf), streams(out); assert set(A) == set(B), (y, set(A) ^ set(B))
    diff = [k for k in A if A[k] != B[k]]; print(y, 'streams', len(A), 'differing', len(diff)); assert 0 < len(diff) <= 4, (y, diff); n += 1
assert n, 'nothing tested'
print('OK', n, 'years')
