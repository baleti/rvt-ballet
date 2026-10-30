"""Which stored, NAMED numeric parameters (ParamValueDouble / ParamValueInt with a name in the reader's table) exist on elements of a REAL project, by element class: candidates for set_num. Aggregate output only
(class and parameter names with counts; no ids, no element names, no paths). usage: tools/scan_numeric_candidates.py FILE [MAX_ELEMENTS]"""
import os, sys, collections, time
for p in (os.path.expanduser('~/rvt-research/edit-lab'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
import rvtedit, rvt_params
src = sys.argv[1]; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 4000; t0 = time.time()
ids = list(rvt_params.params(src).keys())[:cap]; ed = rvtedit.Edit(src); by = collections.defaultdict(collections.Counter); n_el = collections.Counter(); scanned = 0
for eid in ids:
    try: pn, i, r, log, q = ed.g.e.trace(eid)
    except Exception: continue
    scanned += 1; cls = r['class']; seen = set()
    for l in log:
        for kind in ('Double', 'Int'):
            if l[1] == 'ParamValue%s.m_paramId' % kind:
                try: v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v
                except ValueError: continue
                nm = rvt_params.PNAMES.get(str(pid))
                if nm and (kind, nm) not in seen: seen.add((kind, nm)); by[cls][(kind, nm)] += 1
    if seen: n_el[cls] += 1
print('scanned %d of %d elements in %.0f s; classes with stored named numeric params: %d' % (scanned, len(ids), time.time() - t0, len(n_el)))
for cls, c in sorted(n_el.items(), key=lambda t: -t[1])[:8]:
    print('  %-28s %5d elements; top params: %s' % (cls, c, ', '.join('%s %s x%d' % (k[0], k[1], v) for k, v in by[cls].most_common(4))))
