import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
MV = {'op': 'move', 'eid': 1, 'dx': 0.0, 'dy': 0.0, 'dz': 0.5}
X = {'Elevation from Level': 17.5, 'Offset from Host': 0.0, 'Power Total Connected': 0.0, 'Comments': 'a', 'Width': 2.0}

def Y(**kw): y = dict(X); y.update(kw); return y

def test_exact_dz_echo_allowed():
    y = Y(**{'Elevation from Level': 18.0, 'Offset from Host': 0.5, 'Power Total Connected': 0.5})
    assert save.vertical_echo(X, y, MV) == {'Elevation from Level', 'Offset from Host', 'Power Total Connected'}

def test_other_change_not_allowed_and_not_hidden():
    y = Y(**{'Elevation from Level': 18.0, 'Width': 2.1})
    assert 'Width' not in save.vertical_echo(X, y, MV)      # stays in the changed list, gate refuses

def test_no_driver_no_allowance():
    assert save.vertical_echo(X, Y(**{'Power Total Connected': 0.5}), MV) == set()

def test_wrong_amount_not_allowed():
    assert save.vertical_echo(X, Y(**{'Elevation from Level': 18.2}), MV) == set()

def test_horizontal_or_zero_move_no_allowance():
    y = Y(**{'Elevation from Level': 18.0})
    assert save.vertical_echo(X, y, dict(MV, dx=1.0)) == set() and save.vertical_echo(X, y, dict(MV, dz=0.0)) == set()
