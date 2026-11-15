"""SLOW, remote-host only: measures how the offline Revit VM writes a .rvt (SaveAs new, SaveAs overwrite, Save) with tools/rvt_save_pattern_vm.py, which takes a lane
through the normal FIFO lock (can wait hours). Enable with RVT_VM_LANE=1 and RVT_SAVEPAT_SAMPLE=<Autodesk sample .rvt>.
Asserts the run produced a classified timeline (so docs/stable-read.md can state the observed pattern) and appends nothing with client data.
The torn-read guarantees themselves are tested synthetically in tests/test_stable_read.py for every pattern the classifier can name."""
import os, subprocess, sys, pytest
pytestmark = pytest.mark.skipif(os.environ.get('RVT_VM_LANE') != '1' or not os.environ.get('RVT_SAVEPAT_SAMPLE'),
                                reason='needs an offline Revit VM lane (remote-host): RVT_VM_LANE=1 RVT_SAVEPAT_SAMPLE=file.rvt')
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
KNOWN = ('in-place-overwrite-in-steps', 'in-place-single-step', 'truncate-then-rewrite', 'replace-by-rename', 'delete-and-recreate')


def test_revit_write_pattern_is_classified():
    tsv = os.path.expanduser('~/demo-state/rvt-save-pattern.tsv'); n0 = len(open(tsv).readlines()) if os.path.exists(tsv) else 0
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'rvt_save_pattern_vm.py'), os.environ.get('RVT_SAVEPAT_YEAR', '2024'), os.environ['RVT_SAVEPAT_SAMPLE']],
                       capture_output=True, text=True, timeout=6 * 3600)
    rows = open(tsv).readlines()[n0:]
    assert r.returncode == 0 and rows, r.stdout[-500:] + r.stderr[-500:]
    assert any(k in rows[-1] for k in KNOWN), rows[-1]
