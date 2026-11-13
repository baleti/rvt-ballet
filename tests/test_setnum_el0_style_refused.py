"""set_num Int on Italic/Bold/Underline of element 0 is refused (Revit ignores the stored integer there). Fails without the guard, passes with it."""
import pytest
from rvtballet import edit

@pytest.mark.parametrize('p', ['Italic', 'Bold', 'Underline'])
def test_refused(p, monkeypatch):
    monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    with pytest.raises(edit.EditError, match='document-level style holder'): edit.validate_op({'op': 'set_num', 'eid': 0, 'param': p, 'value': 1, 'kind': 'Int'})

def test_other_element_not_blocked(monkeypatch):
    monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    try: edit.validate_op({'op': 'set_num', 'eid': 5, 'param': 'Italic', 'value': 1, 'kind': 'Int'})
    except edit.EditError as e: assert 'document-level style holder' not in str(e)
