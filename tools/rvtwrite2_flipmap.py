#!/usr/bin/env python3
"""rvtwrite2_flipmap.py SRC N SEED: replays the offsets of rvtwrite2_flip.py and prints which CFB region (stream name+kind, slack, FAT, directory, minifat, free) each flipped byte lies in. Research only."""
import sys, os, random, collections
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb
src, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
b = open(src, 'rb').read(); c = cfb.CFB(b); ss = c.ss; own = {}
def mark(start, label):
    s = start
    while s < 0xFFFFFFFA and s not in own: own[s] = label; s = c.fat[s]
h = c.header; import struct
mark(struct.unpack('<I', h[48:52])[0], 'directory'); mf = struct.unpack('<I', h[60:64])[0]
if mf < 0xFFFFFFFA: mark(mf, 'minifat')
mark(c.entries[0].start, 'ministream')
for s, v in enumerate(c.fat):
    if v == 0xFFFFFFFD: own[s] = 'FAT'
    if v == 0xFFFFFFFC: own[s] = 'DIFAT'
for e in c.entries:
    if e.type == 2 and e.size >= c.cutoff: mark(e.start, 'stream:%d:%s' % (e.idx, e.name))
r = random.Random(seed); cnt = collections.Counter()
for i in range(n):
    off = r.randrange(512, len(b)); r.randrange(8)
    sec = (off - ss) // ss if c.major == 4 else (off - 512) // ss
    lab = own.get(sec, 'free/unowned'); 
    if lab.startswith('stream:'):
        e = c.entries[int(lab.split(':')[1])]; chain = []; s = e.start
        while s < 0xFFFFFFFA: chain.append(s); s = c.fat[s]
        pos = chain.index(sec) * ss + (off - (sec + 1) * ss if c.major == 4 else off - 512 - sec * ss)
        if pos >= e.size: lab += ' [slack past size]'
    print(i, off, lab.split(':',2)[-1] if lab.startswith('stream') else lab); cnt[lab.split(':')[2] if lab.startswith('stream') else lab] += 1
print(dict(cnt))
