"""A move/rotate of an element connected to many MEP elements is refused (Revit 2025 hang, measured); few connections and non-move ops stay allowed."""
import pytest
from types import SimpleNamespace
from rvtballet import save, edit


def _run(monkeypatch, n, op):
    monkeypatch.setattr(save, 'membership', lambda buf, eids: {7: ['connected to %d MEP element(s)' % n]})
    ss = SimpleNamespace(edits=lambda mid: SimpleNamespace(ops=[]))
    monkeypatch.setattr(edit, 'compose', lambda ops: [{'op': op, 'eid': 7}])
    return save.group_warning(ss, 'm', b'')


def test_many_connections_move_refused(monkeypatch):
    with pytest.raises(edit.EditError, match='connected to 23 MEP'):
        _run(monkeypatch, 23, 'move')


def test_many_connections_rotate_refused(monkeypatch):
    with pytest.raises(edit.EditError):
        _run(monkeypatch, 12, 'rotate')


def test_few_connections_still_warns_only(monkeypatch):
    assert 'connected to 3' in _run(monkeypatch, 3, 'move')


def test_param_edit_not_refused(monkeypatch):
    assert _run(monkeypatch, 23, 'set') is None
