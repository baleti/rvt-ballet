"""synthetic: the wall resize planner finds +-end-coordinate doubles and refuses collisions (no .rvt needed)"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import rvt_wall_resize_plan as P
def _tpl(*v): return {'hdr': b''.join(struct.pack('<d', x) for x in v), 'rec': b'', 'item': b''}
def test_plan_finds_both_signs():
    h = P.plan(_tpl(0.0, 11.0, -11.0, 10.0), {'x1': 11.0, 'y1': 0.0})
    assert len(h['x1']) == 2 and 'y1' not in h
def test_collision_with_height_refused():
    assert P.collisions({'x1': 10.0, 'y1': 0.0}, [10.0, 0.5]) == ['x1']
    assert P.collisions({'x1': 11.0, 'y1': 0.0}, [10.0, 0.5]) == []
