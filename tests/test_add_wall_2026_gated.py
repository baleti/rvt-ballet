"""2026 add-wall output was refused by Revit 2026 (sev1): the tool must refuse by default and write nothing."""
import os, subprocess, sys, pytest
SRC = '~/c2x-tmp/ip25/2026_56_Snowdon_Towers_Sample_Electrical.rvt'  # Autodesk sample
@pytest.mark.skipif(not os.path.exists(SRC), reason='sample not present')
def test_2026_add_wall_refused(tmp_path):
    out = tmp_path / 'o.rvt'
    env = {k: v for k, v in os.environ.items() if k != 'RVT_ADD26_EXPERIMENT'}
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_aw_auto.py'), SRC, str(out), '-250', '-100', '-240', '-88', '12', '2026'], capture_output=True, text=True, env=env, timeout=100)
    assert r.returncode != 0 and 'REFUSED' in (r.stderr + r.stdout) and not out.exists()
