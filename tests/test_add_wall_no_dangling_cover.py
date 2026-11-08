"""Regression: a wall added by the writer must not reference element ids that do not exist in the target project.
Found 2026-11-08: the rosetta wall template carried CoverType id 73984 (absent in the Snowdon sample); Revit 2026 refused the file (CArchiveException 105).
Uses an Autodesk sample copy; set RVT_AW_SRC / RVT_AW_YEAR to override. Skipped when the sample is absent."""
import os, subprocess, sys, tempfile, pytest
SRC = os.environ.get('RVT_AW_SRC', os.path.expanduser('~/c3x-rd/aw26b/orig.rvt')); YEAR = os.environ.get('RVT_AW_YEAR', '2026')
TOOLS = os.path.join(os.path.dirname(__file__), '..', 'tools')
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research', TOOLS): sys.path.insert(0, os.path.expanduser(p))

@pytest.mark.skipif(not os.path.exists(SRC), reason='sample absent')
def test_new_wall_param_element_ids_exist():
    import wledit, recwalk, rvt_diff as R
    with tempfile.TemporaryDirectory() as d:
        dst = os.path.join(d, 'out.rvt')
        subprocess.run([sys.executable, os.path.join(TOOLS, 'rvt_aw_auto.py'), SRC, dst, '-260', '-100', '-250', '-100', '10', YEAR], check=True, timeout=1500)
        wa, _ = recwalk.walk(SRC); wb, _ = recwalk.walk(dst)
        new = sorted(set(wb) - set(wa)); new = [i for i in new if i < (1 << 48)]
        assert len(new) == 1
        fl = R.field_log(wledit.Editor(dst).m, new[0])[2]
        refs = [v for k, v, s, e in fl if k.startswith('ParamValueElementId.m_value')]
        assert refs, 'no element-id parameters decoded'
        NONE = 0xFFFFFFFFFFFFFFFF
        for v in refs:
            i = int(str(v).split('(')[1].rstrip(')')) if 'EID(' in str(v) else int(v)
            assert i == NONE or i in wb, 'dangling element id %d in new wall' % i
        d2 = {k: v for k, v, s, e in fl}
        assert d2['VWall.m_wallKeyRef#1'] == '2' and float(d2['VWall.m_keyRefOffset#1']) > 0, 'Location Line key ref must be (2, +half thickness) like Revit-made unflipped walls'
