import os, pytest
from rvtballet import edit


def test_negative_type_num_refused(monkeypatch):
    monkeypatch.setenv('RVTBALLET_ENABLE_TYPEPARAM', '1')
    monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    with pytest.raises(edit.EditError, match='negative'):
        edit.validate_op({'op': 'set_type_num', 'eid': 5, 'param': 'Width', 'value': -5})
    assert edit.validate_op({'op': 'set_type_num', 'eid': 5, 'param': 'Width', 'value': 5})['value'] == 5.0
