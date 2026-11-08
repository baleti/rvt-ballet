"""c1x-rvtdel: with the default gate (no RVTBALLET_DELETE_ANY) deleting a class that is not VM verified (FillPatternElem, GStyleElem: ~136k dangling mentions when forced) must be refused with EditError, nothing changed. Autodesk 2024 Construction template."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    pr = rvt_params.params(src); n = 0
    for want in ('FillPatternElem', 'GStyleElem'):
        ids = [e for e, v in pr.items() if isinstance(v, dict) and v.get('class') == want][:1]
        assert ids, 'no %s in sample' % want
        try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': ids[0]})]); raise SystemExit('FAIL: %s %s deleted under default gate' % (want, ids[0]))
        except edit.EditError as e: assert 'only enabled' in str(e), str(e); n += 1
    print('OK default gate refused', n)
finally: shutil.rmtree(_T, ignore_errors=True)
