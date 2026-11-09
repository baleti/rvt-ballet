"""2026 add-wall output was refused by Revit 2026 (sev1): the tool must refuse by default and write nothing."""
import os, subprocess, sys, pytest
SRC = '~/c2x-tmp/ip25/2026_56_Snowdon_Towers_Sample_Electrical.rvt'  # Autodesk sample
@pytest.mark.skipif(not os.path.exists(SRC), reason='sample not present')
def test_2026_add_wall_refused(tmp_path):
    out = tmp_path / 'o.rvt'
    env = {k: v for k, v in os.environ.items() if k != 'RVT_ADD26_EXPERIMENT'}
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_aw_auto.py'), SRC, str(out), '-250', '-100', '-240', '-88', '12', '2026'], capture_output=True, text=True, env=env, timeout=100)
    assert r.returncode != 0 and 'REFUSED' in (r.stderr + r.stdout) and not out.exists()

@pytest.mark.skipif(not os.path.exists(SRC), reason='sample not present')
def test_2026_add_wall_saved_flag_still_refuses_original(tmp_path):
    """RVT_ADD26_SAVED=1 must not let an ORIGINAL (4 partitions) 2026 file through."""
    out = tmp_path / 'o.rvt'
    env = {k: v for k, v in os.environ.items() if k != 'RVT_ADD26_EXPERIMENT'}; env['RVT_ADD26_SAVED'] = '1'
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_aw_auto.py'), SRC, str(out), '-250', '-100', '-240', '-88', '12', '2026'], capture_output=True, text=True, env=env, timeout=100)
    assert r.returncode != 0 and 'Revit-saved' in (r.stderr + r.stdout) and not out.exists()

SAVED = '~/c5x-link/w/pe2026.rvt'   # Revit-saved 2026 Structural (Autodesk sample, one partition stream)
@pytest.mark.skipif(not os.path.exists(SAVED), reason='saved 2026 base not present')
def test_2026_add_wall_saved_flag_accepts_revit_saved_base(tmp_path):
    """Positive path: RVT_ADD26_SAVED=1 on a 1-partition Revit-saved base writes a file with the in-place layout (full first member)."""
    out = tmp_path / 'o.rvt'
    env = {k: v for k, v in os.environ.items() if k not in ('RVT_ADD26_EXPERIMENT', 'RVTGEN_INPLACE')}; env['RVT_ADD26_SAVED'] = '1'
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_aw_auto.py'), SAVED, str(out), '0', '0', '20', '0', '10', '2026'], capture_output=True, text=True, env=env, timeout=1500)
    assert r.returncode == 0 and out.exists(), (r.stdout + r.stderr)[-300:]
    for p in ('~/rvt-research/write-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
    import cfb, rvtw, wlpart
    c = cfb.CFB(out.read_bytes()); n = [k for k in c.streams() if k.startswith('Partitions/')]
    assert len(n) == 1
    assert len(wlpart.Partition(rvtw.Stream(c.streams()[n[0]].data)).mem[0]['raw']) > 100000
