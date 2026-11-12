"""c4x-rvtmatrix item 81: deleting an element that still hosts an IndependentTag must be refused (Snowdon Structural 2025 sample, column 606331 hosts tag 869338).
Skipped when the local Autodesk sample corpus is absent."""
import os, sys, pytest
SRC = '/srv/tank/remote-host-archive/2026-11-01/rvtfix/corpus/2025/49_Snowdon_Towers_Sample_Structural.rvt'
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='local Autodesk sample missing')
for p in ('~/rvt-research', '~/rvt-research/edit-lab', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_tagged_column_delete_refused():
    os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
    import rvtedit
    from rvtballet import edit
    ed = rvtedit.Edit(SRC)
    assert edit.tags_hosting(ed, 606331) == [869338]
    with pytest.raises(edit.EditError, match='host of 1 tag'):
        edit._delete(ed, 606331)
