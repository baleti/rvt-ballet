#!/usr/bin/env python3
"""rvtwrite2_identity.py YEAR LIST.tsv [MAXMB]: RESEARCH ONLY. Widens savegate RVT_WRITABLE in this process to YEAR and runs no-edit SAVE AS through rvtballet, then
compares to the source. Prints short ids + outcome (no names/paths). The shipped gate is not changed. LIST rows: id<TAB>year<TAB>size<TAB>path (rvtwrite2_inv.py)."""
import sys, os, time, asyncio, importlib.util, shutil
year = sys.argv[1]; mx = int(sys.argv[3]) << 20 if len(sys.argv) > 3 else 1 << 62
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (year,)
import json; json.dump({'rvt': {year: 'open'}}, open(o._T + '/gate.json', 'w'))
for sid, y, s, p in (l.rstrip('\n').split('\t') for l in open(sys.argv[2])):
    if y != year or int(s) > mx: continue
    t = time.time(); w = o._T + '/src.rvt'; shutil.copy(p, w); h0 = o.sha(w)
    try: out, msg = asyncio.run(o.save(w, 'none', 0))
    except BaseException as e: out, msg = None, 'EXC %s %s' % (type(e).__name__, str(e)[:160])
    print('\t'.join([year, sid, '%dMB' % (int(s) >> 20), 'saved' if out else 'refused', 'identical=%s' % (bool(out) and o.sha(out) == h0), 'src_ok=%s' % (o.sha(w) == h0 == o.sha(p)), '%.0fs' % (time.time() - t), msg[:200]]), flush=True)
    for x in os.listdir(o._T):
        if x.startswith('out'): os.unlink(o._T + '/' + x)
    shutil.rmtree(o._T + '/m', ignore_errors=True)
