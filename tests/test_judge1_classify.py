import rvt_judge1 as J
C = {'eh': {5: 'ctl'}, 'ec': {5: 'Mullion/x'}}
def P(h): return {'eh': {5: h}, 'ec': {5: 'Mullion/x'}}
V = {'Mullion/x'}
def test_dependent_with_twin():
    assert J.classify_extra([5], C, P('new'), None, {5: 'new'}, V) == ([5], [], [])
def test_transient_with_twin_passes():
    assert J.classify_extra([5], C, P('first'), P('ctl'), {5: 'ctl'}, V) == ([], [5], [])
def test_transient_without_twin_fails():      # a missing/timed-out twin must never give a PASS
    assert J.classify_extra([5], C, P('first'), P('ctl'), None, V) == ([], [], [5])
def test_transient_wrong_class_fails():
    assert J.classify_extra([5], C, P('first'), P('ctl'), {5: 'ctl'}, {'Wall/x'}) == ([], [], [5])
def test_settled_not_equal_control_fails():
    assert J.classify_extra([5], C, P('first'), P('other'), {5: 'ctl'}, V) == ([], [], [5])
