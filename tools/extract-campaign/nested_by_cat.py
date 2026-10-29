#!/usr/bin/env python3
"""nested_by_cat.py : aggregate the manifests of lift/dwa, lift/dwb (copied under nbm/ beforehand) by Revit year x category x nesting depth.
Writes NESTED-BY-CATEGORY.md and nb_index.tsv (key<TAB>year<TAB>category<TAB>depth<TAB>status<TAB>relpath).
Open results (chk/res_nb_*/rfacheck.tsv) are joined by the flattened name key__category__name.rfa."""
import json, os, subprocess, glob, collections, sys
os.chdir(os.environ.get('CAMPAIGN_ROOT', os.getcwd()))
years = {}
for l in open('allrvt_ver.tsv'):
    sz, y, p = l.rstrip('\n').split('\t', 2); years[p] = y
rows = []
for side in 'ab':
    lst = [l.rstrip('\n').split('\t', 1)[1] for l in open('dw_%s.tsv' % side)]
    for i, p in enumerate(lst, 1):
        mf = 'nbm/dw%s/b%d/manifest.json' % (side, i)
        if not os.path.exists(mf): continue
        y = years.get(p, '?')
        m = json.load(open(mf))
        for f in m['families']:
            r = f.get('rfa') or {}
            if not r: continue
            depth = r.get('nested_depth', (1 if r.get('nested') else 0))
            rows.append(('dw%sb%d' % (side, i), y, f.get('category') or '?', depth, r.get('status'), r.get('file', ''), f.get('name'), int(os.path.getmtime(mf))))
open('nb_index.tsv', 'w').write('\n'.join('\t'.join(map(str, r)) for r in rows))
opened = {}
for f in glob.glob('chk/res_nb_*/rfacheck.tsv'):
    for l in open(f):
        p = l.rstrip('\n').split('\t')
        if p[0] in ('OPEN', 'OPENFAIL'): opened[p[1]] = p[0]
def key(r): return r[0] + '__' + r[2].replace('/', '_') + '__' + os.path.basename(r[5])
agg = collections.defaultdict(collections.Counter)
for r in rows:
    d = 'depth%d' % r[3] if r[3] < 3 else 'depth3+'
    k = (r[1], r[2], d)
    agg[k]['total'] += 1; agg[k][r[4] or 'none'] += 1
    o = opened.get(key(r))
    if o: agg[k][o] += 1
out = ['# Nested families by Revit year x category x depth (aggregate only)\n', 'rows: written/skipped/error from manifests; OPEN/OPENFAIL = Revit open check where run.\n',
       '| year | category | depth | total | written | skipped | error | OPEN | OPENFAIL |', '|---|---|---|---|---|---|---|---|---|']
for k in sorted(agg):
    c = agg[k]; out.append('| %s | %s | %s | %d | %d | %d | %d | %d | %d |' % (k + (c['total'], c['written'], c['skipped'], c['error'], c['OPEN'], c['OPENFAIL'])))
open('NESTED-BY-CATEGORY.md', 'w').write('\n'.join(out) + '\n')
print(len(rows), 'families', len(agg), 'groups')

# per year summary (checked = OPEN + OPENFAIL): used for the SCOREBOARD lines
ys = collections.defaultdict(lambda: collections.Counter())
for (y, cat, d), c in agg.items():
    k = 'flat' if d == 'depth0' else d
    ys[(y, k)]['total'] += c['total']; ys[(y, k)]['open'] += c['OPEN']; ys[(y, k)]['fail'] += c['OPENFAIL']
lines = ['', '## Per year summary (opened / checked; total = lifted)', '| year | kind | opened | checked | lifted |', '|---|---|---|---|---|']
for (y, k) in sorted(ys):
    c = ys[(y, k)]; lines.append('| %s | %s | %d | %d | %d |' % (y, k, c['open'], c['open'] + c['fail'], c['total']))
open('NESTED-BY-CATEGORY.md', 'a').write('\n'.join(lines) + '\n')
print('\n'.join(lines[-(len(lines) - 2):]) if '--summary' in sys.argv else '')
