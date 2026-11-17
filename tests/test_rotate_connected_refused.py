"""2022 VM oracle: rotate of an element connected to MEP elements damaged a piping system (Volume 0). rotate_connected_refusal flags it, a move is not flagged."""
import os, pytest
from rvtballet.save import rotate_connected_refusal

def test_helper_synthetic():
    mem = {7: ['connected to 4 MEP element(s)'], 8: ['hosted on 3']}
    assert rotate_connected_refusal(mem, [{'op': 'rotate', 'eid': 7}]) == (7, 4)
    assert rotate_connected_refusal(mem, [{'op': 'move', 'eid': 7}]) is None
    assert rotate_connected_refusal(mem, [{'op': 'rotate', 'eid': 8}]) is None

ORIG = os.path.expanduser('~/c9x-fastedit/old/2022_orig.rvt')
@pytest.mark.skipif(not os.path.exists(ORIG), reason='2022 sample not present')
def test_real_2022_731025():
    from rvtballet.save import membership
    mem = membership(open(ORIG, 'rb').read(), {731025})
    assert rotate_connected_refusal(mem, [{'op': 'rotate', 'eid': 731025}]) == (731025, 4)
    assert rotate_connected_refusal(mem, [{'op': 'move', 'eid': 731025}]) is None
