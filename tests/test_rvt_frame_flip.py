"""Gate escape class (c4x-rvtmatrix item 193): an ECC-valid +1 on a gzip member's frame field must be refused by the output gate (RvtAdapter.source_damage).
'after' is caught today; 'stored' (before-frame, == compressed length + 8 in 1941 of 1941 genuine members) is expected to fail until the gate adds that rule; X1 / X2 have no zero-exception rule."""
import os, sys, glob, pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
S = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*Snowdon*HVAC.rvt')))
pytestmark = pytest.mark.skipif(not S, reason='Autodesk 2024 HVAC sample not present')
sg = pytest.importorskip('savegate.adapters', reason='savegate not importable')
import rvt_frame_flip as ff
X = lambda why: pytest.mark.xfail(strict=True, reason=why)      # strict: when the gate gains the rule the test XPASSes and fails, so the marker gets removed
CASES = ['after', pytest.param('stored', marks=X('gate does not check the before-frame stored length yet')), pytest.param('X1', marks=X('no zero-exception rule for X1')), pytest.param('X2', marks=X('no zero-exception rule for X2'))]


@pytest.mark.parametrize('fld', CASES)
def test_frame_field_flip_refused(tmp_path, fld):
    d = ff.flip(S[0], 'Partitions/21', 10, fld, str(tmp_path / 'o.rvt'))
    assert sg.RvtAdapter().source_damage(open(d, 'rb').read())
