"""c3x-rvtdel: the delete whitelist is VM-verified on 2024 (2026 only SWall/FamilyInstance/Floor). A 2025 file must refuse a FamilyInstance delete (production gate accepted it before the year gate). Autodesk 2025 Structural sample."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2025/49_Snowdon_Towers_Sample_Structural.rvt')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    ids = [e for e, v in rvt_params.params(src).items() if isinstance(v, dict) and v.get('class') == 'FamilyInstance'][:3]
    assert ids, 'no FamilyInstance'
    for i in ids:
        try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': i})]); raise SystemExit('FAIL: 2025 FamilyInstance %s deleted' % i)
        except edit.EditError as e: assert 'not VM-verified on Revit 2025' in str(e), str(e)
    print('OK 2025 refused', len(ids))
finally: shutil.rmtree(_T, ignore_errors=True)
