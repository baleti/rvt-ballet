#!/usr/bin/env python3
"""rvtgap_identity.py LIST.tsv [MAXMB] [N]: identity SAVE AS (no edit, no VM) over files listed as year<TAB>size<TAB>path (seed-stable spread by size); prints short ids + outcome + byte identity + source untouched. Aggregates only, no names."""
import sys, os, time, hashlib, asyncio, importlib.util, shutil, random
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip()]
mx = int(sys.argv[2]) << 20 if len(sys.argv) > 2 else 1 << 62; n = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
year = os.environ.get('YEAR', '2024'); ext = os.environ.get('EXT', 'rvt')
rows = [r for r in rows if r[0] == year and r[2].lower().endswith(ext) and int(r[1]) <= mx]
random.Random(7).shuffle(rows); rows = rows[:n]
for y, s, p in rows:
    t = time.time(); w = o._T + '/src.' + ext; shutil.copy(p, w); h0 = o.sha(w); sid = hashlib.sha1(p.encode()).hexdigest()[:6]
    try: out, msg = asyncio.run(o.save(w, 'none', 0))
    except BaseException as e: out, msg = None, 'EXC %s %s' % (type(e).__name__, str(e)[:100])
    same = bool(out) and o.sha(out) == h0
    print('\t'.join([y, sid, '%dMB' % (int(s) >> 20), 'saved' if out else 'refused', 'identical=%s' % same, 'src_ok=%s' % (o.sha(w) == h0 == o.sha(p)), '%.0fs' % (time.time() - t), msg[:140]]), flush=True)
    for x in os.listdir(o._T):
        if x.startswith('out'): os.unlink(o._T + '/' + x)
    shutil.rmtree(o._T + '/m', ignore_errors=True)
