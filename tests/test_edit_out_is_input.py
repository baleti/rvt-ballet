import os, subprocess, sys, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _run(*a):
    return subprocess.run([sys.executable, "-m", "rvtballet", "edit", *a], capture_output=True, text=True, cwd=ROOT, timeout=120)
def test_out_equals_input_refused_for_path_symlink_hardlink(tmp_path):
    src = tmp_path / "a.rvt"; src.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"\0" * 4096)
    h = hashlib.sha256(src.read_bytes()).hexdigest()
    sym = tmp_path / "sym.rvt"; os.symlink(src, sym)
    hard = tmp_path / "hard.rvt"; os.link(src, hard)
    for out in (src, sym, hard):
        r = _run(str(src), "--set-string", "1", "Mark", "X", "-o", str(out), "--overwrite-output")
        assert r.returncode == 2 and "OUT is the input file" in r.stderr, r.stderr
        assert hashlib.sha256(src.read_bytes()).hexdigest() == h
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.rvt", "hard.rvt", "sym.rvt"]
