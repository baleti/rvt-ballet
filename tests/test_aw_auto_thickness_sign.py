"""rvt_aw_auto must pass the like-wall type thickness to the writer even when the like wall stores a NEGATIVE VWall.m_keyRefOffset
(Snowdon Structural 2024, Concrete 10": -0.41667). Before the fix the thickness was dropped and the added wall kept the 0.328 ft (200 mm) template
face offset, which Revit regenerated on the first edit (c1x-rvtdiff 2026-11-15, paired diff wmv4). Autodesk sample, read-only; skipped if absent."""
import os, re, subprocess, sys, tempfile, pytest
SRC = os.path.expanduser('~/c3x-rd/wb/orig.rvt')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.mark.skipif(not os.path.exists(SRC), reason='Snowdon Structural 2024 sample not present')
def test_thickness_reaches_op_for_negative_key_ref_offset():
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'tools', 'rvt_aw_auto.py'), SRC, os.path.join(d, 'o.rvt'), '-250', '-100', '-240', '-88', '12', '2024'],
                           capture_output=True, text=True, timeout=900, env=dict(os.environ, PYTHONPATH=''))
    m = re.search(r'^OP (aw:\S+)$', r.stdout, re.M)
    assert m, r.stdout + r.stderr
    parts = m.group(1).split(':')
    assert len(parts) == 12, 'thickness field missing: %s' % m.group(1)
    assert abs(float(parts[-1]) - 0.8333333333333333) < 1e-6
