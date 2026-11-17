"""offline tests of tools/rvt_judge1.py verdict logic on synthetic guest output (no VM, no files)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import rvt_judge1 as J

def txt(eh, extra="", cmp="0 only_resaved=0", ok=True, rb=""):
    t = "T_OPEN 10\nBBOXNULL 0\nCOUNT %d\nCOMPARE only_original=%s\n%s%s\n" % (len(eh), cmp, extra, "RESULT ok" if ok else "RESULT fail phase=open InternalException: boom")
    return t + "".join("EH %d %s\n" % kv for kv in eh.items()) + rb

BASE = {1: "aaaaaaaa", 2: "bbbbbbbb", 3: "cccccccc"}
RB0 = "TF 2 X=1.0000,0.0000,0.0000 Y=0.0000,1.0000,0.0000 Z=0.0000,0.0000,1.0000 mirrored=False hand=False facing=0,1,0\nRB 2 loc=1.000000 2.000000 3.000000 rotdeg=0.0000 group=-1 mark=-\n"
RB1 = RB0.replace("RB 2 loc=1.000000", "RB 2 loc=3.000000")
MOVE = [{"kind": "move", "eid": 2, "d": [2, 0, 0]}]

def v(c, o, exp=MOVE, allowed={2}): return J.verdict(J.parse(c), J.parse(o), exp, allowed, lambda s: None)[0]

def test_pass():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, rb=RB1)) == 0
def test_untouched_differs():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd", 3: "eeeeeeee"}, rb=RB1)) == 1
def test_silent_loss():      # an element missing behind a clean open (the successor/A-link failure class) must FAIL
    o = {**BASE, 2: "dddddddd"}; del o[3]
    assert v(txt(BASE, rb=RB0), txt(o, rb=RB1)) == 1
def test_new_element_undeclared():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd", 9: "99999999"}, rb=RB1)) == 1
def test_open_fail():
    assert v(txt(BASE, rb=RB0), txt({}, ok=False)) == 1
def test_cmp_nonzero():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, cmp="1 only_resaved=0", rb=RB1)) == 1
def test_new_dialog():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, extra="DIALOG TaskDialog_Some_Warning\n", rb=RB1)) == 1
def test_dialog_also_in_control_ok():
    d = "DIALOG TaskDialog_Sample\n"
    assert v(txt(BASE, extra=d, rb=RB0), txt({**BASE, 2: "dddddddd"}, extra=d, rb=RB1)) == 0
def test_new_error_failure():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, extra="FAILURE Error Element is corrupt\n", rb=RB1)) == 1
def test_warning_failure_ignored():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, extra="FAILURE Warning Highlighted walls overlap\n", rb=RB1)) == 0
def test_wrong_shift():
    assert v(txt(BASE, rb=RB0), txt({**BASE, 2: "dddddddd"}, rb=RB0)) == 1
def test_control_bad_is_no_verdict():
    assert v(txt(BASE, ok=False), txt(BASE, rb=RB1)) == 2
def test_param_string():
    exp = [{"kind": "param", "eid": 2, "name": "Mark", "type": "String", "value": "AB"}]
    o = txt({**BASE, 2: "dddddddd"}, rb="RBP 2|Mark storage=String value=(string, see utf16) shown=- len=2 utf16=41,42\n")
    assert v(txt(BASE), o, exp) == 0
    assert v(txt(BASE), o.replace("41,42", "41,43"), exp) == 1
def test_bboxnull_relative():
    c = txt(BASE, rb=RB0).replace("BBOXNULL 0", "BBOXNULL 7"); o = txt({**BASE, 2: "dddddddd"}, rb=RB1)
    assert v(c, o.replace("BBOXNULL 0", "BBOXNULL 7")) == 0
    assert v(c, o.replace("BBOXNULL 0", "BBOXNULL 8")) == 1
def test_volatile_ignored():
    c = txt(BASE, rb=RB0) + "VOLATILE 3\n"; o = txt({**BASE, 2: "dddddddd", 3: "eeeeeeee"}, rb=RB1)
    assert v(c, o) == 0
    assert v(txt(BASE, rb=RB0), o) == 1

def test_add_present_passes():      # ADD: allowed id 9 absent from the control must appear in the output
    assert v(txt(BASE), txt({**BASE, 9: "99999999"}), exp=[], allowed={9}) == 0
def test_add_silently_dropped_fails():
    assert v(txt(BASE), txt(BASE), exp=[], allowed={9}) == 1
def test_add_extra_new_element_fails():
    assert v(txt(BASE), txt({**BASE, 9: "99999999", 8: "88888888"}), exp=[], allowed={9}) == 1

def test_add_generated_block_shift_passes():      # clone takes the id of the first load-time generated element; the generated block (one shared hash) shifts up by one
    G = "aaaaaaaa"; c = {**BASE, 10: G, 11: G, 12: G}
    assert v(txt(c), txt({**BASE, 10: "77777777", 11: G, 12: G, 13: G}), exp=[], allowed={10}) == 0
def test_add_shift_with_real_extra_fails():
    G = "aaaaaaaa"; c = {**BASE, 10: G, 11: G, 12: G}
    assert v(txt(c), txt({**BASE, 10: "77777777", 11: G, 12: G, 13: G, 14: "55555555"}), exp=[], allowed={10}) == 1


def test_twin_string_supported_and_refused():
    import rvt_judge1 as j
    assert j.twin_string([{"kind": "move", "eid": 7, "d": [2, 0, 0]}]) == "move|7|2.0|0.0|0.0"
    assert j.twin_string([{"kind": "rotate", "eid": 7, "deg": 90}]) == "rotate|7|90.0"
    assert j.twin_string([{"kind": "param", "eid": 7, "name": "Mark", "type": "String", "value": "A|B"}]) == ""
    assert j.twin_string([{"kind": "absent", "eid": 7}]) == ""


def test_watchdog_limit_bounded_and_overridable(monkeypatch):
    import importlib.util, os
    spec = importlib.util.spec_from_file_location("j1", os.path.join(os.path.dirname(__file__), "..", "tools", "rvt_judge1.py"))
    j = importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
    monkeypatch.delenv("RVT_JUDGE1_MAX_SEC", raising=False)
    assert j.watchdog_limit(2, 2) == 2700 and j.watchdog_limit(2, 2) > 773
    monkeypatch.setenv("RVT_JUDGE1_MAX_SEC", "5")
    assert j.watchdog_limit(9, 9) == 5


def test_sha_helper_resolves_on_net_framework():
    # Revit 2020-2024 run .NET Framework: SHA256 is in mscorlib, so the assembly-qualified Type.GetType returns null there (b19 2024: NullReferenceException on strings > 200 chars)
    import os
    cs = open(os.path.join(os.path.dirname(__file__), "..", "tools", "rvt_judge1.cs")).read()
    assert "?? Type.GetType(\"System.Security.Cryptography.SHA256\")" in cs


def test_twin_string_supports_delete_and_absent():
    import importlib.util, os
    spec = importlib.util.spec_from_file_location("j1b", os.path.join(os.path.dirname(__file__), "..", "tools", "rvt_judge1.py"))
    j = importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
    assert j.twin_string([{"kind": "absent", "eid": 5}]) == "delete|5"
    assert j.twin_string([{"kind": "delete", "eid": 7}, {"kind": "move", "eid": 1, "d": [1, 0, 0]}]).split(chr(30))[0] == "delete|7"
    assert j.twin_string([{"kind": "unknown", "eid": 1}]) == ""
