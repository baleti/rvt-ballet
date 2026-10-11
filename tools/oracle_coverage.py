"""for one converted model + its gt_geom oracle: which oracle elements (classes) have no geometry / no element / box-only in the viewer.  usage: tools/oracle_coverage.py MODELDIR GTFILE.tsv"""
import sys, json, collections
m = json.load(open(sys.argv[1] + '/meta.json')); by = {e[0]: e for e in m['elements']}
skipcls = {'Material', 'GraphicsStyle', 'FillPatternElement', 'LinePatternElement', 'Phase', 'Element', 'Category'}
oc = {}; haveG = set(); haveBB = set()
for l in open(sys.argv[2], errors='ignore'):
    x = l.rstrip('\n').split('\t')
    if x[0] == 'EL' and x[2] not in skipcls: oc[int(x[1])] = (x[2], x[3], x[4])
    elif x[0] == 'BB': haveBB.add(int(x[1]))
    elif x[0] == 'G': haveG.add(int(x[1].split('.')[0]))
rows = collections.defaultdict(collections.Counter)
for i, (cls, cat, name) in oc.items():
    if i not in haveBB and i not in haveG: continue
    e = by.get(i)
    rows[(cls, cat)]['missing in viewer' if e is None else 'class ' + e[1] + ' fid ' + e[6]] += 1
for k, v in sorted(rows.items()): print(k, dict(v))
