"""c1x-rvtlink: deleting an RvtLinkInstance must be refused even with RVTBALLET_ENABLE_DELETE=1 (a Revit-made delete removes 28 records and rewrites ~190 referencing ones, SketchPlane refs need plane resolution; a plain record delete leaves dangling refs). Fails if 'RvtLinkInstance' is ever added to the verified delete classes without that work. Autodesk 2024 HVAC sample."""
import os, sys, glob, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import save, edit
import rvt_params
c = glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt'))
if not c or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 'src.rvt'); shutil.copy(c[0], src); d = save.SaveSessions().doc('m', src)
    ids = [e for e, v in rvt_params.params(src).items() if isinstance(v, dict) and v.get('class') == 'RvtLinkInstance'][:1]
    assert ids, 'no RvtLinkInstance in sample'
    try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': ids[0]})]); raise SystemExit('FAIL: link instance %s deleted' % ids[0])
    except edit.EditError as e: assert 'only enabled' in str(e) and 'RvtLinkInstance' in str(e), str(e)
    print('OK link instance delete refused')
finally: shutil.rmtree(_T, ignore_errors=True)
