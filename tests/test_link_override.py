"""c9x-rvtlink: set_link_override (opt-in) on the Autodesk 2024 HVAC sample pair made in the Revit 2024 VM (ov_A = host re-saved, ov_B = the same plus View.SetLinkOverrides(link type 1363937, ByLinkView, linked view 124186) on view 1363877).
Our output for A must equal Revit's B in every record of every chain (byte-identical), differ from A in exactly the view record, refuse an already-filled view, and refuse the op without the opt-in. Local-only files: skips when absent."""
import os, sys
D = os.path.expanduser('~/c9x-rvtlink-work/ovrp2024'); A = D + '/ov_A.rvt'; B = D + '/ov_B.rvt'
if not (os.path.exists(A) and os.path.exists(B)): print('SKIP: pair files not present'); sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.expanduser('~/src/rvt-extract')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit
import rvt2text as T, olefile
from rvtx import partition as PT
def recs(buf):
    import tempfile
    f = tempfile.mktemp(suffix='.rvt'); open(f, 'wb').write(buf)
    try:
        o = olefile.OleFileIO(f); pn = [y for y in ['/'.join(e) for e in o.listdir(streams=True)] if y.startswith('Partitions/')][0]
        p = PT.parse_joined(T.joined(o.openstream(pn).read()), 8); return {ch: {x[0]: x[1] for x in p[0][ch]} for ch in 'HRZ'}
    finally: os.remove(f)
ab = open(A, 'rb').read(); OP = {'op': 'set_link_override', 'eid': 1363877, 'link': 1363937, 'linked_view': 124186}
os.environ.pop('RVTBALLET_ENABLE_LINKOVERRIDE', None)
try: edit.validate_op(OP); raise SystemExit('FAIL: op accepted without the opt-in')
except edit.EditError: pass
os.environ['RVTBALLET_ENABLE_LINKOVERRIDE'] = '1'
nb, _ = edit.apply_full(ab, [OP])
ra, rb, rn = recs(ab), recs(open(B, 'rb').read()), recs(nb)
for ch in 'HRZ':
    assert rn[ch].keys() == rb[ch].keys() == ra[ch].keys(), ch
    assert all(rn[ch][i] == rb[ch][i] for i in rn[ch]), ch + ': differs from the Revit-made record'
changed = [i for ch in 'HRZ' for i in ra[ch] if ra[ch][i] != rn[ch][i]]; assert changed == [1363877], changed
assert len(rn['R'][1363877]) - len(ra['R'][1363877]) == 138
try: edit.apply_full(nb, [OP]); raise SystemExit('FAIL: second override on a filled map accepted')
except edit.EditError: pass
print('PASS link_override: byte-identical to the Revit-made record, only view 1363877 changed (+138 B), opt-in and filled-map refusals')
