import os
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import pytest
from rvtballet import edit

@pytest.mark.parametrize('v', [0.0, -0.0, float('nan'), float('inf'), -float('inf'), 1e300, 5.1e4, 45000.0, 10001.0, True, '1'])
def test_bad_move_values_refused(v):
    with pytest.raises(edit.EditError):
        edit.validate_op({'op': 'move', 'eid': 5, 'dx': v, 'dy': 0, 'dz': 0})

def test_moves_add_and_cancel():
    m = lambda d: edit.validate_op({'op': 'move', 'eid': 5, 'dx': d, 'dy': 0, 'dz': 0})
    assert edit.compose([m(1.0), m(2.0)])[0]['dx'] == 3.0
    assert edit.compose([m(1.0), m(-1.0)]) == []

def test_far_cumulative_refused():
    m = lambda d: edit.validate_op({'op': 'move', 'eid': 5, 'dx': d, 'dy': 0, 'dz': 0})
    with pytest.raises(edit.EditError):
        edit.compose([m(9000.0), m(9000.0)])


@pytest.mark.parametrize('v', [1e-300, 5e-324, 1e-12, 1e-9])
def test_subresolution_move_refused(v):
    with pytest.raises(edit.EditError):
        edit.validate_op({'op': 'move', 'eid': 5, 'dx': v, 'dy': 0, 'dz': 0})


def test_float_noise_chain_cancels():
    m = lambda d: edit.validate_op({'op': 'move', 'eid': 5, 'dx': d, 'dy': 0, 'dz': 0})
    assert edit.compose([m(0.1), m(0.2), m(-0.3)]) == []
