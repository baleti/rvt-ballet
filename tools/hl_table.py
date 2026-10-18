"""tools/hl_table.py [FILEDIR ...]: line F1 of ~/review-compare/viewer/<file>/<vid>__ours3d_hl2.png against ~/review-compare/revit/<file>/<vid>.png for every pair (tools/hl_score.py registration), table + mean"""
import os, sys, subprocess, re
H = os.path.expanduser('~'); R = H + '/review-compare/revit'; O = H + '/review-compare/viewer'; D = os.path.dirname(os.path.abspath(__file__))
rows = []
for name in (sys.argv[1:] or sorted(os.listdir(O))):
    names = {}
    if os.path.exists('%s/%s/index.tsv' % (R, name)):
        for l in open('%s/%s/index.tsv' % (R, name)):
            t = l.rstrip('\n').split('\t')
            if t[0] == 'VIEW': names[t[1]] = '%s %s' % (t[2], t[4])
    for f in sorted(os.listdir('%s/%s' % (O, name))):
        m = re.match(r'(\d+)__ours3d_hl2?\.png$', f)
        if not m: continue
        vid = m.group(1); rv = '%s/%s/%s.png' % (R, name, vid)
        if not os.path.exists(rv): continue
        out = subprocess.run([sys.executable, D + '/hl_score.py', rv, '%s/%s/%s' % (O, name, f)], capture_output=True, text=True).stdout
        m2 = re.search(r'precision ([\d.]+) recall ([\d.]+) F1 ([\d.]+)', out)
        if m2: rows.append((name, vid, names.get(vid, ''), float(m2.group(1)), float(m2.group(2)), float(m2.group(3))))
for r in rows: print('%-40s %-8s %-34s P %.3f R %.3f F1 %.3f' % r)
if rows: print('mean F1 %.3f over %d views' % (sum(r[5] for r in rows) / len(rows), len(rows)))
