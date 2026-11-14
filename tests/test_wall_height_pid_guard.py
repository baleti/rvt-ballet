"""c3x-rvtmatrix: Unconnected Height by name hits pid -1001105, which Revit ignores when the wall also stores -1001101 (VM judge FAIL readback, 2024 Structural wall)."""
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet import edit


def _log(*pids): return [(0, 'ParamValueDouble.m_paramId', 0, 8, p) for p in pids]


def test_refused_when_both_ids_stored(monkeypatch):
    monkeypatch.setattr(edit, '_eid_val', lambda v: v)
    with pytest.raises(edit.EditError):
        edit._check_wall_height_pid({'eid': 5, 'kind': 'Double'}, -1001105, _log(-1001105, -1001101))


def test_allowed_otherwise(monkeypatch):
    monkeypatch.setattr(edit, '_eid_val', lambda v: v)
    edit._check_wall_height_pid({'eid': 5, 'kind': 'Double'}, -1001105, _log(-1001105))
    edit._check_wall_height_pid({'eid': 5, 'kind': 'Double'}, -1001101, _log(-1001105, -1001101))
