"""4-byte-id layout (Revit 2019-2023 nested): trace prints parameter ids as unsigned 32-bit; they must match the signed ids the reader gives (regression: by-name edit was refused on every 2019 file)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.edit import _eid_val

def test_widths_agree():
    assert _eid_val('EID(4293966091)') == _eid_val('EID(%d)' % ((1 << 64) - 1001205)) == -1001205

def test_positive_and_junk():
    assert _eid_val('EID(26)') == 26 and _eid_val('EID(1116436)') == 1116436 and _eid_val('x') is None

if __name__ == '__main__': test_widths_agree(); test_positive_and_junk(); print('ok')
