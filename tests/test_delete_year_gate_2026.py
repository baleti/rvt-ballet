"""c3x-rvtdel: year gate on 2026 (Snowdon HVAC): a TextNote delete (whitelisted for 2024 only) must be refused with the year message; a FamilyInstance delete must NOT be refused by the year gate (any other refusal reason is fine)."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2026/54_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src); pr = rvt_params.params(src)
    pick = lambda c: [e for e, v in pr.items() if isinstance(v, dict) and v.get('class') == c][:1]
    for c, must_year_refuse in (('TextNote', True), ('FamilyInstance', False)):
        ids = pick(c)
        if not ids: print('no', c); continue
        try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': ids[0]})]); msg = ''
        except edit.EditError as e: msg = str(e)
        assert ('not VM-verified on Revit 2026' in msg) == must_year_refuse, (c, msg[:200])
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
