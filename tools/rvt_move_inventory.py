#!/usr/bin/env python3
"""rvt_move_inventory.py FILE.rvt [N]: for every element class in FILE, try a +1 ft move (edit stage only, in memory, nothing saved) on up to N elements
and print per class: n tried, n edit-accepted, first refusal reason. Opt-in datum move flag on. Aggregate lines only (Autodesk samples)."""
import os, sys, collections
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
from rvtballet.edit import *      # noqa
import rvtballet.edit as E
sys.path.insert(0, E.WL); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt_geometry as G
F = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 2
buf = open(F, 'rb').read(); ix = G.file_geometry_index(F); by = collections.defaultdict(list)
for e, v in ix.items(): by[str(v)].append(e)
for c in sorted(by):
    ok = 0; why = ''; ids = by[c][:N]
    for e in ids:
        try: edit.apply_full(buf, [edit.validate_op({'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})]); ok += 1
        except Exception as x:
            if not why: why = (type(x).__name__ + ': ' + str(x))[:110].replace('\n', ' ')
    print('%-28s total %-6d tried %d accepted %d %s' % (c, len(by[c]), len(ids), ok, why), flush=True)
