#!/usr/bin/env python3
"""rvt_stray_check.py SRC.rvt OUT.rvt: for an ADD-only edit, every differing byte run in the partition bodies must be a pure insertion (old_len 0).
Any replaced/deleted bytes (e.g. an emptied string in an unrelated record, as seen in an early 2026 add-wall output Revit refused) exit 1.
Autodesk samples / synthetic only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_diff
rep = rvt_diff.diff(sys.argv[1], sys.argv[2], False)
bad = []
for pn, d in rep['joined'].items():
    if d['n_runs'] > 12: bad.append('%s: %d runs' % (pn, d['n_runs']))
    for r in d['runs']:
        if r['old_len']: bad.append('%s @%d: %d old bytes replaced/removed' % (pn, r['old_off'], r['old_len']))
print('STRAY' if bad else 'CLEAN', '; '.join(bad[:6]) or ('%d partitions, insertions only' % len(rep['joined'])))
sys.exit(1 if bad else 0)
