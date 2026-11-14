"""c1x-rvtlink item 7 (offline witness): lab Edit.add_copy of an existing RvtLinkInstance (HVAC 2024 sample) must add exactly one element record and change/remove none. NOT a VM verdict (the VM verdict is FAIL: Revit 2024 CorruptModelException on this exact output, 2026-11-14) and NOT wired into rvtballet (link add stays unavailable until the Revit VM opens it clean). Fails if the clone mutates or drops any other record."""
import os, sys, glob, shutil, tempfile
for p in (os.path.expanduser('~/rvt-research/edit-lab'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
c = glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt'))
try:
    import rvtedit
    from savegate import rvt_elements as R
except Exception as e: print('skip', e); sys.exit(0)
if not c: print('skip'); sys.exit(0)
T = tempfile.mkdtemp()
try:
    a = R.elements(open(c[0], 'rb').read())
    lid = [e for e, v in a.items() if v.startswith('RvtLinkInstance|')][0]
    E = rvtedit.Edit(c[0]); new = E.add_copy(lid, 5.0, 0.0); out = os.path.join(T, 'o.rvt'); E.save(out)
    b = R.elements(open(out, 'rb').read())
    assert [e for e in b if e not in a] == [new], 'new records: %s' % [e for e in b if e not in a]
    assert not [e for e in a if e not in b], 'records dropped'
    assert not [e for e in a if a[e] != b[e]], 'records changed'
    print('OK link instance clone adds 1 record, 0 changed (offline only)')
finally: shutil.rmtree(T, ignore_errors=True)
