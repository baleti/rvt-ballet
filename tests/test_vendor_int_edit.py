"""c5x-rvttype 2026-11-13: set_num kind Int on a vendor-original (non Revit-saved) Autodesk sample.
Detail Level (a ParamValueInt) is editable and the gate readback matches (Revit 2024 and 2026 VM: open clean, readback 3);
built-in yes/no fields (Room Bounding ...) are NOT ParamValueInt entries and must be refused, never silently written."""
import os, sys, hashlib
import pytest
SRC = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk Structural 2024 sample not present')
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit, save

def test_detail_level_int_edit_roundtrips_and_original_untouched():
    buf = open(SRC, 'rb').read(); h = hashlib.sha256(buf).hexdigest()
    op = edit.validate_op({'op': 'set_num', 'eid': 2888, 'param': 'Detail Level', 'value': 3, 'kind': 'Int'})
    out = edit.apply_full(buf, [op])[0]
    save._readback(buf, out, [op])
    assert out != buf and hashlib.sha256(buf).hexdigest() == h

def test_builtin_yesno_field_refused():
    buf = open(SRC, 'rb').read()
    op = edit.validate_op({'op': 'set_num', 'eid': 585072, 'param': 'Room Bounding', 'value': 0, 'kind': 'Int'})
    with pytest.raises(edit.EditError, match='0 candidate'):
        edit.apply_full(buf, [op])
