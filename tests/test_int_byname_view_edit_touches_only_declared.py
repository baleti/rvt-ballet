"""Documents the LEGITIMATE derived echo of a by-name Int edit on a view (c8x-rvtjudge5 2026-11-18): 'Detail Level' on view 356 of the public Autodesk Construction-DefaultMetric 2024 .rte changes the stored value on 356 (DBViewPlan) and on its own Viewer 359 and Viewport 360, nothing else. These are the view's derived records, accepted on purpose by the gate (tests/test_save_derived.py) and PASSED by the Revit VM with allowed ids 356,359. A first version of this test wrongly treated 359/360 as a gate hole (xfail); retracted. Needs RVT_PUBLIC_2024_RTE (or ~/c3x-tmp-port4/c2024.rte), else skipped."""
import os, shutil, sys, pytest
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("RVT_PUBLIC_2024_RTE", os.path.expanduser("~/c3x-tmp-port4/c2024.rte"))
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="public 2024 .rte not available")

def test_view_int_edit_changes_exactly_the_view_viewer_viewport(tmp_path, monkeypatch):
    sys.path.insert(0, H); sys.path.insert(0, os.path.expanduser("~/rvt-research"))
    for k, v in (("SAVEGATE_GATE", str(tmp_path / "g.json")), ("SAVEGATE_JOURNAL", str(tmp_path / "j")), ("SAVEGATE_CACHE", str(tmp_path / "c")), ("RVTBALLET_ALLOW_OVERWRITE", "1"), ("RVTBALLET_EDIT_BACKEND", "rvtedit"), ("RVTBALLET_ALLOW_LAYOUT_CHANGE", "1")): monkeypatch.setenv(k, v)
    (tmp_path / "g.json").write_text('{"rvt": {"*": "open"}}')
    from rvtballet import save
    import rvt_params
    p = str(tmp_path / "c.rte"); shutil.copy(SRC, p); a = rvt_params.params(SRC)
    ss = save.SaveSessions(); save.add_edit(ss, "m", p, {"op": "set_num", "eid": 356, "param": "Detail Level", "value": 2, "kind": "Int"}); save.save_overwrite(ss, "m", p)
    b = rvt_params.params(p); dl = lambda r, e: ((r.get(e) or {}).get("params", r.get(e) or {})).get("Detail Level")
    assert dl(b, 356) == 2
    assert sorted(e for e in a if dl(a, e) != dl(b, e)) == [356, 359, 360]
    assert [a[e].get("class") for e in (356, 359, 360)] == ["DBViewPlan", "Viewer", "Viewport"]
