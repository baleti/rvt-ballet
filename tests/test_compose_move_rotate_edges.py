import os
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import pytest
from rvtballet import edit

def mv(e, dx): return {'op': 'move', 'eid': e, 'dx': dx, 'dy': 0.0, 'dz': 0.0}
def rt(e, d): return {'op': 'rotate', 'eid': e, 'deg': d}

def test_float_cancel_moves_dropped(): assert edit.compose([mv(1, 0.1), mv(1, 0.2), mv(1, -0.3)]) == []
def test_rotations_summing_to_360_dropped(): assert edit.compose([rt(1, 200.0), rt(1, 160.0)]) == []
def test_move_and_rotate_on_deleted_element_dropped():
    out = edit.compose([mv(1, 1.0), rt(1, 30.0), {'op': 'delete', 'eid': 1}, mv(1, 2.0)])
    assert out == [{'op': 'delete', 'eid': 1}]
def test_sum_beyond_limit_refused():
    with pytest.raises(edit.EditError): edit.compose([mv(1, 4e4), mv(1, 4e4)])
def test_other_elements_not_merged():
    out = edit.compose([mv(1, 1.0), mv(2, 1.0)]); assert [o['eid'] for o in out] == [1, 2]
