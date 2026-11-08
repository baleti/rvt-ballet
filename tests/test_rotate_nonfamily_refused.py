"""Rotate of a wall / grid / level is refused when the edit is added (not at save time), recorded edits stay empty. Autodesk 2024 Snowdon samples; skipped if absent."""
import os, sys, tempfile
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
C = os.path.expanduser('~/rvt-research/corpus/2024/')
cases = [(C + '43_Snowdon_Towers_Sample_Structural.rvt', 585072), (C + '42_Snowdon_Towers_Sample_HVAC.rvt', 1363057), (C + '42_Snowdon_Towers_Sample_HVAC.rvt', 9946)]
if not all(os.path.exists(f) for f, _ in cases): print('skip: samples absent'); sys.exit(0)
from rvtballet import save, edit
save._import()
for f, eid in cases:
    ss = save.SaveSessions(); ss.doc('m', f)
    try: save.add_edit(ss, 'm', f, {'op': 'rotate', 'eid': eid, 'deg': 30.0}); raise SystemExit('FAIL rotate accepted %d' % eid)
    except edit.EditError as e: print('refused', eid, str(e)[:70])
    assert not ss.edits('m').ops
print('OK')
