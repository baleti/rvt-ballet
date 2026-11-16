"""tools/rvt_untouched_bytes.py: a genuine segment-writer edit leaves 0 bytes changed outside the dirty members and their declared frame fields; the ECC-valid frame faults that
the gate misses (item 193/196: stored, X1, X2, after-length) are all reported as violations (c4x-rvtmatrix item 198)."""
import os, sys, glob, pytest
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, '..', 'tools')); sys.path.insert(0, os.path.join(here, '..'))
S = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*Snowdon*HVAC.rvt')))
pytestmark = pytest.mark.skipif(not S, reason='Autodesk 2024 HVAC sample not present')
import rvt_untouched_bytes as ub, rvt_frame_flip as ff
import cfb, rvtw


def _sd(path, part='Partitions/21'):
    return cfb.CFB(open(path, 'rb').read()).streams()[part].data


def test_segedit_fit_edit_has_no_violations(tmp_path):
    from rvtballet import segedit
    out = str(tmp_path / 'o.rvt'); segedit.apply_ops(S[0], out, [{'op': 'set_string', 'eid': 1365188, 'param': 'Mark', 'value': 'UB1'}], mode='fit')
    r = ub.check_partition(None, None, sa=_sd(S[0]), sb=_sd(out)); assert r['dirty'] == 1 and r['n_violations'] == 0


@pytest.mark.parametrize('fld', ['stored', 'X1', 'X2', 'after'])
def test_frame_fault_is_a_violation(tmp_path, fld):
    d = ff.flip(S[0], 'Partitions/21', 10, fld, str(tmp_path / 'f.rvt'))
    r = ub.check_partition(None, None, sa=_sd(S[0]), sb=_sd(d)); assert r['n_violations'] >= 1


def test_stream_rule_edit_clean_and_other_file_flagged(tmp_path, capsys):
    from rvtballet import segedit
    out = str(tmp_path / 'o.rvt'); segedit.apply_ops(S[0], out, [{'op': 'set_string', 'eid': 1365188, 'param': 'Mark', 'value': 'UB2'}], mode='fit')
    assert ub.main(S[0], out) == 0 and '_other_streams_changed' not in capsys.readouterr().out
    other = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*Snowdon*Structural.rvt')))
    if other:
        assert ub.main(S[0], other[0]) == 1 and '_other_streams_changed' in capsys.readouterr().out
