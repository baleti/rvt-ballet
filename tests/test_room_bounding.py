"""c5x-rvttype 2026-11-13: set_room_bounding flips HostObj.m_roomBounding (one byte), as the Revit-made paired experiment on the
import sys, os
for _l in ("~/rvt-research", "~/rvt-research/write-lab", "~/rvt-research/edit-lab"): sys.path.insert(0, os.path.expanduser(_l))
Autodesk Structural 2024 sample wall 585072 (01 -> 00). Opt-in until a Revit open verdict exists."""
import os, sys, hashlib, tempfile
import pytest
SRC = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk Structural 2024 sample not present')
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit

def test_disabled_by_default():
    os.environ.pop('RVTBALLET_ENABLE_ROOMBOUND', None)
    with pytest.raises(edit.EditError, match='disabled'): edit.validate_op({'op': 'set_room_bounding', 'eid': 585072, 'value': False})

def test_flip_one_byte_and_refusals(monkeypatch):
    monkeypatch.setenv('RVTBALLET_ENABLE_ROOMBOUND', '1')
    buf = open(SRC, 'rb').read(); h = hashlib.sha256(buf).hexdigest()
    with pytest.raises(edit.EditError, match='not a bool|true or false'): edit.validate_op({'op': 'set_room_bounding', 'eid': 585072, 'value': 0})
    op = edit.validate_op({'op': 'set_room_bounding', 'eid': 585072, 'value': False})
    out = edit.apply_full(buf, [op])[0]
    assert out != buf and hashlib.sha256(buf).hexdigest() == h
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'o.rvt'); open(p, 'wb').write(out)
        for rd in (SRC, p):
            ed = __import__('rvtedit').Edit(rd); log = ed.g.e.trace(585072)[3]
            f = [l for l in log if l[1] == 'HostObj.m_roomBounding'][0]
            assert edit._body(ed, 585072)[f[2]] == (1 if rd == SRC else 0)
    with pytest.raises(edit.EditError, match='already'): edit.apply_full(out, [op])
    with pytest.raises(edit.EditError, match='no single-byte'): edit.apply_full(buf, [edit.validate_op({'op': 'set_room_bounding', 'eid': 2888, 'value': False})])
