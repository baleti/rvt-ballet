"""compose() property fuzz (no backend, no files): 3000 random op lists over 4 elements. Checks: idempotent; per element net move/rotate equals the sums (net zero dropped); set_string last value per (eid,param) wins;
nothing survives for an element that is deleted; delete appears at most once; no op invented."""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
R = random.Random(7)
def mk():
    e = R.choice([1, 2, 3, 4]); k = R.choice(['move', 'rotate', 'set_string', 'delete'])
    if k == 'move': return {'op': 'move', 'eid': e, 'dx': R.choice([0, 1, -1, 2.5]), 'dy': R.choice([0, 1, -2]), 'dz': 0.0}
    if k == 'rotate': return {'op': 'rotate', 'eid': e, 'deg': R.choice([0, 30, -30, 90, 360])}
    if k == 'set_string': return {'op': 'set_string', 'eid': e, 'param': R.choice(['Mark', 'Comments']), 'value': str(R.randrange(5))}
    return {'op': 'delete', 'eid': e}
for it in range(3000):
    ops = [mk() for _ in range(R.randrange(1, 9))]
    try: c = edit.compose(ops)
    except edit.EditError: continue
    assert edit.compose(c) == c, ('not idempotent', ops)
    dels = {o['eid'] for o in ops if o['op'] == 'delete'}
    assert sorted(o['eid'] for o in c if o['op'] == 'delete') == sorted(dels), ('delete count', ops, c)
    for o in c:
        assert o['op'] == 'delete' or o['eid'] not in dels, ('op on deleted element', ops, c)
    for e in {1, 2, 3, 4} - dels:
        sm = [sum(o[k] for o in ops if o['op'] == 'move' and o['eid'] == e) for k in ('dx', 'dy', 'dz')]
        mv = [o for o in c if o['op'] == 'move' and o['eid'] == e]
        if max(abs(x) for x in sm) < 1e-12: assert not mv, ('net zero move kept', ops, c)
        else: assert len(mv) == 1 and [mv[0]['dx'], mv[0]['dy'], mv[0]['dz']] == sm, ('move sum', ops, c)
        rs = sum(o['deg'] for o in ops if o['op'] == 'rotate' and o['eid'] == e); ro = [o for o in c if o['op'] == 'rotate' and o['eid'] == e]
        if abs(math.remainder(rs, 360.0)) < 1e-9: assert not ro, ('net zero rotate kept', ops, c)
        else: assert len(ro) == 1 and ro[0]['deg'] == rs, ('rotate sum', ops, c)
        for p in ('Mark', 'Comments'):
            ss = [o['value'] for o in ops if o['op'] == 'set_string' and o['eid'] == e and o['param'] == p]
            got = [o['value'] for o in c if o['op'] == 'set_string' and o['eid'] == e and o['param'] == p]
            assert got == (ss[-1:] if ss else []), ('last wins', ops, c)
print('compose fuzz OK (3000 lists)')
