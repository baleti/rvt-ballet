"""SEV-1 candidate (c8x-rvtjudge5 2026-11-18, item 148): a by-name Int set_num on a view ('Detail Level' on view 356 of the public Autodesk Construction-DefaultMetric 2024 .rte) must change ONLY that element. Today the stored value also changes on 359 and 360 (and for 362 on 365, 366); the Revit VM judge1 fails it ('1 untouched element differs') while the gate accepts it. xfail(strict) until the writer touches exactly the declared element (or refuses): remove the xfail when fixed. Needs RVT_PUBLIC_2024_RTE (path of the public .rte), else skipped."""
import os, shutil, sys, pytest
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("RVT_PUBLIC_2024_RTE", os.path.expanduser("~/c3x-tmp-port4/c2024.rte"))
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason="public 2024 .rte not available")

@pytest.mark.xfail(strict=True, reason="writer changes Detail Level on sibling elements 359, 360 too (NEEDS-FROM-SAVEGATE.md 2026-11-18)")
def test_int_by_name_edit_touches_only_the_declared_element(tmp_path, monkeypatch):
    sys.path.insert(0, H); sys.path.insert(0, os.path.expanduser("~/rvt-research"))
    for k, v in (("SAVEGATE_GATE", str(tmp_path / "g.json")), ("SAVEGATE_JOURNAL", str(tmp_path / "j")), ("SAVEGATE_CACHE", str(tmp_path / "c")), ("RVTBALLET_ALLOW_OVERWRITE", "1"), ("RVTBALLET_EDIT_BACKEND", "rvtedit"), ("RVTBALLET_ALLOW_LAYOUT_CHANGE", "1")): monkeypatch.setenv(k, v)
    (tmp_path / "g.json").write_text('{"rvt": {"*": "open"}}')
    from rvtballet import save
    import rvt_params
    p = str(tmp_path / "c.rte"); shutil.copy(SRC, p); a = rvt_params.params(SRC)
    ss = save.SaveSessions(); save.add_edit(ss, "m", p, {"op": "set_num", "eid": 356, "param": "Detail Level", "value": 2, "kind": "Int"}); save.save_overwrite(ss, "m", p)
    b = rvt_params.params(p); dl = lambda r, e: ((r.get(e) or {}).get("params", r.get(e) or {})).get("Detail Level")
    assert dl(b, 356) == 2
    assert [e for e in a if dl(a, e) != dl(b, e)] == [356]
