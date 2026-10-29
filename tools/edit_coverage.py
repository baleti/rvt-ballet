"""Edit coverage: for every element class in a .rvt, how many elements carry each validated string edit field (rvtballet.edit.FIELDS).
usage: tools/edit_coverage.py FILE.rvt [OUT.md]   (aggregate counts only; no element names/ids are written)"""
import os, sys, collections, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
sys.path.insert(0, edit.WL); import wledit
def main(path, out=None):
    t0 = time.time(); ed = wledit.Editor(path); cls = {}
    import sqlite3
    try: ids = list(ed.m.index) if hasattr(ed.m, 'index') else None
    except Exception: ids = None
    if ids is None: ids = sorted({e for p in ed.m.parts.values() for e in p.get('ids', [])}) if all('ids' in p for p in ed.m.parts.values()) else None
    if ids is None:
        sys.path.insert(0, os.path.expanduser('~/rvt-research')); import rvt_geometry as G
        ids = G.file_geometry_index(path); cls = {k: str(v) for k, v in ids.items()}; ids = list(ids)
    cnt = collections.defaultdict(lambda: collections.Counter()); tot = collections.Counter(); err = collections.Counter()
    for eid in ids:
        c = cls.get(eid, '?'); tot[c] += 1
        try: log = ed.trace(eid)[3]
        except Exception as e: err[c] += 1; continue
        have = {l[1] for l in log}
        for f in edit.FIELDS:
            if f in have: cnt[c][f] += 1
    lines = ['| element class | elements | ' + ' | '.join(edit.FIELDS) + ' | not traceable |', '|---|---|' + '---|' * (len(edit.FIELDS) + 1)]
    for c, n in sorted(tot.items(), key=lambda t: -t[1]):
        lines.append('| %s | %d | %s | %d |' % (c, n, ' | '.join(str(cnt[c][f]) for f in edit.FIELDS), err[c]))
    txt = '\n'.join(lines) + '\n\n%d elements, %d classes, %.0f s\n' % (sum(tot.values()), len(tot), time.time() - t0)
    print(txt)
    if out: open(out, 'w').write(txt)
main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
