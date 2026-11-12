import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
Y9 = os.path.expanduser('~/c3x-tmp-c4x/ddmin/y9.rvt')     # local 2026 Structural add with one 238,572 B member (Autodesk sample derived)
pytestmark = pytest.mark.skipif(not os.path.exists(Y9), reason='local oversize-member sample absent')
def test_split_oversize_cuts_like_revit():
    import wledit, rvt_split_oversize as S
    ed = wledit.Editor(Y9); pt = ed.part('Partitions/27')
    before = b''.join(bytes(m['raw']) for m in pt.mem); n0 = len(pt.mem)
    cuts = S.split_oversize(pt)
    assert cuts == [327] and len(pt.mem) == n0 + 1
    assert [len(pt.mem[i]['raw']) for i in (327, 328)] == [131088, 107484]
    assert b''.join(bytes(m['raw']) for m in pt.mem) == before        # content unchanged
    assert max(len(m['raw']) for m in pt.mem) <= S.CAP
def test_split_refuses_too_big(monkeypatch):
    import rvt_split_oversize as S
    class P:
        mem = [dict(raw=bytearray(3 * S.CAP))] * 5; gaps = []; LIMIT = 0
    with pytest.raises(ValueError): S.split_oversize(P())
