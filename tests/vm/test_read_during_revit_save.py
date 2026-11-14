"""SLOW, remote-host only: a Linux-side reader polls a .rvt while the offline Revit VM saves it (Save / SaveAs / repeated). NOT YET RUN: needs a free VM lane
(remote-host load was 60+ on 2026-11-14, lane gate refuses). Enable with RVT_VM_LANE=1. When run, it must record stat timeline rows (size, mtime_ns, inode)
and assert the stable guard never yields a differing answer."""
import os, pytest
pytestmark = pytest.mark.skipif(os.environ.get('RVT_VM_LANE') != '1', reason='needs an offline Revit VM lane (remote-host); set RVT_VM_LANE=1')


def test_placeholder_needs_lane():
    pytest.skip('write after the first lane run: the observed Revit write pattern is not measured yet (see docs/stable-read.md)')
