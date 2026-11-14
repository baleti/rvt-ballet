"""c5x-rvtlink: set_link_load (opt-in RVTBALLET_ENABLE_LINKLOAD=1). Autodesk 2026 Snowdon Structural sample: unload the Electrical link type 805013
= exactly the bytes of the Revit 2026 VM-verified output (unl26e: Electrical Loaded->Unloaded, other links unchanged, no repair); reload restores the source bytes;
2020 file, multi-partition link type, non-link element and non-bool value are refused. Needs the local sample files (skips otherwise)."""
import os, sys, pytest
A = os.path.expanduser('~/c2x-tmp/ip25/2026_55_Snowdon_Towers_Sample_Structural.rvt'); V = os.path.expanduser('~/c5x-link/w/unl26e_unload.rvt')
B = os.path.expanduser('~/rvt-samples/2020_1_HYPERLOOP_MASTER.rvt')
pytestmark = pytest.mark.skipif(not all(os.path.exists(x) for x in (A, V, B)), reason='needs local samples')

def test_link_load(monkeypatch):
    monkeypatch.setenv('RVTBALLET_ENABLE_LINKLOAD', '1'); monkeypatch.setenv('RVTBALLET_EDIT_BACKEND', 'rvtedit')
    from rvtballet import edit
    buf = open(A, 'rb').read()
    with pytest.raises(edit.EditError): edit.validate_op({'op': 'set_link_load', 'eid': 805013, 'value': 'no'})
    out = edit.apply(buf, [{'op': 'set_link_load', 'eid': 805013, 'value': False}])
    assert out == open(V, 'rb').read(), 'differs from the Revit-verified unload output'
    back = edit.apply(out, [{'op': 'set_link_load', 'eid': 805013, 'value': True}])      # not byte-equal to the source (the second save re-lays the file), so compare every element
    sys.path[:0] = [os.path.expanduser(x) for x in ('~/rvt-research', '~/src/savegate')]
    from savegate import rvt_elements as R
    assert R.elements(back) == R.elements(buf), 'reload does not restore every element'
    with pytest.raises(edit.EditError): edit.apply(buf, [{'op': 'set_link_load', 'eid': 1, 'value': False}])
    with pytest.raises(edit.EditError): edit.apply(open(B, 'rb').read(), [{'op': 'set_link_load', 'eid': 1, 'value': False}])
