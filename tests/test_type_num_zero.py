import pytest
from rvtballet import edit


def test_zero_type_num_refused(monkeypatch):
    monkeypatch.setenv('RVTBALLET_ENABLE_TYPEPARAM', '1')
    monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    for z in (0, 0.0, -0.0):
        with pytest.raises(edit.EditError, match='zero'):
            edit.validate_op({'op': 'set_type_num', 'eid': 5, 'param': 'Width', 'value': z})
    assert edit.validate_op({'op': 'set_type_num', 'eid': 5, 'param': 'Width', 'value': 0.2})['value'] == 0.2
