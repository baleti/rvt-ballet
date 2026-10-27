"""sweep jsonl -> docs/SPEED.md: per file time to the first usable view (reader + tables + preview: element table, levels, grids, bboxes, preview mesh) and total conversion, sorted by size.
usage: tools/speed_table.py [sweep.jsonl]"""
import json, os, sys
src = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/.cache/rvt-ballet/sweep4.jsonl')
R = {}
for l in open(src):
    r = json.loads(l)
    if r['status'] == 'ok' and r.get('timings'): R[r['file']] = r
rows = sorted(R.values(), key=lambda r: r['mb'])
out = ['# Conversion speed (host1, one worker, current converter + Rust fast path)', '',
  'First usable = reader + tables + preview (`timings` of tools/sweep.py): the page opens with the element table, levels, grids and a preview mesh; the full meshes stream in until `total`. Cached models open instantly (about 0.3 s).', '',
  '| year | file | MB | first usable s | total s | elements | triangles |', '|---|---|---|---|---|---|---|']
for r in rows:
    t = r['timings']; fu = t['reader'] + t['tables'] + t['preview']
    out.append('| %s | %s | %.1f | %.1f | %.1f | %d | %d |' % (r['year'], r['file'], r['mb'], fu, t['total'], r['elements'], r['tris']))
big = [r for r in rows if r['mb'] >= 25]
out += ['', '## Files of 25 MB and more', '',
  'Timings come from a shared host1 slice and can be inflated by neighbouring jobs (2026 Site went 48.7 s -> 7.4 s with the Rust face-edge index; 2017 rme_advanced reader 47 s -> 19 s cold, 7 s with a warm extraction cache). Median first usable %.1f s, median total %.1f s (n=%d). Slowest first usable: %s.' % (
    sorted(r['timings']['reader'] + r['timings']['tables'] + r['timings']['preview'] for r in big)[len(big) // 2],
    sorted(r['timings']['total'] for r in big)[len(big) // 2], len(big),
    ', '.join('%s %.0f s' % (r['file'][:30], r['timings']['reader'] + r['timings']['tables'] + r['timings']['preview']) for r in sorted(big, key=lambda r: -(r['timings']['reader'] + r['timings']['tables'] + r['timings']['preview']))[:3]))]
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'SPEED.md'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out[-3:]))
