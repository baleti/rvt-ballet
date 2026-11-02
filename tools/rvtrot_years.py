#!/usr/bin/env python3
"""rvtrot_years.py FILE...: for each file (any Revit year) rotate the first FamilyInstance that has a source mesh by 30 deg through the edit backend and run save._readback on the result: honest rotation must be accepted (false-refusal check of the rotation witness across years), and the same output declared as 31 deg must be refused. One line per file, aggregate only (no element names)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit, save
for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, lib)
import rvt_geometry as G
sg = save._import()
for F in sys.argv[1:]:
    tag = os.path.basename(F)[:2]
    try:
        buf = open(F, 'rb').read(); ix = G.file_geometry_index(F); fi = [e for e, v in ix.items() if str(v) == 'FamilyInstance']; done = False
        for e in fi[:60]:
            t0 = save._tris_of(buf, e)
            if not t0: continue
            op = edit.validate_op({'op': 'rotate', 'eid': e, 'deg': 30})
            try: nb = edit.apply_full(buf, [op])[0]
            except Exception as x: print(tag, 'edit refused:', str(x)[:60], flush=True); continue
            try: save._readback(buf, nb, [op]); ok = 'accepted'
            except sg.VerifyFailed as x: ok = 'FALSE-REFUSED ' + str(x)[:90]
            op2 = edit.validate_op({'op': 'rotate', 'eid': e, 'deg': 31})
            try: save._readback(buf, nb, [op2]); bad = 'WRONG ANGLE ACCEPTED'
            except sg.VerifyFailed: bad = 'wrong angle refused'
            print(tag, len(t0), 'vertices;', ok, ';', bad, flush=True); done = True; break
        if not done: print(tag, 'no FamilyInstance with a mesh in the first 60', flush=True)
    except Exception as x: print(tag, 'ERR', type(x).__name__, str(x)[:80], flush=True)
