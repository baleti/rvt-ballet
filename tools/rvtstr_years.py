#!/usr/bin/env python3
"""rvtstr_years.py FILE...: for each file (any Revit year) edit one string parameter through the edit backend and run save._readback: the honest value must be accepted, the same output declared with another value must be refused (false-refusal / escape check of the string witness across years). One line per file, aggregate only (no names)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit, save
for lib in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, lib)
import rvt_params
sg = save._import(); g = lambda x: x.get('params', x); N = set(rvt_params.PNAMES.values())
for F in sys.argv[1:]:
    tag = os.path.basename(F)[:2]
    try:
        buf = open(F, 'rb').read(); pr = rvt_params.params(F); n_ok = 0; tried = 0
        for e, d in pr.items():
            for n, v in g(d).items():
                if not (isinstance(v, str) and '|' not in n and n in N and n not in ('Name', 'Family and Type', 'Type', 'UniqueId', 'IfcGUID', 'Type IfcGUID')): continue
                if tried >= 120: break
                tried += 1
                mk = lambda val: edit.validate_op({'op': 'set_string', 'eid': e, 'param': n, 'value': val})
                try: op = mk('value A'); nb = edit.apply_full(buf, [op])[0]
                except Exception: continue
                try: save._readback(buf, nb, [op]); ok = 'accepted'
                except sg.VerifyFailed as x: ok = 'FALSE-REFUSED ' + str(x)[:90]
                try: save._readback(buf, nb, [mk('value B')]); bad = 'WRONG VALUE ACCEPTED'
                except sg.VerifyFailed: bad = 'wrong value refused'
                print(tag, ok, ';', bad, flush=True); n_ok += 1; break
            if n_ok >= 3 or tried >= 120: break
        if not n_ok: print(tag, 'no editable empty string parameter found in %d tried (edit refused / not stored)' % tried, flush=True)
    except Exception as x: print(tag, 'ERR', type(x).__name__, str(x)[:80], flush=True)
