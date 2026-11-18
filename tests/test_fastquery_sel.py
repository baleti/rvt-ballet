"""fastquery SEL locator (c5-c7 port): outputs identical with SEL on and off on PUBLIC Autodesk samples (skipped when the corpus is absent);
a query whose winners are all outside the ElemTable / absent (walls on an HVAC model) must not crash; SEL is never used by the scan commands;
the C helper refuses another build number. Run: python -m pytest tests/test_fastquery_sel.py"""
import glob, os, subprocess, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.expanduser('~/rvt-research/corpus')
YEARS = {'2022': '32_Arch_Link_Model.rvt', '2024': '43_Snowdon_Towers_Sample_Structural.rvt', '2025': '48_Snowdon_Towers_Sample_HVAC.rvt',
         '2026': '55_Snowdon_Towers_Sample_Structural.rvt'}
CMDS = ('walls', 'doors', 'rooms', 'sheets', 'wall-types', 'levels', 'counts')


def run(cmd, path, **env):
    e = dict(os.environ, **env)
    r = subprocess.run([sys.executable, '-m', 'rvtballet.fastquery', cmd, path, '--json'], cwd=ROOT, env=e, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout, r.stderr


def f(y):
    p = os.path.join(CORPUS, y, YEARS[y])
    if not os.path.exists(p): pytest.skip('public corpus missing')
    return p


@pytest.mark.parametrize('year', sorted(YEARS))
def test_sel_on_equals_off(year):
    p = f(year)
    for c in CMDS:
        off = run(c, p, RVT_Q_SEL='0', RVT_Q_SEL_AUTO='0', RVT_Q_HDR101='0')
        on = run(c, p, RVT_Q_SEL='1')               # forced on; the scan commands ignore it, the years without 101/w1 framing fall back to the full pass
        assert off[0] == on[0] and off[1] == on[1], (year, c)


def test_all_winners_filtered_no_crash():
    """walls on the 2024 HVAC sample: every locator winner is dropped by SEL_ET -> empty winner list (sel_ was [-1]: IndexError)"""
    p = f('2024'); hv = os.path.join(CORPUS, '2024', '42_Snowdon_Towers_Sample_HVAC.rvt')
    if not os.path.exists(hv): pytest.skip('sample missing')
    rc, out, err = run('walls', hv, RVT_Q_SEL='1')
    assert rc == 0 and out.strip() == '[]', (rc, out[:200], err[-300:])


def test_helper_abi_number():
    import ctypes
    so = os.path.join(ROOT, 'rvtballet', '_rvtframe.so')
    if not os.path.exists(so): pytest.skip('helper not built')
    L = ctypes.CDLL(so); L.rvtframe_abi.restype = ctypes.c_int64
    assert L.rvtframe_abi() == 7
