"""c7x-rvtmatrix: delete of a project-wide singleton (AllProjectRevisions, VM evidence: Revit 'Repair Missing Unique Elements') is refused when the edit is added; a model element (neighbour test target of test_save_delete) is still accepted."""
import os, sys, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1', RVTBALLET_DELETE_ANY='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit
save._import()
ss = save.SaveSessions(); ss.doc('m', RTE)
try: save.add_edit(ss, 'm', RTE, {'op': 'delete', 'eid': 29344}); raise SystemExit('ESCAPE: AllProjectRevisions delete accepted')
except edit.EditError as e: print('refused:', str(e)[:90])
assert not ss.edits('m').ops
print('regex check', [bool(edit.UNIQUE_CLASS.search(c)) for c in ('AllProjectRevisions', 'AutoJoinTracker', 'AreaSettingsElem', 'KeynoteTable', 'SWall', 'Floor', 'CategoryElem', 'BasePoint', 'DBViewPlan', 'FamilyInstance')])
assert not any(edit.UNIQUE_CLASS.search(c) for c in ('SWall', 'Floor', 'CategoryElem', 'BasePoint', 'DBViewPlan', 'FamilyInstance', 'BrowserOrganization'))
os.environ.pop('RVTBALLET_DELETE_ANY')      # allowlist mode: a model class without a VM verdict is refused, a verified one is accepted at add_edit time
ss2 = save.SaveSessions(); ss2.doc('m2', RTE)
try: save.add_edit(ss2, 'm2', RTE, {'op': 'delete', 'eid': 301568}); raise SystemExit('ESCAPE: unverified class delete accepted')
except edit.EditError as e: print('refused:', str(e)[:70])
print('OK')
