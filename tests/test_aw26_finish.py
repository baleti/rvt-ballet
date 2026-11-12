import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); TOOL = os.path.join(HERE, '..', 'tools', 'rvt_aw26_finish.py')
def test_refuses_output_equal_input(tmp_path):
    f = tmp_path / 'a.rvt'; f.write_bytes(b'x')
    r = subprocess.run([sys.executable, TOOL, str(f), str(f), str(f)], capture_output=True, text=True)
    assert r.returncode != 0 and 'REFUSED' in (r.stdout + r.stderr)
    assert f.read_bytes() == b'x'
def test_refuses_output_equal_edited(tmp_path):
    a = tmp_path / 'a.rvt'; b = tmp_path / 'b.rvt'; a.write_bytes(b'x'); b.write_bytes(b'y')
    r = subprocess.run([sys.executable, TOOL, str(a), str(b), str(b)], capture_output=True, text=True)
    assert r.returncode != 0 and 'REFUSED' in (r.stdout + r.stderr) and b.read_bytes() == b'y'
