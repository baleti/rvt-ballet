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
if os.environ.get('RVT_PART_HS'):        # research: 4-byte-id layouts have smaller records (2017: element-header 8, records 12)
    sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import wlpart; _i = wlpart.Partition.__init__
    wlpart.Partition.__init__ = lambda self, st, hs=int(os.environ['RVT_PART_HS']): _i(self, st, hs)
if os.environ.get('RVT_DEBUG_RB'):       # research: print which parameters differ when the move read-back refuses
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from rvtballet import save as _sv; _rp = _sv._read_params; _seen = []
    def _wrap(b):
        v = _rp(b); _seen.append(v)
        if len(_seen) == 2:
            a, n = _seen; eid = int(os.environ['RVT_DEBUG_RB']); x, y = a.get(eid, {}), n.get(eid, {}); x, y = x.get('params', x), y.get('params', y)
            print('RBDIFF', {k: (str(x.get(k))[:40], str(y.get(k))[:40]) for k in set(x) | set(y) if x.get(k) != y.get(k)}, flush=True)
        return v
    _sv._read_params = _wrap
import json; json.dump({'rvt': {year: 'open'}}, open(o._T + '/gate.json', 'w'))
o.main(src, year, scen, *sys.argv[4:])
