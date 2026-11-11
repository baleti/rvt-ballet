import subprocess, sys, os
def test_doctor_runs_readonly_and_reports():
    r = subprocess.run([sys.executable, "-m", "rvtballet", "doctor"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), env={**os.environ, "RVT_DEMO_STATE": "/nonexistent", "RVT_SAMPLES": "/nonexistent"})
    assert r.returncode in (0, 1), r.stderr
    assert "SAVE! policy" in r.stdout and "n/a" in r.stdout and "savegate" in r.stdout
