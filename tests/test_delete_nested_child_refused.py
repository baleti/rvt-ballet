"""c1x-rvtdel: Snowdon Facades 2024 FamilyInstance 593274 is a nested child listed in parent 593273's FamilyInstance.m_subInstTable. A delete of the child alone would leave the parent's raw sub list dangling (invisible to parameter-level checks), so membership must report 'nested in 1 parent(s)' and risky_membership must keep it for delete ops only (parameter edits and moves of a nested child stay allowed)."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import save
if not os.path.exists(SRC): print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); buf = open(src, 'rb').read()
    m = save.membership(buf, {593274, 593273, 593193})
    assert 'nested in 1 parent(s): 593273' in m.get(593274, []), m
    assert not any('nested' in w for w in m.get(593273, [])), m
    assert save.risky_membership(m, [{'op': 'delete', 'eid': 593274}]).get(593274), 'delete of nested child not flagged'
    assert not save.risky_membership(m, [{'op': 'set_str', 'eid': 593274}]).get(593274), 'param edit wrongly flagged'
    from rvtballet import edit
    d = save.SaveSessions().doc('m', src); nb, dl = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': 593274})])
    try: save._readback(d.buf, nb, [{'op': 'delete', 'eid': 593274}]); raise SystemExit('FAIL nested child delete accepted by readback gate')
    except SystemExit: raise
    except Exception as ex: assert 'nested sub-component' in str(ex), ex
    print('PASS nested child flagged for delete only:', m[593274])
finally: shutil.rmtree(_T, ignore_errors=True)
