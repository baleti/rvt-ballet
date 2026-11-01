#!/usr/bin/env python3
"""rvtwrite2_trunc_end.py YEAR SRC N SEED: like rvtwrite2_trunc but cuts at fixed distances from the END (1,7,511,512,513,4096,65536,1e6 bytes). RESEARCH ONLY."""
import sys, os, random, shutil, importlib.util, asyncio
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
year, src, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (year,)
if os.environ.get('RVT_LEGACY_LAYOUT'): adapters._first_member_record_sizes = lambda s: {16}   # research only
if os.environ.get('RVT_MEMBER_MAX'): adapters.RVT_MEMBER_MAX = int(os.environ['RVT_MEMBER_MAX'])
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
import json; json.dump({'rvt': {year: 'open'}}, open(o._T + '/gate.json', 'w'))
b = bytearray(open(src, 'rb').read()); r = random.Random(int(seed)); res = {}
for i in range(n):
    off = len(b) - [1, 7, 511, 512, 513, 4096, 65536, 1000000][i % 8]; d = bytearray(b[:off])
    w = o._T + '/src.rvt'; open(w, 'wb').write(d); h0 = o.sha(w)
    try: out, msg = asyncio.run(o.save(w, os.environ.get('FLIP_SCEN', 'none'), 0))
    except BaseException as e: out, msg = None, 'EXC %s' % type(e).__name__
    k = 'refused' if not out else ('saved_identical_to_damaged' if (o.sha(out) == h0) else 'saved_DIFFERENT')
    k += '' if o.sha(w) == h0 else ' SRC_CHANGED'
    res[k] = res.get(k, 0) + 1; print(i, off, k, (msg or '')[:90], flush=True)
    for x in os.listdir(o._T):
        if x.startswith('out'): os.unlink(o._T + '/' + x)
    shutil.rmtree(o._T + '/m', ignore_errors=True)
print('SUMMARY', year, res)
