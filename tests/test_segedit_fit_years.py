"""Regression (c4x-rvteditopus 2026-11-15): segedit FIT outputs of the Autodesk 2020 rme_basic sample (Mark / move / rotate) pass segedit verify and vcheck
but Revit 2020 fails to OPEN them (InternalException in the offline VM; c9x 2021-2023 fit outputs the same), while the SHIFT layout of the same edit opens.
fit must be refused for years without a Revit-verified fit verdict, and auto must fall back to shift."""
import os, glob, pytest
from rvtballet import segedit
S = sorted(glob.glob(os.path.expanduser("~/rvt-research/corpus/2020/*rme_basic*.rvt")))
pytestmark = pytest.mark.skipif(not S, reason="Autodesk 2020 sample not present")

def test_fit_refused_2020(tmp_path):
    out = tmp_path / "f.rvt"
    with pytest.raises(segedit.Refused, match="fit layout refused"):
        segedit.apply_ops(S[0], str(out), [{"op": "set_string", "eid": 521634, "param": "Mark", "value": "C4X"}], mode="fit")
    assert not out.exists()

def test_auto_is_shift_2020(tmp_path):
    out = tmp_path / "a.rvt"
    info = segedit.apply_ops(S[0], str(out), [{"op": "set_string", "eid": 521634, "param": "Mark", "value": "C4X"}], mode="auto")
    assert info["mode"] == "shift" and "not allowed" in info.get("fallback", "")
