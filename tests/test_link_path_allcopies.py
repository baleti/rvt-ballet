"""c3x-rvtlink: set_link_path on a link type with records in several partitions edits EVERY copy (Revit 2026 reads 41, heuristic picked 39).
Local 2026 Electrical sample ~/c5x-link/y2526b/e26_seed.rvt (skipped if absent). Offline check: after the edit both partitions' copies carry the new path."""
import os, sys, tempfile
SEED = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_LINKPATH_ANY_YEAR'] = '1'
import rvtedit
from rvtballet import edit
out = os.path.join(tempfile.mkdtemp(), 'o.rvt')
edit._apply_rvtedit(SEED, out, [{'op': 'set_link_path', 'eid': 1362427, 'value': 'Moved_e26.rvt'}])
raw = open(out, 'rb').read(); seed = open(SEED, 'rb').read()
import cfb
for name, data in (('seed', seed), ('out', raw)):
    c = cfb.CFB(data); parts = {}
    for k, s in c.streams().items():
        if k.startswith('Partitions/'):
            try: parts[k] = rvtedit.Edit  # presence only
            except Exception: pass
e = rvtedit.Edit(out); ps = sorted({str(q) for q, *_ in e.g.e.m.find(1362427)}); print('partitions with record:', ps)
for q in ps:
    os.environ['PART'] = q; ee = rvtedit.Edit(out)
    log = ee.g.e.trace(1362427)[3]; olds = [l for l in log if l[1] == 'ModelPath.m_path']
    print(q, [l[4] for l in olds][:1]); assert any('Moved_e26' in str(l[4]) for l in olds), q
print('OK all partition copies edited')
