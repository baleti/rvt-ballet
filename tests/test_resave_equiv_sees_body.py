"""rvt_resave_equiv must call two files DIFFERENT when a record body differs even though rvt_diff's header/record walker lists no body change
(2025 Snowdon HVAC: Mark of 1365188 is a 4096-char string in one file and the original in the other; the old tool answered EQUIVALENT under --tolerate-header-only). Local files only, skipped when absent."""
import os, sys, subprocess
A = os.path.expanduser('~/c2x-diff/c4x_rsl_ours/base.rvt'); B = os.path.expanduser('~/c2x-diff/c4x_rsl_revit/base.rvt')
if not (os.path.exists(A) and os.path.exists(B)): print('skip: local pair absent'); sys.exit(0)
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = subprocess.run([sys.executable, R + '/tools/rvt_resave_equiv.py', A, B, '--tolerate-header-only'], capture_output=True, text=True, timeout=1500)
print(p.stdout[-400:])
assert p.returncode == 1 and 'DIFFERENT' in p.stdout and '1365188' in p.stdout, (p.returncode, p.stdout[-300:])
print('ok: body difference detected')
# second case: door-delete pair differs only by VWall.m_wallRunTimeData: DIFFERENT by default, EQUIVALENT with the named opt-in rule
A2 = os.path.expanduser('~/c2x-diff/c4x_rs_ddours/base.rte'); B2 = os.path.expanduser('~/c2x-diff/c4x_rs_ddrevit/base.rte')
if os.path.exists(A2) and os.path.exists(B2):
    q = lambda *x: subprocess.run([sys.executable, R + '/tools/rvt_resave_equiv.py', A2, B2, *x], capture_output=True, text=True, timeout=1500)
    assert q('--tolerate-header-only').returncode == 1
    assert q('--tolerate-header-only', '--tolerate-wall-runtime').returncode == 0
    print('ok: wall runtime flag rule')
# third case: rotate-90 pair: 1-ulp float noise on 301592 disappears with --float-tol, the empty GridsForColumn entry of 76368 remains a difference
A3 = os.path.expanduser('~/c2x-diff/c4x_rs_rotours/base.rte'); B3 = os.path.expanduser('~/c2x-diff/c4x_rs_rotrevit/base.rte')
if os.path.exists(A3) and os.path.exists(B3):
    q3 = lambda *x: subprocess.run([sys.executable, R + '/tools/rvt_resave_equiv.py', A3, B3, '--tolerate-header-only', *x], capture_output=True, text=True, timeout=1500)
    o1 = q3(); assert o1.returncode == 1 and '301592' in o1.stdout and '76368' in o1.stdout
    o2 = q3('--float-tol=1e-9'); assert o2.returncode == 1 and '76368' in o2.stdout and 'body changes [76368]' in o2.stdout, o2.stdout[-200:]
    print('ok: float tolerance')
