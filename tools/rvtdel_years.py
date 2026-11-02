#!/usr/bin/env python3
"""rvtdel_years.py FILE...: for each file (any Revit year) delete up to 3 elements through the edit backend (opt-in RVTBALLET_ENABLE_DELETE=1) and run save._readback: the honest output must be accepted, the UNCHANGED source declared as the output of the delete (declared delete still present) must be refused. Prints one line per attempt; exit 1 on a false refusal or an accepted undone delete. Edit refusals by the backend are reported, not counted as failures."""
import os, sys
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit, save
for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, lib)
import rvt_params
sg = save._import(); bad = 0
for F in sys.argv[1:]:
    tag = os.path.basename(F)[:2]
    try:
        buf = open(F, 'rb').read(); n_ok = tried = 0
        for e in list(rvt_params.params(F))[:60]:
            if tried >= 12 or n_ok >= 3: break
            tried += 1
            try: op = edit.validate_op({'op': 'delete', 'eid': e}); nb, gone = edit.apply_full(buf, [op])
            except Exception as x: continue
            if nb == buf or not gone: continue
            try: save._readback(buf, nb, [op]); ok = 'honest accepted'
            except sg.VerifyFailed as x: ok = 'FALSE-REFUSED ' + str(x)[:80]; bad += 1
            try: save._readback(buf, buf, [op]); u = 'UNDONE DELETE ACCEPTED'; bad += 1
            except sg.VerifyFailed: u = 'undone delete refused'
            print(tag, e, ok, ';', u, flush=True); n_ok += 1
        if not n_ok: print(tag, 'no delete producible in %d tried (backend refused)' % tried, flush=True)
    except Exception as x: print(tag, 'ERR', type(x).__name__, str(x)[:80], flush=True)
sys.exit(1 if bad else 0)
