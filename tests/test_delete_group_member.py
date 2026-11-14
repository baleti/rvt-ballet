"""c1x-rvtdel severity-1 escape: SAVE AS delete of a group member (HVAC 2024 element 1421734, member of ElementGroup 1421744) was accepted and left a stale member id in the group. Must be refused by save._readback; a plain non-member delete is unaffected (covered by the other delete tests)."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    ops = [edit.validate_op({'op': 'delete', 'eid': 1421734})]
    try: nb, dl = edit.apply_full(d.buf, ops)
    except edit.EditError as e: print('OK refused earlier by the edit layer:', str(e)[:100]); sys.exit(0)      # the view-owned guard (added after this test) now stops it before the readback; still a refusal
    try: save._readback(d.buf, nb, ops); raise SystemExit('FAIL: group member delete accepted')
    except Exception as e:
        if isinstance(e, SystemExit): raise
        assert 'group' in str(e), str(e); print('OK group member delete refused:', str(e)[:100])
finally: shutil.rmtree(_T, ignore_errors=True)
