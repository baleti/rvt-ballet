#!/usr/bin/env python3
"""rvtwallmove_years.py FILE...: for each file (any Revit year) move the first SWall(s) by (1,2,0.5) ft through the edit backend and run save._readback: the honest move must be accepted (false-refusal check of the wall placement witness), the same output declared as (2,2,0.5) must be refused. One line per file, aggregate only."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit, save
for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, lib)
import rvt_geometry as G
sg = save._import()
for F in sys.argv[1:]:
    tag = os.path.basename(F)[:2]
    try:
        buf = open(F, 'rb').read(); ix = G.file_geometry_index(F); ws = [e for e, v in ix.items() if str(v) == 'SWall']; n = 0
        for e in ws[:12]:
            if save._trf_origin(buf, e) is None: continue
            op = edit.validate_op({'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 2.0, 'dz': 0.5}); op2 = edit.validate_op({'op': 'move', 'eid': e, 'dx': 2.0, 'dy': 2.0, 'dz': 0.5})
            try: nb = edit.apply_full(buf, [op])[0]
            except Exception as x: print(tag, 'edit refused:', str(x)[:50], flush=True); continue
            try: save._readback(buf, nb, [op]); ok = 'accepted'
            except sg.VerifyFailed as x: ok = 'FALSE-REFUSED ' + str(x)[:90]
            try: save._readback(buf, nb, [op2]); bad = 'WRONG AMOUNT ACCEPTED'
            except sg.VerifyFailed: bad = 'wrong amount refused'
            print(tag, ok, ';', bad, flush=True); n += 1
            if n >= 2: break
        if not n: print(tag, 'no SWall with a readable placement origin', flush=True)
    except Exception as x: print(tag, 'ERR', type(x).__name__, str(x)[:80], flush=True)
