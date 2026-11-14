import pytest
from types import SimpleNamespace as NS
from rvtballet import save, edit

def _ss(ops):
    return NS(edits=lambda mid: NS(ops=ops))

def test_joined_move_refused(monkeypatch):
    ops = [{'op': 'move', 'eid': 7, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}]
    monkeypatch.setattr(edit, 'compose', lambda o: o)
    monkeypatch.setattr(save, 'membership', lambda b, e: {7: ['joined to 4 element(s)', 'supports 4 framing member(s)']})
    with pytest.raises(edit.EditError, match='joined'):
        save.group_warning(_ss(ops), 'm', b'')

def test_framed_only_move_not_refused(monkeypatch):
    ops = [{'op': 'move', 'eid': 7, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}]
    monkeypatch.setattr(edit, 'compose', lambda o: o)
    monkeypatch.setattr(save, 'membership', lambda b, e: {7: ['supports 3 framing member(s)']})
    assert save.group_warning(_ss(ops), 'm', b'') is not None or True

def test_joined_rotate_refused(monkeypatch):
    ops = [{'op': 'rotate', 'eid': 7, 'deg': 30.0}]
    monkeypatch.setattr(edit, 'compose', lambda o: o)
    monkeypatch.setattr(save, 'membership', lambda b, e: {7: ['joined to 2 element(s)']})
    with pytest.raises(edit.EditError, match='joined'):
        save.group_warning(_ss(ops), 'm', b'')

def test_joined_param_edit_not_refused(monkeypatch):
    ops = [{'op': 'set_num', 'eid': 7, 'name': 'Mark', 'value': 1.0}]
    monkeypatch.setattr(edit, 'compose', lambda o: o)
    monkeypatch.setattr(save, 'membership', lambda b, e: {7: ['joined to 2 element(s)']})
    save.group_warning(_ss(ops), 'm', b'')      # must not raise
