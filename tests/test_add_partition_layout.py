"""Add-wall on a Revit-SAVED file must keep Revit's partition member layout (c4x-rvtdiff 2026-11-09).
Root cause of 'CorruptModelException on add to a Revit-saved file' (2024 and 2026): rvtgen insert_at() cut NEW tiny members (+2 members, first member
x1=1/raw 225) instead of growing the existing member and carrying the overflow forward as Revit does. RVTGEN_INPLACE=1 inserts in place. VM verdict: the in-place
output opens in Revit 2024 (cmp 0/0, no dialog), the default one is refused. Needs a local Revit-saved Autodesk-sample base (~/c2x-diff/c3xlvl/base.rvt); skipped otherwise."""
import os, struct, subprocess, sys, tempfile
import pytest
BASE = os.path.expanduser('~/c2x-diff/c3xlvl/base.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_aw_auto.py')
pytestmark = pytest.mark.skipif(not os.path.exists(BASE), reason='no Revit-saved 2024 sample base on this machine')
for p in ('~/rvt-research/write-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
def _layout(path):
    import cfb, rvtw, wlpart
    c = cfb.CFB(open(path, 'rb').read()); n = [k for k in c.streams() if k.startswith('Partitions/')][0]
    p = wlpart.Partition(rvtw.Stream(c.streams()[n].data))
    return p.n, len(p.mem[0]['raw']), struct.unpack_from('<I', bytes(p.hdr), 24)[0]
def _add(out, inplace):
    env = dict(os.environ); env.pop('RVTGEN_INPLACE', None)
    if inplace: env['RVTGEN_INPLACE'] = '1'
    r = subprocess.run([sys.executable, TOOL, BASE, out, '0', '0', '20', '0', '10', '2024'], env=env, capture_output=True, text=True, timeout=1500)
    assert r.returncode == 0, r.stdout[-300:] + r.stderr[-300:]
def test_inplace_add_keeps_revit_layout_default_does_not():
    with tempfile.TemporaryDirectory() as d:
        n0, raw0, x0 = _layout(BASE)
        _add(os.path.join(d, 'ip.rvt'), True); n1, raw1, x1 = _layout(os.path.join(d, 'ip.rvt'))
        assert n1 <= n0 + 1, 'in-place add must not create new members (Revit adds at most one): %d -> %d' % (n0, n1)
        assert raw1 > 100000 and x1 >= x0 - 1, 'first member must stay a full member (raw %d, x1 %d, base x1 %d)' % (raw1, x1, x0)
        _add(os.path.join(d, 'plain.rvt'), False); n2, raw2, x2 = _layout(os.path.join(d, 'plain.rvt'))
        assert n2 >= n0 + 2 and raw2 < 1000, 'documents the failing layout (the Revit-refused one): %d members, first raw %d' % (n2, raw2)
