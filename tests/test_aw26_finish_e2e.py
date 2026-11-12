"""End to end (local Revit-made 2026 Structural pair only; skipped elsewhere): rvt_aw_auto with RVT_ADD26_FINISH=1 on a Revit-SAVED 2026 base must give an output with
no partition member above the Revit cap (the 238 KB member that made Revit 2026 say 'needs to be repaired'), the finish step must report the stamps, and without the finish
step the output must be refused by the member-cap check (fails without the fix)."""
import os, subprocess, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, '..', 'tools')
BASE = os.path.expanduser('~/c2x-diff/c4xaw26/base.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(BASE), reason='local Revit-saved 2026 Structural sample absent')
def _run(tmp_path, finish):
    out = str(tmp_path / ('f.rvt' if finish else 'n.rvt'))
    env = dict(os.environ, RVTGEN_INPLACE='1', RVT_ADD26_EXPERIMENT='1')
    if finish: env['RVT_ADD26_FINISH'] = '1'
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'rvt_aw_auto.py'), BASE, out, '-250', '-100', '-240', '-88', '12', '2026'], capture_output=True, text=True, env=env, timeout=1500)
    return r, out
def test_finish_removes_oversize_member(tmp_path):
    sys.path.insert(0, TOOLS); import rvt_member_cap as mc
    r, out = _run(tmp_path, True)
    assert r.returncode == 0, r.stdout[-400:] + r.stderr[-400:]
    assert 'stamps=12' in r.stdout and 'cuts=[327]' in r.stdout
    assert not mc.oversized(mc.member_sizes(out))
def test_without_finish_oversize_is_refused(tmp_path):
    r, out = _run(tmp_path, False)
    assert r.returncode != 0 and 'member' in (r.stdout + r.stderr).lower() and not os.path.exists(out)
