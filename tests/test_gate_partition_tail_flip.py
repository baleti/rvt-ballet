"""Gate: a changed partition whose bytes after the last gzip member differ from the source tail (beyond trailing zeros) is flagged partition_tail; a zero-only change is not. Autodesk-free write-lab scene (2024 cols2)."""
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
LIB = os.path.expanduser('~/rvt-research/write-lab')


def test_tail_flip_flagged():
    if not os.path.exists(RTE): print('skip'); return
    sys.path.insert(0, LIB); sys.path.insert(0, os.path.expanduser('~/src/savegate'))
    import cfb as _c, rvtw as _w, wlpart as _wl
    from savegate.adapters import RvtAdapter
    src = open(RTE, 'rb').read()
    st = _c.CFB(src).streams(); k = 'Partitions/61'
    tail = bytes(_wl.Partition(_w.Stream(st[k].data)).tail)
    nz = [i for i, b in enumerate(tail) if b]; assert nz
    probe = tail[nz[0]:nz[0] + 48]; at = src.find(probe); assert at > 0 and src.find(probe, at + 1) < 0
    bad = bytearray(src); bad[at + 3] ^= 0x5a; bad = bytes(bad)
    ad = RvtAdapter(); man = {'modified': ['x'], 'allow_changed_streams': ()}
    def tails(buf):
        ad._verify_bufs = (src, buf)
        return [p for p in ad.extra_checks(man) if p[0] == 'partition_tail']
    assert tails(src) == []
    assert tails(bad), 'a flipped non-zero tail byte must be flagged'
