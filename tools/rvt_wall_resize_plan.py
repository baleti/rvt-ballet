"""Offline PLANNER (writes nothing) for a straight-wall length change.
usage: rvt_wall_resize_plan.py FILE.rvt WALL_ID X1 Y1 [WRITE_LAB_DIR]
Finds, in the wall's hdr/rec/item records, every double equal to +-X1 or +-Y1 (end point of the wall)
and reports them. Refuses (exit 2) when X1 or Y1 (nonzero) collides with another dimension value
that cannot be told apart, so the caller must not guess. Witness: Revit 10 ft vs 11 ft new-wall pair
(Snowdon Facades 2024): the +-L doubles are exactly the 72 fields Revit changed (+-1.0 per 1 ft)."""
import os, sys, struct, collections
def plan(tpl, vals, tol=1e-6):
    hits = collections.defaultdict(list)
    for k in ('hdr', 'rec', 'item'):
        a = tpl[k]
        for o in range(len(a) - 7):
            v = struct.unpack_from('<d', a, o)[0]
            if v != v: continue
            for name, t in vals.items():
                if t and (abs(v - t) < tol or abs(v + t) < tol): hits[name].append((k, o, v))
    return dict(hits)
def collisions(vals, others, tol=1e-6):
    """names of end coordinates that equal (in magnitude) another dimension of the wall (height, thickness, base offset...):
    their hits cannot be told from the other dimension, so the planner must refuse"""
    return [n for n, t in vals.items() if t and any(abs(abs(t) - abs(o)) < tol for o in others)]
def main(path, eid, x1, y1, wl=None):
    wl = wl or os.path.expanduser('~/rvt-research/write-lab')
    os.chdir(wl); sys.path.insert(0, '.'); import rvtgen
    tpl = rvtgen.Gen(path).template(int(eid))
    vals = {'x1': float(x1), 'y1': float(y1)}
    others = [float(v) for v in os.environ.get('WALL_OTHER_DIMS', '').split(',') if v]
    bad = collisions(vals, others)
    if bad: print('refuse: end coordinate collides with another wall dimension:', bad); return 2
    h = plan(tpl, vals)
    for n, l in h.items(): print(n, len(l), 'fields', l[:6])
    if not h: print('no match: refuse'); return 2
    return 0
if __name__ == '__main__': sys.exit(main(*sys.argv[1:]))
