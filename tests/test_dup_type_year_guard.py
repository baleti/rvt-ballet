"""duplicate-type generator refuses non-2024-non-2026 Autodesk samples with the explicit year message and writes nothing (skips if samples absent)."""
import os, subprocess, sys, tempfile, glob
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "rvt_dup_type_gen.py")
d = tempfile.mkdtemp(); n = 0
for y in (2023, 2025):
    fs = sorted(glob.glob(os.path.expanduser("~/rvt-research/corpus/%d/*.rvt" % y)))
    if not fs: continue
    out = "%s/o%d.rvt" % (d, y)
    r = subprocess.run([sys.executable, T, fs[0], out, "1", "YrGuard"], capture_output=True, text=True)
    assert r.returncode != 0 and not os.path.exists(out) and "only built for Revit 2024" in (r.stdout + r.stderr), (y, r.stderr[-200:])
    n += 1
print("ok: %d non-2024 samples refused by the year guard, nothing written" % n if n else "skip: no samples")
