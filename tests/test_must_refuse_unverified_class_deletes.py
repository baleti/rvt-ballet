"""item 53 (c6x-rvtmatrix): for every element class of a synthetic Autodesk 2024 file whose DELETE has no Revit-verified implementation,
a delete of one element must raise EditError (nothing written). Skipped when the local file is absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
for _p in ('~/rvt-research', '~/rvt-research/write-lab', '~/src/savegate'): sys.path.insert(0, os.path.expanduser(_p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c6x-rm/cp/fse.rte')
if not os.path.exists(F): print('skip'); sys.exit(0)
from rvtballet import edit
import rvt_geometry as G
ix = G.file_geometry_index(F); buf = open(F, 'rb').read()
first = {}
for e, c in ix.items(): first.setdefault(str(c), e)
bad = 0; n = 0
for cls, eid in sorted(first.items()):
    if cls in edit.DELETE_VM_VERIFIED: continue
    for o in ({'op': 'delete', 'eid': eid},):
        n += 1
        try: edit.apply_full(buf, [edit.validate_op(o)]); print('ACCEPTED', cls, eid, o['op']); bad += 1
        except edit.EditError: pass
        except Exception as ex: print('CRASH', cls, eid, o['op'], type(ex).__name__, str(ex)[:80]); bad += 1
print('classes tried', n, 'bad', bad); sys.exit(1 if bad else 0)
