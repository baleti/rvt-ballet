"""c5x-rvtmatrix: a LinearDimString move is refused when the edit is added (Revit 2024 VM: dimension segment origins unchanged after the record move, so the viewer must not promise it). Autodesk 2024 Snowdon Plumbing sample; skipped if absent."""
import os, sys, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
F = os.path.expanduser('~/rvt-research/corpus/2024/45_Snowdon_Towers_Sample_Plumbing.rvt')
if not os.path.exists(F): print('skip: sample absent'); sys.exit(0)
import rvt_geometry as G
from rvtballet import save, edit
save._import()
ix = G.file_geometry_index(F)
dim = next((e for e, v in ix.items() if str(v) == 'LinearDimString'), None)
other = next((e for e, v in ix.items() if str(v) == 'FamilyInstance'), None)
assert dim, 'no dimension in sample'
ss = save.SaveSessions(); ss.doc('m', F)
try: save.add_edit(ss, 'm', F, {'op': 'move', 'eid': dim, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); raise SystemExit('FAIL: dimension move accepted')
except edit.EditError as e: print('refused:', str(e)[:80])
try: save.add_edits(ss, 'm', F, [{'op': 'move', 'eid': dim, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}]); raise SystemExit('FAIL: dimension move accepted (batch)')
except edit.EditError as e: print('refused batch')
assert not ss.edits('m').ops
print('OK')
