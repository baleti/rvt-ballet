#!/usr/bin/env python3
"""rvt_layout_check.py SRC.rvt OUT.rvt: exit 1 when an ADD output split a partition's original first gzip member (layout Revit 2024 rejected with
CorruptModelException on HVAC clones, 2026-11-08). Necessary, not sufficient: a pass does not prove Revit opens the file.
COUNTEREXAMPLE (c3x-rvtadd 2026-11-08): the multi-partition Snowdon Structural 2024 wall ADD (new wall 1028040, Revit VM PASS recorded) is reported SPLIT (Partitions/20 members 0,157,398,...), so SPLIT is a conservative warning, not a proven Revit rejection; only the single-partition HVAC clones are rejected so far."""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
import rvtgen
src, out = sys.argv[1], sys.argv[2]
s = rvtgen.Gen(src); d = rvtgen.Gen(out); bad = []
for pn in sorted(n for n in s.e.m.parts if n.startswith('Partitions/')):
    o = s.e.part(pn).offs(); n = d.e.part(pn).offs()
    if len(o) > 2 and len(n) > 2 and o[1] > 20000 and not (n[1] - n[0] >= o[1] - o[0] or n[2] - n[1] == o[1] - o[0]): bad.append((pn, o[1], n[:4]))
print('SPLIT' if bad else 'OK', bad)
sys.exit(1 if bad else 0)
