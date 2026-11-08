"""set_link_path to the link's own current path must be a byte-identical no-op, also for paths longer than the reader's 60-char display truncation
(bug: old = truncated string duplicated the tail of long paths inside ExternalResourceRef.m_displayPath). Needs a 2024 .rvt with a long link path:
RVT_LONGLINK_FILE=<file> RVT_LONGLINK_EID=<RvtLinkSymbol id> (Autodesk sample / synthetic only)."""
import os, struct, sys, pytest
F = os.environ.get('RVT_LONGLINK_FILE'); E = os.environ.get('RVT_LONGLINK_EID')
pytestmark = pytest.mark.skipif(not (F and E and os.path.exists(F)), reason='needs RVT_LONGLINK_FILE/EID')

def test_long_link_path_noop(monkeypatch):
    monkeypatch.setenv('RVTBALLET_ENABLE_LINKPATH', '1'); monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    from rvtballet import edit
    import rvtedit
    ed = rvtedit.Edit(F); l = [x for x in ed.g.e.trace(int(E))[3] if x[1] == 'ModelPath.m_path'][0]
    n = struct.unpack_from('<I', ed.g.bj, l[2])[0]; cur = bytes(ed.g.bj[l[2] + 4:l[2] + 4 + 2 * n]).decode('utf-16le')
    assert len(cur) > 60
    buf = open(F, 'rb').read()
    assert edit.apply(buf, [{'op': 'set_link_path', 'eid': int(E), 'value': cur}]) == buf
