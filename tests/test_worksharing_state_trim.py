"""worksharing_state returns 'Central', not 'CentralUsername:', when the next field follows without a line break; never turns a workshared value into 'Not enabled'."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
class _S:
    def __init__(s, d): s.data = d
def _state(text, monkeypatch):
    import types
    cfb = types.ModuleType('cfb'); cfb.CFB = lambda b: types.SimpleNamespace(streams=lambda: {'BasicFileInfo': _S(text.encode('utf-16le'))})
    monkeypatch.setitem(sys.modules, 'cfb', cfb); return save.worksharing_state(b'x')
def test_trim(monkeypatch):
    assert _state('Worksharing: CentralUsername: bob\r\n', monkeypatch) == 'Central'
    assert _state('Worksharing: Not enabled\r\nX', monkeypatch) == 'Not enabled'
    assert _state('Worksharing: Local\x00junk', monkeypatch) == 'Local'
    assert _state('Worksharing: Central\r\n', monkeypatch) == 'Central'
