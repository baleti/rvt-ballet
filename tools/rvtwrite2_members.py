"""max gzip member raw size per Partitions/* stream, per year (aggregate). usage: rvtwrite2_members.py INV.tsv YEAR [MAXMB]"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb, rvtw, wlpart
from collections import Counter
y = sys.argv[2]; mx = int(sys.argv[3]) << 20 if len(sys.argv) > 3 else 1 << 62
for sid, yy, s, p in (l.rstrip('\n').split('\t') for l in open(sys.argv[1])):
    if yy != y or int(s) > mx: continue
    try:
        S = cfb.CFB(open(p, 'rb').read()).streams(); m = []
        for n, e in S.items():
            if n.startswith('Partitions/'):
                st = rvtw.Stream(e.data)
                if len(st.payload) >= 40: m += [len(k['raw']) for k in wlpart.Partition(st).mem]
        print(y, sid, len(m), 'max', max(m) if m else 0, flush=True)
    except Exception as ex: print(y, sid, 'ERR', type(ex).__name__, str(ex)[:60], flush=True)
