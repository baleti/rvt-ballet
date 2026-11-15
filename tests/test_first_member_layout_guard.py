import pytest
from rvtballet import edit


def test_tiny_first_member_refused(monkeypatch):
    monkeypatch.setattr(edit, '_first_members', lambda b: {'Partitions/20': 130848} if b == b's' else {'Partitions/20': 241})
    with pytest.raises(edit.EditError):
        edit._check_first_member(b's', b'o')


def test_revit_saved_layout_passes(monkeypatch):
    monkeypatch.setattr(edit, '_first_members', lambda b: {'Partitions/20': 157})
    edit._check_first_member(b's', b'o')
