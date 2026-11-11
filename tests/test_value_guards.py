import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
from rvtballet import edit

BAD = [float('nan'), float('inf'), -float('inf'), 1e300, -1e16, True, '1', None]

@pytest.mark.parametrize('v', BAD)
def test_set_num_double_rejected(v):
    with pytest.raises(edit.EditError):
        edit.validate_op({'op': 'set_num', 'eid': 5, 'param': 'Cost', 'value': v, 'kind': 'Double'})

@pytest.mark.parametrize('v', [2 ** 31, -2 ** 31 - 1, 1.5])
def test_set_num_int_rejected(v):
    with pytest.raises(edit.EditError):
        edit.validate_op({'op': 'set_num', 'eid': 5, 'param': 'Cost', 'value': v, 'kind': 'Int'})
