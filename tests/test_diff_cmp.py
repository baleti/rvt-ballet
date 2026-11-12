import json, subprocess, sys, pathlib

def rep(fields, streams=("Partitions/1",), added=0):
    return {"streams_changed": [{"stream": s} for s in streams], "n_added": added, "n_removed": 0,
            "changed": [{"id": 7, "fields": [{"field": k, "new": v} for k, v in fields.items()]}]}

def run(tmp, a, w):
    pa, pw = tmp / "a.json", tmp / "w.json"
    pa.write_text(json.dumps(a)); pw.write_text(json.dumps(w))
    return subprocess.run([sys.executable, "tools/rvt_diff_cmp.py", str(pa), str(pw)], capture_output=True, text=True)

def test_equivalent_within_tolerance(tmp_path):
    r = run(tmp_path, rep({"x": 5.0}), rep({"x": 5.0 + 1e-12}))
    assert r.returncode == 0 and "EQUIVALENT" in r.stdout

def test_value_and_field_divergence_detected(tmp_path):
    r = run(tmp_path, rep({"x": 1.0, "y": 2}), rep({"x": 2.0, "z": 3}))
    assert r.returncode == 1
    assert "API 1.0 vs writer 2.0" in r.stdout and "only API changes" in r.stdout and "only writer changes" in r.stdout

def test_added_count_mismatch(tmp_path):
    r = run(tmp_path, rep({"x": 1}, added=3), rep({"x": 1}))
    assert r.returncode == 1 and "added: API 3 vs writer 0" in r.stdout
