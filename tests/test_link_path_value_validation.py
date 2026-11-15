"""set_link_path value validation (no file needed): NUL, lone surrogate, non-BMP, blank, control char, >4096 chars are refused; a BMP unicode path is accepted."""
import pytest

def _v(monkeypatch, value):
    monkeypatch.setenv('RVTBALLET_ENABLE_LINKPATH', '1'); monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    from rvtballet import edit
    return edit, edit.validate_op({'op': 'set_link_path', 'eid': 1, 'value': value})

@pytest.mark.parametrize('bad', ['a\0b', 'a\ud800b', 'C:\\x\U0001F600.rvt', '  ', 'a\tb', 'x' * 5000])
def test_refused(monkeypatch, bad):
    from rvtballet import edit
    with pytest.raises(edit.EditError): _v(monkeypatch, bad)

def test_bmp_unicode_accepted(monkeypatch):
    assert _v(monkeypatch, 'C:\\ok\\\u00e9.rvt')[1]['value'] == 'C:\\ok\\\u00e9.rvt'
