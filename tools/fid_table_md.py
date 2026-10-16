"""~/rvt-research/FID_TABLE_FINAL.txt (reader, definition: Revit Volume at Fine detail) -> docs/FIDELITY-FINAL.md with three honest buckets per class and per year:
reader-accurate / parametric-unproven (true-off) / box-only. usage: tools/fid_table_md.py [FID_TABLE_FINAL.txt]"""
import sys, os, re
src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/rvt-research/FID_TABLE_FINAL.txt')
L = open(src).read().splitlines(); out = ['# Fidelity per class and year (reader acceptance, final corpus run)', '',
  'Source: %s (c5-geometry, final code, 60/61 corpus files). Judged with the reader definition: the element is "accurate" when its mesh matches Revit\'s own geometry (bbox IoU, Revit Volume at Fine detail for loadable families). '
  'Buckets: **reader-accurate** = true geometry that agrees with Revit; **parametric-unproven** = true geometry whose extents/volume do not (yet) agree ("true-off"); **box-only** = no decoded solid, drawn as bounding box.' % os.path.basename(src), '',
  '## Per class (all years)', '', '| class | n | reader-accurate | parametric-unproven | box-only | median IoU | median abs volume error |', '|---|---|---|---|---|---|---|']
yr = []; notes = []; mode = 0; cls = {}
for l in L:
    if l.startswith('per year'): mode = 1; continue
    if mode == 0:
        m = re.match(r'(\w+)\s+(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%\s+iou ([\d.]+)\s+vol ([\d.na]+)%?', l)
        if m: cls[m[1]] = [float(m[3]), float(m[4]), float(m[5]), int(m[2]), float(m[6])]
        if m: out.append('| %s | %s | %s%% | %s%% | %s%% | %s | %s |' % (m[1], m[2], m[3], m[4], m[5], m[6], m[7] + ('%' if m[7] != 'nan' else '')))
    else:
        m = re.match(r'(\w+)\s+(.*)', l)
        f = re.findall(r'(20\d\d):(\d+)/(\d+)/(\d+)\(n(\d+)\)', l)
        if m and f: yr.append((m[1], f))
        elif l.strip(): notes.append(l.strip())
years = sorted({y for _, r in yr for y, *_ in r})
out += ['', '## Per class and year (accurate % / unproven % / box %, n elements)', '', '| class | ' + ' | '.join(years) + ' |', '|---|' + '---|' * len(years)]
for c, r in yr:
    d = {y: '%s/%s/%s (%s)' % (a, b, k, n) for y, a, b, k, n in r}
    out.append('| %s | %s |' % (c, ' | '.join(d.get(y, '') for y in years)))
out += ['', '## Notes from the reader', ''] + ['* ' + n for n in notes]
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'FIDELITY-FINAL.md'), 'w').write('\n'.join(out) + '\n'); print(len(out), 'lines')
import json; json.dump(cls, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'fidclass.json'), 'w'), separators=(',', ':'))   # class -> [accurate %, unproven %, box %, n, median IoU] for the inspector
