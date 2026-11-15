"""rst_basic 2023 footing 512451 (StructFootingUserData): its box does not follow the origin, so a move is refused at the edit stage (the readback used to catch it after the work). Autodesk sample."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
import pytest
from rvtballet import edit
F = os.path.expanduser('~/rvt-research/corpus/2023/36_rst_basic_sample_project.rvt')

@pytest.mark.skipif(not os.path.exists(F), reason='sample missing')
def test_footing_move_refused():
    b = open(F, 'rb').read()
    with pytest.raises(edit.EditError, match='structural footing'):
        edit.apply_full(b, [edit.validate_op({'op': 'move', 'eid': 512451, 'dx': 1.0})])
