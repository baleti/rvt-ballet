"""prune the converted-model cache (~/.cache/rvt-ballet/models): per source name keep the newest KEEP directories that are complete (phase done) and drop the rest,
plus unfinished *.tmp directories older than 1 day. Dry run unless --delete is given. usage: tools/prune_cache.py [--keep N] [--delete] [--dir DIR]"""
import os, sys, json, time, shutil, argparse
ap = argparse.ArgumentParser(); ap.add_argument('--keep', type=int, default=2); ap.add_argument('--delete', action='store_true'); ap.add_argument('--dir', default=os.path.expanduser('~/.cache/rvt-ballet/models'))
a = ap.parse_args()
if not os.path.isdir(a.dir): sys.exit('no converted-model cache at %s (nothing to prune; geom-*.pkl caches live one level up in ~/.cache/rvt-ballet)' % a.dir)
def size(d): return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs if os.path.isfile(os.path.join(r, f)))
groups, drop = {}, []
for n in os.listdir(a.dir):
    d = os.path.join(a.dir, n)
    if not os.path.isdir(d): continue
    if n.endswith('.tmp'):
        if time.time() - os.path.getmtime(d) > 86400: drop.append((d, 'unfinished .tmp'))
        continue
    try: done = json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done'
    except Exception: done = False
    if not done: drop.append((d, 'incomplete (no meta / not done)')) if time.time() - os.path.getmtime(d) > 86400 else None; continue
    groups.setdefault(n.rsplit('-', 1)[0], []).append((os.path.getmtime(d), d))
for name, L in groups.items():
    L.sort(reverse=True)
    for _, d in L[a.keep:]: drop.append((d, 'older than the newest %d of %s' % (a.keep, name)))
tot = 0
for d, why in drop:
    s = size(d); tot += s; print('%s %6.0f MB  %s  (%s)' % ('DELETE' if a.delete else 'would delete', s / 1e6, os.path.basename(d), why))
    if a.delete: shutil.rmtree(d)
print('%s %d directories, %.1f GB' % ('deleted' if a.delete else 'would free', len(drop), tot / 1e9))
