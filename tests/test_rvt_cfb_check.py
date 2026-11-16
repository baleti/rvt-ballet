"""tools/rvt_cfb_check.py accepts a genuine Autodesk template and reports INVALID for each injected container fault (c4x-rvtmatrix 2026-11-16: 7 of 7 caught)."""
import os, sys, glob, struct, pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import rvt_cfb_check as cc
S = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/71_*.rte')))
pytestmark = pytest.mark.skipif(not S, reason='Autodesk 2024 template not present')


def _data():
    return open(S[0], 'rb').read()


def _fat_pos(d):
    ss = 4096; f0 = struct.unpack_from('<I', d, 76)[0]; off = (f0 + 1) * ss
    s = next(i for i in range(100, 1000) if struct.unpack_from('<I', d, off + 4 * i)[0] == i + 1)
    return off + 4 * s, s


def test_genuine_is_valid(tmp_path):
    r = cc.check(S[0]); assert r['unowned_sectors'] == 0


@pytest.mark.parametrize('case', ['redirect', 'cut', 'loop', 'truncate', 'difat', 'dirstart', 'magic'])
def test_fault_is_invalid(tmp_path, case):
    d = bytearray(_data()); pos, s = _fat_pos(d)
    if case == 'redirect': struct.pack_into('<I', d, pos, s + 5)
    elif case == 'cut': struct.pack_into('<I', d, pos, 0xFFFFFFFE)
    elif case == 'loop': struct.pack_into('<I', d, pos, s - 50)
    elif case == 'truncate': d = d[:len(d) - 3 * 4096]
    elif case == 'difat': struct.pack_into('<I', d, 76, 0xFFFFFFFF)
    elif case == 'dirstart': struct.pack_into('<I', d, 48, struct.unpack_from('<I', d, 48)[0] + 1)
    elif case == 'magic': d[0] ^= 1
    p = tmp_path / 'x.rvt'; p.write_bytes(bytes(d))
    with pytest.raises(AssertionError): cc.check(str(p))
