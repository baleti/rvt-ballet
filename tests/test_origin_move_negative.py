import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet.save import _origin_move_bad
D = os.path.expanduser('~/rvtsave-work/c5x64')
O, M = os.path.join(D, 'orig.rvt'), os.path.join(D, 'moved.rvt')
pytestmark = pytest.mark.skipif(not (os.path.exists(O) and os.path.exists(M)), reason='local Snowdon Structural 2024 pair not present')

def _bad(**d):
    return _origin_move_bad(open(O, 'rb').read(), open(M, 'rb').read(), dict(eid=673054, **d))

def test_declared_matches():
    assert _bad(dx=2.0) == []

def test_wrong_distance_refused():
    assert _bad(dx=1.0)

def test_wrong_axis_refused():
    assert _bad(dy=2.0)

def test_no_move_declared_refused():
    assert _bad(dx=0.0)
