import os, pickle, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
PK = os.path.expanduser('~/c3x-tmp-c4x/ddmin/ent.pkl')      # first 700 B of base/ours/Revit-after partitions (local Autodesk sample, c4xaw26)
pytestmark = pytest.mark.skipif(not os.path.exists(PK), reason='local Revit-made pair cache absent')
def test_stamp_entries_reproduces_revit_headers():
    import rvt_ep_stamp as S
    P = pickle.load(open(PK, 'rb'))
    out, n = S.stamp_entries(P['ours'], 0x426, 0x427)
    assert n == 12
    for k in range(1, 13):
        o = 14 + 22 * k
        assert out[o:o + 22] == P['revit'][o:o + 22]
