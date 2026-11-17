#!/usr/bin/env python3
"""rvt_warn_diff.py CONTROL_j1.txt OUTPUT_j1.txt [...]: new/resolved Revit warnings (FAILURE Warning lines of the audit open) between a judge1 control dump and output dump(s).
Evidence for the dashboard row 'audit tool zero new warnings'. Not a verdict: a new warning can be a legitimate semantic effect of the edit (e.g. 'Elements have duplicate "Mark" values' after an ADD)."""
import sys, re, collections

def warns(p):
    return collections.Counter(re.sub(r'\s+', ' ', l.strip()) for l in open(p, errors='replace') if l.startswith('FAILURE Warning'))

def diff(ctl, out):
    wc, wo = warns(ctl), warns(out)
    return dict(wo - wc), dict(wc - wo)

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    rc = 0
    for o in sys.argv[2:]:
        new, gone = diff(sys.argv[1], o)
        print('%s: new %d, resolved %d' % (o, sum(new.values()), sum(gone.values())))
        for k, v in sorted(new.items()): print('  NEW  x%d %s' % (v, k))
        for k, v in sorted(gone.items()): print('  GONE x%d %s' % (v, k))
        rc = rc or int(bool(new))
    sys.exit(rc)
