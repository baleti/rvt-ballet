"""# RVT_TEST_TIMEOUT=3600. c1x-rvtdiff item 55: after an isolated-wall rotate (opt-in) the wall record must be internally consistent: GLine.m_origin/m_dirVec and the four Plane.m_origin / Plane.m_xVec all rotated by the same angle.
Autodesk sample Snowdon Facades 2024, wall 802667 (GLine origin lies 3 ft outside the outline box and its unit vectors carry 1e-15 noise): the old scan-only writer rotated the 4 plane origins and left GLine/xVec unchanged
while the gate said '0 unexpected differences'. Fails on that old behaviour. Set RVT_WALLROT_OUT=path to check an existing output instead of running the edit."""
import os, sys, math, subprocess, tempfile
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt'); EID = 802667; DEG = 90.0
if not os.path.exists(SRC): print('skip'); sys.exit(0)
import wledit
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools')); import rvt_diff
import re
def _vec(v):
    return [float(x) for x in v] if isinstance(v, (list, tuple)) else [float(x) for x in re.findall(r'-?\d+\.?\d*(?:[eE][-+]?\d+)?', str(v))][:3]
def fields(path):
    m = wledit.Editor(path).m; pn, q, log = rvt_diff.field_log(m, EID); d = {}
    for k, v, s, e in log:
        if k in ('GLine.m_origin#1', 'GLine.m_dirVec#1') or k.startswith('Plane.m_origin#') or k.startswith('Plane.m_xVec#'): d[k] = _vec(v)
    return d
def check(a, b):
    th = math.radians(DEG); c, s = math.cos(th), math.sin(th)
    for k in a:
        if 'dirVec' in k or 'xVec' in k:
            x, y = a[k][:2]; ex = (c * x - s * y, s * x + c * y)
            assert math.dist(ex, b[k][:2]) < 1e-9, (k, 'vector not rotated', a[k], b[k])
    gl = b['GLine.m_origin#1']; p1 = b['Plane.m_origin#1']; d = b['GLine.m_dirVec#1']; ga = a['GLine.m_origin#1']; pa = a['Plane.m_origin#1']
    t0 = math.hypot(pa[0] - ga[0], pa[1] - ga[1]); t1 = math.hypot(p1[0] - gl[0], p1[1] - gl[1])
    assert abs(t0 - t1) < 1e-6, ('line origin / plane origin distance changed (rotation about a common pivot)', t0, t1)
    assert abs((p1[0] - gl[0]) * d[1] - (p1[1] - gl[1]) * d[0]) < 1e-6, 'plane origin not on the line through GLine.m_origin along the rotated direction'
out = os.environ.get('RVT_WALLROT_OUT')
if not out:
    out = tempfile.mkdtemp() + '/t.rvt'; env = dict(os.environ, RVTBALLET_ENABLE_WALLROTATE='1', RVTBALLET_MOVE_ANY='1')
    r = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', SRC, '--rotate', str(EID), str(DEG), '-o', out], capture_output=True, text=True, timeout=3400, env=env)
    assert os.path.exists(out), (r.stdout + r.stderr)[-500:]
check(fields(SRC), fields(out)); print('OK wall rotate keeps GLine / Plane fields consistent')
