"""rvt_vm_open.py must refuse years before 2020 immediately (no add-in exists for them; a lane start would only burn minutes and mark the lane degraded)."""
import os, subprocess, sys

TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_vm_open.py')


def test_refuses_pre_2020_without_touching_the_vm():
    for year in ('2017', '2018', '2019'):
        r = subprocess.run([sys.executable, '-I', TOOL, year, '/nonexistent.rvt'],
                           capture_output=True, text=True, timeout=30)
        assert r.returncode != 0
        assert 'refused' in (r.stdout + r.stderr)
        assert str(year) in (r.stdout + r.stderr)
