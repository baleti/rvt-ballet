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
