#!/usr/bin/env python3
"""Diagnose a 'moved element N: parameters changed' refusal without touching save.py: wraps save._readback, prints the parameter keys of the moved eids that differ between source and output reads, then runs the original (so the gate still refuses). usage: rvt_diag_move_params.py FILE 'OPJSON' KEEP.rvt  (same args as rvt_one_edit.py)"""
import os, sys, runpy
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..'))
from rvtballet import save
_orig = save._readback
def _wrap(src_buf, nb, ops, *a, **k):
    try:
        x, y = save._read_params(src_buf), save._read_params(nb)
        g = lambda z: (z.get('params', z) if isinstance(z, dict) else {})
        for o in ops:
            if o.get('op') in ('move', 'rotate'):
                p, q = g(x.get(o['eid'])), g(y.get(o['eid']))
                for key in sorted(set(p) | set(q), key=str):
                    if p.get(key) != q.get(key): print('DIAG eid %s %s: %r -> %r' % (o['eid'], key, str(p.get(key))[:60], str(q.get(key))[:60]), flush=True)
    except Exception as e: print('DIAG failed', type(e).__name__, e, flush=True)
    return _orig(src_buf, nb, ops, *a, **k)
save._readback = _wrap
sys.argv = [os.path.join(H, 'rvt_one_edit.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
