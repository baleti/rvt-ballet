"""c7x-rvtread 115d: change_type and set_type_num (each changes only the element partition: HVAC 2024, Partitions/21) now get manifest frozen_streams from save._pending.
Run: python3 tests/test_save_frozen_changetype.py (skips without the Autodesk 2024 HVAC sample)"""
import os, sys, types
os.environ.update(RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_CHANGETYPE='1', RVTBALLET_ENABLE_TYPEPARAM='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/src/savegate')]
dd = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(dd, n) for n in os.listdir(dd) if n.endswith('HVAC.rvt')] if os.path.isdir(dd) else []
if not F: print('skip'); sys.exit(0)
from rvtballet import save, edit
buf = open(F[0], 'rb').read()
for op in ({'op': 'change_type', 'eid': 1379181, 'type_eid': 1530089}, {'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.1}):
    e = edit.Edits(); e.ops = [edit.validate_op(op)]
    ss = types.SimpleNamespace(edits=lambda mid, e=e: e, applied={}, derived={})
    nb, mf = save._pending(ss, 'm', types.SimpleNamespace(buf=buf, version='2024'), None, None)
    assert mf.get('frozen_streams') is True and mf.get('dirty_members'), (op['op'], sorted(mf))
    print(op['op'], 'frozen_streams set, dirty_members', list(mf['dirty_members']))
print('OK')
