import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save

def test_unconnected_height_warns():
    w = save.noop_numeric_warnings([{'op': 'set_num', 'eid': 5, 'param': 'Unconnected Height', 'value': 20.25}, {'op': 'set_num', 'eid': 6, 'param': 'Top Offset', 'value': 1.0}])
    assert len(w) == 1 and 'element 5' in w[0] and 'Top Offset' in w[0]
