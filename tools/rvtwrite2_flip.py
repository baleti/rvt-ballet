#!/usr/bin/env python3
"""rvtwrite2_flip.py YEAR SRC N SEED: RESEARCH ONLY (widened gate in-process). Flip one byte at N random offsets (one file per trial), no-edit SAVE AS; reports saved/refused and whether a saved output differs from the damaged source (damage carried silently). Aggregate lines only."""
import sys, os, random, shutil, importlib.util, asyncio
sys.path.insert(0, os.path.expanduser('~/src/savegate')); from savegate import adapters
year, src, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (year,)
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
import json; json.dump({'rvt': {year: 'open'}}, open(o._T + '/gate.json', 'w'))
b = bytearray(open(src, 'rb').read()); r = random.Random(int(seed)); res = {}
for i in range(n):
    off = r.randrange(512, len(b)); d = bytearray(b); d[off] ^= 1 << r.randrange(8)
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
