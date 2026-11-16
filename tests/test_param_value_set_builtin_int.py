"""c1x-rvttype: rvt_param_value_set.py with a built-in pid creates the Int set exactly as Revit did in pair c1xyn8 (Structural 2024, link type 576455, Export Type to IFC 0 -> 1): the whole element record is byte-equal. Skips when the local pair is absent."""
import os, subprocess, sys, pytest
B = os.path.expanduser('~/c2x-diff/c1xyn8/base.rvt'); A = os.path.expanduser('~/c2x-diff/c1xyn8/after.rvt')
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_builtin_pid_int_create_equals_revit(tmp_path):
    if not (os.path.exists(B) and os.path.exists(A)): pytest.skip('pair absent')
    out = str(tmp_path / 'o.rvt')
    r = subprocess.run([sys.executable, os.path.join(H, 'tools/rvt_param_value_set.py'), B, out, '576455', 'pid:-1019013', '1', 'yesno'], capture_output=True, text=True, timeout=1500)
    assert 'wrote' in r.stdout, r.stdout + r.stderr
    chk = "import os,sys\nsys.path[:0]=[os.path.expanduser(p) for p in ('~/rvt-research/edit-lab','~/rvt-research/write-lab','~/rvt-research')]\nos.environ['RVT_GEOM']='1'\nimport rvtedit\ndef rec(f):\n    ed=rvtedit.Edit(f);pn,i,r,log,q=ed.g.e.trace(576455);return bytes(ed.g.bj[i:q])\nprint(rec(sys.argv[1])==rec(sys.argv[2]))"
    r2 = subprocess.run([sys.executable, '-c', chk, out, A], capture_output=True, text=True, timeout=1500)
    assert r2.stdout.strip() == 'True', r2.stdout + r2.stderr


def test_builtin_pid_refuses_double(tmp_path):
    if not os.path.exists(B): pytest.skip('pair absent')
    r = subprocess.run([sys.executable, os.path.join(H, 'tools/rvt_param_value_set.py'), B, str(tmp_path / 'o.rvt'), '576455', 'pid:-1019013', '1.5', 'double'], capture_output=True, text=True, timeout=600)
    assert 'REFUSED' in r.stdout + r.stderr and not (tmp_path / 'o.rvt').exists()
