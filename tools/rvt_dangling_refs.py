"""rvt_dangling_refs.py SRC.rte OUT.rte...: referential check of accepted single-element delete outputs (c7x-rvtmatrix, no VM). For each OUT (file name del_<Class>_<eid>.<ext>) count the remaining
elements whose stored integer parameter values equal the deleted eid in SRC, i.e. possible references left dangling. Aggregate: class, eid-free counts only. Heuristic (an int may equal an id by chance)."""
import os, sys, re, collections
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
import rvt_params
g = lambda x: x.get('params', x) if isinstance(x, dict) else {}
def refs(pr, eid): return sum(1 for e, d in pr.items() if e != eid and any(isinstance(v, int) and not isinstance(v, bool) and v == eid for v in g(d).values()))
src = rvt_params.params(sys.argv[1])
for f in sys.argv[2:]:
    m = re.match(r'del_(.+)_(\d+)\.\w+$', os.path.basename(f)); cls, eid = m.group(1), int(m.group(2))
    out = rvt_params.params(f); print(cls, 'refs_in_src=%d refs_in_out=%d gone=%s' % (refs(src, eid), refs(out, eid), eid not in out), flush=True)
