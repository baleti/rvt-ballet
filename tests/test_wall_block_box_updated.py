"""# RVT_TEST_TIMEOUT=1800. c1x-rvtdiff item 87: after Edit.rotate / Edit.move of an isolated wall the cached solid block in the zone item (two bbox copies, far from the
wall record) must carry the NEW box, not the old one (stale block = Revit API bounding box unchanged). Local Autodesk-sample derivative only; skip when absent.
Fails for a writer that patches only record + header (tools/rvt_wall_rotate_exp.py style): then the new box is found once (header) instead of three times."""
import os, sys, struct
import numpy as np
SRC = os.path.expanduser('~/c3x-rd/wb/iso_base.rvt'); EID = 1028040
if not os.path.exists(SRC): print('skip'); sys.exit(0)
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_ENABLE_WALLROTATE'] = '1'
import rvtedit, wledit, tempfile
def hits(path, box):
    n = 0
    for p in wledit.Editor(path).m.parts.values():
        b = p['joined']
        for al in range(8):
            k = (len(b) - al) // 8; a = np.frombuffer(b, dtype='<f8', count=k, offset=al)
            with np.errstate(all='ignore'): ix = np.flatnonzero(np.abs(a - box[0]) < 1e-6)
            n += sum(1 for i in ix if i + 6 <= k and all(abs(a[i + j] - box[j]) < 1e-6 for j in range(6)))
    return n
def hdrbox(path):
    ed = rvtedit.Edit(path); T = ed.g.template(EID); ho = {k: off for k, off, e, _ in T['hlog']}['Outline.m_minmax']
    return struct.unpack_from('<6d', T['hdr'], ho)
old = hdrbox(SRC)
for name, op in (('move', lambda e: e.move(EID, 1.0, 0.0)), ('rotate', lambda e: e.rotate(EID, 90.0))):
    out = tempfile.mkdtemp() + '/t.rvt'; ed = rvtedit.Edit(SRC); op(ed); ed.save(out)
    nb = hdrbox(out); assert nb != old, name
    assert hits(out, nb) >= 3, '%s: new box found %d times (header + 2 block copies expected)' % (name, hits(out, nb))
    assert hits(out, old) == 0, '%s: old box still present' % name
print('OK move and rotate update header box and both zone-item block copies')
