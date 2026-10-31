#!/usr/bin/env python3
"""rvtwrite2_cands.py FILE [N]: list up to N FamilyInstance element ids (id>1000, with geometry box) usable as move targets. Aggregate ids only."""
import sys, os, json
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research')]
from savegate import rvt_elements as R
d = R.elements(open(sys.argv[1], 'rb').read()); n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
c = [e for e, v in d.items() if v.startswith('FamilyInstance|') and e > 1000 and json.loads(v.split('|')[1])[2]]
print(len(c), c[:n])
