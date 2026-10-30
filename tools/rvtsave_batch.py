#!/usr/bin/env python3
"""rvtsave_batch.py YEARDIR...: identity SAVE AS (no VM) of every file in the corpus dirs; prints year, id, size, outcome, seconds, byte-identity of output. Aggregates only, no names."""
import sys, os, time, hashlib, asyncio, importlib.util
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
import shutil
for d in sys.argv[1:]:
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f); t = time.time(); w = o._T + '/src' + os.path.splitext(f)[1]
        shutil.copy(p, w); h0 = o.sha(w)
        try: out, msg = asyncio.run(o.save(w, 'none', 0))
        except BaseException as e: out, msg = None, 'EXC %s %s' % (type(e).__name__, str(e)[:100])
        same = out and o.sha(out) == h0
        print('\t'.join([os.path.basename(d), f[:2], str(os.path.getsize(p) >> 20) + 'MB', 'saved' if out else 'refused', 'identical=%s' % same, 'src_ok=%s' % (o.sha(w) == h0), '%.0fs' % (time.time() - t), msg[:110]]), flush=True)
        for x in os.listdir(o._T):
            if x.startswith('out'): os.unlink(o._T + '/' + x)
        shutil.rmtree(o._T + '/m', ignore_errors=True)
