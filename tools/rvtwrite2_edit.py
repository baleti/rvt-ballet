#!/usr/bin/env python3
"""rvtwrite2_edit.py YEAR SRC SCEN [EID]: RESEARCH ONLY. Widens savegate RVT_WRITABLE/RVT_MEMBER_MAX in this process, then runs rvtsave_oracle.main (RVTSAVE_NOVM=1 keeps the edited output
under ~/rvtsave-work/outs for a later VM open). Shipped gate unchanged."""
import sys, os, importlib.util
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
year, src, scen = sys.argv[1:4]
adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (year,); adapters.RVT_MEMBER_MAX = int(os.environ.get('RVT_MEMBER_MAX', '300000'))
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
if os.environ.get('RVT_PART_LIMIT'):     # research: do not re-split members the original already has above the 2024 limit
    sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import wlpart; wlpart.Partition.LIMIT = int(os.environ['RVT_PART_LIMIT'])
import json; json.dump({'rvt': {year: 'open'}}, open(o._T + '/gate.json', 'w'))
o.main(src, year, scen, *sys.argv[4:])
