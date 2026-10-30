"""inventory .rvt/.rte by Revit year (aggregate only; ids = short sha). usage: rvtwrite2_inv.py OUT.tsv DIR..."""
import sys, os, hashlib, re
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb
rows = []
for d in sys.argv[2:]:
    for r, _, fs in os.walk(d):
        for f in fs:
            if f.lower().endswith(('.rvt', '.rte')):
                p = os.path.join(r, f)
                try:
                    b = open(p, 'rb').read(); c = cfb.CFB(b); s = c.streams()['BasicFileInfo'].data
                    t = s.decode('utf-16le', 'ignore'); m = re.search(r'(20[12]\d)', t); y = m.group(1) if m else '?'
                    ws = 'Worksharing' in t and 'Not enabled' not in t
                except Exception as e: y = 'ERR'; ws = False
                rows.append((hashlib.sha1(p.encode()).hexdigest()[:8], y, os.path.getsize(p), p))
rows.sort(key=lambda x: (x[1], x[2]))
open(sys.argv[1], 'w').write(''.join('%s\t%s\t%d\t%s\n' % x for x in rows))
from collections import Counter; print(sorted(Counter(r[1] for r in rows).items()))
