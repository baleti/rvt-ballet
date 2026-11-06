import os
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import pytest
from rvtballet import edit

@pytest.mark.parametrize('v', [0.0, -0.0, float('nan'), float('inf'), -float('inf'), 1e300, 5.1e4, True, '1'])
def test_bad_move_values_refused(v):
    with pytest.raises(edit.EditError):
        edit.validate_op({'op': 'move', 'eid': 5, 'dx': v, 'dy': 0, 'dz': 0})

def test_moves_add_and_cancel():
    m = lambda d: edit.validate_op({'op': 'move', 'eid': 5, 'dx': d, 'dy': 0, 'dz': 0})
    assert edit.compose([m(1.0), m(2.0)])[0]['dx'] == 3.0
    assert edit.compose([m(1.0), m(-1.0)]) == []
