"""c1x-rvtdel: a delete must leave every surviving element's parameters unchanged. Clean delete passes save._readback; if a surviving element reads back different (simulated by patching the reader for the output), _readback must refuse. Autodesk 2024 Construction template."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte'); EID = 5499
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
    ops = [edit.validate_op({'op': 'delete', 'eid': EID})]
    nb, dl = edit.apply_full(d.buf, ops); save._readback(d.buf, nb, ops); print('clean delete readback OK', len(dl))
    real = save._read_params; a = real(d.buf)
    victim = next(e for e, v in a.items() if e not in dl and isinstance(v, dict) and (v.get('params', v)))
    def fake(buf):
        r = real(buf)
        if buf is nb:
            r = dict(r); v = dict(r[victim]); pp = dict(v.get('params', v)); k = next(iter(pp)); pp[k] = 'TAMPERED'
            r[victim] = dict(v, params=pp) if 'params' in v else pp
        return r
    save._read_params = fake
    try: save._readback(d.buf, nb, ops); raise SystemExit('FAIL: survivor drift accepted')
    except save.sg.VerifyFailed if hasattr(save, 'sg') else Exception as e: assert 'surviving' in str(e), str(e); print('drift refused:', str(e)[:90])

    # dangling reference: a survivor that newly mentions a removed id must be refused
    gone_id = EID
    def fake2(buf):
        r = real(buf)
        if buf is nb:
            r = dict(r); v = dict(r[victim]); pp = dict(v.get('params', v)); pp['Zz Ref'] = '{x: %d, y: 1}' % gone_id
            r[victim] = dict(v, params=pp) if 'params' in v else pp
        return r
    save._read_params = real; save._read_params = fake2
    try: save._readback(d.buf, nb, ops); raise SystemExit('FAIL: dangling reference accepted')
    except Exception as e:
        if isinstance(e, SystemExit): raise
        assert 'dangling' in str(e), str(e); print('dangling refused')
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
