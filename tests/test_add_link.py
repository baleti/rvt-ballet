"""# 2026-11-14: passes --same-file because rvt_add_link now refuses a same-file clone by default (VM: Revit 2024 fails to load BOTH link types when the linked file is present); this test checks the record structure only, never open that output in Revit. c9x-rvtlink: tools/rvt_add_link.py on the Autodesk 2024 Snowdon HVAC sample (single partition): a duplicated link is exactly 3 new records (RvtLinkSymbol, RvtLinkInstance, detail), no existing record changes, the source is untouched, and the new headers have an EMPTY deletion list (193/183/175 B like Revit-made adds; the first version copied the source's 10/7/2 dependents entries = 413/337/219 B, which fails this test).
Revit 2024 VM verdict for the same output: audit open ok, API link types 6->7 and instances 6->7 (ledger 'add Revit link'). Skips when the sample is absent (local only)."""
import os, sys, subprocess, tempfile, hashlib, struct
SRC = next((p for p in (os.path.expanduser('~/c5x-link/w/hvac24.rvt'), os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')) if os.path.exists(p)), None)
if not SRC: print('SKIP: HVAC 2024 sample not present'); sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.expanduser('~/src/rvt-extract')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt2text as T, olefile
from rvtx import partition as PT
def load(p):
    o = olefile.OleFileIO(p); pn = [y for y in ['/'.join(e) for e in o.listdir(streams=True)] if y.startswith('Partitions/')][0]
    j = T.joined(o.openstream(pn).read())
    try: return PT.parse_joined(j, 8)
    except Exception: return PT.parse_joined(j, 4)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = tempfile.mkdtemp(); out = d + '/out.rvt'; h0 = sha(SRC)
r = subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'rvt_add_link.py'), SRC, out, '--src', '1363937', '--same-file'], capture_output=True, text=True)
assert r.returncode == 0 and os.path.exists(out), (r.stdout[-300:], r.stderr[-300:])
assert sha(SRC) == h0, 'source modified'
A, B = load(SRC), load(out)
new_ids = None
for ch in 'HRZ':
    a = {x[0]: x[1] for x in A[0][ch]}; b = {x[0]: x[1] for x in B[0][ch]}
    assert not (set(a) - set(b)), ch + ': records removed'
    assert not [i for i in a if a[i] != b[i]], ch + ': an existing record changed'
    added = sorted(set(b) - set(a)); assert len(added) == 3 and added[1] == added[0] + 1 and added[2] == added[0] + 2, (ch, added)
    new_ids = new_ids or added; assert added == new_ids
H = {x[0]: x[1] for x in B[0]['H']}; R = {x[0]: x[1] for x in B[0]['R']}
assert [len(H[i]) for i in new_ids] == [193, 183, 175], [len(H[i]) for i in new_ids]      # empty deletion lists (N=0)
assert [struct.unpack_from('<H', R[i], 0)[0] for i in new_ids] == [3650, 3643, 942], 'record tags'
print('PASS add_link: 3 records', new_ids, 'headers', [len(H[i]) for i in new_ids])
