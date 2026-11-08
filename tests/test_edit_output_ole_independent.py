"""c1x-rvtsave 218: independent container check. For move and rotate outputs on a synthetic 2024 .rte, olefile (not our reader) must open the file, list the same stream names as the source, read every stream fully to its declared size, and leave the non-edited streams byte-equal."""
import os, sys, io
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import olefile
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); E = 301595
def streams(b):
    o = olefile.OleFileIO(io.BytesIO(b)); d = {}
    for p in o.listdir(streams=True, storages=False):
        s = o.openstream(p); data = s.read(); assert len(data) == o.get_size(p), p; d[tuple(p)] = data
    o.close(); return d
A = streams(buf)
for name, op in (('move', {'op': 'move', 'eid': E, 'dx': 1.0}), ('rotate', {'op': 'rotate', 'eid': E, 'deg': 10.0})):
    out, _ = edit.apply_full(buf, [edit.validate_op(op)]); B = streams(out)
    assert set(A) == set(B), (name, 'stream set differs', set(A) ^ set(B))
    diff = sorted('/'.join(k) for k in A if A[k] != B[k]); print(name, 'streams differing:', len(diff), 'of', len(A), diff[:6])
    assert 0 < len(diff) <= 6, (name, diff)
print('OK')
