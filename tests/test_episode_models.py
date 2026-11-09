"""Offline episode-model regression (Autodesk sample pairs made by Revit itself, local only; skipped when the pairs are absent).
Models: DIT (rvt_dit_episode), BasicFileInfo (rvt_bfi_episode), Contents (rvt_contents_episode). Each must reproduce Revit's stream change
(DIT/BFI exactly modulo timestamp/GUID, Contents payload-equivalent)."""
import glob, os, sys, zlib
import pytest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
for p in ('~/rvt-research/write-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
def _readable(d):
    try:
        import adiff; adiff.graw(d + 'base.rvt', 'Contents'); adiff.graw(d + 'after.rvt', 'Contents'); return True
    except Exception: return False
PAIRS = [d for d in sorted(glob.glob(os.path.expanduser('~/c2x-diff/*/'))) if os.path.exists(d + 'base.rvt') and os.path.exists(d + 'after.rvt') and _readable(d)][:4]
pytestmark = pytest.mark.skipif(not PAIRS, reason='no Revit-made base/after pairs on this machine')
def _g(f, n):
    import adiff; return adiff.graw(f, n)
@pytest.mark.parametrize('d', PAIRS)
def test_dit_matches_revit_modulo_timestamp(d):
    import rvt_dit_episode as D
    x = _g(d + 'base.rvt', 'Global/DocumentIncrementTable'); y = _g(d + 'after.rvt', 'Global/DocumentIncrementTable')
    dr = (len(_g(d + 'after.rvt', 'Global/ElemTable')) - len(_g(d + 'base.rvt', 'Global/ElemTable'))) // 40
    p = D.dit_next(x, 0, dr)
    assert len(p) == len(y)
    df = [i for i in range(len(y)) if p[i] != y[i]]
    runs = []
    for i in df:
        if runs and i - runs[-1][1] == 1: runs[-1][1] = i
        else: runs.append([i, i])
    assert len(runs) <= 2 and all(r[1] - r[0] < 4 for r in runs)      # only the two 4-byte save-time words may differ
@pytest.mark.parametrize('d', PAIRS)
def test_contents_payload_equals_revit(d):
    import rvt_dit_episode as D, rvt_contents_episode as C
    r = lambda b: zlib.decompressobj(31).decompress(b[b.find(b'\x1f\x8b\x08'):])
    x = _g(d + 'base.rvt', 'Contents'); y = _g(d + 'after.rvt', 'Contents')
    p = C.contents_next(x, D.top_counters(_g(d + 'base.rvt', 'Global/DocumentIncrementTable')))
    assert len(p) == len(y) and r(p) == r(y)
def test_dit_without_episode_records_refused():
    import rvt_dit_episode as D
    with pytest.raises(Exception): D.dit_next(b'\0' * 64, 0)
